export const API_BASE_URL = "http://localhost:8000/api";

export const WORKFLOW_STEPS = {
  UPLOAD: 1,
  DEVELOPMENT_PROCESS: 2,
  FEASIBILITY: 3,
  REVIEW: 4,
  // HITL-specific steps (only used when enable_hitl is true)
  HITL_DRAFT_REVIEW: 5,
  HITL_REFLECTION_REVIEW: 6,
  PLAN: 7,
};

// Review types returned by the API
export const REVIEW_TYPES = {
  DRAFT: "draft_review",
  REFLECTION: "reflection_review",
};

// Review actions
export const REVIEW_ACTIONS = {
  APPROVE: "approve",
  FEEDBACK: "feedback",
  TERMINATE: "terminate",
};
