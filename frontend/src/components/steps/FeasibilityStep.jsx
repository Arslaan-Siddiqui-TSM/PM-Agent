import { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { Button } from "../ui";
import "./FeasibilityStep.css";

export const FeasibilityStep = ({
  loading,
  onCheckFeasibility,
  sessionId,
  developmentContext,
}) => {
  // HITL state
  const [hitlMode, setHitlMode] = useState(false);
  const [feasibilityStatus, setFeasibilityStatus] = useState(null);
  const [feasibilityReport, setFeasibilityReport] = useState("");
  const [iteration, setIteration] = useState(0);
  const [maxIterations, setMaxIterations] = useState(3);
  const [critique, setCritique] = useState("");
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reportExpanded, setReportExpanded] = useState(false);
  const reportRef = useRef(null);

  // Auto-fill feedback template - HARDCODED for easy testing based on typical report structure
  const handleAutoFill = () => {
    const template = `Please make the following improvements to the feasibility report:

1. **Technical Stack Section - Add More Specificity**:
   - Specify EXACT version numbers for all technologies (e.g., Python 3.11+, Node.js 20.x, React 18.3)
   - Add justification for WHY each technology was chosen over alternatives
   - Include compatibility matrix showing how all technologies work together
   - Add information about required third-party services and their pricing tiers

2. **Timeline Estimates - Make More Realistic**:
   - Break down into concrete phases with specific milestones (e.g., "Phase 1: Authentication & User Management - 3 weeks")
   - Add 20-30% buffer time for testing and bug fixes in each phase
   - Include time for code reviews, documentation, and deployment
   - Specify which phases can run in parallel vs sequential dependencies
   - Add critical path analysis highlighting bottlenecks

3. **Risk Assessment - Expand Mitigation Strategies**:
   - For each risk, add:
     * Probability score (High/Medium/Low)
     * Impact score (High/Medium/Low)
     * Specific mitigation strategy with steps
     * Contingency/fallback plan
     * Early warning indicators
   - Add more technical risks (API rate limits, database scalability, third-party service downtime)
   - Include team-related risks (key person dependency, skill gaps)

4. **Resource Analysis - Add Detailed Breakdown**:
   - Specify exact team composition (e.g., "2 Senior Backend, 2 Mid-level Frontend, 1 Junior DevOps")
   - Break down by skill level (Junior/Mid/Senior) with hourly rates
   - Add infrastructure costs with monthly breakdown (hosting, databases, CDN, monitoring)
   - Include tooling costs (CI/CD, monitoring, analytics, project management tools)
   - Add onboarding time for new team members (1-2 weeks)

5. **Cost Analysis - Add Financial Details** (if missing):
   - Provide detailed budget breakdown:
     * Development costs (team × hours × rates)
     * Infrastructure costs (monthly recurring)
     * Third-party services (APIs, SaaS tools)
     * Contingency fund (15-20% of total)
   - Add monthly burn rate projection
   - Include total project cost range (best case / worst case)

6. **Success Metrics & KPIs** (if missing):
   - Define measurable success criteria:
     * Performance metrics (page load time < 2s, API response < 500ms)
     * Quality metrics (test coverage > 80%, bug density < 5 per KLOC)
     * User metrics (adoption rate, user satisfaction score)
   - Add acceptance criteria for project completion
   - Include monitoring and alerting strategy

7. **Implementation Architecture** (enhance if present):
   - Add or improve system architecture diagram description
   - Detail data flow between components
   - Specify API design patterns (REST/GraphQL, versioning strategy)
   - Add deployment architecture (staging/production environments)
   - Include database schema considerations and migration strategy

Please revise the report to address ALL of the above points with concrete, specific information.`;

    setFeedback(template);
  };

  // Start HITL workflow
  const handleStartFeasibility = async () => {
    setHitlMode(true);
    await onCheckFeasibility(true); // Pass true to indicate HITL mode
  };

  // Approve report
  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await onCheckFeasibility(false, true, null); // HITL mode, approved, no feedback
    } catch (error) {
      console.error("Error approving report:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Request changes
  const handleRequestChanges = async () => {
    if (!feedback.trim()) {
      alert("Please provide feedback before requesting changes.");
      return;
    }

    setIsSubmitting(true);
    try {
      await onCheckFeasibility(false, false, feedback); // HITL mode, not approved, with feedback
      setFeedback(""); // Clear feedback after submission
    } catch (error) {
      console.error("Error requesting changes:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Update state when feasibility data changes (passed from parent)
  useEffect(() => {
    if (window.__feasibilityData) {
      const data = window.__feasibilityData;
      setFeasibilityStatus(data.status);
      setFeasibilityReport(data.feasibility_report || "");
      setIteration(data.iteration || 0);
      setMaxIterations(data.max_iterations || 3);
      setCritique(data.critique || "");
    }
  }, [loading]);

  const isAwaitingReview = feasibilityStatus === "awaiting_human";
  const isApproved = feasibilityStatus === "approved";
  const isMaxIterations = feasibilityStatus === "max_iterations_reached";

  // Download feasibility report as Markdown
  const handleDownloadReport = () => {
    if (!feasibilityReport) return;
    const blob = new Blob([feasibilityReport], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feasibility_report_${sessionId || "session"}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="step-container feasibility-step">
      <h2>Step 3: Generate Feasibility Assessment</h2>
      <p>
        Analyze project feasibility based on uploaded documents and development
        process information.
      </p>

      {/* Initial Generation Button */}
      {!hitlMode && !feasibilityReport && (
        <Button onClick={handleStartFeasibility} disabled={loading}>
          {loading ? "Analyzing Feasibility..." : "Check Feasibility"}
        </Button>
      )}

      {/* HITL Review Interface */}
      {hitlMode && (
        <div className="hitl-review-section">
          {/* Iteration Counter */}
          {isAwaitingReview && (
            <div className="iteration-counter">
              <span className="iteration-badge">
                Iteration {iteration + 1} of {maxIterations}
              </span>
            </div>
          )}

          {/* Feasibility Report Display */}
          {feasibilityReport && (
            <div className="report-display">
              <h3>Feasibility Report</h3>
              <div style={{ marginBottom: "0.5em" }}>
                <Button
                  onClick={handleDownloadReport}
                  className="secondary-button"
                  style={{ marginRight: "1em" }}
                >
                  Download Report
                </Button>
                <Button
                  onClick={() => setReportExpanded((v) => !v)}
                  className="secondary-button"
                >
                  {reportExpanded ? "Collapse" : "Expand"}
                </Button>
              </div>
              <div
                className="report-content"
                style={{
                  maxHeight: reportExpanded ? "none" : "300px",
                  overflowY: reportExpanded ? "visible" : "auto",
                  border: "1px solid #eee",
                  background: "#fafafa",
                  padding: "1em",
                }}
                ref={reportRef}
              >
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {feasibilityReport}
                </pre>
              </div>
            </div>
          )}

          {/* Critique Display (if available) */}
          {critique && iteration > 0 && (
            <div className="critique-display">
              <h3>Critique from Previous Feedback</h3>
              <div className="critique-content">
                <pre>{critique}</pre>
              </div>
            </div>
          )}

          {/* Review Controls */}
          {isAwaitingReview && !loading && (
            <div className="review-controls">
              <h3>Review Feasibility Report</h3>
              <p>
                Please review the report above. You can approve it to continue,
                or request changes with specific feedback.
              </p>

              {/* Feedback Textarea */}
              <div className="feedback-section">
                <label htmlFor="feedback">
                  Feedback for Revision (required if requesting changes):
                </label>
                <textarea
                  id="feedback"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Provide specific feedback on what needs to be improved..."
                  rows={8}
                  className="feedback-textarea"
                />
              </div>

              {/* Action Buttons */}
              <div className="review-buttons">
                <Button
                  onClick={handleAutoFill}
                  disabled={isSubmitting}
                  className="secondary-button"
                >
                  Auto-fill Feedback Template
                </Button>

                <Button
                  onClick={handleRequestChanges}
                  disabled={isSubmitting || !feedback.trim()}
                  className="warning-button"
                >
                  {isSubmitting ? "Requesting Changes..." : "Request Changes"}
                </Button>

                <Button
                  onClick={handleApprove}
                  disabled={isSubmitting}
                  className="success-button"
                >
                  {isSubmitting ? "Approving..." : "Approve & Continue"}
                </Button>
              </div>
            </div>
          )}

          {/* Status Messages */}
          {loading && (
            <div className="status-message loading">
              <p>
                ⏳ Generating {iteration > 0 ? "revised" : ""} feasibility
                report...
              </p>
            </div>
          )}

          {isApproved && (
            <div className="status-message success">
              <p>✅ Feasibility report approved! Proceeding to next step...</p>
            </div>
          )}

          {isMaxIterations && (
            <div className="status-message warning">
              <p>
                ⚠️ Maximum iterations ({maxIterations}) reached. Using current
                report.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

FeasibilityStep.propTypes = {
  loading: PropTypes.bool.isRequired,
  onCheckFeasibility: PropTypes.func.isRequired,
  sessionId: PropTypes.string,
  developmentContext: PropTypes.object,
};
