from __future__ import annotations

import logging

from functions.chat.rag_engine import RAGEngine
from functions.common.models import ResumeData
from functions.interview.interviewer import InterviewManager
from functions.tracker.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class AppState:
    def __init__(self) -> None:
        self.current_resume_data: ResumeData | None = None
        self.current_resume_text: str = ""
        self.last_fetched_jobs: list[dict] = []
        self.tracker = ApplicationTracker(storage_path="data/applications.json")
        self.interview_manager = InterviewManager(output_dir="temp_audio")
        self._rag_engine: RAGEngine | None = None

    def get_rag_engine(self) -> RAGEngine | None:
        if self._rag_engine is not None:
            return self._rag_engine
        try:
            self._rag_engine = RAGEngine()
            return self._rag_engine
        except Exception as exc:
            logger.error("Failed to initialize RAG engine: %s", exc)
            return None


app_state = AppState()
