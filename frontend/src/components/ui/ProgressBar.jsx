import PropTypes from "prop-types";
import { WORKFLOW_STEPS } from "../../constants";
import "./ProgressBar.css";

const STEPS = [
  { number: WORKFLOW_STEPS.UPLOAD, label: "1. Upload" },
  { number: WORKFLOW_STEPS.DEVELOPMENT_PROCESS, label: "2. Process Info" },
  { number: WORKFLOW_STEPS.FEASIBILITY, label: "3. Feasibility" },
  { number: WORKFLOW_STEPS.REVIEW, label: "4. Review" },
  { number: WORKFLOW_STEPS.REVISION_MANAGEMENT, label: "5. Revisions" },
  { number: WORKFLOW_STEPS.PROJECT_SPECIFICATION, label: "6. Specification" },
  { number: WORKFLOW_STEPS.PLAN_HITL_REVIEW, label: "6.5 Plan Review" },
  { number: WORKFLOW_STEPS.PLAN, label: "7. Plan" },
];

export const ProgressBar = ({ currentStep }) => {
  // Filter steps - only show PLAN_HITL_REVIEW if we're currently in it
  const displaySteps = STEPS.filter(
    (step) =>
      step.number !== WORKFLOW_STEPS.PLAN_HITL_REVIEW ||
      currentStep === WORKFLOW_STEPS.PLAN_HITL_REVIEW
  );

  // Determine if step is complete, active, or pending
  const isStepActive = (stepNumber) => currentStep === stepNumber;
  const isStepComplete = (stepNumber) => currentStep > stepNumber;

  return (
    <div className="progress-bar standard-mode">
      {displaySteps.map((step, index) => {
        const status = isStepComplete(step.number)
          ? "complete"
          : isStepActive(step.number)
          ? "active"
          : "pending";

        return (
          <div key={step.number} className={`progress-step ${status}`}>
            <div className="step-indicator">
              {status === "complete" ? (
                <span className="check-icon">✓</span>
              ) : (
                <span className="step-number">{index + 1}</span>
              )}
            </div>
            <span className="step-label">{step.label}</span>
            {index < displaySteps.length - 1 && (
              <div className="step-connector" />
            )}
          </div>
        );
      })}
    </div>
  );
};

ProgressBar.propTypes = {
  currentStep: PropTypes.number.isRequired,
};
