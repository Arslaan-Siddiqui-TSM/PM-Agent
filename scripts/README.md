# Scripts Directory - PM-Agent Tools

Quick reference for available utility scripts.

## Token Analysis Scripts

### `token_report_reader.py`

Read and display saved token reports for any session.

```bash
# List all token reports for a session
python scripts/token_report_reader.py e50c8bb4 list

# View full token metrics (all reports)
python scripts/token_report_reader.py e50c8bb4 full

# View specific token report
python scripts/token_report_reader.py e50c8bb4 token_stats_feasibility.json
python scripts/token_report_reader.py e50c8bb4 token_stats_revision_v2.json
```

**Output shows:**

- Per-call token counts (input, output)
- LLM provider and model used
- Execution time and tokens/second
- Cost estimates (NVIDIA pricing)
- Timestamps

---

### `compare_versions.py` ⭐ NEW

Compare any two versions of a feasibility report to see what changed.

```bash
# Full comparison (summary + preview + diff)
python scripts/compare_versions.py <session_id> <v1> <v2>

# Examples:
python scripts/compare_versions.py e50c8bb4 1 2        # Compare v1 to v2
python scripts/compare_versions.py e50c8bb4 1 3        # Compare v1 to v3
python scripts/compare_versions.py e50c8bb4 2 3        # Compare v2 to v3
```

**Display modes:**

```bash
# Summary only (character/line counts, % change)
python scripts/compare_versions.py e50c8bb4 1 2 --summary

# Diff only (unified diff with color coding)
python scripts/compare_versions.py e50c8bb4 1 2 --diff
  - Green: Added lines
  - Red: Removed lines

# Preview only (first 50 lines side-by-side)
python scripts/compare_versions.py e50c8bb4 1 2 --preview
```

---

### `run_feasibility_token_report.py`

End-to-end test runner that demonstrates the complete workflow with token tracking.

```bash
python scripts/run_feasibility_token_report.py
```

**What it does:**

1. Creates a test session
2. Runs feasibility generation
3. Displays token metrics in console
4. Saves token reports to JSON
5. Shows cost breakdown

---

## Session Management Scripts

### `setup/` directory

Initialization and setup utilities (development/testing).

---

## Testing Scripts

### `testing/` directory

Unit tests and integration tests for various components.

---

## Usage Examples

### Complete Workflow with Token Analysis

```bash
# 1. Start your server
fastapi run server.py

# 2. Run a feasibility analysis (from your app)
# POST http://localhost:8000/api/feasibility

# 3. View what was generated
python scripts/token_report_reader.py e50c8bb4 full

# 4. Do a revision (from your app)
# POST http://localhost:8000/api/revise-feasibility

# 5. Compare v1 to v2
python scripts/compare_versions.py e50c8bb4 1 2 --summary

# 6. Get full revision history
# GET http://localhost:8000/api/revision-history/e50c8bb4

# 7. Compare v1 to latest (if multiple revisions)
python scripts/compare_versions.py e50c8bb4 1 3
```

---

## File Locations

Token reports are saved in:

```
output/session_<id>/reports/
├── token_stats_feasibility.json       # Initial report tokens
├── token_stats_revision_v2.json       # v2 revision tokens
├── token_stats_revision_v3.json       # v3 revision tokens
└── ...
```

Feasibility reports are saved as:

```
output/session_<id>/reports/
├── feasibility_report_v1.md           # Initial
├── feasibility_report_v2.md           # First revision
├── feasibility_report_v3.md           # Second revision
└── ...
```

---

## Development

To add new scripts:

1. Create in `scripts/` directory
2. Make it executable: `chmod +x scripts/my_script.py`
3. Add usage documentation here
4. Follow the same argument pattern as existing scripts

---

## Troubleshooting

**Scripts not found?**

```bash
# Make sure you're in the project root:
cd /Users/vaidikjaiswal/Desktop/TSM/PM-Agent-using-ReWOO

# Make scripts executable:
chmod +x scripts/*.py
```

**Module import errors?**

```bash
# Ensure Python path is set:
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with python -m:
python -m scripts.token_report_reader e50c8bb4 full
```

**Can't find session data?**

```bash
# Check if output directory exists:
ls -la output/

# Session directories start with session_<shortid>:
ls -la output/ | grep session_
```

---

## Performance Tips

- **compare_versions.py** loads entire files into memory - safe for typical reports (<100KB)
- **token_report_reader.py** is fast (<100ms) even with many reports
- For sessions with 10+ revisions, consider archiving older reports

---

For detailed information on version comparison, see [VERSION_COMPARISON_GUIDE.md](../docs/VERSION_COMPARISON_GUIDE.md).
