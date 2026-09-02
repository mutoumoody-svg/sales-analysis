"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import import_routes, sales_routes, profit_routes, inventory_routes, agent_routes, analysis_routes, export_routes, realtime_routes, trade_daily_routes, operations_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"[{settings.APP_NAME}] Starting...")
    yield
    # Shutdown
    print(f"[{settings.APP_NAME}] Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Business Decision Platform - Sales, Inventory, Profit Analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
_cors_origins = settings.cors_origins_list
_is_wildcard = "*" in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(import_routes.router, prefix=settings.API_V1_PREFIX, tags=["Import"])
app.include_router(sales_routes.router, prefix=settings.API_V1_PREFIX, tags=["Sales"])
app.include_router(profit_routes.router, prefix=settings.API_V1_PREFIX, tags=["Profit"])
app.include_router(inventory_routes.router, prefix=settings.API_V1_PREFIX, tags=["Inventory"])
app.include_router(agent_routes.router, prefix=settings.API_V1_PREFIX, tags=["AI Agents"])
app.include_router(analysis_routes.router, prefix=settings.API_V1_PREFIX, tags=["Analysis"])
app.include_router(export_routes.router, prefix=settings.API_V1_PREFIX, tags=["Export"])
app.include_router(realtime_routes.router, prefix=settings.API_V1_PREFIX, tags=["Realtime"])
app.include_router(trade_daily_routes.router, prefix=settings.API_V1_PREFIX, tags=["ShopDaily"])
app.include_router(operations_routes.router, prefix=settings.API_V1_PREFIX, tags=["Operations"])


@app.get("/")
def root():
    """Health check."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
