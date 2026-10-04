"""
CreditPath FastAPI Application Entrypoint (B13).

Integrates all customer and administrative routers, establishes SQLite database
lifecycle, sets up permissive CORS for frontend interaction, and loads estimators at startup.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.customer import router as customer_router
from app.config import get_config
from app.database import init_db
from app.ml.model_store import get_data_as_of, get_model_version, load_model
from app.schemas import HealthResponse, Meta


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    # 1. Initialize SQLite database schemas
    init_db()

    # 2. Verify and load trained models into memory / state
    forecaster, _ = load_model("forecaster")
    risk_model, _ = load_model("risk_model")
    app.state.forecaster = forecaster
    app.state.risk_model = risk_model
    app.state.model_loaded = True
    app.state.model_version = get_model_version("forecaster")
    app.state.data_as_of = get_data_as_of()

    yield


app = FastAPI(
    title="CreditPath API",
    version="0.1.0",
    description="CreditPath loan-readiness and repayment-timing coaching API.",
    lifespan=lifespan,
)

# Permissive CORS middleware for local Next.js frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount domain routers
app.include_router(customer_router)
app.include_router(admin_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def get_health() -> HealthResponse:
    """Return API health status, model readiness, version, and data cutoff date."""
    cfg = get_config()
    version = get_model_version("forecaster")
    data_as_of = get_data_as_of()
    meta = Meta(
        model_version=version,
        data_as_of=data_as_of,
        disclaimer=cfg.disclaimer,
    )
    return HealthResponse(
        status="ok",
        model_loaded=getattr(app.state, "model_loaded", True),
        model_version=version,
        data_as_of=data_as_of,
        disclaimer=cfg.disclaimer,
        meta=meta,
    )
