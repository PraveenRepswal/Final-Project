from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime
from sqlalchemy.sql import func
from .database import Base

class ATSScoreHistory(Base):
    __tablename__ = "ats_score_history"

    id = Column(Integer, primary_key=True, index=True)
    job_description = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    breakdown = Column(JSON, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String, nullable=False)
    report = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ApplicationTracker(Base):
    __tablename__ = "application_tracker"

    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    role_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    application_date = Column(String, nullable=True)
    job_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
