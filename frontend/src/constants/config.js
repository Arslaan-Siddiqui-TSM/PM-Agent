export const API_BASE_URL = "http://localhost:8000/api";

export const WORKFLOW_STEPS = {
  UPLOAD: 1,
  DEVELOPMENT_PROCESS: 2,
  FEASIBILITY: 3,
  REVIEW: 4,
  REVISION_MANAGEMENT: 5,
  PROJECT_SPECIFICATION: 6,
  PLAN_HITL_REVIEW: 6.5,
  PLAN: 7,
};

// Review types returned by the API (kept for compatibility with HITL review component)
export const REVIEW_TYPES = {
  DRAFT: "draft_review",
  REFLECTION: "reflection_review",
};

// Review actions (kept for compatibility with HITL review component)
export const REVIEW_ACTIONS = {
  APPROVE: "approve",
  FEEDBACK: "feedback",
  TERMINATE: "terminate",
};
