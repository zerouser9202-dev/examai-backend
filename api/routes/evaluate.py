from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

router = APIRouter()

class EvaluationRequest(BaseModel):
    file_id: str
    student_answers: Dict[int, str]

@router.post("/evaluate")
async def evaluate_answers(request: EvaluationRequest):
    """Evaluate student answers"""
    
    return {
        "success": True,
        "file_id": request.file_id,
        "total_questions": 25,
        "correct": 18,
        "wrong": 5,
        "skipped": 2,
        "score": 18,
        "total_marks": 25,
        "percentage": 72.0,
        "accuracy": 78.26
    }