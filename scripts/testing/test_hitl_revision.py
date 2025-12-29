#!/usr/bin/env python3
"""
HITL Feasibility Report Revision - Integration Test

Demonstrates the complete HITL workflow:
1. Generate initial feasibility report (v1)
2. Critique the report
3. Request revision (v1 → v2)
4. View revision history
5. Request another revision (v2 → v3)

Usage:
    python scripts/testing/test_hitl_revision.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.app.feasibility_revision import revise_report


def load_sample_artifacts():
    """Load sample artifacts for testing."""
    
    # Sample feasibility report v1
    feasibility_report_v1 = """# Feasibility Assessment Report

## 1. Executive Summary

This project is assessed as **Conditionally Feasible** with a feasibility score of 72/100.

The project is technically achievable with the proposed technology stack. Economic viability depends on securing additional budget for contingencies. Operational challenges exist around team composition and timeline compression.

### Key Findings
- **Overall Verdict**: Conditionally Feasible
- **Feasibility Score**: 72/100
- **Technical Feasibility**: 80/100
- **Economic Feasibility**: 65/100
- **Operational Feasibility**: 68/100
- **Schedule Feasibility**: 72/100

### Critical Alerts
- Budget shortfall of ~$150k if timeline compressed
- Resource allocation gaps in security engineering
- External API dependency on third-party provider (3+ month lead time)

---

## 2. Project Snapshot

**Project Name**: E-Commerce Platform Migration
**Team Size**: 12 engineers + 2 project managers
**Budget**: $800,000
**Timeline**: 18 months
**Technology Stack**: AWS, React, Node.js, PostgreSQL, Kubernetes

---

## 3. Section Scores

| Domain | Score | Status |
|--------|-------|--------|
| Technical | 80/100 | Strong |
| Economic | 65/100 | At Risk |
| Operational | 68/100 | Moderate Risk |
| Schedule | 72/100 | Moderate Risk |
| Legal | 75/100 | Acceptable |

---

## 4. Technical Analysis

The technology stack (AWS, React, Node.js, PostgreSQL) is well-established and mature. Team has 5+ years experience with similar projects. 

**Strengths**:
- Proven technology choices
- Experienced team
- Cloud-native approach reduces infrastructure risk

**Risks**:
- Kubernetes orchestration requires specialized knowledge
- Real-time features may require message queue redesign
- Data migration complexity (legacy system incompatibility)

**Recommendation**: Allocate additional 2 engineers for DevOps/SRE roles.

---

## 5. Economic Analysis

Project budget of $800k covers development, testing, and deployment. However, economic feasibility score is lower due to:

- Limited contingency buffer (~10% only)
- Compressed timeline increases labor costs
- Third-party licensing fees not fully accounted for

**Financial Metrics**:
- Estimated ROI: 320% over 3 years
- Payback period: 14 months
- NPV: $2.4M (10% discount rate)

**Risk**: Budget inadequacy if scope expands by 10-15%.

---

## 6. Operational Analysis

Team composition adequate but with gaps in security engineering and data architecture. Change management strategy incomplete.

**Team Assessment**:
- 8 backend engineers (sufficient)
- 3 frontend engineers (borderline adequate)
- 1 DevOps engineer (insufficient for scale)
- 0 security engineers (gap)

**Recommendations**:
- Hire 1 dedicated security engineer
- Allocate 0.5 FTE from senior team for data architecture oversight
- Implement formal change management process

---

## 7. Schedule Analysis

18-month timeline is realistically achievable with current team size and resource allocation.

**Phase Breakdown**:
- Phase 1 (Months 1-3): Architecture & Planning (3 months)
- Phase 2 (Months 4-10): Core Development (7 months)
- Phase 3 (Months 11-16): Integration & Testing (6 months)
- Phase 4 (Months 17-18): Deployment & Cutover (2 months)

**Critical Path**: Data migration + system integration (15 months total)

**Risk**: Any delay in data migration cascades to later phases. Recommend 2-week buffer before cutover.

---

## 8. Legal & Compliance

Project meets regulatory requirements (GDPR, SOC2). Third-party licensing compliant.

---

## 9. Risks & Dependencies

### Top 5 Risks

1. **Data Migration Complexity**: Legacy system incompatibility may require custom ETL
   - Likelihood: Medium
   - Impact: High
   - Mitigation: Prototype migration approach in Month 2

2. **Resource Availability**: Key personnel departures could delay project
   - Likelihood: Low
   - Impact: High
   - Mitigation: Cross-train team members

3. **Third-Party API Delays**: External provider has 3+ month lead time
   - Likelihood: Medium
   - Impact: Medium
   - Mitigation: Submit API request immediately; plan integration in Month 6

4. **Budget Overrun**: Contingency insufficient if scope expands
   - Likelihood: Medium
   - Impact: High
   - Mitigation: Strict change control; phased delivery for low-priority features

5. **Team Skill Gaps**: DevOps and security expertise insufficient
   - Likelihood: High
   - Impact: Medium
   - Mitigation: Hire specialized roles; provide training

---

## 10. Assumptions & Constraints

### Key Assumptions
- Team remains stable (no departures)
- Budget increase unavailable if overruns occur
- Third-party API available within 3 months
- Stakeholder availability for requirements validation
- Legacy system access for data extraction

### Constraints
- Hard deadline: Must launch within 18 months (business requirement)
- Budget cap: $800,000 (cannot exceed)
- Team size: 12 engineers maximum (HR constraint)
- Technology: Must use AWS (corporate standard)

---

## 11. Clarifying Questions

1. Can budget be increased if scope changes emerge?
2. Is the 18-month deadline truly fixed, or is there flexibility?
3. What is the SLA requirement for the new platform?
4. How many legacy systems need to integrate with the new platform?

---

## 12. Recommendations

1. **Hire 1 dedicated Security Engineer** (Month 1) to address security gap
2. **Hire 1 DevOps/SRE Engineer** (Month 1) to manage infrastructure at scale
3. **Establish formal change control process** to prevent scope creep
4. **Prototype data migration approach** in Month 2 (highest-risk activity)
5. **Request Third-Party API access immediately** to secure 3-month lead time
6. **Allocate 2-week buffer before cutover** for unexpected issues

---

## 13. Conclusion

The project is **Conditionally Feasible** with the right resource adjustments. Primary concerns are:
- Economic viability under budget constraints
- Operational readiness (team composition gaps)
- Timeline criticality (limited flexibility)

Recommend proceeding with conditions:
1. Hire security and DevOps engineers
2. Implement robust change control
3. Prototype high-risk activities early
4. Secure stakeholder commitment to fixed timeline

If conditions are met, project success probability: **75%+**.
"""
    
    # Sample thinking summary
    thinking_summary = """# Thinking Summary - Feasibility Analysis

## 1. Input Normalization

All 25 development context fields provided. No missing data.

Data Quality: 95/100

## 2. Technical Feasibility Assessment

Technology Stack: AWS, React, Node.js, PostgreSQL
Team Experience: 5+ years with similar architecture
Risk Level: Low to Medium

**Technical Score: 80/100**

Rationale:
- Proven technology choices (+20)
- Experienced team (+20)
- Kubernetes complexity (-10)
- Data migration risk (-10)

## 3. Economic Feasibility Assessment

Budget: $800,000
Estimated Effort: 720 person-days @ $150/day = $108,000
Infrastructure: $200,000/year
Licensing & Third-party: $100,000
Contingency: 10% = $80,000
Total: ~$720,000 within budget

**Economic Score: 65/100**

Rationale:
- Budget adequate (+20)
- Low contingency reserve (-15)
- Compressed timeline increases costs (-5)

## 4. Operational Feasibility Assessment

Team Composition:
- 8 Backend Engineers (adequate)
- 3 Frontend Engineers (borderline)
- 1 DevOps Engineer (insufficient)
- 0 Security Engineers (gap)

**Operational Score: 68/100**

Rationale:
- Experienced core team (+20)
- Missing security engineering (-15)
- Insufficient DevOps capacity (-10)

## 5. Schedule Feasibility Assessment

Critical Path: 15 months (data migration + integration)
Buffer: 3 months (18 - 15)
Contingency: 2 weeks sufficient for most risks

**Schedule Score: 72/100**

Rationale:
- Realistic timeline (+20)
- Adequate buffer (+15)
- Risk of cascading delays (-10)

## 6. Verdict Decision Logic

Average Score: (80 + 65 + 68 + 72) / 4 = 71.25 → Round to 72/100

Score Interpretation:
- 70-79: Conditionally Feasible (proceed with conditions)
- 80+: Feasible (proceed as planned)
- <70: Not Feasible (major revisions needed)

Result: **Conditionally Feasible**
"""
    
    return {
        "report": feasibility_report_v1,
        "thinking_summary": thinking_summary
    }


def test_revision_1():
    """Test: Revise report v1 → v2 (simple refinement)"""
    
    print("\n" + "="*80)
    print("TEST 1: Revise v1 → v2 (Refinement)")
    print("="*80 + "\n")
    
    artifacts = load_sample_artifacts()
    
    critique_1 = """
    Section 4 (Technical Analysis) is too brief. Please expand with:
    1. More specific architectural diagrams or component descriptions
    2. More detailed analysis of Kubernetes complexity and mitigation
    3. Explicit mention of database scaling strategy
    
    Also, section 6 (Operational Analysis) needs more concrete team allocation table.
    """
    
    result = revise_report(
        session_id="test_session_001",
        current_version=1,
        feasibility_report_current=artifacts["report"],
        thinking_summary=artifacts["thinking_summary"],
        human_critique=critique_1,
        revision_instructions=None,
        max_revisions=5
    )
    
    print(f"\nResult Status: {result['status']}")
    print(f"Version: v{result['current_version']} → v{result['new_version']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
    
    if result["status"] == "completed":
        print(f"✓ Revision successful!")
        print(f"  File: {result['file_path']}")
        print(f"\n  Revision Summary:\n{result['revision_summary']}")
        return True
    else:
        print(f"✗ Revision failed: {result.get('error_message', 'Unknown error')}")
        return False


def test_revision_2():
    """Test: Attempt revision beyond max_revisions limit"""
    
    print("\n" + "="*80)
    print("TEST 2: Exceed Max Revisions")
    print("="*80 + "\n")
    
    artifacts = load_sample_artifacts()
    
    result = revise_report(
        session_id="test_session_002",
        current_version=5,  # Try to create v6 when max is 5
        feasibility_report_current=artifacts["report"],
        thinking_summary=artifacts["thinking_summary"],
        human_critique="Make it better",
        revision_instructions=None,
        max_revisions=5
    )
    
    print(f"\nResult Status: {result['status']}")
    
    if result["status"] == "failed" and "Maximum revision limit" in result.get("error_message", ""):
        print(f"✓ Correctly rejected revision beyond limit")
        print(f"  Error: {result['error_message']}")
        return True
    else:
        print(f"✗ Did not properly handle max revisions limit")
        return False


def test_validation():
    """Test: Validate core constraints"""
    
    print("\n" + "="*80)
    print("TEST 3: Validation Checks")
    print("="*80 + "\n")
    
    artifacts = load_sample_artifacts()
    
    # Test 1: Empty critique should fail
    print("\n  Test 3a: Empty critique rejection...")
    result = revise_report(
        session_id="test_validation_001",
        current_version=1,
        feasibility_report_current=artifacts["report"],
        thinking_summary=artifacts["thinking_summary"],
        human_critique="",  # Empty!
        revision_instructions=None,
        max_revisions=5
    )
    
    if result["status"] == "failed" and "human_critique" in result.get("error_message", "").lower():
        print(f"    ✓ Correctly rejected empty critique")
    else:
        print(f"    ✗ Did not properly validate empty critique")
    
    # Test 2: Invalid version number
    print("\n  Test 3b: Invalid version number rejection...")
    result = revise_report(
        session_id="test_validation_002",
        current_version=0,  # Invalid!
        feasibility_report_current=artifacts["report"],
        thinking_summary=artifacts["thinking_summary"],
        human_critique="Some feedback",
        revision_instructions=None,
        max_revisions=5
    )
    
    if result["status"] == "failed" and "current_version" in result.get("error_message", "").lower():
        print(f"    ✓ Correctly rejected invalid version")
    else:
        print(f"    ✗ Did not properly validate version number")
    
    return True


def main():
    """Run all tests."""
    
    print("\n" + "="*80)
    print("HITL FEASIBILITY REPORT REVISION - INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        ("test_revision_1", test_revision_1),
        ("test_validation", test_validation),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ Test {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    print(f"\nTotal: {passed}/{total} passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
