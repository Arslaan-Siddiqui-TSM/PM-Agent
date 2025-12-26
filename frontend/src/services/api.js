import { API_BASE_URL } from "../constants";

/**
 * Upload files or use default files
 * @param {File[]} files - Array of files to upload
 * @param {boolean} useDefaultFiles - Whether to use default sample files
 * @returns {Promise<{session_id: string, uploaded_files: string[]}>}
 */
export const uploadFiles = async (files, useDefaultFiles) => {
  const formData = new FormData();

  if (useDefaultFiles) {
    const response = await fetch(
      `${API_BASE_URL}/upload?use_default_files=true`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return await response.json();
  } else {
    if (files.length === 0) {
      throw new Error("Please select at least one PDF file");
    }

    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return await response.json();
  }
};

/**
 * Check project feasibility
 * @param {string} sessionId - Current session ID
 * @param {Object} developmentContext - Development process answers
 * @returns {Promise<{file_path: string, development_context_json_path: string}>}
 */
export const checkFeasibility = async (sessionId, developmentContext) => {
  const contextWithAnswers = {
    session_id: sessionId,
    use_intelligent_processing: true,
    development_context: developmentContext,
  };

  const response = await fetch(`${API_BASE_URL}/feasibility`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contextWithAnswers),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Feasibility check failed");
  }

  return await response.json();
};

/**
 * Fetch file content from the server
 * @param {string} filePath - Path to the file
 * @returns {Promise<string>}
 */
export const fetchFileContent = async (filePath) => {
  const response = await fetch(
    `${API_BASE_URL}/file-content?file_path=${encodeURIComponent(filePath)}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch file content");
  }

  return await response.text();
};

/**
 * Generate final project plan (standard mode without HITL)
 * @param {string} sessionId - Current session ID
 * @returns {Promise<{result: string, file_path: string}>}
 */
export const generatePlan = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/generate-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      use_intelligent_processing: true,
      max_iterations: 5,
      enable_hitl: false,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Plan generation failed");
  }

  return await response.json();
};

/**
 * Generate project plan with Human-in-the-Loop (HITL) mode
 * @param {string} sessionId - Current session ID
 * @param {number} maxIterations - Maximum reflection iterations
 * @returns {Promise<Object>} - Returns plan data or pending review info
 */
export const generatePlanWithHITL = async (sessionId, maxIterations = 5) => {
  const response = await fetch(`${API_BASE_URL}/generate-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      use_intelligent_processing: true,
      max_iterations: maxIterations,
      enable_hitl: true,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Plan generation failed");
  }

  return await response.json();
};

/**
 * Get pending review data for HITL
 * @param {string} requestId - The review request ID
 * @returns {Promise<Object>} - Pending review data including draft/reflection
 */
export const getPendingReview = async (requestId) => {
  const response = await fetch(`${API_BASE_URL}/pending-review/${requestId}`);

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to fetch pending review");
  }

  return await response.json();
};

/**
 * Submit human review and resume workflow
 * @param {Object} payload - Review submission payload
 * @param {string} payload.request_id - Request ID
 * @param {string} payload.action - 'approve', 'feedback', or 'terminate'
 * @param {string} [payload.feedback_text] - Optional feedback text
 * @param {string} [payload.edited_text] - Optional edited draft/reflection
 * @param {string} [payload.reviewer_id] - Optional reviewer identifier
 * @param {string} authToken - Authorization token (default: 'changeme')
 * @returns {Promise<Object>} - Resume result with status and optional new request_id
 */
export const submitReview = async (payload, authToken = "changeme") => {
  const response = await fetch(`${API_BASE_URL}/resume-review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Review submission failed");
  }

  return await response.json();
};
