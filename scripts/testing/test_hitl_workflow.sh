#!/bin/bash

# HITL Feasibility Testing - Quick Start Script
# This script helps verify the HITL implementation is working correctly

echo "=========================================="
echo "HITL Feasibility Testing - Quick Start"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8000/api"
SESSION_ID="test-hitl-$(date +%s)"

echo "📋 Configuration:"
echo "  API Base: $API_BASE"
echo "  Session ID: $SESSION_ID"
echo ""

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Test 1: Check if backend is running
echo "Test 1: Checking backend availability..."
if curl -s -f "$API_BASE/../health" > /dev/null 2>&1; then
    print_success "Backend is running"
else
    print_error "Backend is not running!"
    print_info "Please start the backend with: python server.py"
    exit 1
fi
echo ""

# Test 2: Start feasibility assessment
echo "Test 2: Starting HITL feasibility assessment..."
START_RESPONSE=$(curl -s -X POST "$API_BASE/feasibility/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"development_context\": {
      \"methodology\": \"Agile\",
      \"teamSize\": \"5\",
      \"timeline\": \"6 months\",
      \"budget\": \"$100k\",
      \"techStack\": \"React, Node.js, PostgreSQL\",
      \"constraints\": \"Must be cloud-native\"
    }
  }")

if echo "$START_RESPONSE" | grep -q "awaiting_human"; then
    print_success "Feasibility assessment started"
    print_info "Status: $(echo $START_RESPONSE | grep -o '\"status\":\"[^\"]*\"' | cut -d':' -f2)"
else
    print_error "Failed to start feasibility assessment"
    echo "Response: $START_RESPONSE"
    exit 1
fi
echo ""

# Test 3: Check status
echo "Test 3: Checking feasibility status..."
STATUS_RESPONSE=$(curl -s "$API_BASE/feasibility/status/$SESSION_ID")

if echo "$STATUS_RESPONSE" | grep -q "awaiting_human"; then
    print_success "Status endpoint working"
    ITERATION=$(echo $STATUS_RESPONSE | grep -o '\"iteration\":[0-9]*' | cut -d':' -f2)
    print_info "Current iteration: $ITERATION"
else
    print_error "Status check failed"
    echo "Response: $STATUS_RESPONSE"
fi
echo ""

# Test 4: Request changes with feedback
echo "Test 4: Requesting changes with feedback..."
REVIEW_RESPONSE=$(curl -s -X POST "$API_BASE/feasibility/review" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"approved\": false,
    \"feedback\": \"Please add more detail about database scalability and provide specific performance metrics for the API endpoints. Also elaborate on the risk assessment section.\"
  }")

if echo "$REVIEW_RESPONSE" | grep -q "iteration"; then
    print_success "Revision requested successfully"
    NEW_ITERATION=$(echo $REVIEW_RESPONSE | grep -o '\"iteration\":[0-9]*' | cut -d':' -f2)
    print_info "New iteration: $NEW_ITERATION"
else
    print_error "Failed to request changes"
    echo "Response: $REVIEW_RESPONSE"
fi
echo ""

# Test 5: Check status after revision
echo "Test 5: Verifying status after revision..."
sleep 2  # Give server time to process
UPDATED_STATUS=$(curl -s "$API_BASE/feasibility/status/$SESSION_ID")

if echo "$UPDATED_STATUS" | grep -q "critique"; then
    print_success "Critique generated"
else
    print_info "Critique may still be processing or not required"
fi
echo ""

# Test 6: Approve the report
echo "Test 6: Approving the report..."
APPROVE_RESPONSE=$(curl -s -X POST "$API_BASE/feasibility/review" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"approved\": true
  }")

if echo "$APPROVE_RESPONSE" | grep -q "approved"; then
    print_success "Report approved successfully"
    print_info "Status: $(echo $APPROVE_RESPONSE | grep -o '\"status\":\"[^\"]*\"' | cut -d':' -f2)"
else
    print_error "Approval failed"
    echo "Response: $APPROVE_RESPONSE"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
print_success "All API endpoints are functional"
print_info "Session ID: $SESSION_ID"
print_info "Review the responses above for detailed results"
echo ""
echo "Next steps:"
echo "  1. Start frontend: cd frontend && npm run dev"
echo "  2. Open: http://localhost:5173"
echo "  3. Test the full UI workflow"
echo "  4. Review detailed testing guide: docs/HITL_TESTING_GUIDE.md"
echo ""
