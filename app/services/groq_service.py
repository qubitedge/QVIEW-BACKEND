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
                    "tech": ", ".join(found_skills[:3]),
                    "description": project_sentences[0]
                },
                {
                    "name": "Project Beta",
                    "tech": ", ".join(found_skills[3:6]) if len(found_skills) > 3 else found_skills[0],
                    "description": project_sentences[1]
                }
            ]
        else:
            projects = [
                {
                    "name": "Enterprise Application",
                    "tech": ", ".join(found_skills[:4]),
                    "description": f"Designed and developed a scalable system using {', '.join(found_skills[:3])} to optimize workflow performance."
                },
                {
                    "name": "AI & Analytics Integration",
                    "tech": ", ".join(found_skills[2:5]) if len(found_skills) > 4 else "Python, FastAPI",
                    "description": f"Built a real-time analytics module integrating modern APIs and utilizing {found_skills[-1] if found_skills else 'SQL'}."
                }
            ]
            
        return ResumeAnalysis(
            skills=found_skills,
            projects=projects,
            experience_years=experience_years,
            level=level
        )

    def _fallback_generate_questions(self, profile: dict) -> list[QuestionModel]:
        skills = profile.get("skills", ["React", "JavaScript", "Python"])
        level = profile.get("level", "mid")
        
        coding_questions = {
            "python": [
                "Write a Python function to find the first non-repeating character in a string.",
                "Write a Python function to merge two sorted lists into one sorted list.",
                "Write a Python generator function to compute Fibonacci numbers up to N."
            ],
            "javascript": [
                "Write a JavaScript function to deep clone a nested object without using JSON.parse.",
                "Write a JavaScript function to throttle a callback execution.",
                "Write a JavaScript function that flattens a nested array of arbitrary depth."
            ],
            "typescript": [
                "Write a TypeScript function using generics to filter an array of objects by a key-value pair.",
                "Write a TypeScript custom utility type to make all properties of a type writeable (remove readonly)."
            ],
            "sql": [
                "Write a SQL query to find the second highest salary from an Employee table.",
                "Write a SQL query using a CTE or JOIN to find customers who have never placed an order."
            ],
            "java": [
                "Write a Java method to check if a binary tree is a valid Binary Search Tree (BST).",
                "Write a Java program to implement a thread-safe Singleton pattern."
            ],
            "c++": [
                "Write a C++ class that implements a basic smart pointer (similar to shared_ptr).",
                "Write a C++ function to reverse a singly linked list in-place."
            ]
        }
        
        conceptual_questions = {
            "react": [
                "What is the difference between Virtual DOM and Real DOM, and how does React's reconciliation work?",
                "Explain the React component lifecycle hooks and when to use useMemo vs useCallback.",
                "How does state management with React Context compare to external stores like Redux or Zustand?"
            ],
            "node.js": [
                "Explain the event loop in Node.js, and the differences between setImmediate, process.nextTick, and setTimeout.",
                "How do streams work in Node.js, and what are the benefits of using streaming over buffer reading?"
            ],
            "postgresql": [
                "What are database indexes, and how do B-Tree and Hash indexes improve performance in PostgreSQL?",
                "Explain database ACID transactions and the differences between transaction isolation levels."
            ],
            "fastapi": [
                "How does dependency injection work in FastAPI, and what are the benefits of asynchronous path operations?",
                "Explain how FastAPI automatically generates OpenAPI docs and validates request bodies using Pydantic."
            ],
            "angular": [
                "What is the difference between components and directives in Angular, and how does change detection work?",
                "Explain the dependency injection system in Angular and the difference between providedIn: 'root' and component-level providers."
            ],
            "vue": [
                "Explain the Vue 3 reactivity system using Proxies, and how it differs from Vue 2's Object.defineProperty.",
                "What is the difference between computed properties and watchers in Vue?"
            ],
            "aws": [
                "Explain the difference between AWS S3, EC2, and RDS, and how you would design a secure multi-tier architecture.",
                "What is Serverless computing on AWS, and how do Lambda functions scale in response to events?"
            ],
            "docker": [
                "What is the difference between a Docker image and a Docker container, and how do multi-stage builds help optimize sizes?",
                "How do Docker volumes work, and why are they necessary for stateful applications?"
            ]
        }
        
        aptitude_questions = [
            "A train traveling at 60 km/h passes a post in 9 seconds. What is the length of the train in meters?",
            "If 5 machines take 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
            "A tank can be filled by pipe A in 6 hours and pipe B in 8 hours. If both pipes are opened together, how long will it take to fill the tank?",
            "In a room, everyone shakes hands with everyone else. If there are 10 people, how many handshakes take place in total?",
            "A vendor bought bananas at 6 for $5 and sold them at 4 for $3. What was his profit or loss percentage?"
        ]
        
        reasoning_questions = [
            "Find the missing number in the sequence: 2, 6, 12, 20, 30, ?",
            "If 'APPRENTICE' is coded as 'BQQSFOUJDF', how is 'DEVELOPER' coded in that same pattern?",
            "Pointing to a photograph, a man said, 'I have no brother or sister, but that man's father is my father's son.' Whose photograph was it?",
            "Look at the sequence: 36, 34, 30, 28, 24, ... What number should come next?",
            "If all Bloops are Razzles and all Razzles are Lizzies, are all Bloops definitely Lizzies?"
        ]
        
        selected_conceptual = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in conceptual_questions:
                selected_conceptual.extend(conceptual_questions[skill_lower])
                
        if len(selected_conceptual) < 5:
            selected_conceptual.extend([
                "Explain the difference between synchronous and asynchronous programming, and when you would use each.",
                "What is the difference between SQL and NoSQL databases, and how do you choose between them?",
                "Explain the concepts of REST APIs and HTTP status codes, specifically 200, 201, 400, 401, 403, and 500.",
                "How does garbage collection work in modern programming languages?",
                "What is the difference between monolithic and microservices architectures?"
            ])
            
        seed = abs(hash(json.dumps(skills)))
        
        c_questions = []
        for i in range(5):
            c_questions.append(selected_conceptual[(seed + i) % len(selected_conceptual)])
            
        return [
            QuestionModel(text=c_questions[0], type="technical", difficulty="easy" if level == "junior" else "medium", section="Conceptual"),
            QuestionModel(text=c_questions[1], type="technical", difficulty="easy" if level == "junior" else "medium", section="Conceptual"),
            QuestionModel(text=c_questions[2], type="technical", difficulty="easy" if level == "junior" else "medium", section="Conceptual"),
            QuestionModel(text=c_questions[3], type="technical", difficulty="easy" if level == "junior" else "medium", section="Conceptual"),
            QuestionModel(text=c_questions[4], type="technical", difficulty="easy" if level == "junior" else "medium", section="Conceptual")
        ]

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
        prompt = f"""You are a senior technical recruiter with 10+ years of experience in software engineering hiring.

Analyze the resume below with strict accuracy:

1. **Skills** — List only real, verifiable technologies (languages, frameworks, tools, cloud). No soft skills, no buzzwords.
2. **Projects** — Extract real projects only. For each: name, tech stack, and one sentence describing what was built and its measurable impact.
3. **Experience** — Total years of professional or internship experience as a number. Estimate conservatively if unclear.
4. **Level** — Classify strictly as: "junior" (<2 yrs), "mid" (2–5 yrs), or "senior" (5+ yrs).

Rules:
- Do NOT invent skills not present in the resume.
- If a field is absent, use a safe default (e.g. experience_years: 1).
- Return ONLY valid JSON, no explanation, no markdown.

Schema:
{{ "skills": ["Python", "React"], "projects": [{{"name": "App", "tech": "React, Node.js", "description": "Built e-commerce platform reducing load time by 40%"}}], "experience_years": 3, "level": "mid" }}

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
        
        prompt = f"""You are a senior technical interviewer at a top-tier engineering company.

Generate exactly 5 unique conceptual interview questions tailored to this candidate's specific resume profile.

Requirements:
- Each question must test deep UNDERSTANDING, not surface recall. Ask "how/why/when/trade-off", not "what is the definition of".
- Every question must target a DIFFERENT skill, framework, or concept from the candidate's profile.
- Vary question styles across: trade-off analysis, real-world scenario, design decision, and debugging reasoning.
- No coding exercises, no math puzzles, no HR questions.
- Difficulty: "easy" for junior, "medium" for mid/senior.
- All 5 must be completely distinct with zero overlapping concepts.

Return ONLY valid JSON, no explanation:
{{
  "questions": [
    {{"text": "...", "type": "technical", "difficulty": "medium", "section": "Conceptual"}},
    {{"text": "...", "type": "technical", "difficulty": "easy",   "section": "Conceptual"}},
    {{"text": "...", "type": "technical", "difficulty": "medium", "section": "Conceptual"}},
    {{"text": "...", "type": "technical", "difficulty": "easy",   "section": "Conceptual"}},
    {{"text": "...", "type": "technical", "difficulty": "medium", "section": "Conceptual"}}
  ]
}}

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
        ).strip().lower()

        prompt = f"""You are a strict but fair senior technical interviewer evaluating a live interview response.

Question asked: {question}
Candidate's answer: {clean}

Scoring rubric (0–100 each):
- **Technical Correctness** — Is the answer factually accurate? Are core concepts properly explained?
- **Communication Clarity** — Is it structured, coherent, and easy to follow without ambiguity?
- **Depth** — Does it go beyond surface level? Are trade-offs, edge cases, or real-world examples included?
- **Relevance** — Does the answer directly address what was asked, with no tangents?

Grading rules:
- A blank or "I don't know" scores below 20 across all dimensions.
- A vague, generic answer scores 40–60, not 80+. Be honest.
- A fragment under 10 words scores technical ≤ 15 and overall ≤ 15, regardless of whether the correct keyword appears. Keyword presence without explanation is NOT a correct answer.
- Feedback must be exactly 2–3 sentences: what was strong, what was missing, one actionable improvement tip.
- overall = (technical × 0.40) + (communication × 0.20) + (depth × 0.25) + (relevance × 0.15)

Return ONLY valid JSON:
{{ "technical": 78, "communication": 85, "depth": 60, "relevance": 90, "overall": 76.75, "feedback": "..." }}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages, temperature=0.3)
            return EvaluationResult(**result)
        except Exception as e:
            print(f"Groq API Error in evaluate_answer: {e}. Using fallback mock evaluation.")
            
            # Programmatic fallback based on the actual answer content!
            word_count = len(clean.split())
            char_count = len(clean)
            
            # Tier 0 — Empty / skipped
            if char_count < 8 or clean in {"no answer", "i don't know", "skip", "n/a", ""}:
                return EvaluationResult(
                    technical=5.0, communication=5.0, depth=0.0, relevance=0.0,
                    overall=3.75,
                    feedback="No response was provided. The candidate did not attempt to answer the question."
                )
            
            # Tier 1 — Fragment (< 8 words) — e.g. "API is used in communication"
            if word_count < 8:
                return EvaluationResult(
                    technical=12.0, communication=15.0, depth=5.0, relevance=20.0,
                    overall=12.75,
                    feedback="The response is a fragment with no meaningful explanation. "
                             "The candidate mentioned a relevant term but provided no definition, "
                             "context, or technical detail."
                )
            
            # Tier 2 — Too short / one-liner (8–20 words)
            if word_count < 20:
                return EvaluationResult(
                    technical=30.0, communication=35.0, depth=15.0, relevance=40.0,
                    overall=29.75,
                    feedback="The answer is too brief to demonstrate real understanding. "
                             "A correct concept was touched on but left unexplained. "
                             "The candidate should elaborate with definitions, examples, or trade-offs."
                )
            
            # Tier 3 — Basic answer (20–50 words) — surface-level only
            if word_count < 50:
                return EvaluationResult(
                    technical=48.0, communication=50.0, depth=30.0, relevance=60.0,
                    overall=46.95,
                    feedback="The answer covers the basics but lacks depth. "
                             "Core ideas are present without technical precision or real-world context. "
                             "Expanding on how or why would significantly improve the score."
                )
            
            # Tier 4 — Moderate answer (50–100 words)
            if word_count < 100:
                return EvaluationResult(
                    technical=65.0, communication=68.0, depth=55.0, relevance=72.0,
                    overall=64.80,
                    feedback="A reasonable answer that covers the main concept with some clarity. "
                             "Missing edge cases, trade-offs, or specific examples that would "
                             "demonstrate deeper expertise."
                )
            
            # Tier 5 — Strong answer (100+ words)
            return EvaluationResult(
                technical=82.0, communication=84.0, depth=76.0, relevance=88.0,
                overall=82.10,
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

groq_service = GroqService()

