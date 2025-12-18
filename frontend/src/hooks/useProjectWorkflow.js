import { useState } from "react";
import { WORKFLOW_STEPS } from "../constants";
import {
  uploadFiles,
  checkFeasibility,
  startFeasibility,
  reviewFeasibility,
  getFeasibilityStatus,
  fetchFileContent,
  generatePlan,
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
   * Handle feasibility check with HITL support
   * @param {boolean} useHitl - Whether to use HITL workflow
   * @param {boolean} approved - If in review mode, whether report is approved
   * @param {string} feedback - If requesting changes, the feedback text
   */
  const handleCheckFeasibility = async (
    useHitl = false,
    approved = null,
    feedback = null
  ) => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      let data;

      // HITL Mode - Start new assessment
      if (useHitl && approved === null) {
        data = await startFeasibility(sessionId, devProcessAnswers);

        // Store data globally for component access
        window.__feasibilityData = data;

        setFeasibilityReport(data.feasibility_report || "");
        setSuccessMessage("Feasibility report generated! Please review.");
      }
      // HITL Mode - Submit review decision
      else if (useHitl && approved !== null) {
        data = await reviewFeasibility(sessionId, approved, feedback);

        // Store data globally for component access
        window.__feasibilityData = data;

        if (data.status === "approved") {
          setSuccessMessage("Feasibility report approved!");
          setStep(WORKFLOW_STEPS.REVIEW);
        } else if (data.status === "awaiting_human") {
          setFeasibilityReport(data.feasibility_report || "");
          setSuccessMessage(
            `Revision ${data.iteration} generated! Please review.`
          );
        } else if (data.status === "max_iterations_reached") {
          setFeasibilityReport(data.feasibility_report || "");
          setSuccessMessage("Max iterations reached. Using current report.");
          setTimeout(() => setStep(WORKFLOW_STEPS.REVIEW), 2000);
        }
      }
      // Legacy Mode - Single-pass generation
      else {
        data = await checkFeasibility(sessionId, devProcessAnswers);

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
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle plan generation
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
  };

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

    // Actions
    handleUpload,
    handleDevelopmentProcessSubmit,
    handleCheckFeasibility,
    handleGeneratePlan,
    handleReset,
    setError,
    setSuccessMessage,
  };
};
