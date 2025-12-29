# Version Comparison & Revision History Guide

## Overview

Your PM-Agent system now supports comprehensive version tracking and comparison across the entire feasibility report generation and revision workflow. This guide shows you how to:

1. **View all revisions** for a session (v1 through vN)
2. **Compare versions** to see what changed between revisions
3. **Analyze token usage** per version
4. **Understand revision metrics** (character count, line count, changes)

---

## Quick Start Commands

### View Revision History

```bash
# In your application frontend or API:
GET /api/revision-history/{session_id}
```

**Response example:**

```json
{
  "session_id": "e50c8bb4-464f-4cc2-942a-c171c5ef4f48",
  "revisions": [
    {
      "version": 1,
      "created_at": "2024-12-22T10:15:33.123456",
      "type": "initial",
      "file_path": "output/session_e50c8bb4/reports/feasibility_report_v1.md"
    },
    {
      "version": 2,
      "created_at": "2024-12-22T10:20:15.654321",
      "type": "human_revision",
      "file_path": "output/session_e50c8bb4/reports/feasibility_report_v2.md"
    },
    {
      "version": 3,
      "created_at": "2024-12-22T10:25:42.987654",
      "type": "human_revision",
      "file_path": "output/session_e50c8bb4/reports/feasibility_report_v3.md"
    }
  ]
}
```

---

## Compare Versions (Command Line)

Use the `compare_versions.py` script to compare any two versions:

### Full Comparison (default)

```bash
python scripts/compare_versions.py e50c8bb4 1 2
```

Shows:

- Summary statistics (character count, line count, changes)
- Side-by-side preview of first 50 lines
- Full unified diff of all changes

### Summary Only

```bash
python scripts/compare_versions.py e50c8bb4 1 2 --summary
```

Shows:

- Character count changes
- Line count changes
- Percentage change

### Diff Only

```bash
python scripts/compare_versions.py e50c8bb4 1 2 --diff
```

Shows:

- Color-coded unified diff
- Green: Added lines
- Red: Removed lines

### Side-by-Side Preview

```bash
python scripts/compare_versions.py e50c8bb4 1 2 --preview
```

Shows:

- First 50 lines of each version
- Side-by-side comparison

---

## File Structure

Your revision reports are organized as follows:

```
output/session_e50c8bb4/
├── reports/
│   ├── feasibility_report_v1.md           # Initial feasibility report
│   ├── feasibility_report_v2.md           # First revision
│   ├── feasibility_report_v3.md           # Second revision
│   ├── feasibility_report_v4.md           # Third revision
│   ├── thinking_summary_v1.md             # Initial thinking
│   ├── token_stats_feasibility.json       # Token metrics for initial report
│   ├── token_stats_revision_v2.json       # Token metrics for v2 revision
│   ├── token_stats_revision_v3.json       # Token metrics for v3 revision
│   └── token_stats_revision_v4.json       # Token metrics for v4 revision
└── [other session files]
```

---

## Understanding Token Reports

Each revision generates a JSON token report showing:

### Token Stats Structure

```json
{
  "session_id": "e50c8bb4",
  "phase": "feasibility_initial",
  "summary": {
    "total_calls": 2,
    "total_input_tokens": 63870,
    "total_output_tokens": 30316,
    "total_tokens": 94186,
    "cost_estimate": {
      "input_cost": 0.001277,
      "output_cost": 0.001819,
      "total_cost": 0.003096
    }
  },
  "calls": [
    {
      "call_id": 1,
      "provider": "nvidia",
      "model": "nvidia/llama-3.1-nemotron-70b-instruct",
      "input_tokens": 32955,
      "output_tokens": 8055,
      "duration_seconds": 15.234,
      "tokens_per_second": 2692.45,
      "timestamp": "2024-12-22T10:15:33.123456"
    },
    {
      "call_id": 2,
      "provider": "nvidia",
      "model": "nvidia/llama-3.1-nemotron-70b-instruct",
      "input_tokens": 30915,
      "output_tokens": 22261,
      "duration_seconds": 18.567,
      "tokens_per_second": 2856.12,
      "timestamp": "2024-12-22T10:16:52.654321"
    }
  ]
}
```

### Read Token Reports

```bash
# View all token reports for a session
python scripts/token_report_reader.py e50c8bb4 list

# View full token report
python scripts/token_report_reader.py e50c8bb4 full

# View specific report
python scripts/token_report_reader.py e50c8bb4 token_stats_feasibility.json
```

---

## Complete Workflow Example

### Step 1: Upload Documents

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf"

# Response: session_id = "e50c8bb4-..."
```

### Step 2: Generate Initial Feasibility Report

```bash
curl -X POST "http://localhost:8000/api/feasibility" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "e50c8bb4-464f-4cc2-942a-c171c5ef4f48"
  }'

# Creates: feasibility_report_v1.md
# Console shows: Token usage, cost estimate
```

### Step 3: View Token Usage

```bash
python scripts/token_report_reader.py e50c8bb4 full
# Shows: 2 LLM calls, total tokens, cost
```

### Step 4: Human Revision (First)

```bash
curl -X POST "http://localhost:8000/api/revise-feasibility" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "e50c8bb4-464f-4cc2-942a-c171c5ef4f48",
    "current_version": 1,
    "human_critique": "The risk assessment needs more detail on technical debt..."
  }'

# Creates: feasibility_report_v2.md
# Console shows: Token usage, cost estimate for revision
```

### Step 5: Compare Versions

```bash
python scripts/compare_versions.py e50c8bb4 1 2

# Output shows:
# - Summary: changed from 1,234 chars to 1,456 chars (+18%)
# - Preview: side-by-side of first 50 lines
# - Diff: exact changes highlighted
```

### Step 6: Second Revision

```bash
curl -X POST "http://localhost:8000/api/revise-feasibility" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "e50c8bb4-464f-4cc2-942a-c171c5ef4f48",
    "current_version": 2,
    "human_critique": "Good, but add more specifics about timeline..."
  }'

# Creates: feasibility_report_v3.md
```

### Step 7: Compare v1 to v3 (Skip v2)

```bash
python scripts/compare_versions.py e50c8bb4 1 3

# Shows cumulative changes from initial to latest
```

### Step 8: Get Full Revision History

```bash
curl -X GET "http://localhost:8000/api/revision-history/e50c8bb4-464f-4cc2-942a-c171c5ef4f48"

# Response shows all v1, v2, v3 with timestamps
```

---

## API Endpoints Reference

### 1. Get Revision History

```
GET /api/revision-history/{session_id}
```

**Returns:**

- All available versions (v1, v2, v3...)
- Timestamps for each version
- File paths
- Type (initial or human_revision)

---

### 2. Revise Feasibility Report

```
POST /api/revise-feasibility
```

**Request Body:**

```json
{
  "session_id": "e50c8bb4-...",
  "current_version": 1,
  "human_critique": "Description of issues and improvements needed",
  "revision_instructions": "Optional: Specific guidance for the revision",
  "max_revisions": 5
}
```

**Response:**

```json
{
  "session_id": "e50c8bb4-...",
  "current_version": 1,
  "new_version": 2,
  "message": "Report revised successfully",
  "file_path": "output/session_e50c8bb4/reports/feasibility_report_v2.md",
  "execution_time": 45.234,
  "token_usage": {
    "total_calls": 1,
    "total_input_tokens": 28450,
    "total_output_tokens": 4788,
    "cost_estimate": {
      "input_cost": 0.000569,
      "output_cost": 0.000287,
      "total_cost": 0.000856
    }
  }
}
```

---

## Token Analysis Best Practices

### Tracking Costs Across Revisions

Use this to understand where tokens are spent:

```bash
# Get initial report tokens
python scripts/token_report_reader.py e50c8bb4 token_stats_feasibility.json

# Get v2 revision tokens
python scripts/token_report_reader.py e50c8bb4 token_stats_revision_v2.json

# Compare to understand revision cost
# Initial: $0.003096
# Revision v2: $0.000856
# Total for v1 + v2: $0.003952
```

### Cost Optimization Tips

1. **Initial Report**: Usually most expensive (full analysis of documents)

   - Typical: 60k-80k input tokens, 20k-30k output tokens
   - Cost: $0.002-0.005

2. **Revisions**: Usually cheaper (focused changes)

   - Typical: 20k-30k input tokens, 3k-5k output tokens
   - Cost: $0.0005-0.001

3. **Monitor Token Growth**:
   ```bash
   python scripts/compare_versions.py e50c8bb4 1 2 --summary
   # If output grows >20%, consider a new session
   ```

---

## Troubleshooting

### "Report not found" error

```bash
# Check if files exist:
ls -la output/session_e50c8bb4/reports/feasibility_report_v*.md

# Make sure session_id is correct (use first 8 chars for file lookup)
```

### Missing v1 in revision history

```bash
# Ensure feasibility_handler.py saves as:
report_filename = "feasibility_report_v1.md"

# (Not with timestamps like feasibility_report_<session>_<timestamp>.md)
```

### Token report not saving

```bash
# Check that output directory exists:
mkdir -p output/session_<id>/reports

# Verify permissions:
chmod 755 output/session_<id>/reports
```

---

## Next Steps

1. **Run a complete workflow** from upload → feasibility → revisions
2. **Compare your v1 to latest** using the script
3. **Analyze token costs** using token_report_reader.py
4. **Iterate on revisions** and track improvements

For questions or issues, check the console logs during execution—they show detailed token metrics and costs.
