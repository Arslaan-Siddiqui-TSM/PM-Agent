# HITL Feasibility Report Revision - Quick Start

## TL;DR

Added **Human-in-the-Loop (HITL) revision system** for feasibility reports. Users can now request iterative refinements without re-running analysis.

```bash
# 1. Generate initial report (existing flow)
curl -X POST http://localhost:8000/feasibility \
  -H "Content-Type: application/json" \
  -d '{"session_id": "my_session", "development_context": {...}}'

# 2. Request revision
curl -X POST http://localhost:8000/revise-feasibility \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my_session",
    "current_version": 1,
    "human_critique": "Section 4 needs more technical depth."
  }'

# 3. Get revision history
curl http://localhost:8000/revision-history/my_session
```

---

## What Changed

### Files Created (7 new)

- `src/states/revision_state.py` - Data model
- `src/app/feasibility_revision.py` - Core logic (600+ lines)
- `src/routes/feasibility_revision_handler.py` - Handler (350+ lines)
- `prompts/feasibility_report_revise.txt` - LLM prompt
- `scripts/testing/test_hitl_revision.py` - Test suite
- `docs/HITL_REVISION_GUIDE.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Summary

### Files Updated (1)

- `src/routes/planning_agent.py` - Added 3 new endpoints

### New API Endpoints (3)

```
POST   /revise-feasibility                  - Request revision
GET    /revision-history/{session_id}       - View all revisions
GET    /current-feasibility-version/{session_id} - Get current version
```

---

## Key Constraints (by Design)

| Aspect                   | Limit         | Reason                    |
| ------------------------ | ------------- | ------------------------- |
| Max versions per session | 5 (v1→v5)     | Prevent infinite loops    |
| Token usage per revision | ~5,500        | Bounded and predictable   |
| Input size               | ~14,000 chars | Keep memory usage safe    |
| Output size              | ~8,000 chars  | Match original format     |
| Retry attempts           | 3             | Handle transient failures |

---

## Testing

```bash
# Run integration tests
python scripts/testing/test_hitl_revision.py

# Expected: 2/2 tests passed ✅
```

---

## Architecture

```
Existing Flow (Unchanged)          New HITL Flow
═══════════════════════           ═════════════════════
1. Upload docs                    1. Generate feasibility v1
2. Answer questionnaire      →    2. User requests revision
3. Generate feasibility v1        3. POST /revise-feasibility
4. Review report                  4. Generates feasibility v2
5. Generate plan                  5. User can refine further
                                  6. Or proceed to plan generation
```

---

## Design Principles

✅ **No Re-Ingestion** - Raw docs never re-processed  
✅ **No Re-Analysis** - Scores/verdict preserved from thinking_summary  
✅ **Bounded Tokens** - ~5,500 tokens per revision  
✅ **Explicit Versioning** - v1, v2, v3 (sequential)  
✅ **Audit Trail** - All revisions tracked with metadata  
✅ **Error Safe** - Comprehensive validation and retry  
✅ **Non-Breaking** - Existing flow completely unchanged

---

## File Organization

```
output/session_XXX/
├── reports/
│   ├── feasibility_report_v1.md
│   ├── feasibility_report_v2.md        ← New revision
│   └── feasibility_report_v3.md
└── revisions/
    ├── revision_log.json              ← Master log
    ├── revision_1_critique.txt        ← User feedback
    └── revision_1_summary.md          ← Changes made
```

---

## Example Workflow

### Initial Generation (Existing)

```bash
curl -X POST http://localhost:8000/feasibility \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "proj_001",
    "development_context": {
      "technologies": "AWS, React, Node.js",
      "technicalExpertise": "5+ years",
      "projectCosts": "$500k",
      ...25 fields total
    }
  }'

Response:
{
  "feasibility_report_file": "output/session_proj/reports/feasibility_report_v1.md",
  "thinking_summary_file": "output/session_proj/reports/thinking_summary_proj.md"
}
```

### User Reviews Report v1

User reads the report and wants:

- More detail on Kubernetes strategy
- Clearer team allocation

### Request Revision (New)

```bash
curl -X POST http://localhost:8000/revise-feasibility \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "proj_001",
    "current_version": 1,
    "human_critique": "Section 4 (Technical Analysis) is too vague on Kubernetes. Add deployment strategy, scaling considerations, and failure recovery approach. Section 6 (Operational Analysis) needs concrete team allocation table showing roles, responsibilities, and utilization rates.",
    "revision_instructions": "Focus on operational readiness for production deployment."
  }'

Response:
{
  "session_id": "proj_001",
  "current_version": 1,
  "new_version": 2,
  "message": "Feasibility report revised successfully (v1 → v2)",
  "file_path": "output/session_proj/reports/feasibility_report_v2.md",
  "execution_time": 22.5
}
```

### Check History (New)

```bash
curl http://localhost:8000/revision-history/proj_001

Response:
{
  "session_id": "proj_001",
  "revisions": [
    {
      "version": 2,
      "created_at": "2024-01-15T10:15:30Z",
      "type": "hitl_revision",
      "previous_version": 1,
      "file_path": "output/session_proj/reports/feasibility_report_v2.md",
      "execution_time": 22.5
    }
  ]
}
```

### Further Refinements (Optional)

User reads v2, requests another revision:

```bash
curl -X POST http://localhost:8000/revise-feasibility \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "proj_001",
    "current_version": 2,
    "human_critique": "Add more specific technology examples for Node.js performance optimization. The risks section needs quantified likelihood/impact scores."
  }'

# Creates feasibility_report_v3.md
```

### Proceed to Plan Generation (Existing)

Once satisfied with the feasibility report, proceed with plan generation:

```bash
curl -X POST http://localhost:8000/generate-plan \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "proj_001",
    "max_iterations": 5
  }'

# Plan generation uses the latest feasibility report version
```

---

## Key Files to Review

### For Implementation Details

- [`src/app/feasibility_revision.py`](src/app/feasibility_revision.py) - Core logic (step-by-step comments)
- [`src/routes/feasibility_revision_handler.py`](src/routes/feasibility_revision_handler.py) - Handler flow

### For API Details

- [`src/routes/planning_agent.py`](src/routes/planning_agent.py) - Endpoints (lines ~200-400)

### For Prompt/LLM Details

- [`prompts/feasibility_report_revise.txt`](prompts/feasibility_report_revise.txt) - LLM instructions

### For Full Documentation

- [`docs/HITL_REVISION_GUIDE.md`](docs/HITL_REVISION_GUIDE.md) - Comprehensive guide
- [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Implementation overview

---

## Error Handling

| Error                 | Status | Meaning                                          |
| --------------------- | ------ | ------------------------------------------------ |
| Session not found     | 404    | Create session first with `/upload`              |
| Feasibility not found | 400    | Generate feasibility first with `/feasibility`   |
| Invalid version       | 400    | Version must be ≥ 1 and ≤ max_revisions          |
| Empty critique        | 400    | Provide meaningful feedback                      |
| Max revisions reached | 409    | Can't exceed v5 (pass max_revisions to increase) |
| LLM failed            | 500    | Retried 3x; check LLM provider status            |

---

## Token Usage

```
Per Revision:
├─ Input:  ~3,500 tokens (report + summary + critique)
├─ Output: ~2,000 tokens (revised report)
└─ Total:  ~5,500 tokens

Safe Budget:
├─ 5 revisions: ~27,500 tokens
├─ vs. typical GPT-4 limits: 100,000+ tokens
└─ Prediction: Very safe and affordable
```

---

## Testing (Run Locally)

```bash
# 1. Run integration tests
python scripts/testing/test_hitl_revision.py

# Expected output:
# ✓ PASS: test_revision_1
# ✓ PASS: test_validation
# Total: 2/2 passed ✅

# 2. Check generated files
ls -la output/session_test_ses/reports/
ls -la output/session_test_ses/revisions/

# 3. Read revision summary
cat output/session_test_ses/revisions/revision_1_summary.md
```

---

## What's NOT Changed

✅ Initial document upload flow  
✅ Document parsing and JSON conversion  
✅ Feasibility analysis algorithm  
✅ Thinking summary generation  
✅ Initial report v1 generation  
✅ Project plan generation  
✅ All existing endpoints

**Revision is completely orthogonal - fully backward compatible!**

---

## Next Steps

### Immediate (Done)

- ✅ Core logic implemented
- ✅ API endpoints added
- ✅ Tests passing
- ✅ Full documentation

### Optional (Future)

- Frontend UI panel for revisions
- Revision diff visualization
- Pre-built critique templates
- Batch revisions
- Rollback to previous version

---

## Support

**Questions?** See [`docs/HITL_REVISION_GUIDE.md`](docs/HITL_REVISION_GUIDE.md)

**Issues?** Check:

1. Session exists (from `/upload`)
2. Feasibility v1 exists (from `/feasibility`)
3. Files in `output/session_XXX/reports/`
4. Test suite: `python scripts/testing/test_hitl_revision.py`

---

## Summary

**What**: Added HITL revision system  
**Where**: 7 new files, 1 updated, 3 endpoints  
**Why**: Enable iterative refinement without re-analysis  
**How**: Preserve scores, track versions, bound tokens  
**Status**: ✅ Complete & tested  
**Impact**: Non-breaking, fully backward compatible

**Ready to use!**
