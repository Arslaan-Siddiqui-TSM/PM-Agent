"""
Test script for Reflection Agent API
Run this after starting the server with: python server.py
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_health_check():
    print_section("1. Testing Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_upload_default_files():
    print_section("2. Testing Upload with Default Files")
    response = requests.post(f"{BASE_URL}/api/upload?use_default_files=true")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        session_id = data.get("session_id")
        print(f"\n✅ Session created: {session_id}")
        return session_id
    else:
        print(f"\n❌ Upload failed")
        return None

def test_feasibility_check(session_id):
    print_section("3. Testing Feasibility Check")
    payload = {
        "session_id": session_id,
        "use_intelligent_processing": True
    }
    
    print("Sending request... (this may take 30-60 seconds)")
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/api/feasibility", json=payload)
    elapsed = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Execution Time: {elapsed:.2f}s")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print(f"\n✅ Feasibility assessment generated")
        print(f"   File saved to: {data.get('file_path')}")
        return True
    else:
        print(f"\n❌ Feasibility check failed")
        return False

def test_generate_plan(session_id):
    print_section("4. Testing Plan Generation (Reflection Agent)")
    payload = {
        "session_id": session_id,
        "use_intelligent_processing": True,
        "max_iterations": 2
    }
    
    print("Sending request... (this may take 2-5 minutes)")
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/api/generate-plan", json=payload)
    elapsed = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Execution Time: {elapsed:.2f}s")
        print(f"Iterations Completed: {data.get('iterations_completed')}")
        print(f"Status: {data.get('status')}")
        print(f"File Path: {data.get('file_path')}")
        
        # Print first 500 chars of the plan
        result = data.get('result', '')
        print(f"\nPlan Preview (first 500 chars):")
        print("-" * 80)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("-" * 80)
        
        print(f"\n✅ Project plan generated successfully!")
        print(f"   Full plan saved to: {data.get('file_path')}")
        return True
    else:
        print(f"❌ Plan generation failed")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return False

def main():
    print_section("🚀 Starting Reflection Agent API Tests")
    print("Make sure the server is running: python server.py")
    print("Press Ctrl+C to cancel at any time")
    
    try:
        # Test 1: Health Check
        if not test_health_check():
            print("\n❌ Health check failed. Is the server running?")
            print("   Start with: python server.py")
            return
        
        # Test 2: Upload Documents
        session_id = test_upload_default_files()
        if not session_id:
            print("\n❌ Upload failed. Cannot continue.")
            return
        
        # Test 3: Feasibility Check (optional but recommended)
        input("\nPress Enter to continue with feasibility check...")
        test_feasibility_check(session_id)
        
        # Test 4: Generate Plan
        input("\nPress Enter to continue with plan generation...")
        test_generate_plan(session_id)
        
        print_section("✅ All Tests Completed!")
        print(f"Session ID: {session_id}")
        print("\nCheck the outputs/ folder for generated files:")
        print("  - feasibility_assessment_*.md")
        print("  - project_plan_*.md")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection failed. Is the server running?")
        print("   Start with: python server.py")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
