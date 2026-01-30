# AI Job Assistant - Resume Parser

AI-powered job assistance platform prototype for resume analysis and job search.

## Features ✅

### 1. Resume Parsing
- 📄 **Upload PDF/DOCX resumes**
- 🤖 **AI-Powered Extraction** - Uses Ollama with **qwen3:4b** for intelligent parsing
- 📊 **Structured Data**: Extracts detailed Contact Info, Education, Experience, Projects, and Skills.
- 🛠️ **Debug Info**: View raw model output, thought process, and parsed JSON.

### 2. ATS Scoring
- 🎯 **Score Calculation**: Analytics against a Job Description.
- 🔍 **Keyword Analysis**: Identifies missing and matching keywords.
- 📈 **Visualizations**: Gauge and Radar charts for quick analysis.

### 3. Chat with Resume (RAG)
- 💬 **Interactive Chat**: Ask questions about the candidate based on the resume.
- 🧠 **RAG Engine**: Uses local vector store (Qdrant) and Embeddings (Sentence-Transformers).
- 🕵️‍♂️ **Transparent Debugging**: View "Retrieved Context", "Full Prompt", and "All Document Chunks".

## Setup

### Prerequisites
- Python 3.12+
- [Ollama](https://ollama.ai/) with model `qwen3:4b`
- [Qdrant](https://qdrant.tech/) (Client installed automatically)

### Installation

1. **Clone and navigate to project**:
   ```bash
   git clone <repo-url>
   cd ai-job-assistant
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # Mac/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure Ollama is running and model is pulled**:
   ```bash
   ollama serve
   ollama pull qwen3:4b
   ```

5. **(Optional) Setup Gemini**:
   Create a `.env` file and add:
   ```env
   GEMINI_API_KEY=your_key_here
   ```

## Usage

### Run the Application

```bash
python main.py
```

The Gradio interface will open at: `http://127.0.0.1:7861`

### Using the Interface

1. Click **"Check System Status"** to verify connections.
2. **Resume Parser Tab**: Upload resume -> Parse -> Check JSON.
3. **ATS Scorer Tab**: Paste JD -> Calculate Score -> View Charts.
4. **Chat Tab**: Ask questions -> Check Debug Expanders.

## Project Structure

```
x:\Project\
├── main.py                      # Gradio web interface
├── resume_parser/               # Core Package
│   ├── ai_extractor.py         # Ollama/Gemini Integration
│   ├── ats_scorer.py           # ATS Scoring Logic
│   ├── rag_engine.py           # QA & Vector Store
│   ├── models.py               # Pydantic Schemas
│   └── text_extractor.py       # File I/O
├── tests/                       # Verification Scripts
├── requirements.txt             # Dependencies
└── .env                         # Secrets (Ignored)
```

## Upcoming Phases

- [ ] Phase 4: Job Search via APIs
- [ ] Phase 5: Job Matching
- [ ] Phase 6: Cover Letter Generator
- [ ] Phase 7: Auto-Apply (Safe Mode)

## License

MIT
