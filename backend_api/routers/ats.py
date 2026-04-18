from fastapi import APIRouter, HTTPException

from backend_api.provider import normalize_provider, select_model_for_provider
from backend_api.schemas import ATSScoreRequest, ATSScoreResponse
from backend_api.state import app_state
from functions.ats.scorer import ATSScorer

router = APIRouter(prefix="/api/v1/ats", tags=["ats"])


@router.post("/score", response_model=ATSScoreResponse)
def score_resume(payload: ATSScoreRequest) -> ATSScoreResponse:
    if app_state.current_resume_data is None:
        raise HTTPException(status_code=400, detail="Parse a resume first")

    provider = normalize_provider(payload.provider)
    selected_model = select_model_for_provider(provider, payload.model, prefer_requested=False)

    try:
        scorer = ATSScorer(model=selected_model, provider=provider, think=payload.think)
        result = scorer.calculate_score(app_state.current_resume_data, payload.job_description)
        return ATSScoreResponse(**result.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
