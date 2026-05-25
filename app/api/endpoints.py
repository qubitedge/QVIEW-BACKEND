from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
import uuid
import os
import json

from app.models.schemas import (
    CandidateCreate, ResumeAnalysis, QuestionGenerateResponse, AnswerSubmit, 
    EvaluationResult, ViolationCreate, InterviewComplete
)
from app.services.groq_service import groq_service
from app.services.resume_parser import resume_parser
from app.services.storage_service import storage_service

router = APIRouter()

DB_FILE = "mock_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("AIHireX Database: Error loading JSON file:", e)
    return {
        "candidates": {},
        "interviews": {},
        "questions": {},
        "answers": {},
        "violations": {}
    }

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        print("AIHireX Database: Error saving JSON file:", e)

# Mock DB for demonstration since actual Supabase DB interaction via python client requires setup
# In a real app, we'd use Supabase python client to interact with the DB.
mock_db = load_db()

def get_current_user():
    # Mock auth dependency
    return {"id": "mock-candidate-id", "role": "candidate"}

def get_admin_user():
    # Mock admin auth dependency
    return {"id": "mock-admin-id", "role": "admin"}

@router.post("/auth/register")
async def register(candidate: CandidateCreate):
    candidate_id = str(uuid.uuid4())
    mock_db["candidates"][candidate_id] = {
        "id": candidate_id,
        "name": candidate.name,
        "email": candidate.email,
        "target_role": candidate.target_role,
        "experience_level": candidate.experience_level,
        "created_at": str(datetime.now())
    }
    save_db(mock_db)
    return {"message": "Candidate registered successfully", "id": candidate_id}

@router.post("/auth/login")
async def login(email: str = Form(...), password: str = Form(...)):
    # Mock login
    return {"access_token": "mock-jwt-token", "token_type": "bearer"}

@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...), 
    candidate_id: str = Form("mock-candidate-id")
):
    contents = await file.read()
    
    # Extract text based on file type
    if file.filename.endswith('.pdf'):
        text = resume_parser.parse_pdf(contents)
    elif file.filename.endswith('.docx'):
        text = resume_parser.parse_docx(contents)
    else:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
        
    # Upload to storage
    url = storage_service.upload_resume(contents, file.filename, candidate_id)
    
    return {"url": url, "extracted_text": text}

@router.post("/resume/analyze", response_model=ResumeAnalysis)
async def analyze_resume(text: str = Form(...)):
    analysis = groq_service.analyze_resume(text)
    return analysis

@router.post("/questions/generate", response_model=QuestionGenerateResponse)
async def generate_questions(profile: dict):
    questions = groq_service.generate_questions(profile)
    return {"questions": questions}

@router.post("/interview/start")
async def start_interview(candidate_id: str = Form(...)):
    interview_id = str(uuid.uuid4())
    mock_db["interviews"][interview_id] = {
        "id": interview_id,
        "candidate_id": candidate_id,
        "status": "active",
        "started_at": str(datetime.now())
    }
    save_db(mock_db)
    return {"interview_id": interview_id}

@router.post("/interview/submit-answer")
async def submit_answer(answer: AnswerSubmit):
    # Retrieve question text passed from frontend
    question_text = answer.question_text or "What is your experience with React?"
    
    evaluation = groq_service.evaluate_answer(question_text, answer.transcript)
    
    answer_id = str(uuid.uuid4())
    mock_db["answers"][answer_id] = {
        "id": answer_id,
        "interview_id": answer.interview_id,
        "question_id": answer.question_id,
        "question_text": question_text,
        "transcript": answer.transcript,
        "evaluation": evaluation.dict()
    }
    save_db(mock_db)
    return evaluation

@router.post("/interview/complete")
async def complete_interview(req: InterviewComplete):
    interview_id = req.interview_id
    if interview_id in mock_db["interviews"]:
        mock_db["interviews"][interview_id]["status"] = "completed"
        mock_db["interviews"][interview_id]["ended_at"] = str(datetime.now())
        
        # Fetch candidate details
        cand_id = mock_db["interviews"][interview_id]["candidate_id"]
        cand_name = mock_db.get("candidates", {}).get(cand_id, {}).get("name", "Candidate")
        
        # Gather real answers and scores
        answers = [a for a in mock_db.get("answers", {}).values() if a["interview_id"] == interview_id]
        if answers:
            overall = sum(a["evaluation"].get("overall", 0) for a in answers) / len(answers)
        else:
            overall = 0
            
        formatted_answers = [{"q": a.get("question_text", ""), "a": a.get("transcript", "")} for a in answers]
        
        report = groq_service.generate_report(
            cand_name, 
            {"overall": round(overall, 2)}, 
            formatted_answers
        )
        mock_db["interviews"][interview_id]["ai_feedback"] = report
        save_db(mock_db)
        return {"message": "Interview completed", "report": report}
    raise HTTPException(status_code=404, detail="Interview not found")

@router.get("/interview/{id}")
async def get_interview(id: str):
    if id in mock_db["interviews"]:
        return mock_db["interviews"][id]
    raise HTTPException(status_code=404, detail="Interview not found")

@router.get("/interview/{id}/report")
async def get_interview_report(id: str):
    if id in mock_db["interviews"]:
        return {"report": mock_db["interviews"][id].get("ai_feedback", "")}
    raise HTTPException(status_code=404, detail="Interview not found")

@router.get("/interview/{id}/results")
async def get_interview_results(id: str):
    interview_id = id
    if interview_id not in mock_db["interviews"]:
        # Fallback: check if id is a candidate_id and find their latest interview
        candidate_interviews = [
            intv for intv in mock_db.get("interviews", {}).values()
            if intv.get("candidate_id") == id
        ]
        if candidate_interviews:
            # Sort by started_at descending to get the latest interview
            candidate_interviews.sort(key=lambda x: x.get("started_at", ""), reverse=True)
            interview_id = candidate_interviews[0]["id"]
        else:
            raise HTTPException(status_code=404, detail="Interview not found")
        
    interview = mock_db["interviews"][interview_id]
    
    # Gather answers for this interview
    answers = [a for a in mock_db.get("answers", {}).values() if a["interview_id"] == interview_id]
    
    # Calculate scores
    total_tech = sum(a["evaluation"]["technical"] for a in answers) if answers else 0
    total_comm = sum(a["evaluation"]["communication"] for a in answers) if answers else 0
    total_depth = sum(a["evaluation"]["depth"] for a in answers) if answers else 0
    
    count = len(answers) if answers else 1
    
    tech_score = round(total_tech / count)
    comm_score = round(total_comm / count)
    depth_score = round(total_depth / count)
    overall_score = round((tech_score + comm_score + depth_score) / 3)
    
    formatted_questions = []
    for a in answers:
        formatted_questions.append({
            "q": a.get("question_text", "Unknown question"),
            "a": a.get("transcript", "No answer provided"),
            "score": round(a["evaluation"].get("overall", 0)),
            "feedback": a["evaluation"].get("feedback", "")
        })
        
    # Get violations count
    violations = [v for v in mock_db.get("violations", {}).values() if v["interview_id"] == interview_id]
    
    # Retrieve Candidate details
    cand_id = interview.get("candidate_id")
    candidate = mock_db.get("candidates", {}).get(cand_id, {
        "name": "Unknown Candidate",
        "email": "unknown@example.com",
        "target_role": "Software Engineer",
        "experience_level": "Junior (0-2 years)"
    })
        
    return {
        "candidate_id": cand_id,
        "status": interview.get("status", "completed"),
        "overall_score": overall_score,
        "technical_score": tech_score,
        "communication_score": comm_score,
        "depth_score": depth_score,
        "ai_feedback": interview.get("ai_feedback", "Report generated automatically based on your answers."),
        "violations": len(violations),
        "questions": formatted_questions,
        "candidate": {
            "name": candidate.get("name"),
            "email": candidate.get("email"),
            "target_role": candidate.get("target_role", "Software Engineer"),
            "experience_level": candidate.get("experience_level", "Junior (0-2 years)")
        }
    }

@router.post("/evaluate/answer", response_model=EvaluationResult)
async def evaluate_answer(question: str = Form(...), answer: str = Form(...)):
    evaluation = groq_service.evaluate_answer(question, answer)
    return evaluation

@router.post("/report/generate")
async def generate_report(name: str = Form(...), scores: str = Form(...), answers: str = Form(...)):
    import json
    report = groq_service.generate_report(name, json.loads(scores), json.loads(answers))
    return {"report": report}

@router.post("/proctor/violation")
async def log_violation(violation: ViolationCreate):
    interview_id = violation.interview_id
    v_id = str(uuid.uuid4())
    
    if "violations" not in mock_db:
        mock_db["violations"] = {}
        
    mock_db["violations"][v_id] = {
        "id": v_id,
        "interview_id": interview_id,
        "type": violation.type,
        "timestamp": str(datetime.now())
    }
    
    # Check if this is an instant-fail violation (tab switch or fullscreen exit)
    is_instant_fail = violation.type in ['tab_switch', 'fullscreen_exit']
    
    # Count webcam/facial proctoring warnings (excluding instant fails)
    webcam_violations = [v for v in mock_db["violations"].values() if v["interview_id"] == interview_id and v["type"] not in ['tab_switch', 'fullscreen_exit']]
    webcam_count = len(webcam_violations)
    
    # Get total violations count
    total_count = sum(1 for v in mock_db["violations"].values() if v["interview_id"] == interview_id)
    
    if is_instant_fail:
        # Create 3 separate violations to penalize and instantly terminate the candidate
        for i in range(3):
            sub_id = f"{v_id}_tab_{i}"
            mock_db["violations"][sub_id] = {
                "id": sub_id,
                "interview_id": interview_id,
                "type": violation.type,
                "timestamp": str(datetime.now())
            }
            
        # Recalculate total violations count after inserting the penalty
        total_count = sum(1 for v in mock_db["violations"].values() if v["interview_id"] == interview_id)
        
        if interview_id in mock_db["interviews"]:
            mock_db["interviews"][interview_id]["status"] = "failed"
            mock_db["interviews"][interview_id]["failure_reason"] = f"Instant termination due to forbidden action: {violation.type}"
        save_db(mock_db)
        return {"failed": True, "violations_count": total_count, "reason": "tab_switch"}
        
    if webcam_count >= 3:
        if interview_id in mock_db["interviews"]:
            mock_db["interviews"][interview_id]["status"] = "failed"
            mock_db["interviews"][interview_id]["failure_reason"] = "Exceeded maximum webcam proctoring warnings (3)"
        save_db(mock_db)
        return {"failed": True, "violations_count": total_count, "reason": "webcam_limit"}
        
    save_db(mock_db)
    return {"failed": False, "violations_count": total_count}

@router.get("/proctor/{interview_id}/violations")
async def get_violations(interview_id: str):
    vlist = [v for v in mock_db["violations"].values() if v["interview_id"] == interview_id]
    return {"violations": vlist}

@router.get("/admin/candidates")
async def get_all_candidates():
    return {"candidates": list(mock_db["candidates"].values())}

@router.get("/admin/interviews")
async def get_all_interviews():
    return {"interviews": list(mock_db["interviews"].values())}

@router.get("/admin/interview/{id}")
async def admin_get_interview(id: str):
    if id in mock_db["interviews"]:
        return mock_db["interviews"][id]
    raise HTTPException(status_code=404, detail="Interview not found")

@router.get("/admin/candidate/{id}")
async def admin_get_candidate(id: str):
    if id in mock_db["candidates"]:
        return mock_db["candidates"][id]
    raise HTTPException(status_code=404, detail="Candidate not found")

@router.patch("/admin/candidate/{id}")
async def update_candidate_status(id: str, status: str = Form(...)):
    if id in mock_db["candidates"]:
        mock_db["candidates"][id]["status"] = status
        save_db(mock_db)
        return mock_db["candidates"][id]
    raise HTTPException(status_code=404, detail="Candidate not found")

@router.post("/interview/{id}/draft")
async def save_draft(id: str, draft: dict):
    if "drafts" not in mock_db:
        mock_db["drafts"] = {}
    mock_db["drafts"][id] = {
        "question_index": draft.get("question_index", 0),
        "code_draft": draft.get("code_draft", ""),
        "text_draft": draft.get("text_draft", ""),
        "updated_at": str(datetime.now())
    }
    save_db(mock_db)
    return {"message": "Draft saved"}

@router.get("/interview/{id}/draft")
async def get_draft(id: str):
    drafts = mock_db.get("drafts", {})
    if id in drafts:
        return drafts[id]
    return {"question_index": 0, "code_draft": "", "text_draft": ""}

@router.post("/admin/interview/{id}/warn")
async def send_warning(id: str, payload: dict):
    if id not in mock_db["interviews"]:
        raise HTTPException(status_code=404, detail="Interview not found")
    interview = mock_db["interviews"][id]
    if "admin_warnings" not in interview:
        interview["admin_warnings"] = []
    
    warning_msg = payload.get("message", "Please follow interview rules.")
    warning = {
        "id": str(uuid.uuid4()),
        "message": warning_msg,
        "timestamp": str(datetime.now()),
        "acknowledged": False
    }
    interview["admin_warnings"].append(warning)
    save_db(mock_db)
    return {"message": "Warning broadcasted", "warning": warning}

@router.get("/interview/{id}/warnings")
async def get_warnings(id: str):
    if id not in mock_db["interviews"]:
        return {"warnings": []}
    interview = mock_db["interviews"][id]
    warnings = interview.get("admin_warnings", [])
    unacknowledged = [w for w in warnings if not w.get("acknowledged", False)]
    for w in unacknowledged:
        w["acknowledged"] = True
    if unacknowledged:
        save_db(mock_db)
    return {"warnings": unacknowledged}

@router.get("/admin/dashboard")
async def get_admin_dashboard_stats():
    candidates = list(mock_db.get("candidates", {}).values())
    interviews = list(mock_db.get("interviews", {}).values())
    answers = list(mock_db.get("answers", {}).values())
    violations = list(mock_db.get("violations", {}).values())
    
    total_interviews = len(interviews)
    active_writing_count = sum(1 for intv in interviews if intv.get("status") == "active")
    completed_count = sum(1 for intv in interviews if intv.get("status") == "completed")
    failed_count = sum(1 for intv in interviews if intv.get("status") == "failed")
    
    # Calculate average score across completed interviews
    completed_interview_ids = {intv["id"] for intv in interviews if intv.get("status") == "completed"}
    completed_scores = []
    for intv_id in completed_interview_ids:
        intv_answers = [a for a in answers if a.get("interview_id") == intv_id]
        if intv_answers:
            avg_score = sum(a["evaluation"].get("overall", 0) for a in intv_answers) / len(intv_answers)
            completed_scores.append(avg_score)
    avg_score = round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else 82.5
    
    # Flagged count: interviews with more than 0 violations
    flagged_ids = {v.get("interview_id") for v in violations if v.get("interview_id")}
    flagged_count = len(flagged_ids)
    
    # Enriched candidate and interview list
    enriched_interviews = []
    for intv in interviews:
        cand_id = intv.get("candidate_id")
        candidate = mock_db.get("candidates", {}).get(cand_id, {
            "name": "Unknown", "email": "unknown@example.com", "target_role": "Software Engineer", "experience_level": "Junior"
        })
        
        # Calculate score
        intv_answers = [a for a in answers if a.get("interview_id") == intv["id"]]
        overall_score = 0
        if intv_answers:
            overall_score = round(sum(a["evaluation"].get("overall", 0) for a in intv_answers) / len(intv_answers))
        
        intv_violations = [v for v in violations if v.get("interview_id") == intv["id"]]
        
        enriched_interviews.append({
            "id": intv["id"],
            "candidate_id": cand_id,
            "name": candidate.get("name"),
            "email": candidate.get("email"),
            "target_role": candidate.get("target_role", "Software Engineer"),
            "experience_level": candidate.get("experience_level", "Junior (0-2 years)"),
            "status": intv.get("status"),
            "started_at": intv.get("started_at"),
            "ended_at": intv.get("ended_at"),
            "overall_score": overall_score,
            "violations_count": len(intv_violations),
            "failure_reason": intv.get("failure_reason")
        })
        
    return {
        "stats": {
            "total": total_interviews,
            "active_writing": active_writing_count,
            "completed": completed_count,
            "failed": failed_count,
            "avg_score": avg_score,
            "flagged": flagged_count
        },
        "interviews": enriched_interviews,
        "violations_log": violations[-20:]
    }

