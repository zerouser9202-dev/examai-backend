"""
Database Models - SQLAlchemy Async ORM
All core tables for ExamAI platform.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum, BigInteger, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class ProcessingStatus(str, PyEnum):
    PENDING = "pending"
    QUEUED = "queued"
    OCR_PROCESSING = "ocr_processing"
    AI_EXTRACTION = "ai_extraction"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class UserRole(str, PyEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TEACHER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    uploaded_files = relationship("UploadedFile", back_populates="user", lazy="dynamic")
    student_attempts = relationship("StudentAttempt", back_populates="user", lazy="dynamic")


# ─── Uploaded Files ────────────────────────────────────────────────────────────

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, png, jpg, etc.
    mime_type = Column(String(100), nullable=False)
    total_pages = Column(Integer, default=0)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    ocr_results = relationship("OCRResult", back_populates="file", cascade="all, delete-orphan")
    question_bank = relationship("QuestionBank", back_populates="file", uselist=False)

    __table_args__ = (
        Index("ix_uploaded_files_user_status", "user_id", "status"),
    )


# ─── OCR Results ───────────────────────────────────────────────────────────────

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=True)
    ocr_engine = Column(String(50), nullable=False)  # paddleocr | easyocr
    confidence_score = Column(Float, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    word_count = Column(Integer, default=0)
    has_hindi = Column(Boolean, default=False)
    has_equations = Column(Boolean, default=False)
    bounding_boxes = Column(JSON, nullable=True)  # Raw OCR bounding box data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("UploadedFile", back_populates="ocr_results")

    __table_args__ = (
        Index("ix_ocr_results_file_page", "file_id", "page_number"),
    )


# ─── Question Bank ─────────────────────────────────────────────────────────────

class QuestionBank(Base):
    __tablename__ = "question_banks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    subject = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    total_questions = Column(Integer, default=0)
    has_answer_key = Column(Boolean, default=False)
    language = Column(String(50), default="en")
    tags = Column(JSON, default=list)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    file = relationship("UploadedFile", back_populates="question_bank")
    questions = relationship("Question", back_populates="bank", cascade="all, delete-orphan", order_by="Question.question_number")
    exams = relationship("Exam", back_populates="question_bank", lazy="dynamic")


# ─── Questions ─────────────────────────────────────────────────────────────────

class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    correct_answer = Column(String(1), nullable=True)  # A, B, C, or D
    explanation = Column(Text, nullable=True)
    marks = Column(Float, default=1.0)
    negative_marks = Column(Float, default=0.0)
    difficulty = Column(String(20), nullable=True)  # easy | medium | hard
    topic = Column(String(255), nullable=True)
    source_page = Column(Integer, nullable=True)
    needs_review = Column(Boolean, default=False)
    review_reason = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)  # AI extraction confidence
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    bank = relationship("QuestionBank", back_populates="questions")
    attempt_answers = relationship("AttemptAnswer", back_populates="question", lazy="dynamic")

    __table_args__ = (
        Index("ix_questions_bank_number", "bank_id", "question_number"),
    )


# ─── Answer Keys ───────────────────────────────────────────────────────────────

class AnswerKey(Base):
    __tablename__ = "answer_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False)
    answers = Column(JSON, nullable=False)  # {"1": "B", "2": "A", ...}
    source = Column(String(50), default="extracted")  # extracted | manual | ai_generated
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ─── Exams ─────────────────────────────────────────────────────────────────────

class Exam(Base):
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_bank_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    instructions = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=60)
    total_marks = Column(Float, default=0)
    passing_marks = Column(Float, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    allow_review = Column(Boolean, default=True)
    shuffle_questions = Column(Boolean, default=False)
    show_result_immediately = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    question_bank = relationship("QuestionBank", back_populates="exams")
    attempts = relationship("StudentAttempt", back_populates="exam", lazy="dynamic")


# ─── Student Attempts ──────────────────────────────────────────────────────────

class StudentAttempt(Base):
    __tablename__ = "student_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_name = Column(String(255), nullable=True)
    roll_number = Column(String(100), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    status = Column(String(20), default="in_progress")  # in_progress | submitted | evaluated

    # Evaluation results (populated after submission)
    total_questions = Column(Integer, default=0)
    attempted = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    wrong = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    total_marks = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    result = Column(String(10), nullable=True)  # PASS | FAIL

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    exam = relationship("Exam", back_populates="attempts")
    user = relationship("User", back_populates="student_attempts")
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")


# ─── Attempt Answers ───────────────────────────────────────────────────────────

class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("student_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    selected_option = Column(String(1), nullable=True)  # A, B, C, D, or None (skipped)
    correct_option = Column(String(1), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    marks_obtained = Column(Float, default=0.0)
    time_spent_seconds = Column(Integer, nullable=True)

    # Relationships
    attempt = relationship("StudentAttempt", back_populates="answers")
    question = relationship("Question", back_populates="attempt_answers")


# ─── Exports ───────────────────────────────────────────────────────────────────

class Export(Base):
    __tablename__ = "exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=True)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("student_attempts.id", ondelete="CASCADE"), nullable=True)
    export_type = Column(String(50), nullable=False)  # pdf_exam, pdf_answer_key, json, csv, txt
    file_path = Column(String(1000), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    status = Column(String(20), default="pending")  # pending | completed | failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
