from fastapi import APIRouter, HTTPException

from backend_api.schemas import JobRankRequest, JobsResponse, JobSearchRequest
from backend_api.state import app_state
from functions.job_portal.matcher import JobMatcher
from functions.job_portal.search import search_jobs

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/search", response_model=JobsResponse)
def search(payload: JobSearchRequest) -> JobsResponse:
    query = payload.role
    if payload.location:
        query = f"{payload.role}, {payload.location}"

    jobs = search_jobs(query)
    app_state.last_fetched_jobs = jobs
    return JobsResponse(jobs=jobs)


@router.post("/rank", response_model=JobsResponse)
def rank(payload: JobRankRequest) -> JobsResponse:
    rag = app_state.get_rag_engine()
    if rag is None or rag.embedding_model is None:
        raise HTTPException(status_code=400, detail="Embedding model unavailable")

    try:
        jobs = payload.jobs or app_state.last_fetched_jobs
        matcher = JobMatcher(embedding_model=rag.embedding_model)
        ranked = matcher.match_jobs(payload.resume_text, jobs)
        return JobsResponse(jobs=ranked)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
