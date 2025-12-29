#!/usr/bin/env python3
"""
Quick reference guide for token tracking in feasibility iteration
Run this to see your token reports across feasibility + revisions
"""

import json
from pathlib import Path
from datetime import datetime

def list_token_reports(session_id: str):
    """List all token reports for a session"""
    session_short = session_id[:8]
    reports_dir = Path(f"output/session_{session_short}/reports")
    
    if not reports_dir.exists():
        print(f"No reports directory found for session {session_id}")
        return
    
    token_reports = list(reports_dir.glob("token_stats*.json"))
    
    if not token_reports:
        print(f"No token reports found for session {session_id}")
        return
    
    print(f"\n{'='*80}")
    print(f"TOKEN REPORTS FOR SESSION {session_id[:12]}")
    print(f"{'='*80}\n")
    
    for report_file in sorted(token_reports):
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            phase = data.get('phase', 'UNKNOWN')
            summary = data.get('summary', {})
            revision = data.get('revision', {})
            cost = data.get('cost_estimate', {})
            
            print(f"📄 {report_file.name}")
            print(f"   Phase: {phase}")
            
            if phase == "FEASIBILITY_GENERATION":
                print(f"   Input Tokens:  {summary.get('total_input_tokens', 0):>10,}")
                print(f"   Output Tokens: {summary.get('total_output_tokens', 0):>10,}")
                print(f"   Total Tokens:  {summary.get('total_tokens', 0):>10,}")
                print(f"   Cost (NVIDIA): ${cost.get('total_cost_usd', 0):>10.4f}")
                print(f"   Duration:      {summary.get('execution_time_seconds', 0):>10.2f}s")
            
            elif phase == "HITL_REVISION":
                print(f"   Revision: v{revision.get('from_version')} → v{revision.get('to_version')}")
                print(f"   Input Tokens:  {summary.get('total_input_tokens', 0):>10,}")
                print(f"   Output Tokens: {summary.get('total_output_tokens', 0):>10,}")
                print(f"   Total Tokens:  {summary.get('total_tokens', 0):>10,}")
                print(f"   Cost (NVIDIA): ${cost.get('total_cost_usd', 0):>10.4f}")
                print(f"   Duration:      {summary.get('execution_time_seconds', 0):>10.2f}s")
            
            print()
        
        except Exception as e:
            print(f"   ⚠️  Error reading report: {e}\n")


def print_full_summary(session_id: str):
    """Print aggregated summary of all token usage for a session"""
    session_short = session_id[:8]
    reports_dir = Path(f"output/session_{session_short}/reports")
    
    if not reports_dir.exists():
        print(f"No reports directory found for session {session_id}")
        return
    
    token_reports = list(reports_dir.glob("token_stats*.json"))
    
    if not token_reports:
        print(f"No token reports found for session {session_id}")
        return
    
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_duration = 0.0
    phases = []
    
    for report_file in sorted(token_reports):
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            summary = data.get('summary', {})
            cost = data.get('cost_estimate', {})
            phase = data.get('phase', 'UNKNOWN')
            
            total_input += summary.get('total_input_tokens', 0)
            total_output += summary.get('total_output_tokens', 0)
            total_cost += cost.get('total_cost_usd', 0)
            total_duration += summary.get('execution_time_seconds', 0)
            phases.append(phase)
        
        except Exception as e:
            print(f"Error reading {report_file}: {e}")
    
    print(f"\n{'='*80}")
    print(f"FULL ITERATION SUMMARY - SESSION {session_id[:12]}")
    print(f"{'='*80}\n")
    
    print(f"Phases Completed:   {', '.join(set(phases))}")
    print(f"Total Input Tokens:      {total_input:>10,}")
    print(f"Total Output Tokens:     {total_output:>10,}")
    print(f"Total Tokens:            {total_input + total_output:>10,}")
    print(f"Total Duration:          {total_duration:>10.2f}s")
    print(f"Total Cost (NVIDIA):     ${total_cost:>10.4f}")
    
    if total_input + total_output > 0:
        ratio = total_input / total_output if total_output > 0 else 0
        print(f"Input:Output Ratio:      {ratio:>10.2f}:1")
    
    if total_duration > 0:
        speed = (total_input + total_output) / total_duration
        print(f"Avg Tokens/Second:       {speed:>10.2f}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python token_report_reader.py <session_id> [full]")
        print("\nExamples:")
        print("  python token_report_reader.py e50c8bb4")
        print("  python token_report_reader.py e50c8bb4 full")
        sys.exit(1)
    
    session_id = sys.argv[1]
    show_full = len(sys.argv) > 2 and sys.argv[2] == "full"
    
    if show_full:
        print_full_summary(session_id)
    else:
        list_token_reports(session_id)
