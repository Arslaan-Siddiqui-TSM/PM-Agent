import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import "./Reviewer.css";

/**
 * Reviewer Component
 *
 * Displays a pending review from the HITL interrupt and allows the reviewer
 * to approve or provide feedback.
 */
function Reviewer() {
  const { id: requestId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [editedText, setEditedText] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const [reviewerId, setReviewerId] = useState("");
  const [tags, setTags] = useState("");

  // Fetch pending review data on mount
  useEffect(() => {
    fetchPendingReview();
  }, [requestId]);

  const fetchPendingReview = async () => {
    try {
      setLoading(true);

      const response = await fetch(`/api/pending-review/${requestId}`);

      if (!response.ok) {
        if (response.status === 404) {
          toast.error(
            "Pending review not found. It may have already been processed."
          );
        } else {
          toast.error(`Failed to fetch review: ${response.statusText}`);
        }
        setLoading(false);
        return;
      }

      const data = await response.json();
      setReviewData(data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching pending review:", error);
      toast.error(`Error: ${error.message}`);
      setLoading(false);
    }
  };

  const handleSubmit = async (action) => {
    if (!reviewData) {
      toast.error("No review data loaded");
      return;
    }

    // Validate inputs
    if (action === "feedback" && !feedbackText.trim() && !editedText.trim()) {
      toast.warning("Please provide either feedback text or edited text");
      return;
    }

    setSubmitting(true);

    try {
      // Parse tags (comma-separated)
      const tagsList = tags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      // Build payload
      const payload = {
        request_id: requestId,
        action: action,
        feedback_text: feedbackText.trim() || null,
        edited_text: editedText.trim() || null,
        tags: tagsList.length > 0 ? tagsList : null,
        reviewer_id: reviewerId.trim() || null,
      };

      // Get HITL secret from environment or use default for local dev
      const hitlSecret = import.meta.env.VITE_HITL_SECRET || "changeme";

      const response = await fetch("/api/resume-review", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${hitlSecret}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();

      // DEBUG: Log the response to see what backend is returning
      console.log("📊 Backend response:", result);
      console.log("  - interrupted_again:", result.interrupted_again);
      console.log("  - new_request_id:", result.new_request_id);
      console.log("  - completed:", result.completed);

      // Show different messages based on action and result
      if (action === "approve") {
        toast.success("✅ Plan approved successfully!");
        // Redirect after short delay
        setTimeout(() => {
          navigate("/");
        }, 2000);
      } else {
        // For feedback action, check if graph interrupted again
        if (result.interrupted_again && result.new_request_id) {
          // Graph created a new interrupt for iteration 2
          toast.success(
            `📝 Feedback incorporated! Redirecting to iteration ${
              result.iteration || "next"
            }...`,
            { autoClose: 2000 }
          );

          // Redirect to the new review page after a short delay
          setTimeout(() => {
            navigate(`/review/${result.new_request_id}`);
          }, 2500);
        } else if (result.completed) {
          // Graph completed (max iterations reached or plan finalized)
          toast.success("✅ Plan finalized! No more iterations needed.", {
            autoClose: 3000,
          });
          setTimeout(() => navigate("/"), 3500);
        } else {
          // Fallback: just show success and redirect
          toast.warning(
            "⚠️ Backend response unclear - check console. Redirecting home...",
            { autoClose: 5000 }
          );
          console.warn("Unexpected backend response format:", result);
          setTimeout(() => navigate("/"), 5000);
        }
      }
    } catch (error) {
      console.error("Error submitting review:", error);
      toast.error(`Failed to submit: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="reviewer-container">
        <div className="loading">Loading review data...</div>
      </div>
    );
  }

  if (!reviewData) {
    return (
      <div className="reviewer-container">
        <div className="error">Review data not found</div>
        <button onClick={() => navigate("/")}>Go Back</button>
      </div>
    );
  }

  return (
    <div className="reviewer-container">
      <div className="reviewer-header">
        <h1>Human Review Required</h1>
        <div className="review-metadata">
          <span>
            <strong>Request ID:</strong> {reviewData.request_id}
          </span>
          <span>
            <strong>Iteration:</strong> {reviewData.iteration}
          </span>
          <span>
            <strong>Confidence:</strong>{" "}
            {(reviewData.metadata?.confidence * 100).toFixed(0)}%
          </span>
          {reviewData.metadata?.quality_score && (
            <span>
              <strong>Quality Score:</strong>{" "}
              {reviewData.metadata.quality_score.toFixed(1)}/10
            </span>
          )}
        </div>
      </div>

      <div className="review-content">
        {/* Model Output Section */}
        <section className="review-section">
          <h2>Model Output</h2>
          <div className="output-box readonly">
            <pre>{reviewData.model_output}</pre>
          </div>
        </section>

        {/* Reflection Notes Section */}
        <section className="review-section">
          <h2>Reflection Notes</h2>
          <div className="notes-box readonly">
            <pre>{reviewData.reflection_notes}</pre>
          </div>
        </section>

        {/* Optional: Show improvement areas if available */}
        {reviewData.metadata?.improvement_areas?.length > 0 && (
          <section className="review-section">
            <h2>Identified Improvement Areas</h2>
            <ul className="improvement-areas">
              {reviewData.metadata.improvement_areas.map((area, idx) => (
                <li key={idx}>{area}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Edited Text Section */}
        <section className="review-section">
          <h2>Edited Text (Optional)</h2>
          <p className="field-hint">
            If you want to directly edit the model output, paste it here.
            Otherwise, leave blank and use feedback text below.
          </p>
          <textarea
            className="edited-text-area"
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            placeholder="Paste edited version of the plan here (optional)..."
            rows={10}
            disabled={submitting}
          />
        </section>

        {/* Feedback Text Section */}
        <section className="review-section">
          <h2>Feedback Text</h2>
          <p className="field-hint">
            Provide feedback for the model to incorporate in the next iteration.
          </p>
          <textarea
            className="feedback-text-area"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="E.g., 'Make it shorter; add AWS infrastructure bullets; improve timeline clarity...'"
            rows={5}
            disabled={submitting}
          />
        </section>

        {/* Reviewer Metadata */}
        <section className="review-section metadata-section">
          <div className="form-row">
            <div className="form-field">
              <label htmlFor="reviewer-id">Reviewer ID (Optional)</label>
              <input
                id="reviewer-id"
                type="text"
                value={reviewerId}
                onChange={(e) => setReviewerId(e.target.value)}
                placeholder="alice@example.com"
                disabled={submitting}
              />
            </div>
            <div className="form-field">
              <label htmlFor="tags">Tags (Optional, comma-separated)</label>
              <input
                id="tags"
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="tone:concise, infra:aws"
                disabled={submitting}
              />
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <section className="review-actions">
          <button
            className="btn btn-approve"
            onClick={() => handleSubmit("approve")}
            disabled={submitting}
          >
            {submitting ? "Submitting..." : "✅ Approve"}
          </button>
          <button
            className="btn btn-feedback"
            onClick={() => handleSubmit("feedback")}
            disabled={submitting}
          >
            {submitting ? "Submitting..." : "📝 Request Changes"}
          </button>
          <button
            className="btn btn-cancel"
            onClick={() => navigate("/")}
            disabled={submitting}
          >
            Cancel
          </button>
        </section>
      </div>
    </div>
  );
}

export default Reviewer;
