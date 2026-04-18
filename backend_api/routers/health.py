from fastapi import APIRouter

from backend_api.schemas import SystemStatusResponse
from backend_api.state import app_state
from functions.resume_parsing.ai_extractor import check_ollama_connection

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    ollama_ready = bool(check_ollama_connection())
    rag_ready = app_state.get_rag_engine() is not None
    message = "System ready" if ollama_ready else "Ollama unavailable"
    return SystemStatusResponse(
        ollama_ready=ollama_ready,
        rag_ready=rag_ready,
        message=message,
    )
