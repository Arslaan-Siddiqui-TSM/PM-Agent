import PropTypes from "prop-types";
import { Button, MarkdownRenderer, DiagramDisplay } from "../ui";
import "./PlanStep.css";

export const PlanStep = ({
  finalPlan,
  planFilePath,
  diagrams,
  diagramsLoading,
  onGenerateDiagrams,
  onReset,
}) => {
  return (
    <div className="step-container">
      <h2>Step 5: Project Plan Generated ✨</h2>

      <div className="success-message">
        <p>🎉 Your project plan has been successfully generated!</p>
        {planFilePath && (
          <p className="file-path">
            Saved to: <code>{planFilePath}</code>
          </p>
        )}
      </div>

      <div className="plan-preview">
        <MarkdownRenderer content={finalPlan} title="Project Plan" />
      </div>

      {/* Diagram Generation Section */}
      <div className="diagram-generation-section">
        <h3>Visual Diagrams</h3>
        <p>
          Would you like to generate visual diagrams from your project plan?
          This will create Gantt charts, architecture diagrams, and other
          visualizations to enhance your plan.
        </p>

        {diagrams.length === 0 ? (
          <Button
            onClick={onGenerateDiagrams}
            disabled={diagramsLoading}
            variant="primary"
          >
            {diagramsLoading ? "Generating Diagrams..." : "Generate Diagrams"}
          </Button>
        ) : (
          <div className="diagrams-generated">
            <p className="success-text">
              ✅ {diagrams.length} diagram(s) successfully generated!
            </p>
            <DiagramDisplay diagrams={diagrams} />
          </div>
        )}
      </div>

      <div className="action-buttons">
        <Button onClick={onReset} variant="secondary">
          Start New Project
        </Button>
      </div>
    </div>
  );
};

PlanStep.propTypes = {
  finalPlan: PropTypes.string.isRequired,
  planFilePath: PropTypes.string,
  diagrams: PropTypes.array.isRequired,
  diagramsLoading: PropTypes.bool.isRequired,
  onGenerateDiagrams: PropTypes.func.isRequired,
  onReset: PropTypes.func.isRequired,
};
