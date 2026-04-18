from __future__ import annotations

import json
import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend_api.provider import normalize_provider, select_model_for_provider
from backend_api.schemas import ResumeParseResponse
from backend_api.state import app_state
from functions.resume_parsing.parser import ResumeParser

router = APIRouter(prefix="/api/v1/resume", tags=["resume"])


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(
    file: UploadFile = File(...),
    provider: str = Form("ollama"),
    model: str = Form("qwen3.5:2b"),
    think: bool = Form(True),
) -> ResumeParseResponse:
    suffix = os.path.splitext(file.filename or "resume.pdf")[1] or ".pdf"
    tmp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        normalized_provider = normalize_provider(provider)
        selected_model = select_model_for_provider(normalized_provider, model, prefer_requested=True)

        parser = ResumeParser(model=selected_model, provider=normalized_provider, think=think)
        result_tuple, raw_text = parser.parse(tmp_path)
        resume_data = result_tuple[0] if isinstance(result_tuple, tuple) else result_tuple
        debug_info = parser.get_debug_info()

        if not resume_data:
            raise HTTPException(status_code=422, detail="Resume extraction failed")

        app_state.current_resume_data = resume_data
        app_state.current_resume_text = raw_text

        rag = app_state.get_rag_engine()
        if rag and raw_text:
            rag.ingest_text(raw_text, metadata={"source": file.filename or "upload"})

        suggested_role = ""
        if resume_data.suggested_roles:
            suggested_role = resume_data.suggested_roles[0]

        return ResumeParseResponse(
            resume_data=json.loads(resume_data.model_dump_json(exclude_none=False)),
            raw_text=raw_text,
            debug_info=debug_info,
            suggested_role=suggested_role,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
