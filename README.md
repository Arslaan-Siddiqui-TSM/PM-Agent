# Project Planning Assistant (ReWOO demo)

Turn multiple project PDFs (specs, BRDs, test plans) into a feasibility assessment and a polished project plan. Backend is FastAPI; frontend is React (Vite). Documents are parsed, classified, and analyzed; embeddings go to Qdrant for retrieval; the plan is generated via an LLM workflow.

Quick, simple, and local-friendly.

## What’s inside

- FastAPI backend (http://localhost:8000)
- React/Vite frontend (http://localhost:5173)
- Document Intelligence Pipeline (classify → extract → analyze)
- Qdrant vector DB (Docker) for embeddings and retrieval

## Prerequisites

- Python 3.13+
- Node.js 18+ (for the frontend)
- Docker (for Qdrant)
- API keys (choose one or more):
  - **NVIDIA NIM**: for both LLM and embeddings (recommended - get key from [build.nvidia.com](https://build.nvidia.com/))
  - **OpenAI**: for both LLM and embeddings (get key from [platform.openai.com](https://platform.openai.com/api-keys))
  - **Google Gemini**: for both LLM and embeddings (get key from [aistudio.google.com](https://aistudio.google.com/app/apikey))

Note: You can configure multiple providers for **automatic fallback**! If your primary provider fails (rate limit, API key issue, etc.), the system automatically tries the next available provider.

## Setup (Windows cmd)

1. Create your environment file

Create a `.env` file in the project root with your API keys. **Choose one of these configurations:**

### Option A: NVIDIA NIM (Recommended)

```env
# Primary LLM Provider
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL=qwen3-next-80b-a3b-instruct

# Embedding Provider
EMBEDDING_PROVIDER=nvidia
NVIDIA_EMBEDDING_MODEL=llama-3.2-nemoretriever-1b-vlm-embed-v1

# Optional: Add fallback providers (automatic failover)
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-key-here

# Other required keys
TAVILY_API_KEY=tvly-your-key-here
```

### Option B: OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini

EMBEDDING_PROVIDER=openai
TAVILY_API_KEY=tvly-your-key-here
```

### Option C: Google Gemini

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-key-here
GEMINI_MODEL=gemini-2.5-pro

EMBEDDING_PROVIDER=gemini
TAVILY_API_KEY=tvly-your-key-here
```

### Option D: Multi-Provider with Fallback

```env
# Primary: NVIDIA, Fallback: OpenAI → Gemini
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-key-here

EMBEDDING_PROVIDER=nvidia
TAVILY_API_KEY=tvly-your-key-here
```

2. Start Qdrant (vector DB)

```cmd
docker compose -f docker-compose.yml up -d qdrant
```

3. Backend: create venv and install

```cmd
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Run the backend API

```cmd
python server.py
```

5. Frontend: install and run

```cmd
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173 and proxies API calls to http://localhost:8000.

## Try it

Option A – UI

- Visit http://localhost:5173
- Keep “Use default sample files” checked and click “Upload & Continue”
- Continue to Feasibility → Generate Project Plan

Option B – API (quick smoke test)

```cmd
curl http://localhost:8000/health/

curl -X POST "http://localhost:8000/api/upload?use_default_files=true"

:: Use the returned session_id below
curl -X POST http://localhost:8000/api/feasibility ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"<SESSION_ID>\",\"use_intelligent_processing\":true}"

curl -X POST http://localhost:8000/api/generate-plan ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"<SESSION_ID>\",\"use_intelligent_processing\":true,\"max_iterations\":5}"
```

Outputs are saved under `outputs/` (feasibility report and final plan markdown files). Uploaded files are stored under `data/uploads/`.

## Key endpoints

- GET `/health/` – service status
- POST `/api/upload?use_default_files=true` – load PDFs from `data/files/`
- POST `/api/upload` – upload your own PDFs (multipart, max 15 files)
- POST `/api/feasibility` – body: `{ session_id, use_intelligent_processing, development_context? }`
- POST `/api/generate-plan` – body: `{ session_id, use_intelligent_processing, max_iterations }`
- GET `/api/file-content?file_path=<path>` – read saved markdown files (restricted to `outputs/` and `uploads/`)

## Folders you’ll use

- `data/files/` – sample input PDFs
- `data/uploads/` – uploaded PDFs (runtime)
- `outputs/` – feasibility and plan markdown files
- `qdrant_storage/` – persistent vector DB data (Docker volume)

## Troubleshooting

- **Qdrant connection failed** – ensure Docker is running: `docker compose up -d qdrant`
- **401/invalid API key** – check API keys in `.env` for your chosen provider(s):
  - NVIDIA: `NVIDIA_API_KEY`
  - OpenAI: `OPENAI_API_KEY`
  - Gemini: `GOOGLE_API_KEY`
- **Rate limits (429)** – the system will automatically try fallback providers if configured, or try again later
- **Upload errors** – only PDFs are accepted; max 15 files
- **LLM initialization failed** – ensure at least one provider's API key is valid

### Multi-Provider Fallback

The system uses **pure LangChain ecosystem** (no OpenAI SDK) and automatically falls back to alternative providers if the primary fails:

1. **Primary provider** (from `LLM_PROVIDER` env var) is tried first
2. If it fails, the system tries **OpenAI** (if `OPENAI_API_KEY` is set)
3. If that fails, tries **Gemini** (if `GOOGLE_API_KEY` is set)
4. If that fails, tries **NVIDIA** (if `NVIDIA_API_KEY` is set)

This ensures maximum reliability!

## Version Comparison & Token Analysis

The system supports **full version history tracking** and **token usage analysis** across feasibility generation and human-in-the-loop revisions.

### View Revision History

```bash
# Get all versions (v1, v2, v3...) for a session
curl http://localhost:8000/api/revision-history/{session_id}
```

### Compare Versions

```bash
# Full comparison (summary + side-by-side + diff)
python scripts/compare_versions.py {session_id} 1 2

# Summary only (character/line counts)
python scripts/compare_versions.py {session_id} 1 2 --summary

# Diff only (color-coded changes)
python scripts/compare_versions.py {session_id} 1 2 --diff

# Preview only (first 50 lines side-by-side)
python scripts/compare_versions.py {session_id} 1 2 --preview
```

### View Token Usage

```bash
# Show all token reports for a session
python scripts/token_report_reader.py {session_id} full

# See cost breakdown and per-call metrics
python scripts/token_report_reader.py {session_id} list
```

**Features:**

- ✅ Initial report saved as v1 (enables v1-to-vN comparison)
- ✅ Revision history tracks all versions with timestamps
- ✅ Token metrics saved per version (cost breakdown)
- ✅ Color-coded diff output (green = added, red = removed)
- ✅ Side-by-side preview for quick visual comparison
- ✅ Character/line count tracking to monitor report growth

See **[VERSION_COMPARISON_GUIDE.md](docs/VERSION_COMPARISON_GUIDE.md)** for detailed examples and workflows.

## More docs

- Environment/config: `docs/ENV_CONFIGURATION.md`
- Architecture and structure: `docs/PROJECT_STRUCTURE.md`, `docs/ARCHITECTURE_DIAGRAMS.md`
- Migration and implementation notes: `docs/implementation/*`
- Version comparison and token analysis: `docs/VERSION_COMPARISON_GUIDE.md`

—
