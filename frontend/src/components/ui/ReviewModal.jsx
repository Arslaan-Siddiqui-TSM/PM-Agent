import { useState } from "react";
import PropTypes from "prop-types";
import { toast } from "react-toastify";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { Button } from "./Button";
import "./ReviewModal.css";

/**
 * ReviewModal Component
 *
 * Modal overlay for HITL review - displays draft plan, reflection notes,
 * and allows user to approve or provide feedback without leaving the workflow.
 */
export const ReviewModal = ({
  reviewData,
  onClose,
  onSubmit,
  isSubmitting,
}) => {
  const [activeTab, setActiveTab] = useState("draft");
  const [feedbackText, setFeedbackText] = useState("");
  const [editedText, setEditedText] = useState("");
  const [reviewerId, setReviewerId] = useState("");
  const [tags, setTags] = useState("");
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);

  if (!reviewData) return null;

  const handleSubmit = (action) => {
    // Validate inputs
    if (action === "feedback" && !feedbackText.trim() && !editedText.trim()) {
      toast.warning("Please provide either feedback text or edited text");
      return;
    }

    // Show confirmation screen before submitting
    setConfirmAction(action);
    setShowConfirmation(true);
  };

  const confirmSubmit = async () => {
    // Parse tags (comma-separated)
    const tagsList = tags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    // Build payload
    const payload = {
      action: confirmAction,
      feedback_text: feedbackText.trim() || null,
      edited_text: editedText.trim() || null,
      tags: tagsList.length > 0 ? tagsList : null,
      reviewer_id: reviewerId.trim() || null,
    };

    await onSubmit(payload);
  };

  const cancelConfirmation = () => {
    setShowConfirmation(false);
    setConfirmAction(null);
  };

  // Confirmation screen
  if (showConfirmation) {
    return (
      <div className="modal-overlay">
        <div className="modal-content review-confirmation">
          <div className="confirmation-header">
            <h2>
              {confirmAction === "approve"
                ? "✅ Confirm Approval"
                : "📝 Confirm Feedback Submission"}
            </h2>
          </div>

          <div className="confirmation-body">
            <div className="confirmation-section">
              <h3>Action</h3>
              <p className="action-badge">
                {confirmAction === "approve"
                  ? "Approve Draft Plan"
                  : "Request Changes"}
              </p>
            </div>

            {feedbackText && (
              <div className="confirmation-section">
                <h3>Your Feedback</h3>
                <div className="feedback-preview">{feedbackText}</div>
              </div>
            )}

            {editedText && (
              <div className="confirmation-section">
                <h3>Edited Text Provided</h3>
                <p className="text-muted">
                  You've provided {editedText.length} characters of edited
                  content
                </p>
              </div>
            )}

            {tags && (
              <div className="confirmation-section">
                <h3>Tags</h3>
                <p>{tags}</p>
              </div>
            )}

            {reviewerId && (
              <div className="confirmation-section">
                <h3>Reviewer ID</h3>
                <p>{reviewerId}</p>
              </div>
            )}

            <div className="confirmation-actions">
              <Button
                onClick={confirmSubmit}
                disabled={isSubmitting}
                variant="primary"
              >
                {isSubmitting
                  ? "Submitting..."
                  : `Confirm ${
                      confirmAction === "approve" ? "Approval" : "Feedback"
                    }`}
              </Button>
              <Button
                onClick={cancelConfirmation}
                disabled={isSubmitting}
                variant="secondary"
              >
                Go Back
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Main review screen
  return (
    <div className="modal-overlay">
      <div className="modal-content review-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-section">
            <h2>📋 Review Required: Iteration {reviewData.iteration}</h2>
            <button
              className="modal-close"
              onClick={onClose}
              disabled={isSubmitting}
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <div className="review-metadata">
            <div className="metadata-item">
              <span className="label">Confidence:</span>
              <span className="value">
                {(reviewData.metadata?.confidence * 100).toFixed(0)}%
              </span>
            </div>
            {reviewData.metadata?.quality_score && (
              <div className="metadata-item">
                <span className="label">Quality Score:</span>
                <span className="value">
                  {reviewData.metadata.quality_score.toFixed(1)}/10
                </span>
              </div>
            )}
            <div className="metadata-item">
              <span className="label">Request ID:</span>
              <span className="value request-id">
                {reviewData.request_id?.substring(0, 8)}...
              </span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button
            className={`tab ${activeTab === "draft" ? "active" : ""}`}
            onClick={() => setActiveTab("draft")}
          >
            📄 Draft Plan
          </button>
          <button
            className={`tab ${activeTab === "reflection" ? "active" : ""}`}
            onClick={() => setActiveTab("reflection")}
          >
            💡 Reflection & Critique
          </button>
          <button
            className={`tab ${activeTab === "feedback" ? "active" : ""}`}
            onClick={() => setActiveTab("feedback")}
          >
            ✏️ Your Feedback
          </button>
        </div>

        {/* Tab Content */}
        <div className="modal-body">
          {activeTab === "draft" && (
            <div className="tab-content">
              <div className="content-info">
                <p>
                  This is the first draft generated by the AI. Review it
                  carefully and provide feedback for improvement.
                </p>
              </div>
              <div className="markdown-container">
                <MarkdownRenderer
                  content={reviewData.model_output}
                  title="Draft Project Plan"
                />
              </div>
            </div>
          )}

          {activeTab === "reflection" && (
            <div className="tab-content">
              <div className="content-info">
                <p>
                  AI's self-critique identifying potential issues and areas for
                  improvement.
                </p>
              </div>

              {reviewData.metadata?.improvement_areas?.length > 0 && (
                <div className="improvement-areas">
                  <h3>🎯 Key Improvement Areas</h3>
                  <ul>
                    {reviewData.metadata.improvement_areas.map((area, idx) => (
                      <li key={idx}>{area}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="markdown-container">
                <MarkdownRenderer
                  content={reviewData.reflection_notes}
                  title="Reflection Notes"
                />
              </div>
            </div>
          )}

          {activeTab === "feedback" && (
            <div className="tab-content feedback-form">
              <div className="content-info">
                <p>
                  Provide your feedback to guide the next iteration. You can
                  either write feedback or directly edit the draft.
                </p>
              </div>

              <div className="form-section">
                <label htmlFor="feedback-text">
                  <strong>Feedback Text</strong>
                  <span className="label-hint">
                    Describe what needs to be improved or changed
                  </span>
                </label>
                <textarea
                  id="feedback-text"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="E.g., 'Focus more on timeline clarity', 'Add budget breakdown details', 'Simplify technical jargon'..."
                  rows={6}
                  disabled={isSubmitting}
                />
              </div>

              <div className="form-section">
                <label htmlFor="edited-text">
                  <strong>Edited Text (Optional)</strong>
                  <span className="label-hint">
                    Paste your edited version of the plan here
                  </span>
                </label>
                <textarea
                  id="edited-text"
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  placeholder="Paste edited version of the plan here (optional)..."
                  rows={8}
                  disabled={isSubmitting}
                />
              </div>

              <div className="form-row">
                <div className="form-section">
                  <label htmlFor="reviewer-id">
                    Reviewer ID <span className="optional">(Optional)</span>
                  </label>
                  <input
                    id="reviewer-id"
                    type="text"
                    value={reviewerId}
                    onChange={(e) => setReviewerId(e.target.value)}
                    placeholder="your.email@example.com"
                    disabled={isSubmitting}
                  />
                </div>

                <div className="form-section">
                  <label htmlFor="tags">
                    Tags <span className="optional">(Optional)</span>
                  </label>
                  <input
                    id="tags"
                    type="text"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    placeholder="clarity, budget, timeline"
                    disabled={isSubmitting}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="modal-footer">
          <div className="footer-hint">
            <p>
              💡 <strong>Tip:</strong> Switch between tabs to review the draft
              and reflection before providing feedback.
            </p>
          </div>

          <div className="action-buttons">
            <Button
              onClick={() => handleSubmit("approve")}
              disabled={isSubmitting}
              variant="success"
            >
              ✅ Approve Draft
            </Button>
            <Button
              onClick={() => handleSubmit("feedback")}
              disabled={isSubmitting}
              variant="primary"
            >
              📝 Request Changes
            </Button>
            <Button
              onClick={onClose}
              disabled={isSubmitting}
              variant="secondary"
            >
              Cancel
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

ReviewModal.propTypes = {
  reviewData: PropTypes.shape({
    request_id: PropTypes.string.isRequired,
    iteration: PropTypes.number.isRequired,
    model_output: PropTypes.string.isRequired,
    reflection_notes: PropTypes.string.isRequired,
    metadata: PropTypes.shape({
      confidence: PropTypes.number,
      quality_score: PropTypes.number,
      improvement_areas: PropTypes.arrayOf(PropTypes.string),
    }),
  }),
  onClose: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  isSubmitting: PropTypes.bool,
};
