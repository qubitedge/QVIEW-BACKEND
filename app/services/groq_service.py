import os
import json
import time
import re
import google.generativeai as genai
from dotenv import load_dotenv
from app.models.schemas import ResumeAnalysis, QuestionModel, EvaluationResult

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Terminal Logger
# ─────────────────────────────────────────────────────────────
COLORS = {
    "INFO":   "\033[94m",   # Blue
    "OK":     "\033[92m",   # Green
    "WARN":   "\033[93m",   # Yellow
    "ERROR":  "\033[91m",   # Red
    "GEMINI": "\033[95m",   # Magenta
    "RESUME": "\033[96m",   # Cyan
    "RESET":  "\033[0m",
}

def log(tag: str, message: str, level: str = "INFO"):
    color = COLORS.get(level, "")
    reset = COLORS["RESET"]
    label = f"[{level}]".ljust(7)
    print(f"{color}{label}{reset} [{tag}] {message}", flush=True)

def log_separator(title: str = ""):
    line = "─" * 60
    if title:
        print(f"\033[90m┌{line}┐\033[0m", flush=True)
        print(f"\033[90m│\033[0m  \033[1m{title}\033[0m", flush=True)
        print(f"\033[90m└{line}┘\033[0m", flush=True)
    else:
        print(f"\033[90m{line}\033[0m", flush=True)


# ─────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────
class GroqService:
    def __init__(self):
        log_separator("GroqService Initialization")
        log("INIT", "Starting up Gemini-backed interview service...")

        log("INIT", "⚠️  NOTE: google.generativeai is DEPRECATED.", "WARN")
        log("INIT", "   → Run: pip install google-genai --break-system-packages", "WARN")
        log("INIT", "   → Then refactor imports to: from google import genai", "WARN")
        log_separator()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            log("INIT", "GEMINI_API_KEY not found in .env file!", "ERROR")
            log("INIT", "Add: GEMINI_API_KEY=your_key_here  to your .env", "WARN")
            self.client_ready = False
        else:
            masked = api_key[:8] + "..." + api_key[-4:]
            log("INIT", f"GEMINI_API_KEY loaded → {masked}", "OK")
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                log("INIT", "Gemini model ready: gemini-2.5-flash", "OK")
                self.client_ready = True
            except Exception as e:
                log("INIT", f"Gemini client init FAILED: {e}", "ERROR")
                self.client_ready = False

        status = "✅ LIVE (Gemini API active)" if self.client_ready else "⚠️  FALLBACK (no API)"
        log("INIT", f"Service status: {status}", "OK" if self.client_ready else "WARN")
        log_separator()

    def _call_gemini(self, prompt: str, tag: str, json_mode: bool = False) -> str | None:
        if not self.client_ready:
            log(tag, "SKIPPED — Gemini client not ready", "WARN")
            return None

        log("GEMINI", f"[{tag}] → Sending request...", "GEMINI")
        start = time.time()
        try:
            if json_mode:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json"
                    ),
                )
            else:
                response = self.model.generate_content(prompt)

            elapsed = round(time.time() - start, 2)
            text = response.text.strip()
            words = len(text.split())
            log("GEMINI", f"[{tag}] ← OK in {elapsed}s (~{words} words)", "OK")
            return text
        except Exception as e:
            elapsed = round(time.time() - start, 2)
            log("GEMINI", f"[{tag}] ✗ FAILED after {elapsed}s → {e}", "ERROR")
            return None

    def introduce_candidate(self, candidate_name: str) -> str:
        log("INTRO", f"Generating intro for: '{candidate_name}'")
        prompt = f"""You are a warm, professional AI interviewer opening a technical interview.
The candidate's name is: {candidate_name}
- Greet them by name in a friendly but professional tone.
- Briefly introduce yourself as their AI interviewer for today.
- Keep under 4 sentences.
- End with exactly: "Could you start by telling me a little about yourself?"
Return ONLY the spoken interviewer message.
"""
        result = self._call_gemini(prompt, tag="INTRO")
        if result:
            log("INTRO", "✅ Intro generated", "OK")
            return result
        log("INTRO", "Using fallback intro", "WARN")
        return f"Hello {candidate_name}! I'm your AI interviewer for today. Could you start by telling me a little about yourself?"

    def analyze_resume(self, text: str) -> ResumeAnalysis:
        log_separator("Resume Analysis")

        if not text.strip():
            log("RESUME", "Empty resume text", "ERROR")
            return ResumeAnalysis(
                skills=[],
                projects=[],
                experience_years=0,
                level="junior"
            )

        prompt = f"""
You are an elite ATS + AI recruiter system.

Analyze this resume carefully.

Extract:
1. Skills
2. Projects
3. Experience years
4. Candidate seniority level
5. Project responsibilities
6. Technologies actually used

IMPORTANT:
- ONLY use technologies explicitly mentioned
- DO NOT hallucinate
- DO NOT invent experience
- Infer experience level carefully

Return ONLY valid JSON.

FORMAT:
{{
  "skills": ["Python", "FastAPI"],
  "projects": [
    {{
      "name": "AI Interview System",
      "tech_stack": ["React", "FastAPI", "Gemini"],
      "description": "...",
      "candidate_role": "...",
      "responsibilities": [],
      "features_built": [],
      "deployment": "",
      "architecture": "",
      "challenges": [],
      "team_size": "",
      "impact": ""
    }}
  ],
  "experience_years": 2,
  "level": "junior"
}}

RESUME:
{text[:12000]}
"""

        result = self._call_gemini(
            prompt,
            tag="RESUME_ANALYSIS",
            json_mode=True
        )

        if result:
            try:
                parsed = json.loads(result)

                analysis = ResumeAnalysis(
                    skills=parsed.get("skills", []),
                    projects=parsed.get("projects", []),
                    experience_years=parsed.get("experience_years", 0),
                    level=parsed.get("level", "junior")
                )

                log("RESUME", f"Skills detected: {analysis.skills}", "OK")
                log("RESUME", f"Projects found: {len(analysis.projects)}", "OK")

                return analysis

            except Exception as e:
                log("RESUME", f"Resume parse failed: {e}", "ERROR")

        return ResumeAnalysis(
            skills=[],
            projects=[],
            experience_years=0,
            level="junior"
        )

    def generate_questions(
        self,
        profile: dict,
        count: int = 3,
        adaptive: bool = False,
        previous_answers: list = None,
        weak_topics: list = None,
        strong_topics: list = None,
        current_difficulty: str = "medium"
    ) -> list[QuestionModel]:
        log_separator("Question Generation")

        candidate_name = profile.get("candidate_name", "Candidate")
        topic          = profile.get("topic", profile.get("target_role", "Software Engineering"))
        experience     = profile.get("experience_level", "Junior")
        resume_text    = profile.get("resume_text", "").strip()

        log("QUESTIONS", f"Candidate   : {candidate_name}")
        log("QUESTIONS", f"Role/Topic  : {topic}")
        log("QUESTIONS", f"Experience  : {experience}")

        # Step 1: Intro
        log("QUESTIONS", "Step 1 → Generating intro question...")
        intro_text = self.introduce_candidate(candidate_name)
        intro_question = QuestionModel(
            text=intro_text, type="behavioral", difficulty="easy", section="Introduction"
        )
        log("QUESTIONS", f"  ✅ Intro: \"{intro_text[:80]}...\"", "OK")

        # Step 2: Resume context
        log("QUESTIONS", "Step 2 → Building resume context...")
        if resume_text:
            char_count = len(resume_text)
            word_count = len(resume_text.split())
            log("RESUME", f"Resume: {char_count} chars / ~{word_count} words", "OK")

            if word_count < 50:
                log("RESUME", f"⚠️  Very short ({word_count} words) — extraction may have failed!", "WARN")
            else:
                log("RESUME", f"Preview: {resume_text[:300]}", "INFO")

            truncated = resume_text[:4000]
            if char_count > 4000:
                log("RESUME", f"Truncated {char_count} → 4000 chars", "WARN")

            context_str = (
                f"Target Role: {profile.get('target_role', topic)}\n\n"
                f"RESUME CONTENT:\n{truncated}\n\n"
                f"INSTRUCTION: Read the resume carefully. Identify specific technologies, "
                f"projects, companies, and domains the candidate has worked with. "
                f"Generate questions DIRECTLY referencing these specifics. "
                f"Do NOT ask generic questions unrelated to their actual experience."
            )
            log("QUESTIONS", "Resume context ready — questions will be resume-specific", "OK")
        else:
            log("RESUME", "No resume — using topic-based generation", "WARN")
            context_str = f"Topic: {topic}\nNo resume. Generate questions for a {experience}-level {topic} interview."

        # Step 3: Generate questions
        seed = int(time.time() * 1000) % 10000
        log("QUESTIONS", f"Step 3 → Generating initial adaptive interview questions (seed={seed})...")

        prompt = f"""You are an elite AI technical interviewer at top product companies.

{context_str}
Experience Level: {experience}
Seed: {seed}

Generate EXACTLY 5 initial interview questions.

STRUCTURE:
1 Introduction follow-up
3 Conceptual/Experience questions
1 System Architecture/Design question

IMPORTANT:
The remaining interview questions will be dynamically generated later
based on candidate performance.

RULES:
- ONLY reference technologies explicitly present in resume/profile
- NO hallucinated frameworks
- Questions must feel like real FAANG interviews
- Ask discussion-focused questions based on real-world experience
- Prefer project-based questioning
- Vary with the seed to prevent repetition.
- NO coding snippet challenges or implementation questions.

IMPORTANT RESTRICTIONS:
- ONLY use technologies explicitly written in the resume
- NEVER invent frameworks/tools
- NEVER assume cloud experience
- NEVER assume deployment experience
- NEVER assume system design knowledge unless explicitly mentioned

SECTION RULES:
- Conceptual / Experience → section="Conceptual"
- Architecture → section="System Design"

Return valid JSON:
{{
  "questions": [
    {{
      "text": "...",
      "type": "technical",
      "difficulty": "medium",
      "section": "Conceptual",
      "follow_up_to": null,
      "expected_topics": []
    }}
  ]
}}
"""
        result = self._call_gemini(prompt, tag="QUESTIONS", json_mode=True)

        if result:
            try:
                parsed = json.loads(result)
                tech_questions = [QuestionModel(**q) for q in parsed.get("questions", [])]
                all_questions = [intro_question] + tech_questions[:6]

                log_separator("All Generated Questions")
                for i, q in enumerate(all_questions):
                    tag_label = "INTRO " if i == 0 else f"Q{i:02d}   "
                    diff_colors = {"easy": "\033[92m", "medium": "\033[93m", "hard": "\033[91m"}
                    dc = diff_colors.get(q.difficulty, "")
                    reset = COLORS["RESET"]
                    print(
                        f"  {dc}[{tag_label}]{reset} "
                        f"{q.difficulty.upper():6} | "
                        f"{q.section:22} | "
                        f"{q.text[:85]}{'...' if len(q.text) > 85 else ''}",
                        flush=True
                    )
                log_separator()
                log("QUESTIONS", f"✅ Done — 1 intro + {len(tech_questions[:5])} technical = {len(all_questions[:6])} total", "OK")
                return all_questions[:6]

            except (json.JSONDecodeError, Exception) as e:
                log("QUESTIONS", f"JSON parse FAILED: {e}", "ERROR")
                log("QUESTIONS", f"Raw (first 500): {result[:500]}", "ERROR")

        log("QUESTIONS", "Falling back to defaults", "WARN")
        return [
            intro_question,
            QuestionModel(text=f"Can you describe your experience with {topic} and how you've used it in a project?", type="technical", difficulty="easy", section="Conceptual"),
            QuestionModel(text=f"What are the core principles and advantages of using {topic} compared to alternatives?", type="technical", difficulty="medium", section="Conceptual"),
            QuestionModel(text=f"How would you approach debugging a critical performance issue in a {topic} application?", type="technical", difficulty="medium", section="Conceptual"),
            QuestionModel(text=f"Describe a time when you had to optimize {topic} code. What specific steps did you take?", type="technical", difficulty="hard", section="Conceptual"),
            QuestionModel(text=f"How would you design a scalable architecture using {topic}?", type="technical", difficulty="hard", section="System Design")
        ][:6]

    def generate_adaptive_question(
        self,
        profile: dict,
        previous_question: str,
        previous_answer: str,
        evaluation: dict,
        context: dict
    ):
        previous_questions = context.get("asked_questions", [])
        overall = evaluation.get("overall", 60)
        
        weak_topics = context.get("weak_topics", [])
        strong_topics = context.get("strong_topics", [])

        if overall >= 85:
            target_difficulty = "hard"
        elif overall >= 70:
            target_difficulty = "medium"
        elif overall >= 50:
            target_difficulty = "medium-easy"
        else:
            target_difficulty = "easy"

        prompt = f"""
You are an elite adaptive AI interviewer.

Your task:
Generate the NEXT BEST interview question.

CANDIDATE PERFORMANCE:
Technical Score: {evaluation.get("technical")}
Depth Score: {evaluation.get("depth")}
Communication: {evaluation.get("communication")}
Overall: {evaluation.get("overall")}

Next question difficulty should be: {target_difficulty}

PREVIOUS QUESTION:
{previous_question}

CANDIDATE ANSWER:
{previous_answer[:3000]}

PREVIOUS QUESTIONS:
{json.dumps(previous_questions)}

CANDIDATE WEAK TOPICS:
{json.dumps(weak_topics)}

CANDIDATE STRONG TOPICS:
{json.dumps(strong_topics)}

RULES:
- If candidate performs well → increase difficulty
- If candidate struggles → simplify
- Ask follow-up questions naturally
- Focus on weak areas
- Explore strengths deeper
- Avoid repeating concepts
- Make interview feel human

IMPORTANT:
If candidate mentions:
- optimization
- scaling
- caching
- deployment
- architecture
- debugging

Ask deep follow-up questions.

RETURN JSON:
{{
  "text": "...",
  "type": "technical",
  "difficulty": "medium",
  "section": "Conceptual",
  "follow_up_to": "{latest_question}"
}}
"""

        result = self._call_gemini(
            prompt,
            tag="ADAPTIVE_Q",
            json_mode=True
        )

        if result:
            try:
                parsed = json.loads(result)
                return QuestionModel(**parsed)
            except Exception as e:
                log("ADAPTIVE", f"Parse failed: {e}", "ERROR")

        return QuestionModel(
            text="Can you explain that concept in more detail?",
            type="technical",
            difficulty="medium",
            section="Conceptual"
        )

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        candidate_profile: dict,
        previous_answers: list,
        expected_topics: list
    ) -> EvaluationResult:
        log_separator("Answer Evaluation")
        log("EVAL", f"Q: {question[:80]}...")

        clean = re.sub(r'^\[written answer\]:\s*', '', answer.strip(), flags=re.IGNORECASE).strip()
        word_count = len(clean.split())
        log("EVAL", f"Answer: {word_count} words | Preview: {clean[:100]}...")

        if word_count < 8 or any(p in clean.lower() for p in ["no answer", "i don't know", "skip", "n/a"]):
            log("EVAL", "Too short / invalid → score 0", "WARN")
            return EvaluationResult(
                technical=0.0, communication=0.0, depth=0.0, relevance=0.0, overall=0.0,
                feedback="No response provided or answer was too brief. Please elaborate."
            )

        prompt = f"""
You are a STRICT senior technical interviewer.

Evaluate this answer realistically.

SCORING RULES:
90-100 = exceptional senior-level answer
75-89 = strong professional answer
60-74 = acceptable but incomplete
40-59 = weak understanding
20-39 = poor understanding
0-19 = incorrect or irrelevant

IMPORTANT:
- Penalize vague answers heavily
- Penalize buzzword stuffing
- Penalize generic textbook definitions
- Reward practical implementation details
- Reward architecture understanding
- Reward debugging/tradeoff discussion

Question:
{question}

Answer:
{clean}

Candidate Profile Info:
{json.dumps(candidate_profile.get("resume_text", "")[:1000]) if candidate_profile else ""}

Expected Topics:
{json.dumps(expected_topics)}

Previous Answers Summary:
{json.dumps([a.get("transcript", "")[:100] for a in previous_answers[-3:]]) if previous_answers else "None"}

Return ONLY JSON:
{{
  "technical": 0,
  "communication": 0,
  "depth": 0,
  "relevance": 0,
  "overall": 0,
  "feedback": "..."
}}
"""
        result = self._call_gemini(prompt, tag="EVAL", json_mode=True)
        if result:
            try:
                r = json.loads(result)
                ev = EvaluationResult(**r)
                log("EVAL", f"✅ technical={ev.technical} comm={ev.communication} depth={ev.depth} relevance={ev.relevance} overall={ev.overall}", "OK")
                log("EVAL", f"Feedback: {ev.feedback}")
                return ev
            except Exception as e:
                log("EVAL", f"Parse error: {e}", "ERROR")

        log("EVAL", "Fallback scores", "WARN")
        return EvaluationResult(technical=60.0, communication=60.0, depth=60.0,
                                relevance=60.0, overall=60.0,
                                feedback="Good effort, evaluation could not complete.")

    def generate_report(self, candidate_name: str, scores: dict, answers: list) -> str:
        log_separator("Final Report")
        log("REPORT", f"Candidate: {candidate_name} | Scores: {json.dumps(scores)}")

        prompt = f"""Senior engineering hiring manager writing a post-interview assessment.
Candidate: {candidate_name}
Scores: {json.dumps(scores)}
Answers: {json.dumps(answers)}

3-paragraph report:
1. Technical Assessment (strengths, gaps, specific topics)
2. Communication & Soft Skills
3. Hiring Recommendation: Strong Yes / Yes / Maybe / No

Return ONLY plain text.
"""
        result = self._call_gemini(prompt, tag="REPORT")
        if result:
            log("REPORT", "✅ Report generated", "OK")
            return result
        log("REPORT", "Fallback report", "WARN")
        return f"Overall score: {scores.get('overall', 0)}. Candidate showed reasonable effort."

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        log("AUDIO", f"Transcription — {len(audio_bytes):,} bytes")
        if not self.client_ready:
            log("AUDIO", "Skipped — client not ready", "WARN")
            return ""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                f.write(audio_bytes)
                temp_path = f.name
            log("GEMINI", "[AUDIO] Uploading to File API...", "GEMINI")
            start = time.time()
            audio_file = genai.upload_file(path=temp_path)
            response = self.model.generate_content(
                ["Transcribe this audio accurately. Return only the transcription.", audio_file]
            )
            elapsed = round(time.time() - start, 2)
            genai.delete_file(audio_file.name)
            os.remove(temp_path)
            transcript = response.text.strip()
            log("AUDIO", f"✅ Done in {elapsed}s: \"{transcript[:80]}\"", "OK")
            return transcript
        except Exception as e:
            log("AUDIO", f"FAILED: {e}", "ERROR")
            return ""


groq_service = GroqService()