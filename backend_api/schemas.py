from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class APIError(BaseModel):
    detail: str


class SystemStatusResponse(BaseModel):
    ollama_ready: bool
    rag_ready: bool
    message: str


class ResumeParseResponse(BaseModel):
    resume_data: Optional[dict[str, Any]] = None
    raw_text: str = ""
    debug_info: str = ""
    suggested_role: str = ""


class ATSScoreRequest(BaseModel):
    job_description: str = Field(min_length=50)
    provider: str = "ollama"
    model: str = "qwen3.5:2b"
    think: bool = True


class ATSScoreResponse(BaseModel):
    score: int
    breakdown: dict[str, float]
    missing_keywords: list[str]
    formatting_issues: list[str]
    suggestions: list[str]
    reasoning: str = ""


class ChatQueryRequest(BaseModel):
    message: str = Field(min_length=1)
    provider: str = "ollama"
    model: str = "qwen3.5:2b"
    think: bool = True


class ChatQueryResponse(BaseModel):
    answer: str
    context: str
    prompt: str
    chunks: list[str]


class JobSearchRequest(BaseModel):
    role: str = Field(min_length=1)
    location: str = ""


class JobRankRequest(BaseModel):
    resume_text: str = Field(min_length=1)
    jobs: list[dict[str, Any]] = Field(default_factory=list)


class JobsResponse(BaseModel):
    jobs: list[dict[str, Any]]


class TrackerCreateRequest(BaseModel):
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    role_type: str = "Full-time"
    status: str = "Applied"
    application_date: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


class TrackerUpdateRequest(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    role_type: Optional[str] = None
    status: Optional[str] = None
    application_date: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


class InterviewStartRequest(BaseModel):
    resume_context: str = ""
    provider: str = "ollama"
    model: str = "qwen3.5:2b"
    think: bool = True


class InterviewStartResponse(BaseModel):
    question: str
    audio_path: Optional[str] = None


class InterviewTurnResponse(BaseModel):
    transcribed_answer: str
    next_question: str
    audio_path: Optional[str] = None
    latest_feedback: str


class InterviewEndResponse(BaseModel):
    report: str
