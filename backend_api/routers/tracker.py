from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend_api.schemas import TrackerCreateRequest, TrackerUpdateRequest
from backend_api.state import app_state
from functions.tracker.tracker import VALID_ROLE_TYPES, VALID_STATUSES

router = APIRouter(prefix="/api/v1/tracker", tags=["tracker"])


@router.get("/applications")
def get_applications() -> list[dict]:
    return [a.model_dump() for a in app_state.tracker.get_all()]


@router.get("/applications/{app_id}")
def get_application(app_id: str) -> dict:
    item = app_state.tracker.get_by_id(app_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return item.model_dump()


@router.post("/applications")
def create_application(payload: TrackerCreateRequest) -> dict:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    if payload.role_type not in VALID_ROLE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid role type")

    item = app_state.tracker.add(
        job_title=payload.job_title,
        company=payload.company,
        role_type=payload.role_type,
        status=payload.status,
        application_date=payload.application_date,
        job_url=payload.job_url,
        notes=payload.notes,
    )
    return item.model_dump()


@router.put("/applications/{app_id}")
def update_application(app_id: str, payload: TrackerUpdateRequest) -> dict:
    if payload.status is not None and payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    if payload.role_type is not None and payload.role_type not in VALID_ROLE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid role type")

    item = app_state.tracker.update(
        app_id=app_id,
        job_title=payload.job_title,
        company=payload.company,
        role_type=payload.role_type,
        status=payload.status,
        application_date=payload.application_date,
        job_url=payload.job_url,
        notes=payload.notes,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return item.model_dump()


@router.delete("/applications/{app_id}")
def delete_application(app_id: str) -> dict[str, bool]:
    deleted = app_state.tracker.delete(app_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"deleted": True}


@router.get("/stats")
def get_stats() -> dict[str, int]:
    return app_state.tracker.get_stats()


@router.get("/reference/statuses")
def get_statuses() -> dict[str, list[str]]:
    return {"statuses": VALID_STATUSES}


@router.get("/reference/role-types")
def get_role_types() -> dict[str, list[str]]:
    return {"role_types": VALID_ROLE_TYPES}
