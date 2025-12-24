from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes.planning_agent import router as agent_router
from src.routes.utils_endpoints import router as utils_router
from src.routes.health_check import router as health_router
from src.routes.diagram_controller import router as diagram_router
from src.routes.gantt_controller import router as gantt_router
from src.routes.wbs_controller import router as wbs_router

# Create FastAPI app
app = FastAPI(
    title="Reflection Agent API",
    description="API for document-based project planning using Reflection agent pattern (draft→critique→revise cycles)",
    version="2.0.0"
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
app.include_router(diagram_router, tags=["diagrams"])
app.include_router(gantt_router, tags=["gantt"])
app.include_router(wbs_router, tags=["wbs"])


@app.get("/")
async def root():
    return {
        "message": "Reflection Agent API - Iterative draft→critique→revise workflow",
        "docs": "/docs",
        "health": "/health",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)