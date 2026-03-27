"""Structured logging setup for Tarot Agent."""

import logging
import json
import sys
from contextvars import ContextVar

from config import settings

# Context variables for request-scoped data
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
reading_id_var: ContextVar[str | None] = ContextVar("reading_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "reading_id": reading_id_var.get(),
        }
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = str(record.exc_info[1])
            log_data["exception_type"] = type(record.exc_info[1]).__name__
        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_var.get()
        prefix = f"[{req_id[:8]}] " if req_id else ""
        base = f"{record.levelname:<8} {prefix}{record.name}: {record.getMessage()}"
        if record.exc_info and record.exc_info[1]:
            base += f"\n  {type(record.exc_info[1]).__name__}: {record.exc_info[1]}"
        return base


def setup_logging() -> None:
    """Configure logging based on environment."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Clear existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.SENTRY_DSN:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
