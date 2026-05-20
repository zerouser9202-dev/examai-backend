from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ProcessRequest(BaseModel):
    file_id: str

@router.post("/process")
async def process_file(request: ProcessRequest):
    """Start OCR processing on uploaded file"""
    
    return {
        "success": True,
        "file_id": request.file_id,
        "status": "queued",
        "message": "Processing started. Check /results/{file_id} for status"
    }

@router.post("/process/{file_id}")
async def process_file_by_id(file_id: str):
    """Process file by ID"""
    
    return {
        "success": True,
        "file_id": file_id,
        "status": "processing",
        "message": "OCR processing initiated"
    }