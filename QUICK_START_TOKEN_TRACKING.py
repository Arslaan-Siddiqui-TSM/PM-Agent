#!/usr/bin/env python3
"""
QUICK START - Token Tracking in Feasibility Iterations
======================================================

Now when you run your feasibility workflow, you'll automatically see:

1. Per-call token usage (input/output)
2. Total tokens for the phase
3. Execution time & speed
4. Cost estimation (NVIDIA pricing)
5. Saved JSON reports for analysis

No code changes needed - it's automatic!
"""

print("""
════════════════════════════════════════════════════════════════════════════════
                    TOKEN TRACKING SETUP - ALL READY! ✅
════════════════════════════════════════════════════════════════════════════════

WHAT YOU'LL SEE NOW:

1️⃣  FEASIBILITY GENERATION (/api/feasibility)
   ├─ Stage 1: Thinking Summary Generation
   │  └─ Shows: Input tokens, Output tokens, Total, Duration, Speed, Cost
   │
   ├─ Stage 2: Feasibility Report Generation  
   │  └─ Shows: Input tokens, Output tokens, Total, Duration, Speed, Cost
   │
   └─ SUMMARY PANEL at the end
      └─ Total tokens, execution time, cost estimate, speed
      └─ Saves: token_stats_<session>_<timestamp>.json

2️⃣  HITL REVISION (/api/revise-feasibility)
   ├─ Calls unified LLM with token tracking
   ├─ Shows: Input tokens, Output tokens, Total, Duration, Speed, Cost
   └─ Saves: token_stats_revision_v<N>_to_v<N+1>_<timestamp>.json

════════════════════════════════════════════════════════════════════════════════

EXAMPLE LOG OUTPUT:

🤖 LLM Token Usage (per call):
╭──────────────────────────────────────────────────────────────╮
│  Provider                        NVIDIA                       │
│  Model               qwen/qwen3-next-80b-a3b-instruct         │
│  ──────────────────  ──────────────────                       │
│  Input Tokens                    32,955                       │
│  Output Tokens                    8,055                       │
│  Total Tokens                    41,010                       │
│  ──────────────────  ──────────────────                       │
│  Duration                        60.07s                       │
│  Speed                        134 tok/s                       │
╰──────────────────────────────────────────────────────────────╯

📊 Feasibility Generation Summary:
════════════════════════════════════════════════════════════════════════════════
Total LLM Calls:         2
Total Input Tokens:      63,870
Total Output Tokens:     30,316
Total Tokens:            94,186
Session Duration:        217.24s
Avg Speed:               434.02 tok/s
Est. Cost (NVIDIA):      $3.0964
════════════════════════════════════════════════════════════════════════════════

✅ Token usage report saved: output/session_e50c8bb4/reports/token_stats_*.json

════════════════════════════════════════════════════════════════════════════════

READING YOUR TOKEN REPORTS:

1. View all token reports for a session:
   python scripts/token_report_reader.py e50c8bb4

2. View full aggregated summary:
   python scripts/token_report_reader.py e50c8bb4 full

3. JSON files are saved in:
   output/session_<id>/reports/token_stats*.json

════════════════════════════════════════════════════════════════════════════════

WHAT'S TRACKED PER CALL:

✓ Input tokens
✓ Output tokens  
✓ Total tokens
✓ Execution time (seconds)
✓ Tokens per second (speed)
✓ Provider (NVIDIA/OpenAI/Gemini)
✓ Model name
✓ Timestamp
✓ Cost estimation

════════════════════════════════════════════════════════════════════════════════

FILES MODIFIED/ADDED:

Modified:
  ├─ src/routes/feasibility_handler.py          (token tracking integration)
  ├─ src/routes/planning_agent.py               (revision endpoint tracking)
  ├─ src/core/langgraph_hitl.py                 (use unified model.invoke)
  └─ src/config/llm_config.py                   (enhanced metadata)

New:
  ├─ src/utils/token_utils.py                   (snapshot/diff/export)
  ├─ src/utils/token_report_display.py          (pretty display functions)
  ├─ scripts/token_report_reader.py             (CLI tool to read reports)
  ├─ scripts/run_feasibility_token_report.py    (end-to-end test runner)
  └─ TOKEN_TRACKING_IMPLEMENTATION.md           (full documentation)

════════════════════════════════════════════════════════════════════════════════
""")
