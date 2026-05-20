from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import json

router = APIRouter()

@router.get("/export/{file_id}/json")
async def export_json(file_id: str):
    """Export questions as JSON"""
    
    data = {
        "file_id": file_id,
        "questions": [
            {
                "question_no": 1,
                "question": "Sample question",
                "options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                "correct_answer": "A"
            }
        ]
    }
    
    return JSONResponse(content=data)

@router.get("/export/{file_id}/csv")
async def export_csv(file_id: str):
    """Export as CSV"""
    
    return {"message": "CSV export ready", "file_id": file_id}