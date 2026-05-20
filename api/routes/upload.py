from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
from datetime import datetime
from config.settings import settings

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a PDF or image file for processing"""
    
    # Check if filename exists
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Check file extension - FIXED: Handle None case
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    stored_filename = f"{unique_id}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_filename)
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    file_size = len(content)
    
    return {
        "success": True,
        "file_id": unique_id,
        "original_filename": filename,
        "stored_filename": stored_filename,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "status": "uploaded",
        "message": "File uploaded successfully"
    }