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
 * Start feasibility assessment with HITL support (NEW)
 * @param {string} sessionId - Current session ID
 * @param {Object} developmentContext - Development process answers
 * @returns {Promise<{status: string, iteration: number, feasibility_report: string, message: string}>}
 */
export const startFeasibility = async (sessionId, developmentContext) => {
  const response = await fetch(`${API_BASE_URL}/feasibility/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      development_context: developmentContext,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(
      errorData.detail || "Failed to start feasibility assessment"
    );
  }

  return await response.json();
};

/**
 * Submit human review decision for feasibility report (NEW)
 * @param {string} sessionId - Current session ID
 * @param {boolean} approved - True to approve, false to request changes
 * @param {string} feedback - Required when approved=false. Feedback for revision.
 * @returns {Promise<{status: string, iteration: number, feasibility_report: string, message: string}>}
 */
export const reviewFeasibility = async (
  sessionId,
  approved,
  feedback = null
) => {
  const response = await fetch(`${API_BASE_URL}/feasibility/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      approved: approved,
      feedback: feedback,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to submit review");
  }

  return await response.json();
};

/**
 * Get current status of feasibility assessment workflow (NEW)
 * @param {string} sessionId - Current session ID
 * @returns {Promise<{status: string, iteration: number, feasibility_report: string, critique: string}>}
 */
export const getFeasibilityStatus = async (sessionId) => {
  const response = await fetch(
    `${API_BASE_URL}/feasibility/status/${sessionId}`,
    {
      method: "GET",
    }
  );

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to get feasibility status");
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
 * Generate final project plan
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
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Plan generation failed");
  }

  return await response.json();
};
