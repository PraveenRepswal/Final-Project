from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend_api.routers.ats import router as ats_router
from backend_api.routers.chat import router as chat_router
from backend_api.routers.health import router as health_router
from backend_api.routers.interview import router as interview_router
from backend_api.routers.jobs import router as jobs_router
from backend_api.routers.resume import router as resume_router
from backend_api.routers.tracker import router as tracker_router

load_dotenv()

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
FRONTEND_DIR_RESOLVED = FRONTEND_DIR.resolve()
TEMP_AUDIO_DIR = Path(__file__).resolve().parents[1] / "temp_audio"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="AI Job Assistant Backend",
    version="0.1.0",
    description="Backend API for resume parsing, ATS, chat, jobs, interview, and tracker",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(resume_router)
app.include_router(ats_router)
app.include_router(chat_router)
app.include_router(interview_router)
app.include_router(jobs_router)
app.include_router(tracker_router)

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

if TEMP_AUDIO_DIR.exists():
    app.mount("/temp_audio", StaticFiles(directory=str(TEMP_AUDIO_DIR)), name="temp_audio")


@app.get("/app", include_in_schema=False)
def app_home() -> FileResponse:
    index_file = FRONTEND_DIR / "main.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend home page not found")
    return FileResponse(
        index_file,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/app/{page_name}", include_in_schema=False)
def app_page(page_name: str) -> FileResponse:
    # Keep file serving constrained to frontend root to avoid traversal.
    page_file = (FRONTEND_DIR / Path(page_name).name).resolve()
    if page_file.parent != FRONTEND_DIR_RESOLVED or not page_file.exists() or not page_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend page not found")
    return FileResponse(
        page_file,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Job Assistant Backend API"}
