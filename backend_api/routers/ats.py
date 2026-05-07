from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend_api.schemas import ATSScoreRequest, ATSScoreResponse
from backend_api.state import app_state
from functions.common.llama_cpp_client import default_model as llama_cpp_default_model
from functions.ats.scorer import ATSScorer
from backend_api.database import get_db
from backend_api.models import ATSScoreHistory

router = APIRouter(prefix="/api/v1/ats", tags=["ats"])


@router.post("/score", response_model=ATSScoreResponse)
async def score_resume(payload: ATSScoreRequest, db: AsyncSession = Depends(get_db)) -> ATSScoreResponse:
    if app_state.current_resume_data is None:
        raise HTTPException(status_code=400, detail="Parse a resume first")

    selected_model = payload.model
    if payload.provider == "gemini":
        selected_model = "gemini-2.5-flash"
    elif payload.provider in {"llama.cpp", "llama_cpp", "llamacpp"}:
        selected_model = llama_cpp_default_model()

    try:
        scorer = ATSScorer(model=selected_model, provider=payload.provider, think=payload.think)
        result = scorer.calculate_score(app_state.current_resume_data, payload.job_description)
        
        # Save to PostgreSQL without resume_data
        db_record = ATSScoreHistory(
            job_description=payload.job_description,
            model=selected_model,
            score=result.score,
            breakdown=result.breakdown,
            metadata_=getattr(result, "metadata", None) or {}
        )
        db.add(db_record)
        await db.commit()
        await db.refresh(db_record)
        
        return ATSScoreResponse(**result.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
