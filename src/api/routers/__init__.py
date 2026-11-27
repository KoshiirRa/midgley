"""FastAPI APIRouter sub-modules for Midgley REST gateway (Issue #562)."""

from src.api.routers.locations import router as locations_router
from src.api.routers.tax import router as tax_router

__all__ = ["locations_router", "tax_router"]
