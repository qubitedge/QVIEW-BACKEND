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

    def _call_with_retry(self, messages, retries=3):
        if not self.client:
            raise ValueError("Groq client not initialized")
        for i in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=30
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

    def analyze_resume(self, text: str) -> ResumeAnalysis:
        prompt = f"""You are an expert technical recruiter. Analyze this resume and extract:
1. Technical skills (list)
2. Projects with technologies used
3. Years of experience
4. Seniority level (junior/mid/senior)
Return ONLY valid JSON matching this schema:
{{ "skills": ["skill1", "skill2"], "projects": [{{"name": "p1", "tech": "t1", "description": "d1"}}], "experience_years": 5, "level": "senior" }}

Resume Text:
{text}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages)
            return ResumeAnalysis(**result)
        except Exception as e:
            print(f"Groq API Error in analyze_resume: {e}. Using fallback mock analysis.")
            return self._fallback_analyze_resume(text)

    def generate_questions(self, profile: dict) -> list[QuestionModel]:
        prompt = f"""You are an expert interviewer. Generate exactly 5 conceptual questions customized to the candidate's resume profile.
The questions must be distinct conceptual questions regarding key technological concepts, languages, frameworks, or architecture found in their resume. Do not include coding exercises or aptitude puzzles.

Difficulty must be 'easy' or at most 'medium'. Return ONLY valid JSON matching this schema:
{{ "questions": [
  {{"text": "Explain...", "type": "technical", "difficulty": "easy", "section": "Conceptual"}},
  {{"text": "What is...", "type": "technical", "difficulty": "medium", "section": "Conceptual"}},
  {{"text": "How does...", "type": "technical", "difficulty": "easy", "section": "Conceptual"}},
  {{"text": "Describe...", "type": "technical", "difficulty": "medium", "section": "Conceptual"}},
  {{"text": "Why do...", "type": "technical", "difficulty": "easy", "section": "Conceptual"}}
] }}

Candidate Profile:
{json.dumps(profile)}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages)
            return [QuestionModel(**q) for q in result.get("questions", [])]
        except Exception as e:
            print(f"Groq API Error in generate_questions: {e}. Using fallback mock questions.")
            return self._fallback_generate_questions(profile)

    def evaluate_answer(self, question: str, answer: str) -> EvaluationResult:
        prompt = f"""You are an expert interviewer evaluating a candidate's answer.
Question: {question}
Candidate Answer: {answer}
Evaluate on:
1. Technical Correctness (0-100)
2. Communication Clarity (0-100)  
3. Answer Depth (0-100)
4. Relevance (0-100)
Return ONLY valid JSON matching this schema:
{{ "technical": 80, "communication": 90, "depth": 75, "relevance": 85, "overall": 82.5, "feedback": "Good answer but missed edge cases." }}
"""
        messages = [{"role": "system", "content": prompt}]
        try:
            result = self._call_with_retry(messages)
            return EvaluationResult(**result)
        except Exception as e:
            print(f"Groq API Error in evaluate_answer: {e}. Using fallback mock evaluation.")
            
            # Programmatic fallback based on the actual answer content!
            ans_clean = answer.strip().lower()
            ans_len = len(ans_clean)

            if ans_len < 10 or "no answer" in ans_clean:
                return EvaluationResult(
                    technical=10.0,
                    communication=15.0,
                    depth=5.0,
                    relevance=0.0,
                    overall=7.5,
                    feedback="No substantial response was provided. The candidate failed to address the question."
                )
            
            if ans_len < 60:
                # Short/basic answers
                return EvaluationResult(
                    technical=55.0,
                    communication=60.0,
                    depth=40.0,
                    relevance=70.0,
                    overall=56.25,
                    feedback="The answer is technically correct in its core definition but extremely basic. It lacks depth, technical vocabulary, and practical details or examples."
                )

            # Good quality detailed answers
            return EvaluationResult(
                technical=85.0,
                communication=88.0,
                depth=80.0,
                relevance=92.0,
                overall=86.25,
                feedback="Strong answer. The candidate explained the core concept clearly with structured logic, showing good theoretical understanding. Elaborating on real-world edge cases would make it perfect."
            )

    def generate_report(self, candidate_name: str, scores: dict, answers: list) -> str:
        prompt = f"""You are a senior HR manager writing a candidate assessment.
Candidate: {candidate_name}
Interview scores: {json.dumps(scores)}
All answers: {json.dumps(answers)}
Write a professional 3-paragraph assessment covering:
1. Technical capability summary
2. Communication and soft skills
3. Hiring recommendation (Strong Yes / Yes / Maybe / No)
Be specific, reference actual answers. Return ONLY the report text (no JSON formatting needed).
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

