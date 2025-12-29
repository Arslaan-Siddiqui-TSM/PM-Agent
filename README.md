# PM Agent (PMA)

**Intelligent project planning automation that combines AI reasoning with human expertise to generate feasibility assessments and implementation plans from project documents.**

---

## 🎯 What is PMA?

PMA is a system that automates the critical first phase of software project planning:

1. **Input**: Project documents (specs, requirements, test plans, RFDs, etc.)
2. **Analysis**: AI intelligently reads, classifies, and analyzes documents
3. **Assessment**: Generate feasibility report with risk analysis
4. **Planning**: Create detailed implementation plans with human feedback loops
5. **Output**: Polished project plans with version history and cost tracking

**Perfect for**: Technical leads, project managers, and planning teams who need to quickly evaluate project scope and create actionable roadmaps with confidence.

---

## 🚀 Quick Demo (3 minutes)

```bash
# 1. Setup (one-time)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d qdrant

# 2. Start services (2 terminals)
python server.py              # Terminal 1: Backend
cd frontend && npm run dev    # Terminal 2: Frontend

# 3. Open browser
Visit http://localhost:5173 → Click "Upload & Continue"
```

Within seconds, you'll see:
- Documents auto-analyzed
- Feasibility assessment generated
- Human-in-the-loop review interface ready
- Project plan with editing capability

---

## 💡 Key Problems PMA Solves

| Problem | PMA Solution |
|---------|-------------|
| **Time-consuming manual planning** | Generates first draft automatically |
| **Document information scattered** | Unified context from all sources |
| **Missed requirements/risks** | AI analyzes across all documents |
| **Plan quality depends on reviewer** | Human feedback guides AI refinement |
| **No version history/tracking** | Complete audit trail of changes |
| **Unknown project costs** | Token usage tracking per operation |

---

## 🏗️ How It Works

### Architecture (Simple View)

```
┌─────────────────────────────────────────────┐
│    React Frontend (http://localhost:5173)   │
│   - Document upload                         │
│   - Review/edit interface                   │
│   - Plan comparison & history               │
└────────────────┬────────────────────────────┘
                 │ (API calls)
┌────────────────▼────────────────────────────┐
│     FastAPI Backend (http://localhost:8000) │
│   - File processing                         │
│   - LangGraph orchestration                 │
│   - HITL state management                   │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┴────────────┬────────────┐
    │                         │            │
┌───▼────────┐  ┌───────────▼──┐  ┌────▼─────────┐
│ LLM Calls  │  │ Qdrant VectorDB  │  Session Files  │
│(NVIDIA/OAI)│  │(Context Retrieval) │  (JSON state)   │
└────────────┘  └────────────────┘  └─────────────┘
```

### Workflow Stages

#### 1️⃣ **Upload & Classify** (Automatic)
- User uploads project documents (PDF, Markdown)
- System reads and understands document types automatically
- Extracts key information (requirements, constraints, tech stack hints)

#### 2️⃣ **Feasibility Assessment** (AI → Human Review)
- LLM analyzes technical feasibility
- Evaluates resource requirements
- Identifies risks and blockers
- Human reviews and approves/modifies
- **Output**: Feasibility report (saved with version)

#### 3️⃣ **Development Context** (User Input)
- User enters team size, timeline, budget
- Specifies tech stack and constraints
- Sets iteration preferences

#### 4️⃣ **Plan Generation with HITL** (Multi-Stage)

```
AI generates draft → Human reviews & edits → AI reflects on feedback
                                                       ↓
                                        Human reviews reflection
                                                       ↓
                                      AI revises plan → Done or loop
```

**HITL = Human-In-The-Loop**: System pauses for human judgment at critical points.

---

## 👥 User Roles & Workflows

### Product Manager / Planning Lead
- **Goal**: Get initial project scope assessment quickly
- **Steps**: 
  1. Upload project docs (2 min)
  2. Review generated assessment (5 min)
  3. Answer development context (3 min)
  4. Review and edit draft plan (10-15 min)
  5. Approve final plan with feedback (5 min)
- **Output**: Implementation roadmap ready for development team

### Engineering Lead
- **Goal**: Ensure plan aligns with technical reality
- **Steps**:
  1. Review feasibility analysis
  2. Edit plan with technical details
  3. Provide feedback on reflection stage
  4. Validate final plan against team capacity
- **Output**: Realistic, team-approved implementation plan

### Executive / Decision Maker
- **Goal**: Understand project scope and feasibility
- **Interaction**: View final reports and recommendations
- **Time**: 5-10 minutes to review key findings

---

## 🔌 API Reference for Integration

### Core Endpoints

#### Upload Documents
```bash
POST /api/upload?use_default_files=false
Content-Type: multipart/form-data

Files: [doc1.pdf, doc2.pdf, ...]
# Response: { "session_id": "abc123", "uploaded_files": [...] }
```

#### Generate Feasibility Assessment
```bash
POST /api/feasibility
{
  "session_id": "abc123",
  "development_context": {
    "team_size": 5,
    "timeline_weeks": 12,
    "budget_usd": 150000,
    "tech_stack": "Python, React, PostgreSQL"
  }
}
# Response: { "file_path": "outputs/session_abc123/reports/feasibility_v1.md" }
```

#### Start Plan Generation (with HITL)
```bash
POST /api/generate-plan
{
  "session_id": "abc123",
  "enable_hitl": true,
  "max_iterations": 5
}
# Response: { "request_id": "req-xyz", "review_type": "draft_review", "content": "..." }
```

#### Resume from HITL Pause
```bash
POST /api/resume-review
Authorization: Bearer <HITL_SECRET>
{
  "request_id": "req-xyz",
  "action": "feedback",
  "feedback_text": "Add more details on infrastructure costs",
  "edited_text": "..."
}
# Response: { "interrupted_again": true, "new_request_id": "req-abc" }
# OR: { "completed": true, "final_plan": "..." }
```

#### Get Pending Review
```bash
GET /api/pending-review/req-xyz
# Response: { "request_id": "...", "review_type": "draft_review", "content": "...", "iteration": 1 }
```

---

## 📊 Features & Capabilities

### 🤖 Intelligent Analysis
- **Document Classification**: Auto-identifies FSD, NFRD, BRD, test plans, RFDs
- **Requirement Extraction**: Pulls structured info from unstructured docs
- **Gap Analysis**: Identifies missing information and conflicts
- **Context Retrieval**: Vector embeddings find relevant context quickly

### 🔄 Human-AI Collaboration (HITL)
- **Draft Review**: Edit AI-generated plans directly
- **Feedback Integration**: AI refines based on human guidance
- **Iterative Refinement**: Up to 5 revision cycles
- **Edit Preservation**: Your changes survive all revisions

### 📈 Planning & Tracking
- **Version History**: All plan versions with timestamps
- **Change Diffs**: Side-by-side comparison of revisions
- **Cost Analysis**: Token usage per operation (detailed breakdown)
- **Audit Trail**: Complete history of who made what changes

### 🌍 Multi-Provider LLM Support
- **NVIDIA NIM** (Recommended) - Cost-effective, fast
- **OpenAI** - Full GPT-4 capability
- **Google Gemini** - Advanced reasoning
- **Automatic Failover** - Seamless switching if primary fails

### 📁 Session Management
- Each project gets a unique session ID
- All intermediate files saved (inputs, reports, plans)
- Easy recovery and re-run from checkpoints
- JSON state snapshots for debugging

---

## 🛠️ Setup Guide

### Prerequisites
- **Python 3.13+**
- **Node.js 18+** (for frontend)
- **Docker** (for Qdrant vector DB)
- **API Key** from one: NVIDIA NIM, OpenAI, or Google Gemini

### Step 1: Configure Environment

Create `.env` in project root:

```env
# === LLM Configuration ===
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-xxxxx
NVIDIA_MODEL=qwen3-next-80b-a3b-instruct

# === Embeddings ===
EMBEDDING_PROVIDER=nvidia
NVIDIA_EMBEDDING_MODEL=llama-3.2-nemoretriever-1b-vlm-embed-v1

# === Optional Fallback (if primary fails) ===
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=AIzaSy-xxxxx

# === Other Services ===
TAVILY_API_KEY=tvly-xxxxx  # Optional: for web search
HITL_SECRET=changeme       # Security token for HITL endpoints

# === Qdrant ===
QDRANT_URL=http://localhost:6333
```

### Step 2: Start Qdrant (Vector Database)

```bash
docker compose up -d qdrant
# Verify: curl http://localhost:6333/health
```

### Step 3: Install & Run Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py
# Server runs on http://localhost:8000
```

### Step 4: Install & Run Frontend

```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:5173
```

### Step 5: Test the System

Open browser → **http://localhost:5173**
- Click "Upload & Continue" (uses sample files)
- Follow the workflow
- Review generated plans

---

## 📂 Project Structure

```
PMA/
├── frontend/              # React UI
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks (useProjectWorkflow)
│   │   └── services/      # API client
│   └── package.json
│
├── src/                   # Backend Python
│   ├── app/              # LangGraph workflows
│   │   └── graph.py      # Main orchestration
│   ├── routes/           # FastAPI endpoints
│   │   ├── upload.py
│   │   ├── feasibility.py
│   │   ├── planning.py
│   │   └── review_resume.py
│   ├── core/             # Core logic
│   │   ├── document_analyzer.py
│   │   └── llm_service.py
│   ├── states/           # Pydantic state models
│   │   └── reflection_state.py
│   ├── utils/            # Helpers
│   │   └── helper.py
│   └── tools/            # LangGraph tools
│
├── scripts/              # Standalone utilities
│   ├── generate_project_plan.py  # Batch planning
│   ├── compare_versions.py       # Plan comparison
│   └── token_report_reader.py    # Cost analysis
│
├── output/               # Generated files
│   ├── session_xxx/      # Per-session outputs
│   │   ├── reports/      # Feasibility, plans
│   │   └── context/      # Document context
│   └── pending_reviews/  # HITL pause files
│
├── server.py             # FastAPI entry point
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Qdrant config
└── README.md             # This file
```

---

## 🐛 Troubleshooting

### "Cannot connect to Qdrant"
```bash
# Verify Qdrant is running
docker ps | grep qdrant

# If not running, start it
docker compose up -d qdrant

# Check health
curl http://localhost:6333/health
```

### "401 Unauthorized" on /api/resume-review
- Verify `HITL_SECRET` is set in `.env`
- Check frontend sends header: `Authorization: Bearer <HITL_SECRET>`

### "ImportError: No module named 'src'"
```bash
# Run from project root (not from scripts/ directory)
cd /path/to/PMA
python scripts/generate_project_plan.py
```

### "Plan generation stuck on review"
- Check server logs for LLM API errors
- Verify API keys are valid
- Try reloading page (frontend will re-fetch pending review)

### "Qdrant OOM / too slow"
- Reduce number of documents
- Use simpler models (NIM over GPT-4)
- Check `output/cache/` for large cached embeddings

---

## 📊 Monitoring & Analytics

### View Cost Breakdown
```bash
python scripts/token_report_reader.py <session_id> full
# Shows: tokens/cost per LLM call, total spend
```

### Compare Plan Versions
```bash
python scripts/compare_versions.py <session_id> 1 2 --full
# Shows: diff, character count, side-by-side preview
```

### Check Session Files
```bash
ls output/session_<session_id>/reports/
# Lists all generated reports and plans
```

---

## 🔐 Security & Privacy

- **No external data storage**: All files stay on your infrastructure
- **Local vector DB**: Qdrant runs in Docker on your machine
- **Auth token**: HITL endpoints protected by `HITL_SECRET`
- **Session isolation**: Each session is independent
- **No user tracking**: No telemetry or external calls except to configured LLM provider

---

## 🚀 Production Considerations

### Scaling for Teams
- Deploy FastAPI on cloud (AWS, GCP, Azure)
- Use managed Qdrant (Qdrant Cloud)
- Frontend static site (S3, Vercel, Netlify)
- Database for session persistence (PostgreSQL)

### High Availability
- Multiple backend instances with load balancer
- Persistent session storage (not local files)
- Backup Qdrant instance
- LLM provider failover (configured in `.env`)

### Cost Optimization
- Use NVIDIA NIM (cheapest: ~$0.50 per plan)
- Cache document embeddings
- Limit max_iterations (default 5, can reduce to 2-3)
- Monitor token usage per session

---

## 📚 Deep Dives

For detailed information, see:
- [Architecture Details](docs/ARCHITECTURE_DIAGRAMS.md)
- [HITL Workflow Design](docs/LANGGRAPH_HITL.md)
- [Version Comparison Guide](docs/VERSION_COMPARISON_GUIDE.md)
- [Environment Configuration](docs/ENV_CONFIGURATION.md)

---

## 🤝 Contributing

To extend PMA:
1. Review `src/app/graph.py` for workflow structure
2. Add new nodes in `src/routes/` for endpoints
3. Update `frontend/src/hooks/useProjectWorkflow.js` for UI
4. Test with `scripts/generate_project_plan.py`

---

## ✅ Checklist for Leads

Before using PMA with your team:

- [ ] All team members have read this README
- [ ] `.env` is configured with valid API key
- [ ] Qdrant is running (`docker compose up -d qdrant`)
- [ ] Backend & frontend both start without errors
- [ ] Sample workflow completes successfully
- [ ] Team understands HITL review process
- [ ] Cost tracking mechanism is understood
- [ ] Session storage location is backed up

---

## 📞 Support

- **Issues**: Check logs in `output/` directory
- **Debug**: Run standalone script: `python scripts/generate_project_plan.py`
- **LLM Errors**: Check `.env` and API quotas
- **Frontend**: Open browser DevTools (F12) to see API errors

---

## 📝 License

Internal tool. All rights reserved.

**Version**: 1.0  
**Last Updated**: December 2025
