"""
Credit Engine 2.0 - FastAPI Application

Main entry point for the Credit Engine 2.0 backend.

Architecture:
- RawReport → Parser → NormalizedReport (SSOT #1)
- NormalizedReport → AuditEngine → AuditResult (SSOT #2)
- AuditResult → StrategySelector → LetterPlan (SSOT #3)
- LetterPlan → Renderer → DisputeLetter (SSOT #4)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import reports_router, letters_router, auth_router
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield

# Create FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="Credit Engine 2.0",
    description="""
    Credit Engine 2.0 - Dispute Letter Generation System

    This system parses credit reports, detects Metro-2 compliance violations,
    and generates dispute letters using a Single Source of Truth (SSOT) architecture.

    ## Pipeline
    1. **Parsing Layer**: Upload HTML → NormalizedReport (SSOT #1)
    2. **Audit Engine**: NormalizedReport → AuditResult (SSOT #2)
    3. **Strategy Selector**: AuditResult → LetterPlan (SSOT #3)
    4. **Renderer**: LetterPlan → DisputeLetter (SSOT #4)

    ## Key Principles
    - Each SSOT is immutable once created
    - Downstream modules cannot re-audit or recompute
    - Furnisher classification is set once during parsing
    - Violations are detected deterministically (no LLMs)
    - Letter variation uses phrasebanks, not templates
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(letters_router)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Credit Engine 2.0",
        "version": "2.0.0",
        "description": "Dispute Letter Generation System",
        "docs": "/docs",
        "architecture": {
            "ssot_1": "NormalizedReport - Output of Parsing Layer",
            "ssot_2": "AuditResult - Output of Audit Engine",
            "ssot_3": "LetterPlan - Output of Strategy Selector",
            "ssot_4": "DisputeLetter - Output of Renderer"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


# For running with: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
