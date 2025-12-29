# PM Agent using ReWOO Pattern

**An intelligent project planning assistant that transforms project documents into feasibility assessments and polished implementation plans using Human-In-The-Loop (HITL) review cycles.**

---

## 🎯 Executive Summary

This project automates the critical early-stage planning process for software projects. It:

1. **Analyzes** project specifications, requirements, and test plans
2. **Assesses** technical and resource feasibility
3. **Generates** detailed implementation plans with human feedback integration
4. **Supports** iterative refinement through HITL review stages

Perfect for technical leads, product managers, and project planners who need to quickly evaluate project scope and create actionable roadmaps.

---

## ✨ Key Features

### 🤖 Intelligent Processing

- **Document Classification**: Automatically identifies document types (FSD, NFRD, BRD, test plans, etc.)
- **Structured Extraction**: Pulls requirements, constraints, and technical details
- **Context Analysis**: Identifies gaps, conflicts, and dependencies
- **Smart Retrieval**: Vector embeddings (Qdrant) for relevant context recall

### 🔄 Human-In-The-Loop Workflow

- **Draft Review**: Humans review and edit AI-generated plans
- **Reflection Review**: Humans critique AI analysis before revisions
- **Iterative Refinement**: Multiple feedback cycles with clear state management
- **Edit Preservation**: Human edits are preserved verbatim through all iterations

### 📊 Multi-Provider LLM Support

- **NVIDIA NIM** (Recommended) - Cost-effective, high performance
- **OpenAI** - Full GPT-4 capability
- **Google Gemini** - Advanced reasoning
- **Automatic Fallback** - Seamless provider switching if one fails

### 📈 Comprehensive Tracking

- **Version History**: All plan revisions tracked with timestamps
- **Token Usage**: Detailed cost analysis per operation
- **Change Diffs**: Color-coded side-by-side comparisons
- **Audit Logs**: Complete review history with reviewer metadata

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vite)                   │
│              http://localhost:5173                          │
├─────────────────────────────────────────────────────────────┤
│                  API Gateway (FastAPI)                      │
│              http://localhost:8000                          │
├─────────────────────────────────────────────────────────────┤
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│   │  Feasibility │  │   Planning   │  │  HITL Flow   │     │
│   │    Agent     │  │    Agent     │  │  Management  │     │
│   └──────────────┘  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│        LangGraph with Checkpointing (State Persistence)     │
├─────────────────────────────────────────────────────────────┤
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│   │   LLM APIs   │  │  Qdrant      │  │   Session    │     │
│   │  (Multi)     │  │  Vector DB   │  │  Storage     │     │
│   └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module          | Purpose                                                    |
| --------------- | ---------------------------------------------------------- |
| `src/app/`      | LangGraph workflows (draft, reflect, revise nodes)         |
| `src/routes/`   | FastAPI endpoints for uploads, feasibility, planning, HITL |
| `src/core/`     | Document parsing, embeddings, session management           |
| `src/states/`   | Pydantic state models for graph execution                  |
| `frontend/src/` | React components, hooks, services                          |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- Docker (for Qdrant)
- API key from one of: NVIDIA NIM, OpenAI, or Google Gemini

### 1. Setup Environment

Create `.env` in project root:

```env
# Choose ONE primary LLM provider
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-xxxxx
NVIDIA_MODEL=qwen3-next-80b-a3b-instruct

# Embedding provider
EMBEDDING_PROVIDER=nvidia
NVIDIA_EMBEDDING_MODEL=llama-3.2-nemoretriever-1b-vlm-embed-v1

# Optional fallback providers
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=xxxxx

# Tavily for web search (optional)
TAVILY_API_KEY=tvly-xxxxx

# HITL security
HITL_SECRET=changeme
```

### 2. Start Services

```bash
# Start Qdrant vector DB
docker compose up -d qdrant

# Backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python server.py

# Frontend (in new terminal)
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** → Upload files → Review & approve plans

### 3. Try the UI

1. Click "Upload & Continue" (uses sample files)
2. Answer development context questions
3. Review feasibility assessment
4. Approve revisions
5. Generate project plan
6. Review draft (edit if needed)
7. Approve/provide feedback on reflection
8. See revised plan

---

## 📋 Workflow Stages

### Stage 1: Upload & Processing

- Upload project documents (PDF, Markdown)
- Auto-parse and extract requirements
- Build document context

### Stage 2: Feasibility Assessment

- Analyze technical feasibility
- Evaluate resource requirements
- Identify risks and constraints
- **Output**: Feasibility report with recommendations

### Stage 3: Development Context

- Enter team size, timeline, budget
- Specify tech stack
- Note constraints

### Stage 4: Project Planning (with HITL)

1. **Draft Generation** → AI generates initial plan
2. **Draft Review** ✏️ → Human edits and provides feedback
3. **Reflection** → AI critiques the draft
4. **Reflection Review** ✏️ → Human reviews critique
5. **Revision** → AI revises based on feedback
6. **Repeat** → Up to 5 iterations or until complete

**Output**: Final implementation plan

---

## 🎮 HITL (Human-In-The-Loop) Review

The system pauses at key points for human input:

### Draft Review

- See AI-generated plan
- Edit text directly
- Provide feedback ("make it shorter", "add AWS details", etc.)
- Action: Approve → Continue, or Feedback → Iterate

### Reflection Review

- See AI's self-critique
- Review identified improvements
- Provide corrective feedback
- Action: Approve → Generate revisions, or Feedback → Refine critique

**Key Benefit**: Human expertise guides AI refinement → higher quality output

---

## 🔌 API Reference

### Core Endpoints

#### File Upload

```bash
POST /api/upload?use_default_files=true
# Returns: { session_id, uploaded_files }
```

#### Feasibility Check

```bash
POST /api/feasibility
{
  "session_id": "xxx",
  "development_context": { "team_size": 5, "budget": 100000, ... }
}
# Returns: { file_path, file_content }
```

#### Generate Plan (with HITL)

```bash
POST /api/generate-plan
{
  "session_id": "xxx",
  "enable_hitl": true,
  "max_iterations": 5
}
# Returns: { request_id, review_type, draft/reflection, iteration }
# OR: { final_plan, file_path } if completed
```

#### Resume Review (HITL)

```bash
POST /api/resume-review
{
  "request_id": "xxx",
  "action": "feedback",
  "feedback_text": "Add more detail on...",
  "edited_text": "..."
}
# Returns: { interrupted_again, new_request_id } OR { completed, final_plan }
```

#### Get Pending Review

```bash
GET /api/pending-review/{request_id}
# Returns: pending review data for display
```

---

## 📊 Outputs & Storage

### Generated Files

```
output/
├── session_xxx/
│   ├── reports/
│   │   ├── feasibility_report_v1.md
│   │   ├── feasibility_report_v2.md
│   │   ├── project_plan_final.md
│   │   └── token_stats_*.json
│   └── context/
│       └── unified_context_*.md
└── pending_reviews/
    └── request-uuid.json
```

### Key Files

- **Feasibility Report**: Technical assessment, resource analysis, risk matrix
- **Project Plan**: Phased roadmap, team structure, timeline, budget breakdown
- **Token Reports**: Cost analysis per LLM call
- **Revision History**: All versions with diffs

---

## 🔍 Monitoring & Analysis

### View Revision History

```bash
curl http://localhost:8000/api/revision-history/{session_id}
```

### Compare Plan Versions

```bash
python scripts/compare_versions.py {session_id} 1 2 --full
# Shows: diff, character counts, side-by-side preview
```

### Analyze Token Usage

```bash
python scripts/token_report_reader.py {session_id} full
# Shows: LLM cost breakdown, tokens per call, total spend
```

---

## 🛠️ Configuration

### Environment Variables

| Variable         | Purpose                 | Example                      |
| ---------------- | ----------------------- | ---------------------------- |
| `LLM_PROVIDER`   | Primary LLM source      | `nvidia`, `openai`, `gemini` |
| `NVIDIA_API_KEY` | NIM API key             | `nvapi-...`                  |
| `OPENAI_API_KEY` | OpenAI API key          | `sk-...`                     |
| `GOOGLE_API_KEY` | Gemini API key          | `AIzaSy...`                  |
| `TAVILY_API_KEY` | Search (optional)       | `tvly-...`                   |
| `HITL_SECRET`    | Auth for HITL endpoints | Any string                   |

### Execution Parameters

In graph configuration:

- `max_iterations`: Max draft-reflect-revise cycles (default: 5)
- `enable_hitl`: Enable human review pauses (default: true for UI, false for scripts)

---

## 🐛 Troubleshooting

| Issue                           | Solution                                              |
| ------------------------------- | ----------------------------------------------------- |
| Qdrant connection error         | `docker compose up -d qdrant`                         |
| 401 Unauthorized on API         | Check API keys in `.env`                              |
| Rate limit (429)                | Wait or switch provider (auto-failover if configured) |
| Import errors in scripts        | Run from project root: `python scripts/script.py`     |
| UI shows white screen           | Check browser console, verify backend running         |
| Plan generation stuck on review | Reload page, check backend logs                       |

---

## 📚 Additional Resources

- **Architecture**: See [docs/ARCHITECTURE_DIAGRAMS.md](docs/ARCHITECTURE_DIAGRAMS.md)
- **Detailed Setup**: See [docs/ENV_CONFIGURATION.md](docs/ENV_CONFIGURATION.md)
- **HITL Design**: See [docs/LANGGRAPH_HITL.md](docs/LANGGRAPH_HITL.md)
- **Version Tracking**: See [docs/VERSION_COMPARISON_GUIDE.md](docs/VERSION_COMPARISON_GUIDE.md)

---

## �� Team

**Built with** LangGraph, FastAPI, React, Qdrant, and multi-LLM support.

---

## 📝 License

Internal tool. All rights reserved.
