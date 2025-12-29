import PropTypes from "prop-types";
import { Button, MarkdownRenderer } from "../ui";
import "./ReviewStep.css";

export const ReviewStep = ({
  loading,
  feasibilityReport,
  feasibilityFilePath,
  developmentContextJsonPath,
  feasibilityVersion,
  revisionHistory,
  onApproveAndContinue,
}) => {
  const revisionCount = revisionHistory?.length || 0;

  return (
    <div className="step-container">
      <h2>Step 4: Review Feasibility Assessment</h2>

      <div className="report-container">
        <div className="report-info">
          <p>✅ Feasibility assessment has been generated and saved.</p>
          <p>
            Current version: <strong>v{feasibilityVersion || 1}</strong> (
            {revisionCount} total revisions)
          </p>
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

      <div className="approval-actions">
        <Button onClick={onApproveAndContinue} disabled={loading}>
          {loading ? "Approving..." : "✅ Approve & Continue to Versioning"}
        </Button>
      </div>
    </div>
  );
};

ReviewStep.propTypes = {
  loading: PropTypes.bool.isRequired,
  feasibilityReport: PropTypes.string,
  feasibilityFilePath: PropTypes.string,
  developmentContextJsonPath: PropTypes.string,
  feasibilityVersion: PropTypes.number,
  revisionHistory: PropTypes.array,
  onApproveAndContinue: PropTypes.func.isRequired,
};
