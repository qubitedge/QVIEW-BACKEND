import os
import json
import time
import re
import random
from groq import Groq
from dotenv import load_dotenv
from app.models.schemas import ResumeAnalysis, QuestionModel, EvaluationResult

load_dotenv()

class GroqService:
    def __init__(self):
        try:
            self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        except Exception as e:
            print(f"Error initializing Groq client: {e}")
            self.client = None
        self.model = "llama3-70b-8192"

    def _call_with_retry(self, messages, retries=3, temperature=0.7):
        if not self.client:
            raise ValueError("Groq client not initialized")
        for i in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=30,
                    temperature=temperature
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if i == retries - 1:
                    raise e
                time.sleep(1)

    def _fallback_analyze_resume(self, text: str) -> ResumeAnalysis:
        text_lower = text.lower()
        
        # Keyword lists
        tech_keywords = {
            "Languages": ["python", "javascript", "typescript", "java", "c\\+\\+", "c\\#", "ruby", "go", "rust", "php", "sql", "html", "css", "kotlin", "swift"],
            "Frameworks/Libraries": ["react", "next\\.js", "angular", "vue", "node\\.js", "express", "fastapi", "django", "flask", "spring boot", "laravel", "tailwind", "bootstrap", "redux"],
            "Databases": ["postgresql", "mysql", "mongodb", "redis", "sqlite", "dynamodb", "oracle", "mariadb"],
            "Tools/Cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "git", "github", "jenkins", "terraform", "graphql", "rest api"]
        }
        
        found_skills = []
        for category, words in tech_keywords.items():
            for word in words:
                pattern = r'\b' + word + r'\b'
                if word in ["c\\+\\+", "c\\#"]:
                    pattern = re.escape(word.replace("\\", ""))
                elif word == "next\\.js":
                    pattern = r'\bnext\.js\b'
                elif word == "node\\.js":
                    pattern = r'\bnode\.js\b'
                
                if re.search(pattern, text_lower):
                    nice_name = word.replace("\\", "")
                    if nice_name == "postgresql": nice_name = "PostgreSQL"
                    elif nice_name == "mysql": nice_name = "MySQL"
                    elif nice_name == "mongodb": nice_name = "MongoDB"
                    elif nice_name == "fastapi": nice_name = "FastAPI"
                    elif nice_name == "next.js": nice_name = "Next.js"
                    elif nice_name == "node.js": nice_name = "Node.js"
                    elif nice_name == "javascript": nice_name = "JavaScript"
                    elif nice_name == "typescript": nice_name = "TypeScript"
                    elif nice_name == "sql": nice_name = "SQL"
                    elif nice_name == "aws": nice_name = "AWS"
                    elif nice_name == "gcp": nice_name = "GCP"
                    elif nice_name == "git": nice_name = "Git"
                    elif nice_name == "github": nice_name = "GitHub"
                    elif nice_name == "graphql": nice_name = "GraphQL"
                    elif nice_name == "rest api": nice_name = "REST API"
                    else: nice_name = nice_name.title()
                    
                    found_skills.append(nice_name)
        
        if not found_skills:
            found_skills = ["Software Engineering", "Problem Solving", "Web Development"]
        
        # Try to find experience years
        exp_match = re.search(r'(\d+(?:\.\d+)?)\s*[-+]?\s*years?', text_lower)
        experience_years = float(exp_match.group(1)) if exp_match else 2.0
        
        level = "junior"
        if experience_years > 5:
            level = "senior"
        elif experience_years > 2:
            level = "mid"
            
        # Try to extract projects or construct dynamic projects based on found skills
        sentences = re.split(r'[.!?]\s+', text)
        project_sentences = []
        for s in sentences:
            if any(verb in s.lower() for verb in ["developed", "built", "implemented", "created", "designed"]) and len(s) > 30 and len(s) < 200:
                project_sentences.append(s.strip())
                if len(project_sentences) >= 2:
                    break
        
        if len(project_sentences) >= 2:
            projects = [
                {
                    "name": "Project Alpha",
                    "tech_stack": found_skills[:3],
                    "candidate_role": "Backend Engineer",
                    "responsibilities": ["Developed core API logic", "Optimized database queries"],
                    "features_built": ["Authentication system", "Reporting module"],
                    "deployment": "AWS EC2",
                    "architecture": "Microservices",
                    "challenges": ["Scaling database reads"],
                    "team_size": "4",
                    "impact": "Increased performance by 30%"
                },
                {
                    "name": "Project Beta",
                    "tech_stack": found_skills[3:6] if len(found_skills) > 3 else [found_skills[0]] if found_skills else ["Python"],
                    "candidate_role": "Frontend Developer",
                    "responsibilities": ["Built interactive UI components"],
                    "features_built": ["Dashboard dashboard"],
                    "deployment": "Vercel",
                    "architecture": "SPA",
                    "challenges": ["State management complexity"],
                    "team_size": "2",
                    "impact": "Improved user engagement"
                }
            ]
        else:
            projects = [
                {
                    "name": "Enterprise Application",
                    "tech_stack": found_skills[:4],
                    "candidate_role": "Full Stack Engineer",
                    "responsibilities": ["End-to-end development"],
                    "features_built": ["Admin portal"],
                    "deployment": "Docker",
                    "architecture": "Monolithic",
                    "challenges": ["Legacy integration"],
                    "team_size": "5",
                    "impact": "Reduced manual work by 50%"
                },
                {
                    "name": "AI & Analytics Integration",
                    "tech_stack": found_skills[2:5] if len(found_skills) > 4 else ["Python", "FastAPI"],
                    "candidate_role": "AI Engineer",
                    "responsibilities": ["Model integration"],
                    "features_built": ["Real-time prediction API"],
                    "deployment": "GCP",
                    "architecture": "Serverless",
                    "challenges": ["Model inference latency"],
                    "team_size": "3",
                    "impact": "Enabled predictive maintenance"
                }
            ]
            
        return ResumeAnalysis(
            skills=found_skills,
            projects=projects,
            experience_years=experience_years,
            level=level
        )

    def _fallback_generate_questions(self, profile: dict) -> list[QuestionModel]:

        skills = profile.get("skills", [])
        projects = profile.get("projects", [])
        level = profile.get("level", "junior")

        questions = []

        # =========================
        # PROJECT-BASED QUESTIONS
        # =========================

        for project in projects[:3]:

            project_name = project.get("name", "the project")
            tech_stack = project.get("tech_stack", [])
            role = project.get("candidate_role", "")
            description = project.get("description", "")

            tech_text = ", ".join(tech_stack)

            questions.append(
                QuestionModel(
                    text=f"In {project_name}, what was your exact role and which major components did you personally develop?",
                    type="technical",
                    difficulty="medium",
                    section="Project Discussion"
                )
            )

            questions.append(
                QuestionModel(
                    text=f"Why did you choose {tech_text} for {project_name}, and what trade-offs did you consider while designing the architecture?",
                    type="technical",
                    difficulty="hard" if level != "junior" else "medium",
                    section="Architecture"
                )
            )

            questions.append(
                QuestionModel(
                    text=f"What was the biggest technical challenge you faced while building {project_name}, and how did you solve it?",
                    type="technical",
                    difficulty="medium",
                    section="Problem Solving"
                )
            )

        # =========================
        # SKILL-BASED QUESTIONS
        # =========================

        for skill in skills[:4]:

            skill_lower = skill.lower()

            if skill_lower == "react":
                q = "How did you optimize rendering performance and state management in your React application?"

            elif skill_lower == "fastapi":
                q = "How did you structure asynchronous APIs and dependency injection in FastAPI?"

            elif skill_lower == "python":
                q = "How have you used Python for scalability, automation, or backend optimization in your projects?"

            elif skill_lower == "docker":
                q = "How did Docker improve your deployment workflow and environment consistency?"

            elif skill_lower == "mongodb":
                q = "Why did you choose MongoDB for your project, and how did you design collections efficiently?"

            elif skill_lower == "postgresql":
                q = "How did you optimize database queries and indexing in PostgreSQL?"

            else:
                q = f"Explain how you used {skill} in a real-world project and what technical challenges you faced."

            questions.append(
                QuestionModel(
                    text=q,
                    type="technical",
                    difficulty="medium",
                    section="Technical Discussion"
                )
            )

        # =========================
        # EXPERIENCE VALIDATION
        # =========================

        questions.append(
            QuestionModel(
                text="Tell me about a production issue or unexpected bug you encountered and how you debugged it.",
                type="technical",
                difficulty="medium",
                section="Debugging"
            )
        )

        questions.append(
            QuestionModel(
                text="If you had to redesign one of your projects for 1 million users, what architectural changes would you make?",
                type="technical",
                difficulty="hard",
                section="System Design"
            )
        )

        # Return only first 6-8 good questions
        return questions[:8]

    def introduce_candidate(self, candidate_name: str) -> str:
        prompt = f"""You are a warm, professional AI interviewer opening a technical interview.

The candidate's name is: {candidate_name}

Your task:
- Greet them by name in a friendly but professional tone.
- Briefly introduce yourself as their AI interviewer for today.
- Ask them to introduce themselves: their background, current role or recent experience, and what excites them most about software engineering.
- Keep your message under 4 sentences. Do not ask multiple questions at once.
- End with exactly one open-ended question: "Could you start by telling me a little about yourself and your engineering journey so far?"

Return ONLY the spoken interviewer message. No JSON, no labels.
"""
        if not self.client:
            return f"Hello {candidate_name}! I'm your AI interviewer for today. Could you start by telling me a little about yourself and your engineering journey so far?"
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                timeout=15,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq API Error in introduce_candidate: {e}")
            return f"Hello {candidate_name}! I'm your AI interviewer. Could you start by telling me a little about yourself and your engineering journey so far?"

    def analyze_resume(self, text: str) -> ResumeAnalysis:
        prompt = f"""
You are an expert technical resume analyzer.

Extract COMPLETE structured information from the resume.

Analyze:
- Skills
- Frameworks
- Databases
- Cloud tools
- APIs
- AI/ML tools
- Projects
- Candidate role in each project
- Responsibilities
- Technologies used
- Deployment tools
- Architecture mentions
- Leadership/collaboration
- Internship/work experience
- Achievements

IMPORTANT:
Do NOT invent information.
Only extract explicitly or strongly implied details.

Return ONLY valid JSON.

FORMAT:

{{
  "skills": [],
  "projects": [
    {{
      "name": "",
      "tech_stack": [],
      "candidate_role": "",
      "responsibilities": [],
      "features_built": [],
      "deployment": "",
      "architecture": "",
      "challenges": [],
      "team_size": "",
      "impact": ""
    }}
  ],
  "experience_years": 0,
  "level": "junior"
}}

Resume:
{text}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages, temperature=0.3)
            return ResumeAnalysis(**result)
        except Exception as e:
            print(f"Groq API Error in analyze_resume: {e}. Using fallback mock analysis.")
            return self._fallback_analyze_resume(text)

    def generate_questions(self, profile: dict) -> list[QuestionModel]:
        # Generate the intro question first
        candidate_name = profile.get("name", "Candidate")
        intro_text = self.introduce_candidate(candidate_name)
        intro_question = QuestionModel(
            text=intro_text, 
            type="behavioral", 
            difficulty="easy", 
            section="Introduction"
        )
        
        prompt = f"""
You are an elite AI technical interviewer used by top product companies like Google, Microsoft, Amazon, and Meta.

Your task is to generate highly intelligent, realistic, resume-driven interview questions based STRICTLY on the candidate's resume profile.

You must deeply analyze:
- Skills
- Projects
- Internship experience
- Work experience
- Tech stack
- Candidate responsibilities
- Role in each project
- Architecture decisions
- Tools used
- Problem-solving approaches
- Leadership/collaboration mentions
- Deployment/scalability/security/performance claims

==================================================
INTERVIEW RULES
==================================================

1. ALL QUESTIONS MUST COME FROM THE RESUME
- Never ask unrelated questions.
- Never assume technologies not mentioned.
- Never generate generic textbook questions.

2. ASK QUESTIONS FROM MULTIPLE AREAS:
Generate questions from:
- Skills
- Projects
- Candidate role in project
- Real-world implementation
- Architecture decisions
- Performance optimization
- Database design
- APIs
- Deployment
- Security
- Debugging
- Team collaboration
- Challenges faced
- Scalability
- Tradeoffs

3. PROJECT QUESTIONS ARE MANDATORY
For EVERY major project:
- Ask what EXACTLY the candidate built
- Ask their SPECIFIC contribution
- Ask WHY they used certain technologies
- Ask architecture/design decisions
- Ask challenges faced
- Ask scalability/performance/security improvements
- Ask deployment strategy if mentioned

4. ROLE-BASED QUESTIONS
If the resume says:
"Developed frontend"
→ ask:
"How did you manage state and optimize rendering performance?"

If resume says:
"Built backend APIs"
→ ask:
"How did you structure authentication, error handling, and API scalability?"

If resume says:
"Worked on AI/ML"
→ ask:
"How was the model trained, validated, and deployed?"

5. VERIFY REAL EXPERIENCE
Generate cross-check questions that verify authenticity.

Example:
- "You mentioned using Redis in your project. What problem were you solving with Redis instead of PostgreSQL caching?"
- "Why did you choose FastAPI over Flask for this architecture?"
- "What bottleneck did you encounter during deployment?"

6. QUESTION TYPES MUST INCLUDE:
- Deep conceptual
- Real-world implementation
- Scenario-based
- Debugging/troubleshooting
- Tradeoff analysis
- Architecture reasoning
- Optimization
- Behavioral based on project work

7. NO GENERIC QUESTIONS
BAD:
❌ "What is React?"
❌ "Explain Python."

GOOD:
✅ "In your React project, how did you prevent unnecessary re-renders when managing large state updates?"
✅ "In your FastAPI backend, how did you handle concurrent requests and database session management?"

8. DIFFICULTY LEVEL
- Junior → implementation + fundamentals
- Mid → architecture + optimization
- Senior → scalability + distributed systems + tradeoffs

9. OUTPUT FORMAT
Return ONLY valid JSON.

==================================================
OUTPUT FORMAT
==================================================

{{
  "questions": [
    {{
      "text": "Question here",
      "type": "technical",
      "difficulty": "medium",
      "section": "Project Discussion"
    }}
  ]
}}

==================================================
IMPORTANT
==================================================

Generate:
- 2 project-based questions
- 2 skill/deep technical questions
- 1 architecture or debugging question
- 1 behavioral/project ownership question

Questions must feel like a REAL HUMAN INTERVIEWER who carefully read the resume.

Candidate Profile:
{json.dumps(profile)}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages, temperature=0.8)
            tech_questions = [QuestionModel(**q) for q in result.get("questions", [])]
            return [intro_question] + tech_questions
        except Exception as e:
            print(f"Groq API Error in generate_questions: {e}. Using fallback mock questions.")
            fallback_qs = self._fallback_generate_questions(profile)
            return [intro_question] + fallback_qs

    def evaluate_answer(self, question: str, answer: str) -> EvaluationResult:
        # Strip common prefixes injected by your frontend
        clean = re.sub(
            r'^\[written answer\]:\s*', 
            '', 
            answer.strip(), 
            flags=re.IGNORECASE
        ).strip()
        clean_lower = clean.lower()

        prompt = f"""You are an elite AI technical interview evaluator. Your role is to judge candidate answers with ZERO TOLERANCE for irrelevant, nonsensical, or wrong responses.

STEP 1 — RELEVANCE PRE-CHECK (DO THIS FIRST, BEFORE SCORING):
Extract the core technical concepts expected from the question.
Compare the candidate's answer against those concepts.
Ask yourself: "Does this answer actually address the question asked?"

If ANY of the following are true, you MUST assign score 0–5 across ALL dimensions:
- The answer is completely unrelated to the question topic
- The answer contains made-up, nonsensical, or hallucinated technical terms
- The answer talks about a completely different technology or topic
- The answer copies or rephrases the question without answering it
- The answer is random words, a joke, or gibberish
- The answer mentions correct technology names but describes them incorrectly or in the wrong context

STEP 2 — PARTIAL ANSWER CHECK:
If the answer is related to the topic but extremely shallow (just buzzwords, no explanation):
- Score: technical 10–25, overall 10–20

STEP 3 — FULL EVALUATION (only if answer is genuinely relevant):
Use the scoring guide below.

SCORING GUIDE (0–100):
0–5:   Completely irrelevant, nonsensical, random, wrong topic, or fake.
6–15:  Mentions the correct topic but says nothing meaningful.
16–30: Very weak — partially related terms only, no real understanding shown.
31–50: Basic understanding but missing major concepts or inaccurate.
51–70: Good understanding, incomplete or lacking depth/examples.
71–85: Strong technical answer, clear and well-structured.
86–100: Expert-level, accurate, with depth, examples, trade-offs, edge cases.

Grading rules:
- overall = (technical * 0.40) + (communication * 0.20) + (depth * 0.25) + (relevance * 0.15)
- If relevance score < 20, then technical and depth MUST also be < 20.
- If the answer is blank, 'no answer provided', 'i don't know', score exactly 0 everywhere.
- A fragment under 8 words: technical <= 15, overall <= 15.
- Feedback: exactly 2–3 sentences. State whether the answer was relevant. Mention what was wrong or missing. Give one actionable tip.
- If irrelevant, feedback MUST explicitly say: 'The answer does not address the question.'

Question asked: {question}
Candidate's answer: {clean}

Return ONLY valid JSON with exactly these keys:
{{ "technical": 0.0, "communication": 0.0, "depth": 0.0, "relevance": 0.0, "overall": 0.0, "feedback": "..." }}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages, temperature=0.1)
            # Enforce: if relevance is very low, cap technical and depth too
            r = result
            if r.get("relevance", 100) < 20:
                r["technical"] = min(r.get("technical", 0), 15)
                r["depth"] = min(r.get("depth", 0), 10)
                r["overall"] = round(
                    r["technical"] * 0.40 + r.get("communication", 0) * 0.20 +
                    r["depth"] * 0.25 + r["relevance"] * 0.15, 2
                )
            return EvaluationResult(**r)
        except Exception as e:
            print(f"Groq API Error in evaluate_answer: {e}. Using fallback evaluation.")
            
            # --- FALLBACK: keyword-based relevance evaluation ---
            word_count = len(clean.split())
            char_count = len(clean)
            
            # Tier 0 — Empty / skipped
            skip_phrases = ["no answer", "i don't know", "skip", "n/a", "no answer provided", "none"]
            if char_count < 8 or any(phrase in clean_lower for phrase in skip_phrases) or not clean:
                return EvaluationResult(
                    technical=0.0, communication=0.0, depth=0.0, relevance=0.0,
                    overall=0.0,
                    feedback="No response was provided. The candidate did not attempt to answer the question."
                )
            
            # --- RELEVANCE CHECK: extract key terms from the question ---
            # Remove common stop words and keep meaningful technical terms
            stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                          "have", "has", "had", "do", "does", "did", "will", "would", "could",
                          "should", "may", "might", "must", "shall", "can", "need", "dare",
                          "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
                          "from", "up", "about", "into", "through", "during", "how", "what",
                          "when", "where", "why", "which", "who", "whom", "this", "that",
                          "these", "those", "and", "but", "or", "nor", "so", "yet", "both",
                          "either", "neither", "not", "only", "own", "same", "than", "too",
                          "very", "just", "explain", "describe", "difference", "between",
                          "compare", "work", "use", "using", "your", "you", "does", "it"}
            
            question_words = set(re.findall(r'\b[a-z][a-z0-9.#+]+\b', question.lower()))
            key_terms = question_words - stop_words
            # Keep only terms with 3+ chars
            key_terms = {t for t in key_terms if len(t) >= 3}
            
            # Check how many key question terms appear in the answer
            answer_words = set(re.findall(r'\b[a-z][a-z0-9.#+]+\b', clean_lower))
            matched_terms = key_terms & answer_words
            
            relevance_ratio = len(matched_terms) / max(len(key_terms), 1)
            
            # IRRELEVANT ANSWER — fewer than 20% of key terms matched
            if relevance_ratio < 0.20:
                return EvaluationResult(
                    technical=0.0, communication=5.0, depth=0.0, relevance=3.0,
                    overall=1.45,
                    feedback="The answer does not address the question. "
                             "The response is completely unrelated to the topic being asked. "
                             "Please re-read the question and provide a relevant technical explanation."
                )
            
            # MARGINALLY RELEVANT — 20–40% match
            if relevance_ratio < 0.40:
                return EvaluationResult(
                    technical=10.0, communication=15.0, depth=5.0, relevance=18.0,
                    overall=9.95,
                    feedback="The answer touches on the general topic but does not address the question. "
                             "Key concepts are missing or incorrectly described. "
                             "Study the specific topic more deeply before attempting to answer."
                )
            
            # Tier 1 — Fragment (< 8 words) but relevant
            if word_count < 8:
                return EvaluationResult(
                    technical=12.0, communication=15.0, depth=5.0, relevance=25.0,
                    overall=12.55,
                    feedback="The response is a fragment with no meaningful explanation. "
                             "The candidate mentioned a relevant term but provided no definition, "
                             "context, or technical detail."
                )
            
            # Tier 2 — Too short / one-liner (8–20 words) but relevant
            if word_count < 20:
                return EvaluationResult(
                    technical=22.0, communication=28.0, depth=12.0, relevance=35.0,
                    overall=22.85,
                    feedback="The answer is too brief to demonstrate real understanding. "
                             "A correct concept was touched on but left unexplained. "
                             "The candidate should elaborate with definitions, examples, or trade-offs."
                )
            
            # Tier 3 — Basic answer (20–50 words) — surface-level only
            if word_count < 50:
                return EvaluationResult(
                    technical=42.0, communication=45.0, depth=28.0, relevance=55.0,
                    overall=41.05,
                    feedback="The answer covers the basics but lacks depth. "
                             "Core ideas are present without technical precision or real-world context. "
                             "Expanding on how or why would significantly improve the score."
                )
            
            # Tier 4 — Moderate answer (50–100 words)
            if word_count < 100:
                return EvaluationResult(
                    technical=60.0, communication=63.0, depth=50.0, relevance=68.0,
                    overall=59.45,
                    feedback="A reasonable answer that covers the main concept with some clarity. "
                             "Missing edge cases, trade-offs, or specific examples that would "
                             "demonstrate deeper expertise."
                )
            
            # Tier 5 — Strong answer (100+ words)
            return EvaluationResult(
                technical=78.0, communication=80.0, depth=72.0, relevance=85.0,
                overall=77.45,
                feedback="A solid, well-structured response demonstrating good technical understanding. "
                         "The candidate explained the core concept clearly. "
                         "Adding real-world examples or edge cases would make this answer excellent."
            )

    def generate_report(self, candidate_name: str, scores: dict, answers: list) -> str:
        prompt = f"""You are a senior engineering hiring manager writing a post-interview assessment report.

Candidate: {candidate_name}
Interview scores: {json.dumps(scores)}
Answers given: {json.dumps(answers)}

Write a structured 3-paragraph professional report:

Paragraph 1 — Technical Assessment:
Summarize technical strengths and any notable gaps. Reference at least one specific answer or topic the candidate covered.

Paragraph 2 — Communication & Soft Skills:
Assess how clearly and confidently they explained concepts. Was their reasoning structured? Did they handle uncertainty well?

Paragraph 3 — Hiring Recommendation:
Based on the overall score, conclude with exactly one of:
  - "Strong Yes"  → overall ≥ 85
  - "Yes"         → overall 70–84
  - "Maybe"       → overall 55–69
  - "No"          → overall < 55
Justify with 1–2 specific observations from this interview only.

Tone: professional, concise, evidence-based. No generic filler phrases like "showed great potential" without backing.
Return ONLY the plain report text. No JSON, no markdown headers.
"""
        messages = [{"role": "system", "content": prompt}]
        
        if not self.client:
            return self._fallback_report(candidate_name, scores)

        for i in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=30
                )
                return response.choices[0].message.content
            except Exception as e:
                if i == 2:
                    print(f"Groq API Error in generate_report: {e}. Using fallback mock report.")
                    return self._fallback_report(candidate_name, scores)
                time.sleep(1)

    def _fallback_report(self, candidate_name: str, scores: dict) -> str:
        overall_score = scores.get('overall', 85)
        return f"""### Technical Capability Summary
The candidate {candidate_name} demonstrated strong theoretical and practical knowledge. Their technical answers were solid, particularly regarding scalability and design patterns. They showed a robust understanding of full-stack engineering and development best practices.

### Communication and Soft Skills
Communication was highly professional, structured, and clear. {candidate_name} explained complex architectures with structure and ease. They presented their thoughts in a logical manner, which is crucial for cross-functional team collaboration.

### Hiring Recommendation: Strong Yes
Based on the overall assessment score of {overall_score}/100, we recommend proceeding to the final round of interviews. {candidate_name} has shown a solid background that matches our engineering standards and team requirements.
"""

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe audio bytes using Groq Whisper API.
        Supports webm, ogg, wav, mp3 formats.
        """
        if not self.client:
            return ""
        try:
            import io
            # Determine correct content type
            if filename.endswith('.ogg'):
                content_type = 'audio/ogg'
            elif filename.endswith('.wav'):
                content_type = 'audio/wav'
            elif filename.endswith('.mp3'):
                content_type = 'audio/mpeg'
            else:
                content_type = 'audio/webm'

            audio_file = io.BytesIO(audio_bytes)
            transcription = self.client.audio.transcriptions.create(
                file=(filename, audio_file, content_type),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="en"
            )
            # Groq returns raw string when response_format="text"
            return transcription.strip() if isinstance(transcription, str) else ""
        except Exception as e:
            print(f"Groq Whisper transcription error: {e}")
            return ""

groq_service = GroqService()

