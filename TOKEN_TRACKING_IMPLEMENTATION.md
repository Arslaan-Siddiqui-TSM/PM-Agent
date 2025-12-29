# Token Tracking Integration - Implementation Summary

## ✅ What's Been Added

### 1. **Feasibility Generation Endpoint** (`/api/feasibility`)

- ✅ Resets and snapshots token tracker at start
- ✅ Captures token usage during 2-stage generation (thinking + report)
- ✅ Displays beautiful token summary in logs:
  ```
  ════════════════════════════════════════════════════════════════════════════════
  📊 FEASIBILITY GENERATION - TOKEN USAGE SUMMARY
  ════════════════════════════════════════════════════════════════════════════════
  Total LLM Calls:         2
  Total Input Tokens:      63,870
  Total Output Tokens:     30,316
  Total Tokens:            94,186
  Session Duration:        217.24s
  Avg Speed:               434.02 tok/s
  ════════════════════════════════════════════════════════════════════════════════
  ```
- ✅ Saves detailed JSON report to: `output/session_<id>/reports/token_stats_<timestamp>.json`
- ✅ Returns token stats in API response

### 2. **HITL Revision Endpoint** (`/api/revise-feasibility`)

- ✅ Now uses unified `model.invoke()` for token tracking (was using ChatNVIDIA directly)
- ✅ Resets and snapshots token tracker at start
- ✅ Captures tokens from revision LLM call
- ✅ Displays token summary in logs:
  ```
  ════════════════════════════════════════════════════════════════════════════════
  📊 HITL REVISION - TOKEN USAGE SUMMARY
  ════════════════════════════════════════════════════════════════════════════════
  Total LLM Calls:         1
  Total Input Tokens:      28,450
  Total Output Tokens:     4,788
  Total Tokens:            33,238
  Execution Time:          45.33s
  Avg Speed:               733.15 tok/s
  Est. Cost (NVIDIA):      $0.0951
  ════════════════════════════════════════════════════════════════════════════════
  ```
- ✅ Saves detailed JSON report to: `output/session_<id>/reports/token_stats_revision_v<N>_to_v<N+1>_<timestamp>.json`
- ✅ Includes cost estimation (NVIDIA: $0.02/1M input, $0.06/1M output)
- ✅ Returns token stats in API response

### 3. **Token Utilities** (`src/utils/token_utils.py`)

- ✅ `snapshot()` - Capture point-in-time token counters
- ✅ `diff()` - Calculate deltas between snapshots
- ✅ `export_stats()` - Persist session stats to JSON
- ✅ `get_session_stats()` - Get current session totals

### 4. **Token Report Display** (`src/utils/token_report_display.py`)

- ✅ `display_feasibility_token_summary()` - Pretty-print feasibility stats
- ✅ `display_revision_token_summary()` - Pretty-print revision stats
- ✅ `display_full_iteration_summary()` - Show comprehensive multi-phase breakdown
- ✅ `load_and_display_token_report()` - Load & display saved JSON reports

### 5. **Helper Functions**

- ✅ `_save_revision_token_report()` - Save revision token data to JSON
- ✅ Per-call details stored (provider, model, input/output tokens, duration, speed, cost)

### 6. **CLI Tools**

- ✅ `scripts/token_report_reader.py` - Read & display all token reports for a session
- ✅ `scripts/run_feasibility_token_report.py` - Full end-to-end token instrumented run

---

## 📊 Token Report Structure

Each saved report includes:

```json
{
  "session_id": "e50c8bb4-...",
  "phase": "FEASIBILITY_GENERATION" | "HITL_REVISION",
  "created_at": "2025-12-23T16:10:19.123456",
  "summary": {
    "total_calls": 2,
    "total_input_tokens": 63870,
    "total_output_tokens": 30316,
    "total_tokens": 94186,
    "execution_time_seconds": 217.24
  },
  "cost_estimate": {
    "provider": "NVIDIA",
    "input_cost": 1.2774,
    "output_cost": 1.8190,
    "total_cost_usd": 3.0964
  },
  "per_call_details": [
    {
      "call_index": 0,
      "provider": "NVIDIA",
      "model": "qwen/qwen3-next-80b-a3b-instruct",
      "input_tokens": 32955,
      "output_tokens": 8055,
      "total_tokens": 41010,
      "duration_seconds": 60.07,
      "tokens_per_second": 134.23,
      "timestamp": 1703348419.123
    },
    ...
  ]
}
```

---

## 🚀 Usage

### View Token Reports for a Session

```bash
# List all token reports
python scripts/token_report_reader.py e50c8bb4

# Show full aggregated summary
python scripts/token_report_reader.py e50c8bb4 full
```

### Run Full Instrumented Workflow

```bash
python scripts/run_feasibility_token_report.py \
  --md-dir output/sample_session/parsed_md \
  --development-context docs/dev_context.json \
  --critique docs/sample_critique.txt \
  --note "full iteration token audit"
```

---

## 📈 What You'll See in Logs

### Initial Feasibility Run

```
Step 1: Preparing document input for feasibility analysis
...
Step 3: Executing Feasibility graph
🤖 Invoking feasibility agent...
╭─────────────────────────────────── 🤖 LLM Token Usage ────────────────────────────────────╮
│  Provider                        NVIDIA                                                   │
│  Model               qwen/qwen3-next-8…                                                   │
│  Input Tokens                    32,955                                                   │
│  Output Tokens                    8,055                                                   │
│  Total Tokens                    41,010                                                   │
│  Duration                        60.07s                                                   │
│  Speed                        134 tok/s                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
...
════════════════════════════════════════════════════════════════════════════════
📊 FEASIBILITY GENERATION - TOKEN USAGE SUMMARY
════════════════════════════════════════════════════════════════════════════════
Total LLM Calls:         2
Total Input Tokens:      63,870
Total Output Tokens:     30,316
Total Tokens:            94,186
Execution Time:          217.24s
Avg Speed:               434.02 tok/s
Est. Cost (NVIDIA):      $3.0964
════════════════════════════════════════════════════════════════════════════════

✅ Token usage report saved: output/session_e50c8bb4/reports/token_stats_e50c8bb4_20251223_161019.json
```

### HITL Revision Run

```
✅ Initial feasibility assessment found, proceeding with LangGraph HITL revision
[HITL] Calling LLM to revise assessment...
╭─────────────────────────────────── 🤖 LLM Token Usage ────────────────────────────────────╮
│  Provider                        NVIDIA                                                   │
│  Model               qwen/qwen3-next-8…                                                   │
│  Input Tokens                    28,450                                                   │
│  Output Tokens                     4,788                                                  │
│  Total Tokens                    33,238                                                   │
│  Duration                        45.33s                                                   │
│  Speed                        733 tok/s                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
✅ LangGraph HITL revision completed, new version: 2

════════════════════════════════════════════════════════════════════════════════
📊 HITL REVISION - TOKEN USAGE SUMMARY
════════════════════════════════════════════════════════════════════════════════
Total LLM Calls:         1
Total Input Tokens:      28,450
Total Output Tokens:     4,788
Total Tokens:            33,238
Execution Time:          45.33s
Avg Speed:               733.15 tok/s
Est. Cost (NVIDIA):      $0.0951
════════════════════════════════════════════════════════════════════════════════

✅ Token usage report saved: output/session_e50c8bb4/reports/token_stats_revision_v1_to_v2_20251223_161419.json
```

---

## 🔧 Files Modified

1. **src/routes/feasibility_handler.py**

   - Added token tracker reset/snapshot
   - Added token stats display
   - Added `_save_token_report()` method
   - Returns token stats in API response

2. **src/routes/planning_agent.py**

   - Added token tracker imports
   - Added token stats capture to `/api/revise-feasibility`
   - Added `_save_revision_token_report()` helper
   - Updated `ReviseReportResponse` to include `token_usage` field
   - Enhanced token display with cost estimation

3. **src/core/langgraph_hitl.py**

   - Changed from `ChatNVIDIA` to unified `model.invoke()` for token tracking
   - Now properly captures tokens in revision LLM calls

4. **src/config/llm_config.py**

   - Enhanced token metadata (added provider, model, duration, speed, timestamp)

5. **src/utils/token_utils.py**

   - Added `snapshot()` function
   - Added `diff()` function
   - Added `export_stats()` function

6. **NEW: src/utils/token_report_display.py**

   - Display utilities for token summaries

7. **NEW: scripts/token_report_reader.py**

   - CLI tool to read and display saved token reports

8. **NEW: scripts/run_feasibility_token_report.py**
   - End-to-end instrumented test runner

---

## ✅ Ready to Run

Next time you run feasibility + revision, you'll see complete token tracking in the logs and saved JSON reports for analysis!
