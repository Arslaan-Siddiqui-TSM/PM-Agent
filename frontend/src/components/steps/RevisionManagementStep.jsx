import { useState, useMemo } from "react";
import PropTypes from "prop-types";
import { Button, MarkdownRenderer } from "../ui";
import "./RevisionManagementStep.css";

export const RevisionManagementStep = ({
  loading,
  feasibilityReport,
  feasibilityVersion,
  revisionHistory,
  onRequestRevision,
  onRefreshRevisionHistory,
  onFetchRevisionContent,
  onContinueToSpecification,
}) => {
  const [critique, setCritique] = useState("");
  const [instructions, setInstructions] = useState("");
  const [selectedRevision, setSelectedRevision] = useState(null);
  const [selectedRevisionContent, setSelectedRevisionContent] = useState("");

  const handleLoadSelectedRevision = async (rev) => {
    setSelectedRevision(rev);
    setSelectedRevisionContent("");
    if (rev?.file_path && onFetchRevisionContent) {
      const content = await onFetchRevisionContent(rev.file_path);
      setSelectedRevisionContent(content);
    }
  };

  const diff = useMemo(() => {
    if (!feasibilityReport || !selectedRevisionContent) return [];
    const a = feasibilityReport.split("\n");
    const b = selectedRevisionContent.split("\n");
    const maxLen = Math.max(a.length, b.length);
    const rows = [];
    for (let i = 0; i < maxLen; i++) {
      const left = a[i] ?? "";
      const right = b[i] ?? "";
      let type = "unchanged";
      if (left !== right) {
        if (!left && right) type = "added";
        else if (left && !right) type = "removed";
        else type = "changed";
      }
      rows.push({ left, right, type });
    }
    return rows;
  }, [feasibilityReport, selectedRevisionContent]);

  return (
    <div className="step-container">
      <h2>Step 5: Revision Management & Versioning</h2>

      <div className="current-version-box">
        <div className="version-info">
          <h3>Current Approved Version</h3>
          <p className="version-number">v{feasibilityVersion}</p>
          <p className="version-description">
            This is your current feasibility report. You can request revisions
            below, or finalize and proceed to the project plan.
          </p>
        </div>

        <div className="current-report">
          {feasibilityReport && (
            <MarkdownRenderer
              content={feasibilityReport}
              title="Current Feasibility Report"
            />
          )}
        </div>
      </div>

      {/* Revision Request Form */}
      <div className="revision-panel">
        <div className="panel-header">
          <h3>Request Further Revisions</h3>
          <p className="panel-hint">
            Provide feedback to refine the feasibility report further.
          </p>
        </div>

        <div className="revision-form">
          <label className="field-label">Human Critique (required)</label>
          <textarea
            value={critique}
            onChange={(e) => setCritique(e.target.value)}
            placeholder="Describe what needs improvement or clarification in the report..."
            className="feedback-textarea"
            rows={4}
          />

          <label className="field-label">
            Revision Instructions (optional)
          </label>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Optional guidance: sections to update, tone, sources, details to add..."
            className="feedback-textarea"
            rows={3}
          />

          <div className="revision-buttons">
            <Button
              onClick={() =>
                onRequestRevision && onRequestRevision(critique, instructions)
              }
              disabled={loading || !critique.trim()}
            >
              {loading ? "Submitting Revision..." : "Request Revision"}
            </Button>
            <Button
              onClick={() =>
                onRefreshRevisionHistory && onRefreshRevisionHistory()
              }
              variant="secondary"
            >
              Refresh History
            </Button>
          </div>
        </div>
      </div>

      {/* Revision History */}
      {revisionHistory && revisionHistory.length > 0 && (
        <div className="revision-history-panel">
          <h3>Revision History</h3>
          <ul className="history-list">
            {revisionHistory.map((rev) => (
              <li key={rev.version} className="history-item">
                <div className="history-meta">
                  <span className="history-version">v{rev.version}</span>
                  <span className="history-time">{rev.created_at}</span>
                  <span className="history-type">{rev.type}</span>
                </div>
                <div className="history-actions">
                  <Button
                    variant="secondary"
                    onClick={() => handleLoadSelectedRevision(rev)}
                  >
                    Load & Compare
                  </Button>
                  {rev.file_path && (
                    <span className="file-path-inline">
                      <code>{rev.file_path}</code>
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Diff Viewer */}
      {selectedRevisionContent && (
        <div className="diff-view">
          <h3>
            Comparing: Current (v{feasibilityVersion}) vs Selected (v
            {selectedRevision?.version})
          </h3>
          <div className="diff-grid">
            <div className="diff-column">
              <div className="diff-title">Current v{feasibilityVersion}</div>
              {diff.map((row, idx) => (
                <pre key={`l-${idx}`} className={`diff-line ${row.type}`}>
                  {row.left}
                </pre>
              ))}
            </div>
            <div className="diff-column">
              <div className="diff-title">
                Previous v{selectedRevision?.version}
              </div>
              {diff.map((row, idx) => (
                <pre key={`r-${idx}`} className={`diff-line ${row.type}`}>
                  {row.right}
                </pre>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Action Button */}
      <div className="action-buttons">
        <Button onClick={onContinueToSpecification} disabled={loading}>
          {loading ? "Loading..." : "✅ Continue to Project Specification"}
        </Button>
      </div>
    </div>
  );
};

RevisionManagementStep.propTypes = {
  loading: PropTypes.bool.isRequired,
  feasibilityReport: PropTypes.string,
  feasibilityVersion: PropTypes.number,
  revisionHistory: PropTypes.array,
  onRequestRevision: PropTypes.func,
  onRefreshRevisionHistory: PropTypes.func,
  onFetchRevisionContent: PropTypes.func,
  onContinueToSpecification: PropTypes.func.isRequired,
};
