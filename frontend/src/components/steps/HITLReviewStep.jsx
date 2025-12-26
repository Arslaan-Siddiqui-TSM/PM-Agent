import { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Button, MarkdownRenderer } from "../ui";
import { REVIEW_TYPES, REVIEW_ACTIONS } from "../../constants";
import "./HITLReviewStep.css";

/**
 * HITLReviewStep Component
 *
 * Human-in-the-Loop review interface for draft and reflection review stages.
 * Provides editing capabilities, feedback input, and action buttons.
 */
export const HITLReviewStep = ({
  reviewType,
  reviewData,
  iteration,
  loading,
  onSubmitReview,
}) => {
  const [activeTab, setActiveTab] = useState("preview");
  const [editedContent, setEditedContent] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const [reviewerId, setReviewerId] = useState("");
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  const isDraftReview = reviewType === REVIEW_TYPES.DRAFT;
  const content = isDraftReview ? reviewData?.draft : reviewData?.reflection;
  const contextDraft = !isDraftReview ? reviewData?.draft : null;

  // Initialize edited content when review data changes
  useEffect(() => {
    if (content) {
      setEditedContent(content);
    }
  }, [content]);

  const handleActionClick = (action) => {
    // Validate feedback action
    if (
      action === REVIEW_ACTIONS.FEEDBACK &&
      !feedbackText.trim() &&
      editedContent === content
    ) {
      return; // Button should be disabled anyway
    }
    setPendingAction(action);
    setShowConfirmation(true);
  };

  const handleConfirmSubmit = () => {
    const hasEdits = editedContent !== content;

    const payload = {
      request_id: reviewData?.request_id,
      action: pendingAction,
      feedback_text: feedbackText.trim() || null,
      edited_text: hasEdits ? editedContent : null,
      reviewer_id: reviewerId.trim() || null,
    };

    onSubmitReview(payload);
    setShowConfirmation(false);
    setPendingAction(null);
  };

  const handleCancelConfirmation = () => {
    setShowConfirmation(false);
    setPendingAction(null);
  };

  const getActionLabel = (action) => {
    switch (action) {
      case REVIEW_ACTIONS.APPROVE:
        return isDraftReview
          ? "Approve & Continue to AI Critique"
          : "Approve & Continue to Revision";
      case REVIEW_ACTIONS.FEEDBACK:
        return "Submit Feedback & Continue";
      case REVIEW_ACTIONS.TERMINATE:
        return "Finalize with Current Content";
      default:
        return action;
    }
  };

  const getActionDescription = (action) => {
    switch (action) {
      case REVIEW_ACTIONS.APPROVE:
        return isDraftReview
          ? "The draft will be sent to the AI for critique analysis."
          : "The critique will be used to generate the revised plan.";
      case REVIEW_ACTIONS.FEEDBACK:
        return isDraftReview
          ? "Your feedback and edits will be included in the AI critique process."
          : "Your feedback will guide the revision process.";
      case REVIEW_ACTIONS.TERMINATE:
        return "The workflow will end and the current draft will be saved as the final plan.";
      default:
        return "";
    }
  };

  // Confirmation Modal
  if (showConfirmation) {
    return (
      <div className="step-container hitl-review-step">
        <div className="confirmation-modal">
          <div className="confirmation-header">
            <h2>
              {pendingAction === REVIEW_ACTIONS.APPROVE &&
                "✅ Confirm Approval"}
              {pendingAction === REVIEW_ACTIONS.FEEDBACK &&
                "📝 Confirm Feedback"}
              {pendingAction === REVIEW_ACTIONS.TERMINATE &&
                "🏁 Confirm Finalization"}
            </h2>
          </div>

          <div className="confirmation-body">
            <div className="confirmation-action">
              <h3>Action</h3>
              <p className={`action-badge action-${pendingAction}`}>
                {getActionLabel(pendingAction)}
              </p>
              <p className="action-description">
                {getActionDescription(pendingAction)}
              </p>
            </div>

            {feedbackText && (
              <div className="confirmation-section">
                <h3>Your Feedback</h3>
                <div className="feedback-preview">{feedbackText}</div>
              </div>
            )}

            {editedContent !== content && (
              <div className="confirmation-section">
                <h3>Content Modified</h3>
                <p className="edit-summary">
                  You've made changes to the{" "}
                  {isDraftReview ? "draft" : "reflection"} content. These
                  changes will be preserved.
                </p>
              </div>
            )}
          </div>

          <div className="confirmation-actions">
            <Button
              variant="secondary"
              onClick={handleCancelConfirmation}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              variant={
                pendingAction === REVIEW_ACTIONS.TERMINATE
                  ? "danger"
                  : "primary"
              }
              onClick={handleConfirmSubmit}
              disabled={loading}
            >
              {loading ? "Submitting..." : "Confirm"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="step-container hitl-review-step">
      {/* Header */}
      <div className="hitl-header">
        <div className="hitl-title">
          <h2>
            {isDraftReview ? "📝 Review AI Draft" : "🔍 Review AI Critique"}
          </h2>
          <span className="iteration-badge">Iteration {iteration || 1}</span>
        </div>
        <p className="hitl-subtitle">
          {isDraftReview
            ? "Review the AI-generated draft plan. You can edit the content, provide feedback, or approve to continue."
            : "Review the AI's critique of the draft. You can adjust the feedback points or approve to proceed with revision."}
        </p>
      </div>

      {/* Context Section for Reflection Review */}
      {!isDraftReview && contextDraft && (
        <div className="context-section">
          <h3>📄 Current Draft (Read-only Context)</h3>
          <div className="context-content">
            <MarkdownRenderer content={contextDraft} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="content-section">
        <div className="content-header">
          <h3>{isDraftReview ? "Draft Plan" : "AI Critique"}</h3>
          <div className="tab-switcher">
            <button
              className={`tab-btn ${activeTab === "preview" ? "active" : ""}`}
              onClick={() => setActiveTab("preview")}
            >
              Preview
            </button>
            <button
              className={`tab-btn ${activeTab === "edit" ? "active" : ""}`}
              onClick={() => setActiveTab("edit")}
            >
              Edit
            </button>
          </div>
        </div>

        <div className="content-body">
          {activeTab === "preview" ? (
            <div className="preview-pane">
              <MarkdownRenderer
                content={editedContent || content || "No content available"}
              />
            </div>
          ) : (
            <div className="edit-pane">
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                placeholder={`Edit the ${
                  isDraftReview ? "draft" : "critique"
                } content...`}
                className="edit-textarea"
                spellCheck="false"
              />
              {editedContent !== content && (
                <div className="edit-indicator">
                  <span className="modified-badge">✏️ Modified</span>
                  <button
                    className="reset-btn"
                    onClick={() => setEditedContent(content)}
                  >
                    Reset to Original
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Feedback Section */}
      <div className="feedback-section">
        <h3>💬 Your Feedback (Optional)</h3>
        <p className="feedback-hint">
          {isDraftReview
            ? "Add comments or suggestions for the AI to consider during critique generation."
            : "Provide guidance on how the revision should address these critique points."}
        </p>
        <textarea
          value={feedbackText}
          onChange={(e) => setFeedbackText(e.target.value)}
          placeholder={
            isDraftReview
              ? "E.g., 'Focus more on security requirements' or 'The timeline seems aggressive'..."
              : "E.g., 'Prioritize the budget concerns' or 'The scope critique is valid but needs softer language'..."
          }
          className="feedback-textarea"
          rows={4}
        />
      </div>

      {/* Reviewer ID (Collapsible) */}
      <details className="reviewer-section">
        <summary>👤 Reviewer Identification (Optional)</summary>
        <input
          type="text"
          value={reviewerId}
          onChange={(e) => setReviewerId(e.target.value)}
          placeholder="Enter your name or ID for audit purposes"
          className="reviewer-input"
        />
      </details>

      {/* Action Buttons */}
      <div className="action-buttons">
        <Button
          variant="secondary"
          onClick={() => handleActionClick(REVIEW_ACTIONS.TERMINATE)}
          disabled={loading}
          className="terminate-btn"
        >
          🏁 Finalize Now
        </Button>

        <div className="primary-actions">
          <Button
            variant="outline"
            onClick={() => handleActionClick(REVIEW_ACTIONS.FEEDBACK)}
            disabled={
              loading || (!feedbackText.trim() && editedContent === content)
            }
            title={
              !feedbackText.trim() && editedContent === content
                ? "Add feedback or make edits first"
                : ""
            }
          >
            📝 Submit with Feedback
          </Button>
          <Button
            variant="primary"
            onClick={() => handleActionClick(REVIEW_ACTIONS.APPROVE)}
            disabled={loading}
          >
            ✅ Approve & Continue
          </Button>
        </div>
      </div>

      {/* Help Text */}
      <div className="help-section">
        <details>
          <summary>ℹ️ What do these actions mean?</summary>
          <div className="help-content">
            <div className="help-item">
              <strong>✅ Approve & Continue:</strong>
              <p>
                Accept the current content and proceed to the next stage of the
                workflow.
              </p>
            </div>
            <div className="help-item">
              <strong>📝 Submit with Feedback:</strong>
              <p>
                Include your feedback and/or edits. The AI will consider them in
                the next step.
              </p>
            </div>
            <div className="help-item">
              <strong>🏁 Finalize Now:</strong>
              <p>
                End the workflow immediately. The current draft becomes the
                final plan.
              </p>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
};

HITLReviewStep.propTypes = {
  reviewType: PropTypes.oneOf([REVIEW_TYPES.DRAFT, REVIEW_TYPES.REFLECTION])
    .isRequired,
  reviewData: PropTypes.shape({
    request_id: PropTypes.string,
    draft: PropTypes.string,
    reflection: PropTypes.string,
    iteration: PropTypes.number,
    metadata: PropTypes.object,
  }),
  iteration: PropTypes.number,
  loading: PropTypes.bool,
  onSubmitReview: PropTypes.func.isRequired,
};

HITLReviewStep.defaultProps = {
  reviewData: null,
  iteration: 1,
  loading: false,
};
