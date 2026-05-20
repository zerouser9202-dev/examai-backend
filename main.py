"""
ExamAI - Enterprise OCR Exam Processing System
Main FastAPI Application Entry Point
"""
import sys
import os
from pathlib import Path

# Add current directory to path - IMPORTANT!
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
import time

# Import local modules
from config.settings import settings
from database.connection import init_db
from api.routes import upload, process, results, evaluate, export, auth, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("🚀 ExamAI starting up...")
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database init skipped: {e}")
    yield
    logger.info("🛑 ExamAI shutting down...")


app = FastAPI(
    title="ExamAI - OCR Exam Processing System",
    description="Enterprise-grade AI-powered OCR examination platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )


# Register routers - Comment out if routes don't exist yet
try:
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
except: pass
try:
    app.include_router(upload.router, prefix="/api", tags=["Upload"])
except: pass
try:
    app.include_router(process.router, prefix="/api", tags=["Processing"])
except: pass
try:
    app.include_router(results.router, prefix="/api", tags=["Results"])
except: pass
try:
    app.include_router(evaluate.router, prefix="/api", tags=["Evaluation"])
except: pass
try:
    app.include_router(export.router, prefix="/api", tags=["Export"])
except: pass
try:
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
except: pass


@app.get("/")
async def root():
    return {"message": "ExamAI Backend Running", "status": "active"}


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "ExamAI Backend"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)