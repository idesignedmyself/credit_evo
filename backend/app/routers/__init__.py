"""Credit Engine 2.0 - API Routers"""
from .reports import router as reports_router
from .letters import router as letters_router
from .auth import router as auth_router
from .disputes import router as disputes_router
from .scheduler import router as scheduler_router
from .copilot import router as copilot_router
from .outcomes import router as outcomes_router
from .admin import router as admin_router
from .cfpb import router as cfpb_router

__all__ = [
    "reports_router",
    "letters_router",
    "auth_router",
    "disputes_router",
    "scheduler_router",
    "copilot_router",
    "outcomes_router",
    "admin_router",
    "cfpb_router",
]
