"""
Test script for Human-In-The-Loop review flow

This script tests the review endpoints by:
1. Creating a sample pending review file
2. Calling POST /resume-review with 'approve' payload
3. Verifying audit log and pending file cleanup
4. Repeating with 'feedback' payload
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
HITL_SECRET = os.getenv("HITL_SECRET", "changeme")
PENDING_DIR = Path("output/pending_reviews")
AUDIT_LOG = Path("output/review_audit.jsonl")

# Ensure directories exist
PENDING_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


def create_sample_pending_review(request_id: str) -> dict:
    """Create a sample pending review file for testing."""
    
    payload = {
        "type": "human_review",
        "node": "reflect",
        "request_id": request_id,
        "iteration": 2,
        "model_output": """## Project Plan - E-Commerce Platform

### Executive Summary
Build a modern e-commerce platform with microservices architecture...

### Timeline
- Phase 1: 2 months
- Phase 2: 3 months
- Phase 3: 1 month

### Tech Stack
- Frontend: React, TypeScript
- Backend: Python FastAPI
- Database: PostgreSQL
- Infrastructure: AWS
""",
        "reflection_notes": """Model reflection notes:
- Timeline seems reasonable but lacks buffer time
- Tech stack is well-chosen but missing caching layer
- Should add more detail on deployment strategy
- Consider adding CI/CD pipeline details
""",
        "metadata": {
            "confidence": 0.46,
            "source_docs": ["requirements.pdf"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "iteration_count": 2,
            "quality_score": 7.2,
            "improvement_areas": ["Timeline clarity", "Infrastructure details"]
        }
    }
    
    # Write to file
    pending_file = PENDING_DIR / f"{request_id}.json"
    with open(pending_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created pending review file: {pending_file}")
    return payload


def test_get_pending_review(request_id: str):
    """Test GET /pending-review/{request_id}"""
    print(f"\n{'='*60}")
    print(f"TEST: GET /pending-review/{request_id}")
    print(f"{'='*60}")
    
    url = f"{API_BASE_URL}/api/pending-review/{request_id}"
    
    try:
        response = requests.get(url)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully fetched pending review")
            print(f"   - Iteration: {data.get('iteration')}")
            print(f"   - Confidence: {data.get('metadata', {}).get('confidence')}")
            print(f"   - Model output length: {len(data.get('model_output', ''))}")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_resume_with_approve(request_id: str):
    """Test POST /resume-review with 'approve' action"""
    print(f"\n{'='*60}")
    print(f"TEST: POST /resume-review (APPROVE)")
    print(f"{'='*60}")
    
    url = f"{API_BASE_URL}/api/resume-review"
    
    payload = {
        "request_id": request_id,
        "action": "approve",
        "feedback_text": None,
        "edited_text": None,
        "tags": None,
        "reviewer_id": "test-reviewer@example.com"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HITL_SECRET}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully submitted approval")
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Check if pending file was deleted
            pending_file = PENDING_DIR / f"{request_id}.json"
            if not pending_file.exists():
                print(f"✅ Pending file was deleted")
            else:
                print(f"⚠️  Pending file still exists")
            
            # Check audit log
            if AUDIT_LOG.exists():
                with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    last_record = json.loads(lines[-1]) if lines else {}
                    if last_record.get("request_id") == request_id:
                        print(f"✅ Audit record appended")
                        print(f"   - Action: {last_record.get('action')}")
                        print(f"   - Reviewer: {last_record.get('reviewer_id')}")
            
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_resume_with_feedback(request_id: str):
    """Test POST /resume-review with 'feedback' action"""
    print(f"\n{'='*60}")
    print(f"TEST: POST /resume-review (FEEDBACK)")
    print(f"{'='*60}")
    
    url = f"{API_BASE_URL}/api/resume-review"
    
    payload = {
        "request_id": request_id,
        "action": "feedback",
        "feedback_text": "Make it shorter; add AWS infrastructure bullets; improve timeline clarity with milestones",
        "edited_text": None,
        "tags": ["tone:concise", "infra:aws", "timeline:detailed"],
        "reviewer_id": "test-reviewer@example.com"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HITL_SECRET}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully submitted feedback")
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Check if pending file was deleted
            pending_file = PENDING_DIR / f"{request_id}.json"
            if not pending_file.exists():
                print(f"✅ Pending file was deleted")
            else:
                print(f"⚠️  Pending file still exists")
            
            # Check audit log
            if AUDIT_LOG.exists():
                with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    last_record = json.loads(lines[-1]) if lines else {}
                    if last_record.get("request_id") == request_id:
                        print(f"✅ Audit record appended")
                        print(f"   - Action: {last_record.get('action')}")
                        feedback_text = last_record.get("feedback_text") or ""
                        feedback_preview = feedback_text[:50]
                        print(f"   - Feedback: {feedback_preview}...")
                        tags = last_record.get("tags") or []
                        print(f"   - Tags: {tags}")
            
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_unauthorized_access(request_id: str):
    """Test POST /resume-review without authorization"""
    print(f"\n{'='*60}")
    print(f"TEST: POST /resume-review (UNAUTHORIZED)")
    print(f"{'='*60}")
    
    url = f"{API_BASE_URL}/api/resume-review"
    
    payload = {
        "request_id": request_id,
        "action": "approve",
        "reviewer_id": "attacker@example.com"
    }
    
    headers = {
        "Content-Type": "application/json",
        # No Authorization header
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 401:
            print(f"✅ Correctly rejected unauthorized request")
            return True
        else:
            print(f"❌ Should have returned 401, got {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("HITL REVIEW FLOW TEST SUITE")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"HITL Secret: {'*' * len(HITL_SECRET)}")
    print("="*60)
    
    results = []
    
    # Test 1: Approve flow
    request_id_1 = "test-approve-123"
    create_sample_pending_review(request_id_1)
    results.append(("GET pending review (approve)", test_get_pending_review(request_id_1)))
    results.append(("POST approve", test_resume_with_approve(request_id_1)))
    
    # Test 2: Feedback flow
    request_id_2 = "test-feedback-456"
    create_sample_pending_review(request_id_2)
    results.append(("GET pending review (feedback)", test_get_pending_review(request_id_2)))
    results.append(("POST feedback", test_resume_with_feedback(request_id_2)))
    
    # Test 3: Unauthorized access
    request_id_3 = "test-unauthorized-789"
    create_sample_pending_review(request_id_3)
    results.append(("POST unauthorized", test_unauthorized_access(request_id_3)))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
