import { useState, useCallback } from "react";
import { WORKFLOW_STEPS, REVIEW_TYPES } from "../constants";
import {
  uploadFiles,
  checkFeasibility,
  fetchFileContent,
  generatePlan,
  generatePlanWithHITL,
  getPendingReview,
  submitReview,
} from "../services";

const INITIAL_DEV_PROCESS_ANSWERS = {
  methodology: "",
  teamSize: "",
  timeline: "",
  budget: "",
  techStack: "",
  constraints: "",
};

export const useProjectWorkflow = () => {
  const [step, setStep] = useState(WORKFLOW_STEPS.UPLOAD);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Step 2: Development process data
  const [devProcessAnswers, setDevProcessAnswers] = useState(
    INITIAL_DEV_PROCESS_ANSWERS
  );

  // Step 3/4: Feasibility data
  const [feasibilityReport, setFeasibilityReport] = useState("");
  const [feasibilityFilePath, setFeasibilityFilePath] = useState("");
  const [developmentContextJsonPath, setDevelopmentContextJsonPath] =
    useState("");

  // Step 5: Plan data
  const [finalPlan, setFinalPlan] = useState("");
  const [planFilePath, setPlanFilePath] = useState("");

  // HITL-specific state
  const [enableHITL, setEnableHITL] = useState(false);
  const [hitlReviewData, setHitlReviewData] = useState(null);
  const [hitlRequestId, setHitlRequestId] = useState(null);
  const [hitlThreadId, setHitlThreadId] = useState(null);
  const [hitlReviewType, setHitlReviewType] = useState(null);
  const [hitlIteration, setHitlIteration] = useState(1);

  /**
   * Handle file upload
   */
  const handleUpload = async (files, useDefaultFiles) => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const data = await uploadFiles(files, useDefaultFiles);
      setSessionId(data.session_id);
      setSuccessMessage("Files uploaded successfully!");
      setStep(WORKFLOW_STEPS.DEVELOPMENT_PROCESS);
      return { uploadedFiles: data.uploaded_files };
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle development process form submission
   */
  const handleDevelopmentProcessSubmit = (answers) => {
    setDevProcessAnswers(answers);
    setError(null);
    setStep(WORKFLOW_STEPS.FEASIBILITY);
  };

  /**
   * Handle feasibility check
   */
  const handleCheckFeasibility = async () => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const data = await checkFeasibility(sessionId, devProcessAnswers);

      // Store file paths
      if (data.file_path) {
        setFeasibilityFilePath(data.file_path);
      }
      if (data.development_context_json_path) {
        setDevelopmentContextJsonPath(data.development_context_json_path);
      }

      // Fetch the feasibility report content
      if (data.file_path) {
        try {
          const content = await fetchFileContent(data.file_path);
          setFeasibilityReport(content);
        } catch (err) {
          console.error("Error fetching file content:", err);
          setFeasibilityReport(
            "Feasibility assessment generated successfully. Review the assessment before proceeding."
          );
        }
      }

      setSuccessMessage("Feasibility assessment generated successfully!");
      setStep(WORKFLOW_STEPS.REVIEW);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle plan generation (standard mode without HITL)
   */
  const handleGeneratePlan = async () => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const data = await generatePlan(sessionId);
      setFinalPlan(data.result);
      setPlanFilePath(data.file_path);
      setSuccessMessage("Project plan generated successfully!");
      setStep(WORKFLOW_STEPS.PLAN);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle plan generation with HITL mode
   */
  const handleGeneratePlanWithHITL = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const data = await generatePlanWithHITL(sessionId);

      if (data.status === "pending_review") {
        // HITL mode: plan generation paused for human review
        setHitlRequestId(data.request_id);
        setHitlThreadId(data.thread_id);
        setHitlReviewType(data.review_type);
        setHitlIteration(1);

        // Fetch the pending review data
        const reviewData = await getPendingReview(data.request_id);
        setHitlReviewData(reviewData);

        // Navigate to appropriate HITL step
        if (data.review_type === REVIEW_TYPES.DRAFT) {
          setStep(WORKFLOW_STEPS.HITL_DRAFT_REVIEW);
        } else if (data.review_type === REVIEW_TYPES.REFLECTION) {
          setStep(WORKFLOW_STEPS.HITL_REFLECTION_REVIEW);
        }

        setSuccessMessage("Draft generated! Please review before continuing.");
      } else if (data.status === "completed") {
        // Plan completed without any interrupts (shouldn't happen in HITL mode)
        setFinalPlan(data.result);
        setPlanFilePath(data.file_path);
        setSuccessMessage("Project plan generated successfully!");
        setStep(WORKFLOW_STEPS.PLAN);
      } else {
        throw new Error(`Unexpected status: ${data.status}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  /**
   * Handle HITL review submission
   */
  const handleSubmitReview = useCallback(
    async (payload) => {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);

      try {
        const result = await submitReview({
          ...payload,
          request_id: hitlRequestId,
        });

        if (result.status === "success") {
          // Check if the workflow was terminated
          if (payload.action === "terminate") {
            // Workflow ended - fetch final plan if available
            if (result.final_plan) {
              setFinalPlan(result.final_plan);
              setPlanFilePath(result.file_path || "");
            } else {
              // Use the current draft as the final plan
              setFinalPlan(hitlReviewData?.draft || "Plan finalized by user.");
            }
            setSuccessMessage("Workflow finalized successfully!");
            setStep(WORKFLOW_STEPS.PLAN);
            resetHITLState();
            return;
          }

          // Check if there's another interrupt (new review needed)
          if (result.interrupted_again && result.new_request_id) {
            // Fetch new pending review
            const newReviewData = await getPendingReview(result.new_request_id);
            setHitlReviewData(newReviewData);
            setHitlRequestId(result.new_request_id);
            setHitlReviewType(newReviewData.type);
            setHitlIteration(newReviewData.iteration || hitlIteration + 1);

            // Navigate to appropriate step
            if (newReviewData.type === REVIEW_TYPES.DRAFT) {
              setStep(WORKFLOW_STEPS.HITL_DRAFT_REVIEW);
              setSuccessMessage("Revision complete! Review the new draft.");
            } else if (newReviewData.type === REVIEW_TYPES.REFLECTION) {
              setStep(WORKFLOW_STEPS.HITL_REFLECTION_REVIEW);
              setSuccessMessage(
                "Review submitted! Now review the AI critique."
              );
            }
          } else if (result.final_plan || result.result) {
            // Workflow completed
            setFinalPlan(result.final_plan || result.result);
            setPlanFilePath(result.file_path || "");
            setSuccessMessage("Project plan generated successfully!");
            setStep(WORKFLOW_STEPS.PLAN);
            resetHITLState();
          } else {
            // Continue processing - check for more interrupts
            // This handles the case where the review was accepted but we need to poll for next state
            setSuccessMessage("Review submitted! Processing...");

            // If we were in draft review, we should expect reflection review next
            if (hitlReviewType === REVIEW_TYPES.DRAFT) {
              // Wait briefly and check if there's a new pending review
              await new Promise((resolve) => setTimeout(resolve, 1500));

              // Try to get the thread state or wait for callback
              if (result.new_request_id) {
                const newReviewData = await getPendingReview(
                  result.new_request_id
                );
                setHitlReviewData(newReviewData);
                setHitlRequestId(result.new_request_id);
                setHitlReviewType(newReviewData.type);
                setStep(WORKFLOW_STEPS.HITL_REFLECTION_REVIEW);
              }
            }
          }
        } else {
          throw new Error(result.message || "Review submission failed");
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [hitlRequestId, hitlReviewData, hitlReviewType, hitlIteration]
  );

  /**
   * Reset HITL-specific state
   */
  const resetHITLState = () => {
    setHitlReviewData(null);
    setHitlRequestId(null);
    setHitlThreadId(null);
    setHitlReviewType(null);
    setHitlIteration(1);
  };

  /**
   * Reset the entire workflow
   */
  const handleReset = () => {
    setStep(WORKFLOW_STEPS.UPLOAD);
    setSessionId(null);
    setDevProcessAnswers(INITIAL_DEV_PROCESS_ANSWERS);
    setFeasibilityReport("");
    setFeasibilityFilePath("");
    setDevelopmentContextJsonPath("");
    setFinalPlan("");
    setPlanFilePath("");
    setError(null);
    setEnableHITL(false);
    resetHITLState();
  };

  /**
   * Toggle HITL mode
   */
  const toggleHITL = useCallback((enabled) => {
    setEnableHITL(enabled);
  }, []);

  return {
    // State
    step,
    sessionId,
    loading,
    error,
    successMessage,
    devProcessAnswers,
    feasibilityReport,
    feasibilityFilePath,
    developmentContextJsonPath,
    finalPlan,
    planFilePath,
    // HITL state
    enableHITL,
    hitlReviewData,
    hitlRequestId,
    hitlThreadId,
    hitlReviewType,
    hitlIteration,

    // Actions
    handleUpload,
    handleDevelopmentProcessSubmit,
    handleCheckFeasibility,
    handleGeneratePlan,
    handleGeneratePlanWithHITL,
    handleSubmitReview,
    handleReset,
    setError,
    setSuccessMessage,
    toggleHITL,
  };
};
