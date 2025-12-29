# HITL Feasibility Report Revision - Implementation Guide

## Overview

Human-in-the-Loop (HITL) revision support has been added to the feasibility report generation workflow. This enables non-expert users to request iterative refinements to feasibility reports without re-running the entire analysis pipeline.

**Key Benefits:**

- ✅ No re-ingestion of raw documents
- ✅ No re-analysis or recalculation
- ✅ Bounded token usage (~5,500 tokens per revision)
- ✅ Explicit versioning (v1, v2, v3...)
- ✅ Preserves verdict & core findings
- ✅ Audit trail of all revisions

---

## Architecture

### New Components

```
src/
├── states/
│   └── revision_state.py                    # NEW: RevisionState dataclass
├── app/
│   └── feasibility_revision.py              # NEW: Core revision logic
└── routes/
    ├── feasibility_revision_handler.py      # NEW: Handler for revision workflow
    └── planning_agent.py                    # UPDATED: New API endpoints

prompts/
└── feasibility_report_revise.txt            # NEW: Revision LLM prompt template
```

### Data Flow

```
User provides feedback
         │
         ▼
POST /revise-feasibility (with session_id, current_version, critique)
         │
         ▼
FeasibilityRevisionHandler
         │
    ┌────┴────┐
    │          │
    ▼          ▼
Load v1.md   Load thinking_summary.md
    │          │
    └────┬─────┘
         │
         ▼
revise_report() [core module]
         │
    ┌────┴────────────┐
    │                 │
    ▼                 ▼
Build prompt    Invoke LLM (with retry)
    │                 │
    └────┬────────────┘
         │
         ▼
    Parse response
         │
    ┌────┼────────────────┐
    │    │                │
    ▼    ▼                ▼
Validate Report   Save to disk   Update revision_log.json
    │
    └──── Return file_path + metadata
```

---

## API Endpoints

### 1. Revise Feasibility Report

**Endpoint**: `POST /revise-feasibility`

**Request Body:**

```json
{
  "session_id": "abc123def456",
  "current_version": 1,
  "human_critique": "Section 4 (Technical Analysis) is too brief. Please expand with specific Kubernetes mitigation strategies.",
  "revision_instructions": "(Optional) Any additional structured guidance",
  "max_revisions": 5
}
```

**Response (201 Created):**

```json
{
  "session_id": "abc123def456",
  "current_version": 1,
  "new_version": 2,
  "message": "Feasibility report revised successfully (v1 → v2)",
  "file_path": "output/session_abc/reports/feasibility_report_v2.md",
  "execution_time": 23.45
}
```

**Error Cases:**

- `404 Not Found`: Session not found or initial feasibility assessment missing
- `400 Bad Request`: Invalid version, empty critique, or other validation errors
- `409 Conflict`: Maximum revisions reached (v5 already exists)
- `500 Internal Server Error`: LLM invocation or file I/O errors

---

### 2. Get Revision History

**Endpoint**: `GET /revision-history/{session_id}`

**Response:**

```json
{
  "session_id": "abc123def456",
  "revisions": [
    {
      "version": 2,
      "created_at": "2024-01-15T10:15:30Z",
      "type": "hitl_revision",
      "previous_version": 1,
      "critique_file": "output/session_abc/revisions/revision_1_critique.txt",
      "summary_file": "output/session_abc/revisions/revision_1_summary.md",
      "file_path": "output/session_abc/reports/feasibility_report_v2.md",
      "execution_time": 23.45
    }
  ]
}
```

---

### 3. Get Current Version

**Endpoint**: `GET /current-feasibility-version/{session_id}`

**Response:**

```json
{
  "session_id": "abc123def456",
  "current_version": 2
}
```

---

## File Structure

All revision artifacts are stored in a session-specific directory:

```
output/session_abc/
├── context/
│   └── unified_context_abc.md              # Original (unchanged)
├── reports/
│   ├── thinking_summary_abc_20240115.md    # Original (unchanged)
│   ├── feasibility_report_v1.md            # Initial generation
│   ├── feasibility_report_v2.md            # Revision 1
│   └── feasibility_report_v3.md            # Revision 2
└── revisions/
    ├── revision_log.json                   # Master revision log
    ├── revision_1_critique.txt             # User feedback for v1→v2
    ├── revision_1_summary.md               # Changes made in v1→v2
    ├── revision_1_instructions.txt         # Structured guidance (optional)
    ├── revision_2_critique.txt             # User feedback for v2→v3
    ├── revision_2_summary.md               # Changes made in v2→v3
    └── ...
```

---

## Revision Constraints

### Input Constraints

| Artifact              | Size Limit        | Purpose                   |
| --------------------- | ----------------- | ------------------------- |
| Previous report (vN)  | ≤ 8,000 chars     | Full report content       |
| Thinking summary      | ≤ 4,000 chars     | Original analysis (fixed) |
| Human critique        | ≤ 2,000 chars     | User feedback             |
| Revision instructions | ≤ 1,000 chars     | Optional guidance         |
| **Total input**       | **~14,000 chars** | ~3,500 tokens (safe)      |

### Output Constraints

| Metric                 | Limit             | Rationale             |
| ---------------------- | ----------------- | --------------------- |
| Revised report size    | ≤ 8,000 chars     | Match original format |
| Output tokens          | ≤ 2,000           | Keep revision fast    |
| **Total per revision** | **~5,500 tokens** | Bounded & predictable |

### Versioning Constraints

| Constraint                    | Limit       | Reason                               |
| ----------------------------- | ----------- | ------------------------------------ |
| Max versions per session      | 5 (v1 → v5) | Prevent infinite loops; safety limit |
| Revision attempts per version | 3 retries   | Handle transient LLM failures        |
| Backoff strategy              | Exponential | 1s → 2s → 4s                         |

---

## Core Module: `revise_report()`

**Location**: `src/app/feasibility_revision.py`

**Entry Point:**

```python
def revise_report(
    session_id: str,
    current_version: int,
    feasibility_report_current: str,
    thinking_summary: str,
    human_critique: str,
    revision_instructions: Optional[str] = None,
    max_revisions: int = 5
) -> Dict[str, Any]:
```

**Process Flow:**

```
1. VALIDATE INPUTS
   ├─ session_id not empty
   ├─ current_version ≥ 1
   ├─ feasibility_report_current not empty
   ├─ thinking_summary not empty
   └─ human_critique not empty

2. CALCULATE NEXT VERSION
   ├─ next_version = current_version + 1
   ├─ if next_version > max_revisions: raise ValueError
   └─ OK: proceed

3. BUILD REVISION PROMPT
   ├─ Load revision prompt template
   ├─ Assemble user payload (4 sections)
   ├─ Combine template + payload
   └─ Return full prompt

4. INVOKE LLM WITH RETRY
   ├─ Invoke model.invoke(prompt)
   ├─ On failure: retry up to 3 times
   ├─ Exponential backoff: 1s → 2s → 4s
   └─ Return response

5. EXTRACT & PARSE
   ├─ Extract revised report (between delimiters)
   ├─ Extract revision summary
   └─ Return both

6. VALIDATE REVISED REPORT
   ├─ Not empty
   ├─ ≥ 3,000 chars (substantial)
   ├─ ≤ 8,500 chars (safe)
   ├─ Has markdown headers
   ├─ Preserves verdict
   └─ Return bool

7. SAVE TO DISK
   ├─ Create output directory
   ├─ Save feasibility_report_v(N+1).md
   ├─ Save revision_1_critique.txt
   ├─ Save revision_1_summary.md
   └─ Save revision_1_instructions.txt (if provided)

8. UPDATE REVISION LOG
   ├─ Load existing revision_log.json
   ├─ Add new revision entry
   ├─ Save updated log
   └─ Return metadata

9. RETURN RESULT
   └─ {status, new_version, file_path, ...}
```

---

## Revision Prompt Template

**Location**: `prompts/feasibility_report_revise.txt`

**Key Features:**

1. **Explicit Constraints**: Users must preserve verdict and scores
2. **Clear Input Contract**: Four distinct sections (previous report, thinking summary, critique, instructions)
3. **Detailed Process**: Step-by-step revision workflow
4. **Output Specification**: Delimited sections for easy parsing
5. **Tone & Style**: Professional, stakeholder-appropriate language

**Input Format:**

```
SECTION 1: feasibility_report_vN.md
───────────────────────────────────
[Full previous report markdown]

SECTION 2: thinking_summary.md
──────────────────────────────
[Original thinking summary (PRESERVE SCORES)]

SECTION 3: human_critique
──────────────────────────
[Free-form user feedback]

SECTION 4: revision_instructions (optional)
────────────────────────────────────────────
[Structured guidance if provided]
```

**Output Format:**

```
---REVISION_REPORT_START---
[FULL REVISED REPORT]
---REVISION_REPORT_END---

---REVISION_SUMMARY_START---
# Revision Summary
## Sections Revised
## Changes Made
## Unmodified Sections
---REVISION_SUMMARY_END---
```

---

## Usage Example

### Step 1: Generate Initial Feasibility (Prerequisites)

```bash
curl -X POST http://localhost:8000/feasibility \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my_session_001",
    "development_context": {
      "technologies": "AWS, React, Node.js",
      "technicalExpertise": "5+ years",
      "projectCosts": "$500k",
      ...
    }
  }'
```

**Response:**

```json
{
  "session_id": "my_session_001",
  "feasibility_report_file": "output/session_my_s/reports/feasibility_report_v1.md",
  "thinking_summary_file": "output/session_my_s/reports/thinking_summary_my_s_....md"
}
```

### Step 2: Request Revision

User reviews the feasibility report v1 and wants refinements:

```bash
curl -X POST http://localhost:8000/revise-feasibility \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my_session_001",
    "current_version": 1,
    "human_critique": "Section 4 (Technical Analysis) lacks detail on data migration strategy. Please expand with migration phases and rollback plan.",
    "revision_instructions": "Focus on operational risks related to data migration."
  }'
```

**Response:**

```json
{
  "session_id": "my_session_001",
  "current_version": 1,
  "new_version": 2,
  "message": "Feasibility report revised successfully (v1 → v2)",
  "file_path": "output/session_my_s/reports/feasibility_report_v2.md",
  "execution_time": 22.5
}
```

### Step 3: View Revision History

```bash
curl http://localhost:8000/revision-history/my_session_001
```

**Response:**

```json
{
  "session_id": "my_session_001",
  "revisions": [
    {
      "version": 2,
      "created_at": "2024-01-15T10:15:30Z",
      "type": "hitl_revision",
      "previous_version": 1,
      "critique_file": "output/session_my_s/revisions/revision_1_critique.txt",
      "summary_file": "output/session_my_s/revisions/revision_1_summary.md",
      "file_path": "output/session_my_s/reports/feasibility_report_v2.md",
      "execution_time": 22.5
    }
  ]
}
```

### Step 4: Get Current Version

```bash
curl http://localhost:8000/current-feasibility-version/my_session_001
```

**Response:**

```json
{
  "session_id": "my_session_001",
  "current_version": 2
}
```

---

## Error Handling

### Validation Errors

```
empty human_critique
→ HTTPException(400, "human_critique cannot be empty")

invalid current_version (< 1)
→ HTTPException(400, "current_version must be ≥ 1")

session not found
→ HTTPException(404, "Session not found")

initial feasibility missing
→ HTTPException(400, "Initial feasibility assessment not found")
```

### File Not Found Errors

```
feasibility_report_v1.md missing
→ HTTPException(404, "Feasibility report version 1 not found")

thinking_summary.md missing
→ HTTPException(404, "Thinking summary not found")
```

### Version Limit Errors

```
current_version = 5 (max reached)
→ HTTPException(409, "Maximum revision limit reached")
```

### LLM Errors

```
LLM invocation fails
→ Retry up to 3 times with exponential backoff (1s → 2s → 4s)
→ If all retries fail: HTTPException(500, "Revision failed: {error}")
```

### Output Validation Errors

```
revised report too short (< 3000 chars)
→ HTTPException(500, "Revised report failed validation")

verdict not preserved
→ HTTPException(500, "Revised report does not preserve verdict")

not valid markdown
→ HTTPException(500, "Revised report failed validation")
```

---

## Testing

### Unit Tests

Run the integration test suite:

```bash
python scripts/testing/test_hitl_revision.py
```

**Tests Included:**

1. ✅ Basic revision (v1 → v2)
2. ✅ Max revisions limit enforcement
3. ✅ Input validation (empty critique, invalid version)
4. ✅ File I/O and artifact persistence
5. ✅ Revision log creation and updates

**Expected Output:**

```
HITL FEASIBILITY REPORT REVISION - INTEGRATION TESTS
================================

TEST 1: Revise v1 → v2 (Refinement)
...
✓ REVISION COMPLETED SUCCESSFULLY

TEST 2: Exceed Max Revisions
...
✓ Correctly rejected revision beyond limit

TEST 3: Validation Checks
...
✓ Correctly rejected empty critique
✓ Correctly rejected invalid version

TEST SUMMARY
✓ PASS: test_revision_1
✓ PASS: test_validation
Total: 2/2 passed
```

---

## Design Principles

### 1. **No Re-Ingestion**

- Raw documents and unified_context are NEVER re-processed
- Only prior report (vN) and thinking_summary are used
- Token usage remains bounded and predictable

### 2. **Verdict Preservation**

- LLM is explicitly instructed to preserve feasibility verdict
- Prompt includes thinking_summary as reference truth
- Output validation checks for verdict presence

### 3. **Explicit Versioning**

- Each revision creates a new numbered version (v1, v2, v3...)
- Version numbers are never skipped or reused
- Revision log tracks full audit trail

### 4. **Bounded Token Usage**

- Input: ~3,500 tokens (fixed)
- Output: ~2,000 tokens (fixed)
- Per-revision: ~5,500 tokens (safe)
- 5 revisions max: ~27,500 tokens (very safe)

### 5. **Handler Separation**

- Revision logic isolated in `src/app/feasibility_revision.py`
- Handler orchestrates workflow in `src/routes/feasibility_revision_handler.py`
- API endpoints delegate to handler in `src/routes/planning_agent.py`
- Clear separation of concerns

### 6. **Audit Trail**

- All revisions tracked in `revision_log.json`
- Critique saved in `revision_N_critique.txt`
- Summary saved in `revision_N_summary.md`
- Full reproducibility and accountability

---

## Integration with Existing Flow

### Does NOT Break Initial Flow

- ✅ Initial generation (`/feasibility`) unchanged
- ✅ Document ingestion unchanged
- ✅ Thinking summary generation unchanged
- ✅ Feasibility report v1 generation unchanged

### Orthogonal Feature

- ✅ Revision is optional (users can ignore and proceed to plan generation)
- ✅ Plan generation works with any version (v1, v2, v3...)
- ✅ No dependencies on revision logic elsewhere

### Safe for Concurrent Sessions

- ✅ Each session has own output directory
- ✅ No shared state between sessions
- ✅ Revision log scoped to session
- ✅ No global locks or race conditions

---

## Next Steps (Optional Enhancements)

1. **Frontend Integration**: Add revision UI panel in `FeasibilityStep.jsx`
2. **Diff Visualization**: Show what changed between versions (highlight added/removed text)
3. **Revision Templates**: Pre-built critique suggestions (e.g., "Add more evidence", "Expand risks")
4. **Batch Revisions**: Process multiple critiques in parallel
5. **Rollback**: Allow reverting to previous version
6. **Export History**: Download all versions as ZIP with revision log

---

## Support & Troubleshooting

### Common Issues

**Issue**: "Initial feasibility assessment not found"

- **Cause**: `/feasibility` endpoint not called before `/revise-feasibility`
- **Fix**: Call `/feasibility` first to generate v1

**Issue**: "Feasibility report version 1 not found"

- **Cause**: Files not saved properly during initial generation
- **Fix**: Check `output/session_XXX/reports/` directory exists and contains `feasibility_report_v1.md`

**Issue**: "Maximum revision limit reached"

- **Cause**: Already created v5, trying to create v6
- **Fix**: Pass `max_revisions: 6+` if needed, or start new session

**Issue**: "LLM invocation failed after 3 retries"

- **Cause**: LLM service down or rate limited
- **Fix**: Check LLM provider status, wait a moment, retry

### Debug Mode

Enable verbose output:

```python
handler = FeasibilityRevisionHandler(verbose=True)
result = handler.revise_feasibility(...)
```

Check revision artifacts:

```bash
cat output/session_XXX/revisions/revision_1_critique.txt
cat output/session_XXX/revisions/revision_1_summary.md
cat output/session_XXX/revisions/revision_log.json
```

---

## Summary

The HITL feasibility report revision feature enables users to iteratively refine feasibility reports through human feedback while maintaining:

- ✅ Bounded token usage
- ✅ Preserved verdict and scores
- ✅ Explicit versioning
- ✅ Audit trails
- ✅ No re-analysis required
- ✅ Clear error handling

All without disrupting the existing initial generation flow.
