from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.health_check import router as health_router
from src.routes.planning_agent import router as agent_router
from src.routes.review_resume import router as review_router
from src.routes.utils_endpoints import router as utils_router

# Create FastAPI app
app = FastAPI(
    title="Reflection Agent API",
    description="API for document-based project planning using Reflection agent pattern with Human-in-the-Loop support (draft→review→critique→review→revise cycles)",
    version="2.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent_router, prefix="/api", tags=["agent"])
app.include_router(utils_router, prefix="/api", tags=["utils"])
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(review_router, prefix="/api", tags=["hitl"])


@app.get("/")
async def root():
    return {
        "message": "Reflection Agent API - Iterative draft→critique→revise workflow with HITL support",
        "docs": "/docs",
        "health": "/health",
        "version": "2.1.0",
        "hitl_endpoints": {
            "pending_review": "/api/pending-review/{request_id}",
            "resume_review": "/api/resume-review",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
