import { useState } from "react";
import { WORKFLOW_STEPS } from "../constants";
import {
  uploadFiles,
  checkFeasibility,
  fetchFileContent,
  generatePlan,
  generatePlanWithHitl,
  getPendingPlanReview,
  resumePlanReview,
  reviseFeasibility,
  getRevisionHistory,
  getCurrentFeasibilityVersion,
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
  const [feasibilityVersion, setFeasibilityVersion] = useState(1);
  const [revisionHistory, setRevisionHistory] = useState([]);

  // Plan data
  const [finalPlan, setFinalPlan] = useState("");
  const [planFilePath, setPlanFilePath] = useState("");

  // HITL revision state for interrupt/resume flow
  const [hitlStatus, setHitlStatus] = useState("idle"); // idle | awaiting-feedback | completed
  const [hitlResumeConfig, setHitlResumeConfig] = useState(null); // resume_config from backend

  // Plan HITL state
  const [enablePlanHitl, setEnablePlanHitl] = useState(false);
  const [planHitlRequestId, setPlanHitlRequestId] = useState(null);
  const [planHitlReviewType, setPlanHitlReviewType] = useState(null);
  const [planHitlThreadId, setPlanHitlThreadId] = useState(null);
  const [planHitlIteration, setPlanHitlIteration] = useState(1);
  const [planHitlPendingData, setPlanHitlPendingData] = useState(null);

  const resetRevisionState = () => {
    setHitlStatus("idle");
    setHitlResumeConfig(null);
  };

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
   * Handle plan generation (standard mode)
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
   * Handle plan generation with HITL enabled
   */
  const handleGeneratePlanWithHitl = async () => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const data = await generatePlanWithHitl(sessionId);

      if (data.status === "pending_review") {
        // HITL interrupt: fetch pending review data and show review step
        setPlanHitlRequestId(data.request_id);
        setPlanHitlReviewType(data.review_type);
        setPlanHitlThreadId(data.thread_id);
        setPlanHitlIteration(data.iteration || 1);

        // Fetch the pending review content
        try {
          const reviewData = await getPendingPlanReview(data.request_id);
          setPlanHitlPendingData(reviewData);
          setSuccessMessage(
            `Plan draft ready for review (${data.review_type})`
          );
          setStep(WORKFLOW_STEPS.PLAN_HITL_REVIEW);
        } catch (err) {
          console.error("Failed to fetch pending review:", err);
          setError("Failed to load review data");
        }
      } else if (data.status === "completed") {
        // Plan generation completed without interrupts
        setFinalPlan(data.result);
        setPlanFilePath(data.file_path);
        setSuccessMessage("Project plan generated successfully!");
        setStep(WORKFLOW_STEPS.PLAN);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle plan review submission (approve, feedback, or terminate)
   */
  const handleSubmitPlanReview = async (
    action,
    feedback,
    editedText,
    reviewerId
  ) => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        request_id: planHitlRequestId,
        action: action,
        feedback_text: feedback || null,
        edited_text: editedText || null,
        reviewer_id: reviewerId || null,
      };

      const data = await resumePlanReview(payload);

      console.log("📊 handleSubmitPlanReview: Backend response:", {
        status: data.status,
        interrupted_again: data.interrupted_again,
        new_request_id: data.new_request_id,
        completed: data.completed,
        action: data.action,
      });

      // Check if graph interrupted again (e.g., moving to reflection review)
      if (data.interrupted_again && data.new_request_id) {
        // Another interrupt (reflection review or continued iteration)
        const newRequestId = data.new_request_id;
        const reviewType = data.review_type;
        const iteration = data.iteration || planHitlIteration + 1;

        setPlanHitlRequestId(newRequestId);
        setPlanHitlReviewType(reviewType);
        setPlanHitlIteration(iteration);

        // Fetch updated pending review data
        try {
          const reviewData = await getPendingPlanReview(newRequestId);
          setPlanHitlPendingData(reviewData);
          setSuccessMessage(
            `Proceeding to ${reviewType} (iteration ${iteration})`
          );
          console.log(
            "✅ New review data loaded successfully:",
            newRequestId,
            reviewType
          );
          // Stay on PLAN_HITL_REVIEW step with new data
        } catch (err) {
          console.error("Failed to fetch next review:", err);
          setError("Failed to load next review data");
        } finally {
          setLoading(false);
        }
      } else if (data.completed || data.has_final_plan) {
        // Plan generation completed
        setFinalPlan(data.final_plan || "Plan finalized");
        setPlanFilePath(data.file_path);
        setSuccessMessage(
          "Project plan finalized successfully after HITL review!"
        );

        // Reset HITL state
        setPlanHitlRequestId(null);
        setPlanHitlReviewType(null);
        setPlanHitlThreadId(null);
        setPlanHitlIteration(1);
        setPlanHitlPendingData(null);

        setStep(WORKFLOW_STEPS.PLAN);
        setLoading(false);
      } else {
        // Fallback: treat as success but log for debugging
        console.warn("Unexpected response format from resume-review:", data);
        setSuccessMessage("Review submitted successfully");
        setLoading(false);
      }
    } catch (err) {
      setError(err.message);
      console.error("Review submission failed:", err);
      setLoading(false);
    }
  };

  /**
   * Refresh revision history from backend
   */
  const handleRefreshRevisionHistory = async () => {
    if (!sessionId) return;
    try {
      const history = await getRevisionHistory(sessionId);
      setRevisionHistory(history.revisions || []);
    } catch (err) {
      console.error("Failed to load revision history", err);
    }
  };

  /**
   * Fetch arbitrary revision content by file path
   */
  const handleFetchRevisionContent = async (filePath) => {
    try {
      return await fetchFileContent(filePath);
    } catch (err) {
      setError(err.message);
      return "";
    }
  };

  /**
   * Sync current feasibility version from backend (optional)
   */
  const handleSyncCurrentVersion = async () => {
    if (!sessionId) return;
    try {
      const data = await getCurrentFeasibilityVersion(sessionId);
      if (data.current_version) {
        setFeasibilityVersion(data.current_version);
      }
    } catch (err) {
      console.error("Failed to sync current version", err);
    }
  };

  /**
   * Request or resume a feasibility revision (interrupt-friendly)
   */
  const handleRequestRevision = async (humanCritique, revisionInstructions) => {
    if (!sessionId) {
      setError("No active session. Please complete previous steps first.");
      return;
    }

    const isResume = !!hitlResumeConfig;
    const critiqueValue = humanCritique && humanCritique.trim();
    if (isResume && !critiqueValue) {
      setError("Human critique is required to resume.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const previousVersion = feasibilityVersion;
      const params = {
        sessionId,
        currentVersion: feasibilityVersion,
      };

      if (isResume) {
        params.humanCritique = critiqueValue;
      }

      if (revisionInstructions && revisionInstructions.trim()) {
        params.revisionInstructions = revisionInstructions.trim();
      }

      const data = await reviseFeasibility(params);

      if (data && data.status === "interrupt") {
        setHitlResumeConfig(data.resume_config || null);
        setHitlStatus("awaiting-feedback");
        setSuccessMessage("Awaiting human critique to resume revision.");
        return;
      }

      if (typeof data.new_version === "number") {
        setFeasibilityVersion(data.new_version);
      }
      if (data.file_path) {
        setFeasibilityFilePath(data.file_path);
        try {
          const content = await fetchFileContent(data.file_path);
          setFeasibilityReport(content);
        } catch (err) {
          console.error("Error fetching revised report", err);
        }
      }

      await handleRefreshRevisionHistory();
      setHitlStatus("completed");
      setHitlResumeConfig(null);
      setSuccessMessage(
        `Feasibility report revised successfully (v${previousVersion} → v${data.new_version}).`
      );
    } catch (err) {
      console.error("Revision request failed:", err);
      setError(err.message || "Failed to request revision");
    } finally {
      setLoading(false);
    }
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
    setFeasibilityVersion(1);
    setRevisionHistory([]);
    setFinalPlan("");
    setPlanFilePath("");
    setError(null);
    resetRevisionState();
  };

  return {
    // State
    step,
    setStep,
    sessionId,
    loading,
    error,
    successMessage,
    devProcessAnswers,
    feasibilityReport,
    feasibilityFilePath,
    developmentContextJsonPath,
    feasibilityVersion,
    revisionHistory,
    hitlStatus,
    hitlResumeConfig,
    finalPlan,
    planFilePath,
    // Plan HITL state
    enablePlanHitl,
    planHitlRequestId,
    planHitlReviewType,
    planHitlIteration,
    planHitlPendingData,

    // Actions
    handleUpload,
    handleDevelopmentProcessSubmit,
    handleCheckFeasibility,
    handleGeneratePlan,
    handleGeneratePlanWithHitl,
    handleSubmitPlanReview,
    handleRequestRevision,
    handleRefreshRevisionHistory,
    handleFetchRevisionContent,
    handleSyncCurrentVersion,
    handleReset,
    setEnablePlanHitl,
    setError,
    setSuccessMessage,
  };
};
