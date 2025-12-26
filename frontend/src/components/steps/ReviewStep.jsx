import { useState } from "react";
import PropTypes from "prop-types";
import { Button, MarkdownRenderer } from "../ui";
import { ProjectSpecForm } from "../forms";
import "./ReviewStep.css";

export const ReviewStep = ({
  loading,
  feasibilityReport,
  feasibilityFilePath,
  developmentContextJsonPath,
  enableHITL,
  onToggleHITL,
  onGeneratePlan,
}) => {
  const [feedback, setFeedback] = useState("");
  const [projectSpec, setProjectSpec] = useState(null);

  const handleSpecChange = (updatedSpec) => {
    setProjectSpec(updatedSpec);
  };

  return (
    <div className="step-container">
      <h2>Step 4: Review Feasibility Assessment</h2>

      <div className="report-container">
        <div className="report-info">
          <p>✅ Feasibility assessment has been generated and saved.</p>
          {feasibilityFilePath && (
            <p className="file-path">
              Feasibility Report: <code>{feasibilityFilePath}</code>
            </p>
          )}
          {developmentContextJsonPath && (
            <p className="file-path">
              Development Context JSON:{" "}
              <code>{developmentContextJsonPath}</code>
            </p>
          )}
        </div>

        {feasibilityReport && (
          <MarkdownRenderer
            content={feasibilityReport}
            title="Feasibility Assessment Report"
          />
        )}
      </div>

      {/* Project Specification Form */}
      <ProjectSpecForm onSpecChange={handleSpecChange} />

      <div className="feedback-section">
        <h3>Additional Feedback (Optional)</h3>
        <p className="feedback-hint">
          Add any additional comments or concerns about the feasibility
          assessment.
        </p>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="E.g., 'Focus more on security requirements' or 'Add mobile app considerations'..."
          className="feedback-textarea"
          rows={4}
        />
      </div>

      {/* HITL Mode Toggle */}
      <div className="hitl-toggle-section">
        <div className="hitl-toggle-header">
          <label className="hitl-toggle">
            <input
              type="checkbox"
              checked={enableHITL}
              onChange={(e) => onToggleHITL(e.target.checked)}
            />
            <span className="toggle-slider"></span>
            <span className="toggle-label">
              🔄 Enable Human-in-the-Loop Review
            </span>
          </label>
        </div>
        <div className="hitl-info">
          {enableHITL ? (
            <div className="hitl-enabled-info">
              <p>
                <strong>✅ HITL Mode Enabled</strong>
              </p>
              <p>
                You'll review and provide feedback at each stage of the plan
                generation:
              </p>
              <ul>
                <li>
                  📝 <strong>Draft Review:</strong> Review the AI-generated
                  draft plan
                </li>
                <li>
                  🔍 <strong>Critique Review:</strong> Review and adjust the
                  AI's analysis
                </li>
                <li>
                  ✏️ <strong>Revision:</strong> AI incorporates your feedback
                  into the final plan
                </li>
              </ul>
              <p className="hitl-tip">
                💡 You can edit content, provide feedback, or finalize at any
                point.
              </p>
            </div>
          ) : (
            <div className="hitl-disabled-info">
              <p>
                <strong>⚡ Standard Mode</strong>
              </p>
              <p>
                The AI will automatically generate the plan through multiple
                reflection iterations without human review checkpoints.
              </p>
            </div>
          )}
        </div>
      </div>

      <Button onClick={onGeneratePlan} disabled={loading}>
        {loading
          ? "Generating Plan..."
          : enableHITL
          ? "🔄 Generate Plan with Review"
          : "⚡ Generate Project Plan"}
      </Button>
    </div>
  );
};

ReviewStep.propTypes = {
  loading: PropTypes.bool.isRequired,
  feasibilityReport: PropTypes.string,
  feasibilityFilePath: PropTypes.string,
  developmentContextJsonPath: PropTypes.string,
  enableHITL: PropTypes.bool,
  onToggleHITL: PropTypes.func,
  onGeneratePlan: PropTypes.func.isRequired,
};

ReviewStep.defaultProps = {
  enableHITL: false,
  onToggleHITL: () => {},
};
