# HITL Feasibility Assessment - Integration Testing Guide

## Overview

This guide provides comprehensive testing procedures for the Human-in-the-Loop (HITL) feasibility assessment feature.

**Feature Summary:**

- Iterative feasibility report generation with human review
- Approval/feedback mechanism with auto-fill template
- Critique generation from natural language feedback
- Automatic revision based on structured critique
- Maximum iteration limits (default: 3)
- Complete audit trail with revision history

---

## Prerequisites

### Backend Setup

1. **Start the FastAPI server:**

```bash
cd /Users/vaidikjaiswal/Desktop/PM-Agent-using-ReWOO
python server.py
```

Server should start on: `http://localhost:8000`

2. **Verify backend endpoints:**
   - Open: `http://localhost:8000/docs`
   - Confirm these endpoints exist:
     - `POST /api/feasibility/start`
     - `POST /api/feasibility/review`
     - `GET /api/feasibility/status/{session_id}`

### Frontend Setup

1. **Start the React dev server:**

```bash
cd frontend
npm run dev
```

Frontend should start on: `http://localhost:5173`

2. **Verify dependencies:**

```bash
npm list react-toastify prop-types
```

---

## Test Plan

### Phase 1: API Endpoint Testing

#### Test 1.1: Start Feasibility Endpoint

**Request:**

```bash
curl -X POST http://localhost:8000/api/feasibility/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "development_context": {
      "methodology": "Agile",
      "teamSize": "5",
      "timeline": "6 months",
      "budget": "$100k",
      "techStack": "React, Node.js, PostgreSQL",
      "constraints": "Must be cloud-native"
    }
  }'
```

**Expected Response:**

```json
{
  "session_id": "test-session-123",
  "status": "awaiting_human",
  "iteration": 0,
  "max_iterations": 3,
  "feasibility_report": "# FEASIBILITY ASSESSMENT\n\n...",
  "thinking_summary": "...",
  "message": "Feasibility report generated. Awaiting human review.",
  "execution_time": 45.23
}
```

**Validation Checklist:**

- [ ] Status code: 200
- [ ] Status field: "awaiting_human"
- [ ] Iteration is 0
- [ ] Feasibility report is not empty
- [ ] Report contains structured sections
- [ ] Execution time is reasonable (<60s)

---

#### Test 1.2: Review with Approval

**Request:**

```bash
curl -X POST http://localhost:8000/api/feasibility/review \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "approved": true
  }'
```

**Expected Response:**

```json
{
  "session_id": "test-session-123",
  "status": "approved",
  "message": "Feasibility report approved successfully.",
  "feasibility_report": "# FEASIBILITY ASSESSMENT\n\n...",
  "execution_time": 0.12
}
```

**Validation Checklist:**

- [ ] Status code: 200
- [ ] Status field: "approved"
- [ ] Workflow completes immediately
- [ ] No additional iterations triggered

---

#### Test 1.3: Review with Feedback (Request Changes)

**Request:**

```bash
curl -X POST http://localhost:8000/api/feasibility/review \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "approved": false,
    "feedback": "Please add more detail about database scalability and provide specific performance metrics for the API endpoints."
  }'
```

**Expected Response:**

```json
{
  "session_id": "test-session-123",
  "status": "awaiting_human",
  "iteration": 1,
  "max_iterations": 3,
  "feasibility_report": "# FEASIBILITY ASSESSMENT (Revised)\n\n...",
  "critique": "# FEASIBILITY REPORT CRITIQUE (Iteration 1)...",
  "message": "Revision 1 complete. Awaiting review.",
  "execution_time": 52.45
}
```

**Validation Checklist:**

- [ ] Status code: 200
- [ ] Status field: "awaiting_human"
- [ ] Iteration incremented to 1
- [ ] Critique is generated and not empty
- [ ] Revised report addresses feedback
- [ ] Report shows changes from previous version

---

#### Test 1.4: Status Endpoint

**Request:**

```bash
curl http://localhost:8000/api/feasibility/status/test-session-123
```

**Expected Response:**

```json
{
  "session_id": "test-session-123",
  "status": "awaiting_human",
  "iteration": 1,
  "max_iterations": 3,
  "approved": false,
  "feasibility_report": "...",
  "thinking_summary": "...",
  "critique": "...",
  "revision_history_count": 2,
  "message": "Current status: awaiting_human"
}
```

**Validation Checklist:**

- [ ] Status code: 200
- [ ] Status reflects current workflow state
- [ ] Iteration counter is accurate
- [ ] Revision history count matches iterations
- [ ] All content fields are populated

---

### Phase 2: Frontend UI Testing

#### Test 2.1: Initial Report Generation

**Steps:**

1. Open frontend: `http://localhost:5173`
2. Upload documents (or use default files)
3. Complete development process form
4. Click "Check Feasibility" button

**Expected Behavior:**

- [ ] Button shows loading state: "Analyzing Feasibility..."
- [ ] After completion, HITL review UI appears
- [ ] Iteration badge shows: "Iteration 1 of 3"
- [ ] Feasibility report is displayed in scrollable container
- [ ] Three buttons are visible: Auto-fill, Request Changes, Approve
- [ ] Feedback textarea is empty
- [ ] Success toast appears

---

#### Test 2.2: Auto-fill Feedback Template

**Steps:**

1. In HITL review UI, click "Auto-fill Feedback Template" button

**Expected Behavior:**

- [ ] Textarea is populated with structured template
- [ ] Template contains 5 numbered sections
- [ ] Template includes placeholders like [specific technology choices]
- [ ] Cursor is positioned in textarea
- [ ] Template is editable

**Template Structure Validation:**

```
1. **Technical Stack Section**:
2. **Timeline Estimates**:
3. **Risk Assessment**:
4. **Resource Analysis**:
5. **Additional Notes**:
```

---

#### Test 2.3: Request Changes with Feedback

**Steps:**

1. Click "Auto-fill Feedback Template"
2. Edit the template with specific feedback
3. Click "Request Changes" button

**Expected Behavior:**

- [ ] Button shows loading: "Requesting Changes..."
- [ ] Buttons are disabled during submission
- [ ] After completion, new iteration appears
- [ ] Iteration badge updates: "Iteration 2 of 3"
- [ ] New revised report is displayed
- [ ] Critique section appears showing AI-generated critique
- [ ] Feedback textarea is cleared
- [ ] Success toast shows iteration number

---

#### Test 2.4: Request Changes WITHOUT Feedback

**Steps:**

1. Ensure feedback textarea is empty
2. Click "Request Changes" button

**Expected Behavior:**

- [ ] Alert appears: "Please provide feedback before requesting changes."
- [ ] Request is NOT submitted
- [ ] No API call is made
- [ ] UI remains in current state

---

#### Test 2.5: Approve Report

**Steps:**

1. Click "Approve & Continue" button

**Expected Behavior:**

- [ ] Button shows loading: "Approving..."
- [ ] After completion, success message appears
- [ ] Workflow advances to Review step (Step 4)
- [ ] Feasibility report is available in Review step
- [ ] Success toast confirms approval

---

#### Test 2.6: Multiple Iterations

**Steps:**

1. Generate initial report
2. Request changes (iteration 1)
3. Request changes again (iteration 2)
4. Request changes a third time (iteration 3)

**Expected Behavior:**

- [ ] Iteration 1: Badge shows "Iteration 2 of 3"
- [ ] Iteration 2: Badge shows "Iteration 3 of 3"
- [ ] Iteration 3: Warning message appears
- [ ] Message: "Maximum iterations (3) reached"
- [ ] Workflow automatically advances after 2 seconds
- [ ] Final report is used despite not being explicitly approved

---

#### Test 2.7: Critique Display

**Steps:**

1. Generate initial report
2. Request changes with specific feedback
3. Wait for revision to complete

**Expected Behavior:**

- [ ] Critique section appears below the report
- [ ] Critique has distinct styling (yellow/warning theme)
- [ ] Critique is scrollable
- [ ] Critique contains structured sections:
  - Executive Summary
  - Critical Issues
  - High Priority Improvements
  - Missing Information
- [ ] Critique references the human feedback

---

### Phase 3: Edge Cases and Error Handling

#### Test 3.1: Network Error During Generation

**Steps:**

1. Stop the backend server
2. Click "Check Feasibility" button

**Expected Behavior:**

- [ ] Error toast appears with message
- [ ] Loading state ends
- [ ] Buttons are re-enabled
- [ ] User can retry after fixing issue

---

#### Test 3.2: Network Error During Review

**Steps:**

1. Generate report successfully
2. Stop the backend server
3. Click "Approve & Continue"

**Expected Behavior:**

- [ ] Error toast appears
- [ ] User remains on feasibility step
- [ ] Report content is preserved
- [ ] User can retry after backend restarts

---

#### Test 3.3: Invalid Session ID

**Steps:**

1. Manually call API with non-existent session ID

**Request:**

```bash
curl -X POST http://localhost:8000/api/feasibility/start \
  -H "Content-Type: application/json" \
  -d '{"session_id": "invalid-session-999"}'
```

**Expected Behavior:**

- [ ] Status code: 404
- [ ] Error message indicates session not found
- [ ] Frontend shows error toast

---

#### Test 3.4: Empty Feasibility Report

**Test Scenario:** LLM returns empty or very short content

**Expected Behavior:**

- [ ] Validation catches insufficient content
- [ ] Error message is clear
- [ ] User is prompted to retry
- [ ] No corrupt state in UI

---

### Phase 4: State Management Testing

#### Test 4.1: Refresh Page During Review

**Steps:**

1. Generate report and reach HITL review UI
2. Refresh browser page (F5)

**Expected Behavior:**

- [ ] Session state is lost (expected - in-memory)
- [ ] User starts from upload step
- [ ] No errors in console
- [ ] Clean state reset

**Note:** Persistent session storage is out of scope for this HITL feature.

---

#### Test 4.2: Browser Back Button

**Steps:**

1. Complete upload and dev process
2. Generate feasibility report
3. Click browser back button

**Expected Behavior:**

- [ ] Returns to previous step
- [ ] No errors in console
- [ ] State remains consistent

---

### Phase 5: Visual and UX Testing

#### Test 5.1: Responsive Design

**Test on different screen sizes:**

- Desktop (1920x1080)
- Tablet (768x1024)
- Mobile (375x667)

**Validation Checklist:**

- [ ] Buttons stack vertically on mobile
- [ ] Report content is readable on all sizes
- [ ] Textarea is usable on mobile
- [ ] No horizontal scrolling
- [ ] Touch targets are adequate (>44px)

---

#### Test 5.2: Loading States

**Validate visual feedback:**

- [ ] Buttons show loading text during operations
- [ ] Loading indicator is visible
- [ ] Buttons are disabled during loading
- [ ] No double-submission possible

---

#### Test 5.3: Color and Contrast

**Accessibility validation:**

- [ ] Iteration badge is readable
- [ ] Report text has sufficient contrast
- [ ] Critique section is distinguishable
- [ ] Button colors are distinct
- [ ] Focus states are visible

---

### Phase 6: Performance Testing

#### Test 6.1: Large Report Handling

**Test with extensive feasibility report (>10,000 chars)**

**Validation:**

- [ ] Report renders without lag
- [ ] Scrolling is smooth
- [ ] No memory leaks in browser
- [ ] Textarea remains responsive

---

#### Test 6.2: Multiple Rapid Iterations

**Steps:**

1. Request changes 3 times in quick succession

**Expected Behavior:**

- [ ] Each request is queued properly
- [ ] No race conditions
- [ ] Iteration counter increments correctly
- [ ] All reports are distinct

---

## Success Criteria

### Critical Requirements (Must Pass)

- [ ] Initial report generation works
- [ ] Approval workflow advances to next step
- [ ] Request changes triggers revision
- [ ] Iteration counter is accurate
- [ ] Max iterations limit is enforced
- [ ] Feedback validation prevents empty submissions
- [ ] Auto-fill template populates correctly
- [ ] Error messages are clear and actionable

### Important Requirements (Should Pass)

- [ ] Critique is generated and displayed
- [ ] Responsive design works on mobile
- [ ] Loading states provide feedback
- [ ] Toast notifications appear
- [ ] Status endpoint returns accurate data

### Nice-to-Have (Optional)

- [ ] Report markdown is well-formatted
- [ ] Critique provides actionable insights
- [ ] Revision actually improves content
- [ ] Performance is optimal (<5s per iteration)

---

## Debugging Tips

### Backend Debugging

**Check logs:**

```bash
# Server should print detailed logs
# Look for these indicators:
- "STARTING FEASIBILITY ASSESSMENT (HITL Mode)"
- "PROCESSING HUMAN REVIEW"
- "Current iteration: X"
- "Route: NEEDS_REVISION -> critique"
```

**Inspect checkpointer state:**

```python
from src.app.feasibility_graph import get_checkpointer

checkpointer = get_checkpointer()
# Examine saved states
```

### Frontend Debugging

**Check browser console:**

- No errors should appear
- API calls should return 200 status
- Global `window.__feasibilityData` should be populated

**React DevTools:**

- Verify state updates in FeasibilityStep component
- Check hook values in useProjectWorkflow

**Network tab:**

- Verify API endpoints are called correctly
- Check request/response payloads
- Confirm proper HTTP methods (POST/GET)

---

## Known Limitations

1. **Session Persistence**: State is lost on page refresh (in-memory only)
2. **Concurrent Users**: MemorySaver is not suitable for production with multiple users
3. **Large Files**: Very large documents may cause timeouts
4. **LLM Variability**: Critique quality depends on LLM performance

---

## Rollback Plan

If critical issues are found:

1. **Disable HITL Mode**: Set frontend to use legacy `checkFeasibility()`
2. **Revert Backend**: Keep old `/api/feasibility` endpoint active
3. **Feature Flag**: Add environment variable to toggle HITL

**Quick revert:**

```javascript
// In FeasibilityStep.jsx, replace handleStartFeasibility with:
const handleStartFeasibility = async () => {
  await onCheckFeasibility(false); // Use legacy mode
};
```

---

## Post-Testing Actions

### If Tests Pass:

- [ ] Document any edge cases discovered
- [ ] Update user documentation
- [ ] Create demo video/screenshots
- [ ] Plan production deployment

### If Tests Fail:

- [ ] Log all failures with reproduction steps
- [ ] Prioritize critical bugs
- [ ] Fix and re-test
- [ ] Consider rollback if blocking

---

## Contact & Support

For issues during testing:

1. Check server logs in terminal
2. Check browser console for errors
3. Verify all dependencies are installed
4. Review the implementation plan in conversation history

---

**Testing Date**: ******\_******
**Tester Name**: ******\_******
**Test Results**: ☐ Pass ☐ Fail ☐ Partial
**Notes**: ******************\_\_\_******************
