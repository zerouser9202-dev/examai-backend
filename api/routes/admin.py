from fastapi import APIRouter

router = APIRouter()

@router.get("/stats")
async def admin_stats():
    return {"total_uploads": 0, "total_questions": 0}