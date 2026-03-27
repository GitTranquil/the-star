"""FastAPI application entry point for Tarot Agent."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.logging import setup_logging
from api.endpoints import router
from api.middleware import inject_request_id, handle_errors

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_logging()

    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
        except ImportError:
            logger.warning("sentry-sdk not installed, skipping Sentry init")

    logger.info("Tarot Agent starting up")
    yield
    logger.info("Tarot Agent shutting down")


app = FastAPI(
    title="Tarot Agent",
    description="AI-powered tarot reading API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.middleware("http")(handle_errors)
app.middleware("http")(inject_request_id)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)
