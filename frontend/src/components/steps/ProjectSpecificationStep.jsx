import { useState } from "react";
import PropTypes from "prop-types";
import { Button } from "../ui";
import { ProjectSpecForm } from "../forms";
import "./ProjectSpecificationStep.css";

export const ProjectSpecificationStep = ({
  loading,
  onGeneratePlan,
  enableHitl,
  onEnableHitlChange,
}) => {
  const [projectSpec, setProjectSpec] = useState(null);

  const handleSpecChange = (updatedSpec) => {
    setProjectSpec(updatedSpec);
  };

  const handleGeneratePlan = () => {
    if (onGeneratePlan) {
      onGeneratePlan();
    }
  };

  return (
    <div className="step-container">
      <h2>Step 6: Project Specification</h2>

      <div className="spec-container">
        <ProjectSpecForm onSpecChange={handleSpecChange} />

        {/* HITL Toggle Section */}
        <div className="hitl-toggle-container">
          <div className="hitl-toggle-section">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={enableHitl}
                onChange={(e) => onEnableHitlChange(e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-switch"></span>
              <span className="toggle-text">
                Enable Human-in-the-Loop Review
              </span>
            </label>
          </div>

          {enableHitl && (
            <div className="hitl-info-box">
              <div className="hitl-status">
                <span className="status-badge">✅ HITL Mode Enabled</span>
              </div>

              <p className="hitl-description">
                You'll review and provide feedback at each stage of the plan
                generation:
              </p>

              <div className="hitl-stages">
                <div className="stage">
                  <span className="stage-icon">📝</span>
                  <strong>Draft Review:</strong>
                  <span className="stage-desc">
                    Review the AI-generated draft plan
                  </span>
                </div>

                <div className="stage">
                  <span className="stage-icon">🔍</span>
                  <strong>Critique Review:</strong>
                  <span className="stage-desc">
                    Review and adjust the AI's analysis
                  </span>
                </div>

                <div className="stage">
                  <span className="stage-icon">✏️</span>
                  <strong>Revision:</strong>
                  <span className="stage-desc">
                    AI incorporates your feedback into the final plan
                  </span>
                </div>
              </div>

              <div className="hitl-warning">
                <span className="warning-icon">⚠️</span>
                You can edit content, provide feedback, or finalize at any
                point.
              </div>
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="action-buttons">
          <Button onClick={handleGeneratePlan} disabled={loading}>
            {loading
              ? "Generating Plan..."
              : enableHitl
              ? "🎯 Generate Plan with Review"
              : "✅ Generate Project Plan"}
          </Button>
        </div>
      </div>
    </div>
  );
};

ProjectSpecificationStep.propTypes = {
  loading: PropTypes.bool.isRequired,
  onGeneratePlan: PropTypes.func.isRequired,
  enableHitl: PropTypes.bool.isRequired,
  onEnableHitlChange: PropTypes.func.isRequired,
};
