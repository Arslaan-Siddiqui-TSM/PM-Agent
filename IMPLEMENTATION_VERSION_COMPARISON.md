# Version Comparison Implementation Summary

## What's New

You can now **compare any two versions** of your feasibility report and see **exactly what changed** during revisions. This is the final piece to enable full v1-to-vN comparison workflow.

---

## Key Features Implemented

### 1. ✅ Compare Versions Tool (`scripts/compare_versions.py`)

**Compare any two report versions side-by-side with color-coded changes**

```bash
# Basic usage (shows summary + preview + full diff)
python scripts/compare_versions.py e50c8bb4 1 2

# Or with specific mode:
python scripts/compare_versions.py e50c8bb4 1 2 --summary   # Stats only
python scripts/compare_versions.py e50c8bb4 1 2 --diff      # Changes only
python scripts/compare_versions.py e50c8bb4 1 2 --preview   # Side-by-side
```

**Output includes:**

- Character count changes (with % change)
- Line count changes
- Unified diff with color coding:
  - 🟢 Green = added lines
  - 🔴 Red = removed lines
- Side-by-side preview (first 50 lines)

---

### 2. ✅ Revision History API

**Already working - shows all versions (v1, v2, v3...)**

```bash
curl http://localhost:8000/api/revision-history/{session_id}
```

Returns:

```json
{
  "session_id": "e50c8bb4-...",
  "revisions": [
    {
      "version": 1,
      "type": "initial",
      "created_at": "2024-12-22T10:15:33.123456",
      "file_path": "output/session_e50c8bb4/reports/feasibility_report_v1.md"
    },
    {
      "version": 2,
      "type": "human_revision",
      "created_at": "2024-12-22T10:20:15.654321",
      "file_path": "output/session_e50c8bb4/reports/feasibility_report_v2.md"
    }
  ]
}
```

---

### 3. ✅ Token Tracking Per Version

**Each revision includes token usage stats**

```bash
# View all token metrics
python scripts/token_report_reader.py e50c8bb4 full

# View specific version tokens
python scripts/token_report_reader.py e50c8bb4 token_stats_revision_v2.json
```

Shows per-version:

- Input tokens count
- Output tokens count
- Cost estimate (NVIDIA pricing)
- LLM provider and model
- Execution duration
- Tokens per second

---

### 4. ✅ Version Numbering Fixed

**Initial report now saves as `feasibility_report_v1.md`**

Before (broken):

```
feasibility_report_e50c8bb4_20241222-101533.md
feasibility_report_e50c8bb4_20241222-101638.md (v2)
```

After (fixed):

```
feasibility_report_v1.md              (initial)
feasibility_report_v2.md              (first revision)
feasibility_report_v3.md              (second revision)
```

This enables:

- ✅ Revision history scanner finds v1-vN
- ✅ Version comparison v1 vs any other
- ✅ Chronological ordering

---

### 5. ✅ Documentation

**Comprehensive guides for using all features**

New docs:

- `docs/VERSION_COMPARISON_GUIDE.md` – Complete workflow examples
- `scripts/README.md` – Quick reference for all scripts
- README.md updated with version comparison section

---

## Complete Workflow Example

### 1. Upload & Generate Feasibility

```bash
# Frontend: Upload documents
POST /api/upload

# Frontend: Generate feasibility report
POST /api/feasibility → Creates feasibility_report_v1.md
```

### 2. Review & Revise (Human-in-the-Loop)

```bash
# Human reviews v1
# Human provides critique via API

POST /api/revise-feasibility
{
  "session_id": "e50c8bb4-...",
  "current_version": 1,
  "human_critique": "Needs more detail on..."
}
→ Creates feasibility_report_v2.md
```

### 3. Compare Versions

```bash
# From command line:
python scripts/compare_versions.py e50c8bb4 1 2

# Shows:
# ✓ Summary: Changed from 5,432 chars to 6,108 chars (+12.4%)
# ✓ Preview: First 50 lines side-by-side
# ✓ Diff: Line-by-line changes highlighted
```

### 4. View Token Costs

```bash
python scripts/token_report_reader.py e50c8bb4 full

# Shows:
# v1 (initial):     $0.003096 (63,870 input / 30,316 output)
# v2 (revision):    $0.000856 (28,450 input / 4,788 output)
# Total:            $0.003952
```

### 5. View Revision History API

```bash
curl http://localhost:8000/api/revision-history/e50c8bb4-...

# Shows all versions with timestamps and file paths
```

---

## File Changes Summary

| File                                | Change     | Purpose                                     |
| ----------------------------------- | ---------- | ------------------------------------------- |
| `scripts/compare_versions.py`       | ➕ NEW     | Compare two report versions                 |
| `scripts/README.md`                 | ➕ NEW     | Quick reference for all scripts             |
| `docs/VERSION_COMPARISON_GUIDE.md`  | ➕ NEW     | Comprehensive workflow guide                |
| `src/routes/feasibility_handler.py` | 🔄 FIXED   | Save initial report as v1 (not timestamped) |
| `README.md`                         | 🔄 UPDATED | Added version comparison section            |

---

## API Endpoints Summary

| Endpoint                             | Method | Purpose                                 |
| ------------------------------------ | ------ | --------------------------------------- |
| `/api/revision-history/{session_id}` | GET    | Get all versions (v1, v2, v3...)        |
| `/api/revise-feasibility`            | POST   | Create next version with human feedback |
| `/api/feasibility`                   | POST   | Generate initial v1 report              |

---

## Command Reference

```bash
# View all versions for a session
curl http://localhost:8000/api/revision-history/e50c8bb4-464f-4cc2-942a-c171c5ef4f48

# Compare v1 to v2 (full output)
python scripts/compare_versions.py e50c8bb4 1 2

# Compare v1 to v3 (summary only)
python scripts/compare_versions.py e50c8bb4 1 3 --summary

# View all token reports
python scripts/token_report_reader.py e50c8bb4 full

# View specific token report
python scripts/token_report_reader.py e50c8bb4 token_stats_feasibility.json
```

---

## What This Enables

### Before

- ❌ Could only see revisions starting from v2
- ❌ Couldn't compare v1 to later versions
- ❌ No way to track how reports evolved

### After

- ✅ Full revision history (v1, v2, v3...)
- ✅ Compare any two versions with exact changes
- ✅ Track token costs per revision
- ✅ View cost growth across iterations
- ✅ Understand revision impact (what % of content changed)

---

## Next Steps

### Immediate (Ready to Use Now)

1. **Restart your FastAPI server** (old code still cached)

   ```bash
   # Ctrl+C to stop current server
   fastapi run server.py
   ```

2. **Run a test workflow**:

   - Upload documents
   - Generate feasibility (creates v1)
   - Do a revision (creates v2)
   - Compare: `python scripts/compare_versions.py <session_id> 1 2`

3. **Explore token metrics**:
   - `python scripts/token_report_reader.py <session_id> full`

### Optional Enhancements

- Add UI display of version comparisons
- Create side-by-side editor for comparing versions
- Export comparison reports as PDF
- Add automated quality metrics (readability, coverage)

---

## Architecture

```
API Layer:
  ├── GET  /api/revision-history/{session_id}   → Lists all versions
  └── POST /api/revise-feasibility                → Creates next version

CLI Tools:
  ├── scripts/compare_versions.py                 → Show differences
  ├── scripts/token_report_reader.py              → Show token usage
  └── scripts/run_feasibility_token_report.py     → End-to-end test

File System:
  └── output/session_<id>/reports/
       ├── feasibility_report_v1.md               (initial)
       ├── feasibility_report_v2.md               (revision 1)
       ├── feasibility_report_v3.md               (revision 2)
       ├── token_stats_feasibility.json           (v1 tokens)
       ├── token_stats_revision_v2.json           (v2 tokens)
       └── token_stats_revision_v3.json           (v3 tokens)
```

---

## Status

**Implementation: ✅ COMPLETE**

- [x] Version comparison script
- [x] Revision history API
- [x] Token tracking per version
- [x] v1 naming fixed
- [x] Documentation
- [x] Syntax validation

**Ready for testing** after server restart.

---

## Support

For issues or questions:

1. Check [VERSION_COMPARISON_GUIDE.md](docs/VERSION_COMPARISON_GUIDE.md)
2. Check [scripts/README.md](scripts/README.md)
3. Review console logs during execution
4. Verify files exist: `ls -la output/session_<id>/reports/`
