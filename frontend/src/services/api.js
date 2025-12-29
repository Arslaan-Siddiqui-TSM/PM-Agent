import { API_BASE_URL } from "../constants";

/**
 * Upload files or use default files
 */
export const uploadFiles = async (files, useDefaultFiles) => {
  const formData = new FormData();

  if (useDefaultFiles) {
    const response = await fetch(
      `${API_BASE_URL}/upload?use_default_files=true`,
      { method: "POST" }
    );
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }
    return await response.json();
  }

  if (!files || files.length === 0) {
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
};

/**
 * Check project feasibility
 */
export const checkFeasibility = async (sessionId, developmentContext) => {
  const payload = {
    session_id: sessionId,
    use_intelligent_processing: true,
    development_context: developmentContext,
  };

  const response = await fetch(`${API_BASE_URL}/feasibility`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Feasibility check failed");
  }

  return await response.json();
};

/**
 * Fetch file content from the server
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
 * Generate final project plan (standard mode)
 */
export const generatePlan = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/generate-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      use_intelligent_processing: true,
      max_iterations: 2,
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
 * Request or resume a feasibility revision (interrupt-aware)
 */
export const reviseFeasibility = async ({
  sessionId,
  currentVersion,
  humanCritique,
  revisionInstructions,
  maxRevisions = 5,
}) => {
  const payload = {
    session_id: sessionId,
    current_version: currentVersion,
    ...(humanCritique !== undefined && humanCritique !== null
      ? { human_critique: humanCritique }
      : {}),
    max_revisions: maxRevisions,
  };

  if (revisionInstructions !== undefined && revisionInstructions !== null) {
    payload.revision_instructions = revisionInstructions;
  }

  const response = await fetch(`${API_BASE_URL}/revise-feasibility`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    console.error("Revision API error:", errorData);
    throw new Error(errorData.detail || "Revision failed");
  }

  return await response.json();
};

/**
 * Get revision history for a session
 */
export const getRevisionHistory = async (sessionId) => {
  const response = await fetch(
    `${API_BASE_URL}/revision-history/${encodeURIComponent(sessionId)}`
  );

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to fetch revision history");
  }

  return await response.json();
};

/**
 * Get current feasibility report version for a session
 */
export const getCurrentFeasibilityVersion = async (sessionId) => {
  const response = await fetch(
    `${API_BASE_URL}/current-feasibility-version/${encodeURIComponent(
      sessionId
    )}`
  );

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to fetch current version");
  }

  return await response.json();
};

/**
 * Generate project plan with HITL enabled
 */
export const generatePlanWithHitl = async (sessionId, maxIterations = 5) => {
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
 * Fetch pending plan review data
 */
export const getPendingPlanReview = async (requestId) => {
  const response = await fetch(
    `${API_BASE_URL}/pending-review/${encodeURIComponent(requestId)}`
  );

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to fetch pending review");
  }

  return await response.json();
};

/**
 * Resume plan review with human feedback
 */
export const resumePlanReview = async (payload) => {
  const hitlSecret = import.meta.env.VITE_HITL_SECRET || "changeme";

  const response = await fetch(`${API_BASE_URL}/resume-review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${hitlSecret}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Resume review failed");
  }

  return await response.json();
};
