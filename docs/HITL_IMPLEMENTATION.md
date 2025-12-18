# HITL Feasibility Assessment Implementation

## 🎯 Overview

This implementation adds **Human-in-the-Loop (HITL)** capability to the feasibility assessment workflow, enabling iterative review and revision of feasibility reports based on human feedback.

## ✨ Features

### Core Capabilities

- ✅ **Iterative Review**: Generate → Review → Revise cycle
- ✅ **Human Approval**: Explicit approval required to proceed
- ✅ **Feedback Processing**: Natural language feedback converted to structured critique
- ✅ **Automatic Revision**: LLM revises report based on critique
- ✅ **Iteration Limits**: Configurable max iterations (default: 3)
- ✅ **Complete Audit Trail**: Full revision history preserved

### User Interface

- ✅ **Three-Button Control**: Auto-fill, Request Changes, Approve
- ✅ **Feedback Template**: Pre-filled structured template for guidance
- ✅ **Iteration Counter**: Visual indicator of current/max iterations
- ✅ **Critique Display**: Shows AI analysis of feedback
- ✅ **Status Messages**: Clear feedback on workflow state
- ✅ **Responsive Design**: Works on desktop, tablet, and mobile

## 📁 Files Changed

### Backend (Python)

```
src/
├── states/
│   └── feasibility_state.py          # Added HITL fields
├── app/
│   ├── feasibility_graph.py          # Added 4 HITL nodes + checkpointer
│   └── feasibility_agent.py          # Added revision generation
├── routes/
│   ├── feasibility_handler.py        # Added 3 HITL methods
│   └── planning_agent.py             # Added 3 HITL endpoints
└── prompts/
    ├── feasibility_critique.txt      # New: Critique generation
    └── feasibility_revise.txt        # New: Revision guidance
```

### Frontend (React)

```
frontend/src/
├── services/
│   └── api.js                        # Added 3 HITL API methods
├── hooks/
│   └── useProjectWorkflow.js         # Enhanced with HITL support
├── components/steps/
│   ├── FeasibilityStep.jsx           # Complete HITL UI
│   └── FeasibilityStep.css           # HITL styling
└── App.jsx                           # Pass HITL props
```

### Documentation

```
docs/
└── HITL_TESTING_GUIDE.md             # Comprehensive test plan
scripts/testing/
└── test_hitl_workflow.sh             # Automated API tests
```

## 🚀 Quick Start

### 1. Start Backend

```bash
cd /Users/vaidikjaiswal/Desktop/PM-Agent-using-ReWOO
python server.py
```

Backend runs on: `http://localhost:8000`

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs on: `http://localhost:5173`

### 3. Run API Tests

```bash
./scripts/testing/test_hitl_workflow.sh
```

This will verify all API endpoints are working correctly.

### 4. Test UI Workflow

1. Open: `http://localhost:5173`
2. Upload documents (or use default)
3. Fill development process form
4. Click "Check Feasibility"
5. Review the generated report
6. Try all three buttons:
   - **Auto-fill**: Populates feedback template
   - **Request Changes**: Triggers revision
   - **Approve**: Advances to next step

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     HITL Workflow                           │
└─────────────────────────────────────────────────────────────┘

  START
    │
    ▼
┌───────────────────┐
│ Generate Report   │ ◄──────────────┐
│ (iteration n)     │                │
└─────────┬─────────┘                │
          │                          │
          ▼                          │
┌───────────────────┐                │
│ Human Review Gate │                │
│ (interrupt)       │                │
└─────────┬─────────┘                │
          │                          │
          ▼                          │
    ┌─────────┐                      │
    │ Approve?│                      │
    └────┬────┘                      │
         │                           │
    ┌────┴────┐                      │
    │         │                      │
   YES       NO                      │
    │         │                      │
    │    ┌────▼─────────┐            │
    │    │ Get Feedback │            │
    │    └────┬─────────┘            │
    │         │                      │
    │    ┌────▼──────────┐           │
    │    │ Generate      │           │
    │    │ Critique      │           │
    │    └────┬──────────┘           │
    │         │                      │
    │    ┌────▼──────────┐           │
    │    │ Check Max     │           │
    │    │ Iterations    │           │
    │    └────┬──────────┘           │
    │         │                      │
    │    ┌────┴────┐                 │
    │    │         │                 │
    │   OK    MAX REACHED            │
    │    │         │                 │
    │    └────┬────┘                 │
    │         │                      │
    │         ├──────────────────────┘
    │         │
    ▼         ▼
   END       END
(approved) (max iter)
```

## 🔌 API Endpoints

### Start Feasibility

```http
POST /api/feasibility/start
Content-Type: application/json

{
  "session_id": "abc123",
  "development_context": {
    "methodology": "Agile",
    "teamSize": "5",
    "timeline": "6 months",
    ...
  }
}
```

**Response:**

```json
{
  "status": "awaiting_human",
  "iteration": 0,
  "feasibility_report": "# FEASIBILITY ASSESSMENT...",
  "message": "Awaiting human review"
}
```

### Review Feasibility

```http
POST /api/feasibility/review
Content-Type: application/json

{
  "session_id": "abc123",
  "approved": false,
  "feedback": "Please add more detail about..."
}
```

**Response (if requesting changes):**

```json
{
  "status": "awaiting_human",
  "iteration": 1,
  "feasibility_report": "# REVISED REPORT...",
  "critique": "# CRITIQUE...",
  "message": "Revision 1 complete"
}
```

### Get Status

```http
GET /api/feasibility/status/{session_id}
```

**Response:**

```json
{
  "status": "awaiting_human",
  "iteration": 1,
  "approved": false,
  "feasibility_report": "...",
  "critique": "...",
  "revision_history_count": 2
}
```

## 🧪 Testing

### Automated Tests

```bash
./scripts/testing/test_hitl_workflow.sh
```

### Manual Testing

See comprehensive guide: [`docs/HITL_TESTING_GUIDE.md`](./docs/HITL_TESTING_GUIDE.md)

### Test Coverage

- ✅ API endpoint functionality
- ✅ Frontend UI interactions
- ✅ Error handling
- ✅ Edge cases (max iterations, empty feedback)
- ✅ State management
- ✅ Responsive design
- ✅ Performance

## 📊 State Management

### FeasibilityState Fields

```python
class FeasibilityState(BaseModel):
    # Original fields
    session_id: str
    md_file_paths: Optional[List[str]]
    development_context: Optional[Dict[str, str]]
    unified_context_path: str
    thinking_summary: str
    feasibility_report: str

    # HITL fields (NEW)
    approved: Optional[bool]              # Review decision
    human_feedback: Optional[str]         # User's feedback
    critique_md: Optional[str]            # Structured critique
    revision_history: List[Dict]          # Audit trail
    iteration: int = 0                    # Current iteration
    max_iterations: int = 3               # Limit
    status: Literal[...]                  # Workflow state
```

### Status Values

- `"generating"` - Creating/revising report
- `"awaiting_human"` - Paused for review
- `"revising"` - Processing feedback
- `"approved"` - Workflow complete
- `"max_iterations_reached"` - Limit hit
- `"failed"` - Error occurred

## 🎨 UI Components

### Auto-fill Template

```
Please improve the following areas:

1. **Technical Stack Section**:
   - Add more detail about [specific technology choices]
   - Clarify [specific technical concern]

2. **Timeline Estimates**:
   - Provide more realistic estimates for [specific phase]
   - Consider [specific constraint or factor]

3. **Risk Assessment**:
   - Add analysis of [specific risk]
   - Provide mitigation strategies for [specific concern]

4. **Resource Analysis**:
   - Elaborate on [specific resource requirement]
   - Clarify [specific resource concern]

5. **Additional Notes**:
   - [Any other specific feedback]
```

### Button States

| Button             | Action                            | Validation        |
| ------------------ | --------------------------------- | ----------------- |
| Auto-fill          | Populate feedback template        | None              |
| Request Changes    | Submit feedback, trigger revision | Feedback required |
| Approve & Continue | Complete workflow, advance        | None              |

## ⚙️ Configuration

### Max Iterations

Default: 3 revisions allowed

**To change:**

```python
# In FeasibilityState initialization
FeasibilityState(
    ...
    max_iterations=5  # Allow 5 revisions
)
```

### Prompts

Located in `prompts/`:

- `feasibility_critique.txt` - Critique generation
- `feasibility_revise.txt` - Revision guidance

**Customization:** Edit these files to adjust critique format or revision instructions.

## 🐛 Troubleshooting

### Backend Issues

**Problem:** "Session not found" error

- **Solution:** Ensure session was created via upload endpoint first

**Problem:** Critique generation fails

- **Solution:** Check `prompts/feasibility_critique.txt` exists and is readable

**Problem:** Max iterations not enforced

- **Solution:** Verify `max_iterations` field in FeasibilityState

### Frontend Issues

**Problem:** Buttons don't respond

- **Solution:** Check browser console for errors, verify API endpoints are reachable

**Problem:** Report not displaying

- **Solution:** Check `window.__feasibilityData` in console, verify API response

**Problem:** Auto-fill doesn't work

- **Solution:** Check textarea element exists, verify event handler is attached

### Common Errors

```
Error: "Feedback is required when requesting changes"
→ Fill in the feedback textarea before clicking "Request Changes"

Error: "Session expired"
→ Re-upload documents to create a new session

Error: "Document processing not complete"
→ Wait for upload processing to finish before starting feasibility
```

## 📈 Performance Notes

### Expected Timings

- Initial report generation: 30-60 seconds
- Critique generation: 10-20 seconds
- Revision generation: 30-60 seconds
- Status check: <1 second

### Optimization Tips

- Use smaller document sets for faster processing
- Consider caching unified context file
- Implement pagination for large reports

## 🔒 Security Considerations

### Production Deployment

⚠️ **Note:** Current implementation uses in-memory `MemorySaver` which is NOT suitable for production.

**For production:**

1. Replace `MemorySaver` with persistent checkpointer (PostgreSQL, Redis)
2. Add authentication/authorization
3. Implement rate limiting
4. Add session timeouts
5. Sanitize user feedback input
6. Add CORS restrictions

## 🛣️ Future Enhancements

### Planned Features

- [ ] Persistent state storage (database)
- [ ] Export revision history to PDF
- [ ] Compare revisions side-by-side
- [ ] Collaborative review (multiple reviewers)
- [ ] Custom iteration limits per session
- [ ] Feedback templates library
- [ ] Analytics dashboard

### Under Consideration

- [ ] Real-time collaboration
- [ ] Version control integration
- [ ] Automated quality scoring
- [ ] A/B testing of prompts

## 📝 License

Same as parent project.

## 🤝 Contributing

When contributing to HITL features:

1. Test all 3 API endpoints
2. Verify UI components render correctly
3. Update testing guide if adding new functionality
4. Follow existing code style
5. Add documentation for new features

## 📞 Support

For issues or questions:

1. Review this README
2. Check testing guide: `docs/HITL_TESTING_GUIDE.md`
3. Examine server logs for backend issues
4. Check browser console for frontend issues

---

**Implementation Date:** November 13, 2025  
**Version:** 1.0.0  
**Status:** ✅ Ready for Testing
