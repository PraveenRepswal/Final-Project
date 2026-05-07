# AI Job Assistant

AI Job Assistant is an API-first platform for resume intelligence and job search workflows.
It combines resume parsing, ATS scoring, resume-grounded chat (RAG), remote job search, semantic job ranking, mock interview simulation, and job application tracking.

For deeper architecture and flow notes, see [Project details.md](Project%20details.md).

## Current Progress Snapshot

### Completed and Integrated
- FastAPI backend with modular routers and shared runtime state.
- Static multi-page frontend served by backend.
- Resume parsing with provider switching (Ollama, Gemini, llama.cpp).
- ATS scoring with LLM-first path and fallback behavior.
- RAG chat over parsed resume text with streaming support.
- Remote job search + semantic ranking.
- Voice mock interview flow (start, turn, end, report).
- JSON-backed application tracker CRUD + stats.

### Current Implementation Status
- Single-user session state is active and stable.
- Tracker persistence is file-based (`data/applications.json`).
- RAG vector index is in-memory (recreated on app restart).
- Frontend pages are feature-connected via `frontend/api-client.js`.

### Not Yet Implemented
- Multi-user authentication and role-based access.
- Database persistence for resumes/interviews/RAG vectors.
- Production deployment profile (workers, scaling, observability).

## Key Features

### Resume Parsing
- Accepts PDF and DOCX files.
- Extracts structured profile fields (contact, education, experience, projects, skills, suggested roles).
- Stores parsed resume data and text in app state.
- Ingests resume text into RAG chunks automatically after parsing.

### ATS Scoring
- Scores parsed resume against job description.
- Returns score, breakdown, missing keywords, formatting issues, and suggestions.
- Supports provider-aware model routing.

### Resume Chat (RAG)
- Resume-grounded Q and A.
- Uses Sentence-Transformers embeddings with Qdrant (in-memory).
- Supports standard and streaming query endpoints.

### Job Search and Ranking
- Searches remote jobs via integrated job sources.
- Ranks jobs semantically against resume text/profile.
- Reuses embedding model from RAG engine.

### Mock Interview
- Start interview with resume context.
- Upload spoken answers turn by turn.
- STT -> interviewer response -> optional TTS.
- End interview to receive compiled report.

### Application Tracker
- Create, read, update, delete job applications.
- Track status, role type, date, URL, notes.
- Stats endpoint for total/interviews/offers/rejections.
- Data persisted to JSON file.

## Architecture

- Backend: FastAPI with routers in `backend_api/routers`.
- Domain logic: `functions/*` modules.
- Frontend: static HTML + JS in `frontend`.
- Runtime state: `backend_api/state.py`.
- Static entry points:
  - `/app`
  - `/app/{page_name}`

## API Overview

Base URL: `http://127.0.0.1:8000`

### Health
- `GET /api/v1/health`
- `GET /api/v1/system/status`

### Resume
- `POST /api/v1/resume/parse`

### ATS
- `POST /api/v1/ats/score`

### Chat
- `POST /api/v1/chat/query`
- `POST /api/v1/chat/query/stream`

### Jobs
- `POST /api/v1/jobs/search`
- `POST /api/v1/jobs/rank`

### Interview
- `POST /api/v1/interview/start`
- `POST /api/v1/interview/turn`
- `POST /api/v1/interview/end`

### Tracker
- `GET /api/v1/tracker/applications`
- `GET /api/v1/tracker/applications/{app_id}`
- `POST /api/v1/tracker/applications`
- `PUT /api/v1/tracker/applications/{app_id}`
- `DELETE /api/v1/tracker/applications/{app_id}`
- `GET /api/v1/tracker/stats`
- `GET /api/v1/tracker/reference/statuses`
- `GET /api/v1/tracker/reference/role-types`

## Setup

### Prerequisites
- Python 3.12+
- pip
- Optional provider backends:
  - Ollama for local model serving
  - Gemini API key
  - llama.cpp OpenAI-compatible server

### 1) Create and activate virtual environment (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure environment variables

Create a `.env` file in project root as needed:

```env
# Optional Gemini
GEMINI_API_KEY=your_key_here

# Optional llama.cpp
LLAMA_CPP_BASE_URL=http://127.0.0.1:8000
LLAMA_CPP_MODEL=local-model
LLAMA_CPP_API_KEY=

# Optional Ollama override
OLLAMA_CHAT_URL=http://127.0.0.1:11434/api/chat
```

### 4) Start model provider(s)

Example Ollama setup:

```powershell
ollama serve
ollama pull qwen3.5:2b
```

```powershell
llama-server -m "X:\LlamaModels\Qwen3.5-2B-GGUF\Qwen3.5-2B-Q8_0.gguf" -rea off
```

### 5) Run backend API

```powershell
uvicorn backend_api.main:app --reload --host 127.0.0.1 --port 8000
```

### 6) Open frontend

- Home: `http://127.0.0.1:8000/app`
- Any page directly: `http://127.0.0.1:8000/app/main.html`

## Frontend Pages

- `frontend/main.html` - Home and resume upload entry.
- `frontend/ATS.html` - ATS scoring.
- `frontend/CWR.html` - Chat with resume.
- `frontend/JS.html` - Job search and ranking.
- `frontend/Application Tracker.html` - Application tracker.
- `frontend/MI.html` - Mock interview.
- `frontend/Analytics.html` - Tracker analytics.
- `frontend/Interview_report.html` - Interview report view.

## Project Structure

```text
backend_api/
  main.py
  provider.py
  schemas.py
  state.py
  routers/
functions/
  resume_parsing/
  ats/
  chat/
  interview/
  job_portal/
  tracker/
frontend/
data/
tests/
```

## Verification

Quick checks after startup:

```powershell
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/system/status
```

Utility test scripts are available in `tests/`.

## Known Limitations

- App state is process-local and not shared across instances.
- RAG index is not persisted across restart.
- No user-level separation for tracker or interview sessions.
- External provider availability directly impacts feature readiness.

