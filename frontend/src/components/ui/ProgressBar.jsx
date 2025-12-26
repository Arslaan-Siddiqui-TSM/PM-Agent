import PropTypes from "prop-types";
import { WORKFLOW_STEPS } from "../../constants";
import "./ProgressBar.css";

const STANDARD_STEPS = [
  { number: WORKFLOW_STEPS.UPLOAD, label: "1. Upload" },
  { number: WORKFLOW_STEPS.DEVELOPMENT_PROCESS, label: "2. Process Info" },
  { number: WORKFLOW_STEPS.FEASIBILITY, label: "3. Feasibility" },
  { number: WORKFLOW_STEPS.REVIEW, label: "4. Review" },
  { number: WORKFLOW_STEPS.PLAN, label: "5. Plan" },
];

const HITL_STEPS = [
  { number: WORKFLOW_STEPS.UPLOAD, label: "1. Upload" },
  { number: WORKFLOW_STEPS.DEVELOPMENT_PROCESS, label: "2. Process" },
  { number: WORKFLOW_STEPS.FEASIBILITY, label: "3. Feasibility" },
  { number: WORKFLOW_STEPS.REVIEW, label: "4. Settings" },
  { number: WORKFLOW_STEPS.HITL_DRAFT_REVIEW, label: "5. Draft" },
  { number: WORKFLOW_STEPS.HITL_REFLECTION_REVIEW, label: "6. Critique" },
  { number: WORKFLOW_STEPS.PLAN, label: "7. Plan" },
];

export const ProgressBar = ({ currentStep, enableHITL }) => {
  const steps = enableHITL ? HITL_STEPS : STANDARD_STEPS;

  // Determine if step is complete, active, or pending
  const getStepStatus = (stepNumber) => {
    if (currentStep > stepNumber) return "complete";
    if (currentStep === stepNumber) return "active";
    return "pending";
  };

  // For HITL mode, handle the transition between steps properly
  const isStepActive = (stepNumber) => {
    if (enableHITL) {
      // Special handling for HITL steps
      if (
        currentStep === WORKFLOW_STEPS.HITL_DRAFT_REVIEW &&
        stepNumber === WORKFLOW_STEPS.HITL_DRAFT_REVIEW
      ) {
        return true;
      }
      if (
        currentStep === WORKFLOW_STEPS.HITL_REFLECTION_REVIEW &&
        stepNumber === WORKFLOW_STEPS.HITL_REFLECTION_REVIEW
      ) {
        return true;
      }
    }
    return currentStep === stepNumber;
  };

  const isStepComplete = (stepNumber) => {
    if (enableHITL) {
      // In HITL mode, check based on the actual step numbers
      return currentStep > stepNumber;
    }
    return currentStep > stepNumber;
  };

  return (
    <div
      className={`progress-bar ${enableHITL ? "hitl-mode" : "standard-mode"}`}
    >
      {steps.map((step, index) => {
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
            {index < steps.length - 1 && <div className="step-connector" />}
          </div>
        );
      })}
    </div>
  );
};

ProgressBar.propTypes = {
  currentStep: PropTypes.number.isRequired,
  enableHITL: PropTypes.bool,
};

ProgressBar.defaultProps = {
  enableHITL: false,
};
