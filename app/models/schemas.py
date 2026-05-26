from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    target_role: Optional[str] = None
    experience_level: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class ProjectModel(BaseModel):
    name: str
    tech_stack: List[str] = []
    description: str = ""
    candidate_role: str = ""
    responsibilities: List[str] = []
    features_built: List[str] = []
    deployment: str = ""
    architecture: str = ""
    challenges: List[str] = []
    team_size: str = ""
    impact: str = ""

class ResumeAnalysis(BaseModel):
    skills: List[str]
    projects: List[ProjectModel]
    experience_years: float
    level: str

class QuestionModel(BaseModel):
    text: str
    type: str
    difficulty: str
    section: str = "Conceptual"

class QuestionGenerateResponse(BaseModel):
    questions: List[QuestionModel]

class AnswerSubmit(BaseModel):
    interview_id: str
    question_id: str
    transcript: str
    question_text: Optional[str] = None


class EvaluationResult(BaseModel):
    technical: float
    communication: float
    depth: float
    relevance: float
    overall: float
    feedback: str

class ViolationCreate(BaseModel):
    interview_id: str
    type: str

class InterviewComplete(BaseModel):
    interview_id: str

