# Project Details - AI Job Assistant

## 1. Project Overview
AI Job Assistant is a Python-based, API-first system for resume intelligence and job search workflows. It combines resume parsing, ATS scoring, resume-grounded chat (RAG), remote job aggregation, semantic job ranking, mock interview simulation, and job application tracking.

The backend is built with FastAPI and serves both JSON APIs and static frontend pages. Core AI operations support multiple providers:
- Ollama (for local inference)
- llama.cpp server (OpenAI-compatible endpoint)(default)
- Gemini (Google GenAI)

## 2. Goals and Scope
Primary goals:
- Parse unstructured resumes (PDF/DOCX) into structured candidate data.
- Evaluate resume fit against a job description.
- Support conversational Q&A grounded in the uploaded resume.
- Search and rank jobs semantically against candidate profile.
- Run a voice-based mock interview with deferred evaluation.
- Persist and manage application tracking records.

Out-of-scope (current version):
- Multi-user authentication and tenant isolation.
- Database-backed persistence (tracker currently uses JSON file storage).
- Distributed deployment and autoscaling profiles.

## 3. Technology Stack

### 3.1 Backend and API
- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic v2
- python-dotenv

### 3.2 AI and LLM Integration
- Ollama REST API
- llama.cpp OpenAI-compatible server
- Google GenAI SDK (Gemini)
- LangChain core/community integrations

### 3.3 NLP, Embeddings, and Retrieval
- Sentence Transformers: all-MiniLM-L6-v2
- Qdrant (in-memory mode)
- langchain-qdrant
- langchain-text-splitters

### 3.4 Document Parsing
- pdfplumber
- pypdf
- python-docx

### 3.5 Interview Audio Pipeline
- faster-whisper (STT, tiny model in current manager)
- pocket-tts (TTS)
- transformers (available in repository for alternate STT paths)

### 3.6 Frontend
- Static HTML pages
- Vanilla JavaScript API client
- Backend-served static assets

### 3.7 Data and Storage
- JSON file persistence for tracker data: data/applications.json
- Ephemeral in-memory vector index for RAG
- Temporary audio files: temp_audio/

## 4. High-Level Design (HLD)

### 4.1 System Context
The system has three logical layers:
1. Presentation Layer: static HTML pages and JS API client.
2. Service Layer: FastAPI routers exposing feature APIs.
3. Domain/Engine Layer: function modules for parsing, scoring, retrieval, jobs, interview, and tracking.

### 4.2 Main Runtime Components
- API Gateway App: FastAPI application initialization and route registration.
- Shared App State:
  - current_resume_data
  - current_resume_text
  - cached last_fetched_jobs
  - tracker instance (JSON-backed)
  - interview manager instance
  - lazy-initialized RAG engine
- Feature Routers:
  - Health
  - Resume
  - ATS
  - Chat
  - Interview
  - Jobs
  - Tracker

### 4.3 Deployment Shape
Single-process backend service with local/remote model endpoints.
Typical local deployment:
- FastAPI at :8000
- Ollama at :11434
- Optional llama.cpp at :8000 or :8080 (separate endpoint host configurable)
- Optional Gemini cloud calls

### 4.4 Data Flow Summary
1. Resume is uploaded and parsed.
2. Parsed resume is cached into app state.
3. Resume text is chunked and indexed into in-memory Qdrant.
4. ATS, chat, and job ranking consume cached resume data/context.
5. Interview service uses audio upload, STT, LLM turn generation, and optional TTS.
6. Tracker service persists CRUD operations to applications.json.

## 5. Low-Level Design (LLD)

### 5.1 Entry Point and App Composition
File: backend_api/main.py
- Initializes FastAPI app and CORS policy.
- Registers all feature routers.
- Mounts static frontend and temp_audio directories when present.
- Exposes:
  - / root ping message
  - /app and /app/{page_name} static page entry points

### 5.2 Shared State Container
File: backend_api/state.py
- AppState class owns mutable runtime state.
- get_rag_engine() lazily creates RAGEngine and caches it.
- Graceful fallback: returns None if RAG initialization fails.

### 5.3 Provider and Model Routing
File: backend_api/provider.py
- normalize_provider(provider): canonicalizes aliases, especially llama.cpp variants.
- select_model_for_provider(provider, requested_model): applies provider-specific defaults:
  - Ollama default: qwen3.5:2b
  - Gemini default: gemini-2.5-flash
  - llama.cpp default: env-driven LLAMA_CPP_MODEL (normalized)

### 5.4 API Schemas
File: backend_api/schemas.py
- Defines request/response contracts for all routes.
- Ensures field-level constraints (example: min_length for JD and chat messages).
- Covers:
  - health/system status
  - resume parse response
  - ATS score request/response
  - chat request/response
  - jobs search/rank
  - interview start/turn/end
  - tracker create/update contracts

## 6. Detailed Feature Flows

### 6.1 Resume Parsing Flow
Primary modules:
- backend_api/routers/resume.py
- functions/resume_parsing/parser.py
- functions/resume_parsing/text_extractor.py
- functions/resume_parsing/ai_extractor.py
- functions/resume_parsing/ai_extractor_gemini.py
- functions/resume_parsing/ai_extractor_llamacpp.py

Flow:
1. API receives multipart file + provider/model/think.
2. Upload is persisted to temporary file.
3. Provider-specific model fallback is selected when user passes incompatible/default model names.
4. ResumeParser.parse(tmp_path) is executed:
   - extract_text(file_path):
     - PDF via pdfplumber page iteration
     - DOCX via paragraph/table extraction
   - AI extractor chosen by provider:
     - Ollama extractor
     - Gemini extractor
     - llama.cpp extractor
5. Model output parsing/normalization:
   - JSON extraction from plain text, fenced blocks, or embedded payloads
   - Schema normalization for list/string/dict field variants
   - ResumeData validation via Pydantic
6. App state update:
   - current_resume_data assigned
   - current_resume_text assigned
7. RAG ingestion:
   - if RAG engine available, ingest raw text chunks into Qdrant
8. Response returns:
   - structured resume_data
   - raw_text
   - full debug_info
   - first suggested role
9. Temporary upload file deleted in finally block.

Error handling:
- 422 when extraction result is empty/invalid.
- 500 for unexpected failures.
- File cleanup always attempted.

### 6.2 ATS Scoring Flow
Primary modules:
- backend_api/routers/ats.py
- functions/ats/scorer.py

Flow:
1. API verifies a resume has already been parsed in app state.
2. Provider/model are normalized and defaulted.
3. ATSScorer.calculate_score(resume_data, job_description):
   - First tries _score_with_llm:
     - Builds strict scoring prompt and JSON contract.
     - Provider paths:
       - Gemini via google-genai
       - llama.cpp via OpenAI-compatible wrapper
       - Ollama via chat API with schema format
   - Parses JSON to ATSResult dataclass.
4. On any LLM error, fallback to _score_heuristic:
   - Keyword overlap
   - skills intersection
   - formatting checks (email/phone/skills)
   - education/experience basic scoring
5. API returns normalized ATSScoreResponse.

### 6.3 Resume Chat (RAG) Flow
Primary modules:
- backend_api/routers/chat.py
- functions/chat/rag_engine.py

Flow:
1. API validates RAG engine readiness and that chunks exist.
2. Provider/model selection via shared provider helper.
3. rag.query(question, provider, model, think):
   - similarity_search(k=4) over Qdrant collection
   - context prompt assembly
   - streamed generation by provider:
     - Ollama stream
     - Gemini stream
     - llama.cpp stream
4. Non-stream endpoint:
   - consumes stream fully and returns final answer/context/prompt/chunks.
5. Stream endpoint:
   - emits NDJSON chunks with incremental answer
   - emits done payload with final metadata
   - emits error payload on exceptions

RAG internals:
- Embeddings: all-MiniLM-L6-v2
- Chunking: RecursiveCharacterTextSplitter (500/50)
- Vector store: Qdrant in-memory collection

### 6.4 Job Search and Ranking Flow
Primary modules:
- backend_api/routers/jobs.py
- functions/job_portal/search.py
- functions/job_portal/matcher.py

Search flow:
1. API builds query from role + optional location.
2. search_jobs(query) fans out to four providers in parallel:
   - Remote OK API
   - We Work Remotely RSS
   - Jobicy API
   - Remotive API
3. Source payloads are normalized to common schema.
4. Local filtering:
   - keyword checks against title/location/tags/description
   - URL-level deduplication
5. Result cached in app_state.last_fetched_jobs and returned.

Ranking flow:
1. API verifies embedding model availability from RAG engine.
2. Uses payload jobs or cached last_fetched_jobs.
3. JobMatcher.match_jobs(resume_text, jobs):
   - embed_query(resume_text)
   - embed_documents(job composite text)
   - cosine similarity per job
   - match_score = similarity * 100
   - sort descending by match_score
4. Ranked jobs returned.

### 6.5 Interview Flow
Primary modules:
- backend_api/routers/interview.py
- functions/interview/interviewer.py (active in app state)

Important note:
- There are two InterviewManager implementations in repository:
  - functions/interview/interviewer.py (actively used)
  - functions/interview/engine.py (legacy/alternate path)

Active flow (interviewer.py):
1. /start
   - configure_llm(provider, model, think)
   - start_interview(resume_context):
     - reset history/scores
     - system+user prompt for interview opener
     - call provider-specific chat completion
     - set current_question and history
     - optional TTS generation for question audio
2. /turn
   - audio upload saved to temp file
   - handle_turn(audio_path, resume_context):
     - transcribe audio (faster-whisper tiny, timeout wrapped)
     - append candidate answer to history
     - generate next question via chat completion
     - launch background answer evaluation thread (LLM first, heuristic fallback)
     - optional TTS generation for next question
   - API returns transcribed answer + next question + audio path + latest feedback
3. /end
   - end_interview():
     - compute average score from evaluated turns
     - build markdown report

Robustness features:
- Thread-based timeout wrappers for STT, LLM, and TTS.
- Fallback questions and text responses on errors.
- Internal debug trace buffer for diagnostics.

### 6.6 Application Tracker Flow
Primary modules:
- backend_api/routers/tracker.py
- functions/tracker/tracker.py

Flow:
1. CRUD endpoints validate enums (status, role_type) before mutation.
2. ApplicationTracker loads JSON file on startup.
3. add/update/delete operations mutate in-memory list and persist to disk.
4. stats endpoint computes summary buckets.
5. reference endpoints expose valid statuses and role types.

Persistence model:
- JSON array with ApplicationEntry objects
- fields: id, job_title, company, role_type, status, application_date, job_url, notes, created_at, updated_at

## 7. API Surface Summary

Base prefix: /api/v1

Health:
- GET /health
- GET /system/status

Resume:
- POST /resume/parse

ATS:
- POST /ats/score

Chat:
- POST /chat/query
- POST /chat/query/stream

Jobs:
- POST /jobs/search
- POST /jobs/rank

Interview:
- POST /interview/start
- POST /interview/turn
- POST /interview/end

Tracker:
- GET /tracker/applications
- GET /tracker/applications/{app_id}
- POST /tracker/applications
- PUT /tracker/applications/{app_id}
- DELETE /tracker/applications/{app_id}
- GET /tracker/stats
- GET /tracker/reference/statuses
- GET /tracker/reference/role-types

Static pages:
- GET /app
- GET /app/{page_name}

## 8. Data Contracts and Core Models

### 8.1 ResumeData Model
File: functions/common/models.py
Main fields:
- Contact: name, email, phone, location, linkedin, github, portfolio
- Career: skills, education, experience, summary
- Extended: achievements, certifications, projects, publications, languages, volunteer, awards, interests
- AI insights: ai_summary, key_strengths, suggested_roles

### 8.2 ATSResult Model
File: functions/ats/scorer.py
- score (0-100)
- breakdown object
- missing_keywords list
- formatting_issues list
- suggestions list
- reasoning text

### 8.3 Tracker Entry Model
File: functions/tracker/tracker.py
- UUID-based record with immutable id and mutable status/notes/metadata.

## 9. Configuration and Environment Variables

Common:
- GEMINI_API_KEY: required for Gemini provider usage.
- OLLAMA_NUM_GPU: controls Ollama GPU option.

llama.cpp integration:
- LLAMA_CPP_BASE_URL: default endpoint base URL.
- LLAMA_CPP_MODEL: model id/path alias.
- LLAMA_CPP_API_KEY: optional bearer token.

Interview:
- OLLAMA_CHAT_URL: custom Ollama chat endpoint override.

## 10. Concurrency and Performance Characteristics

- Job source fan-out uses ThreadPoolExecutor for parallel network calls.
- Interview answer evaluation runs in background thread.
- Timeout wrappers prevent indefinite UI/API blocking in interview path.
- RAG is in-memory and fast for single-resume context but not persistent.
- Embedding and vector search are local and CPU-bound by default.

## 11. Security and Reliability Notes

Implemented safeguards:
- Static file serving with path normalization to prevent traversal.
- API validation via Pydantic and explicit enum checks in tracker routes.
- Try/except wrappers and HTTPException translation for predictable API errors.

Known limitations:
- CORS is fully open (allow_origins = [*]) for development convenience.
- No auth/rate limiting yet.
- In-memory RAG index resets on process restart.
- Tracker uses file-based persistence without transactional locking.

## 12. Current Design Tradeoffs

- Simplicity over persistence: in-memory Qdrant avoids setup complexity.
- Multi-provider flexibility adds branching complexity but improves portability.
- Interview pipeline prioritizes responsiveness with timeout and fallback behavior.
- JSON-file tracker is lightweight but not ideal for concurrent multi-user writes.

## 13. Suggested Future Enhancements

1. Add authentication and per-user session isolation.
2. Replace tracker JSON storage with database (SQLite/PostgreSQL).
3. Persist vector index per user/resume and support multi-resume corpus.
4. Add structured observability (metrics, tracing, log correlation IDs).
5. Add unit/integration tests for routers and domain modules.
6. Consolidate interview managers (remove legacy duplicate) to reduce drift.
7. Add request throttling and provider-level circuit breakers.

## 14. File-Level Responsibility Map

Backend API:
- backend_api/main.py: app wiring, CORS, static mounting
- backend_api/state.py: singleton runtime state and lazy RAG init
- backend_api/provider.py: provider normalization and model defaults
- backend_api/schemas.py: Pydantic request/response models
- backend_api/routers/*.py: endpoint handlers per feature

Domain Functions:
- functions/resume_parsing/*: extraction + model parsing + normalization
- functions/ats/scorer.py: ATS scoring (LLM + fallback)
- functions/chat/rag_engine.py: embedding, indexing, retrieval, streaming answer
- functions/job_portal/search.py: multi-source fetch + normalization/filter
- functions/job_portal/matcher.py: semantic similarity ranking
- functions/interview/interviewer.py: active interview pipeline
- functions/tracker/tracker.py: application persistence and CRUD logic
- functions/common/llama_cpp_client.py: llama.cpp API compatibility wrapper
- functions/common/models.py: shared ResumeData model

## 15. End-to-End Sequence Snapshot

Typical user journey:
1. Upload resume using /api/v1/resume/parse.
2. Resume gets parsed, normalized, cached, and indexed into RAG.
3. Run /api/v1/ats/score for JD fit analysis.
4. Ask questions with /api/v1/chat/query (or stream endpoint).
5. Search jobs via /api/v1/jobs/search.
6. Rank jobs via /api/v1/jobs/rank using resume text.
7. Practice interview with /api/v1/interview/start -> /turn -> /end.
8. Track applications through /api/v1/tracker/* endpoints.

This architecture gives a cohesive single-resume workflow with modular feature domains, while retaining provider flexibility across local and cloud AI backends.
