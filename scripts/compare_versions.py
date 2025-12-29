#!/usr/bin/env python3
"""
Version Comparison Tool - Compare feasibility reports across revisions

Usage:
  python scripts/compare_versions.py <session_id> <v1> <v2>
  
Examples:
  python scripts/compare_versions.py e50c8bb4 1 2
  python scripts/compare_versions.py e50c8bb4 1 3
  python scripts/compare_versions.py e50c8bb4 2 3
"""

import sys
from pathlib import Path
import difflib
from typing import Tuple


def load_report(session_id: str, version: int) -> str:
    """Load a feasibility report by version"""
    session_short = session_id[:8]
    report_path = Path(f"output/session_{session_short}/reports/feasibility_report_v{version}.md")
    
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return f.read()


def show_diff(v1_text: str, v2_text: str, v1_num: int, v2_num: int):
    """Show unified diff between two versions"""
    v1_lines = v1_text.splitlines(keepends=True)
    v2_lines = v2_text.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        v1_lines,
        v2_lines,
        fromfile=f"feasibility_report_v{v1_num}.md",
        tofile=f"feasibility_report_v{v2_num}.md",
        lineterm=''
    )
    
    print("\n" + "="*80)
    print(f"COMPARISON: v{v1_num} → v{v2_num}")
    print("="*80 + "\n")
    
    has_diff = False
    for line in diff:
        has_diff = True
        if line.startswith('+') and not line.startswith('+++'):
            print(f"\033[92m{line}\033[0m", end='')  # Green for additions
        elif line.startswith('-') and not line.startswith('---'):
            print(f"\033[91m{line}\033[0m", end='')  # Red for deletions
        else:
            print(line, end='')
    
    if not has_diff:
        print("[No differences found]")
    
    print("\n" + "="*80 + "\n")


def show_summary(v1_text: str, v2_text: str, v1_num: int, v2_num: int):
    """Show summary statistics"""
    print("\n" + "="*80)
    print(f"SUMMARY: v{v1_num} → v{v2_num}")
    print("="*80)
    
    v1_chars = len(v1_text)
    v2_chars = len(v2_text)
    char_diff = v2_chars - v1_chars
    char_pct = (char_diff / v1_chars * 100) if v1_chars > 0 else 0
    
    v1_lines = len(v1_text.splitlines())
    v2_lines = len(v2_text.splitlines())
    line_diff = v2_lines - v1_lines
    
    print(f"\nv{v1_num}:")
    print(f"  Characters: {v1_chars:,}")
    print(f"  Lines:      {v1_lines}")
    
    print(f"\nv{v2_num}:")
    print(f"  Characters: {v2_chars:,}")
    print(f"  Lines:      {v2_lines}")
    
    print(f"\nChanges:")
    if char_diff > 0:
        print(f"  Characters: +{char_diff:,} ({char_pct:+.1f}%)")
    elif char_diff < 0:
        print(f"  Characters: {char_diff:,} ({char_pct:.1f}%)")
    else:
        print(f"  Characters: No change")
    
    if line_diff > 0:
        print(f"  Lines:      +{line_diff}")
    elif line_diff < 0:
        print(f"  Lines:      {line_diff}")
    else:
        print(f"  Lines:      No change")
    
    print("\n" + "="*80 + "\n")


def show_side_by_side(v1_text: str, v2_text: str, v1_num: int, v2_num: int):
    """Show first 50 lines of each version side by side"""
    v1_lines = v1_text.splitlines()[:50]
    v2_lines = v2_text.splitlines()[:50]
    
    print("\n" + "="*80)
    print(f"PREVIEW: v{v1_num} (left) vs v{v2_num} (right)")
    print("="*80 + "\n")
    
    max_lines = max(len(v1_lines), len(v2_lines))
    
    for i in range(max_lines):
        v1_line = v1_lines[i] if i < len(v1_lines) else ""
        v2_line = v2_lines[i] if i < len(v2_lines) else ""
        
        # Truncate for display
        v1_display = v1_line[:35]
        v2_display = v2_line[:35]
        
        print(f"{v1_display:<37} | {v2_display}")
    
    print("\n" + "="*80 + "\n")


def main():
    if len(sys.argv) < 4:
        print("Usage: python compare_versions.py <session_id> <v1> <v2> [--diff|--summary|--preview]")
        print("\nExamples:")
        print("  python scripts/compare_versions.py e50c8bb4 1 2")
        print("  python scripts/compare_versions.py e50c8bb4 1 2 --diff")
        print("  python scripts/compare_versions.py e50c8bb4 1 3 --summary")
        print("  python scripts/compare_versions.py e50c8bb4 2 3 --preview")
        sys.exit(1)
    
    session_id = sys.argv[1]
    v1 = int(sys.argv[2])
    v2 = int(sys.argv[3])
    display_mode = sys.argv[4] if len(sys.argv) > 4 else "--full"
    
    try:
        print(f"\nLoading v{v1}...", end=" ")
        v1_text = load_report(session_id, v1)
        print("✅")
        
        print(f"Loading v{v2}...", end=" ")
        v2_text = load_report(session_id, v2)
        print("✅\n")
        
        if display_mode == "--diff":
            show_diff(v1_text, v2_text, v1, v2)
        elif display_mode == "--summary":
            show_summary(v1_text, v2_text, v1, v2)
        elif display_mode == "--preview":
            show_side_by_side(v1_text, v2_text, v1, v2)
        else:  # --full or default
            show_summary(v1_text, v2_text, v1, v2)
            show_side_by_side(v1_text, v2_text, v1, v2)
            show_diff(v1_text, v2_text, v1, v2)
    
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
