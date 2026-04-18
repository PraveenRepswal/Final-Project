from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend_api.provider import normalize_provider, select_model_for_provider
from backend_api.schemas import (
    InterviewEndResponse,
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewTurnResponse,
)
from backend_api.state import app_state

router = APIRouter(prefix="/api/v1/interview", tags=["interview"])


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(payload: InterviewStartRequest) -> InterviewStartResponse:
    try:
        manager = app_state.interview_manager
        normalized_provider = normalize_provider(payload.provider)
        selected_model = select_model_for_provider(normalized_provider, payload.model)
        manager.configure_llm(provider=normalized_provider, model=selected_model, think=payload.think)
        question, audio_path, _ = manager.start_interview(payload.resume_context)
        return InterviewStartResponse(question=question, audio_path=audio_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/turn", response_model=InterviewTurnResponse)
async def next_turn(
    audio: UploadFile = File(...),
    resume_context: str = Form(""),
) -> InterviewTurnResponse:
    suffix = os.path.splitext(audio.filename or "answer.wav")[1] or ".wav"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name

        manager = app_state.interview_manager
        user_text, next_question, audio_path, _ = manager.handle_turn(tmp_path, resume_context)
        return InterviewTurnResponse(
            transcribed_answer=user_text,
            next_question=next_question,
            audio_path=audio_path,
            latest_feedback=manager.get_latest_feedback(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/end", response_model=InterviewEndResponse)
def end_interview() -> InterviewEndResponse:
    try:
        report = app_state.interview_manager.end_interview()
        return InterviewEndResponse(report=report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
