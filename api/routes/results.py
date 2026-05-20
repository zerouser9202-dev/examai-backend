from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/results/{file_id}")
async def get_results(file_id: str):
    """Get OCR processing results"""
    
    return {
        "success": True,
        "file_id": file_id,
        "status": "completed",
        "pages_processed": 5,
        "questions_extracted": 25,
        "message": "Results ready"
    }

@router.get("/results/{file_id}/questions")
async def get_questions(file_id: str):
    """Get extracted questions"""
    
    return {
        "file_id": file_id,
        "total_questions": 25,
        "questions": [
            {
                "question_no": 1,
                "question": "What is the capital of India?",
                "options": {"A": "Mumbai", "B": "Delhi", "C": "Kolkata", "D": "Chennai"},
                "correct_answer": "B"
            }
        ]
    }