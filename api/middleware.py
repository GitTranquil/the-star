"""Middleware for CORS, auth, request ID injection, and error handling."""

import uuid
import logging
from typing import Annotated

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

from config import settings
from core.exceptions import TarotAgentError, AuthenticationError
from core.logging import request_id_var, user_id_var

logger = logging.getLogger(__name__)


async def inject_request_id(request: Request, call_next):
    """Middleware to inject a unique request ID into each request."""
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


async def handle_errors(request: Request, call_next):
    """Middleware to catch TarotAgentError and return structured JSON responses."""
    try:
        return await call_next(request)
    except TarotAgentError as e:
        logger.error(f"{type(e).__name__}: {e.message}", exc_info=True)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": type(e).__name__, "message": e.message},
        )
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "InternalError", "message": "An unexpected error occurred"},
        )


async def get_current_user(request: Request) -> str:
    """
    FastAPI dependency that validates Supabase JWT and returns user_id.

    Extracts the Bearer token from the Authorization header,
    decodes the Supabase JWT, and returns the user's UUID.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_ANON_KEY,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token: missing subject")
        user_id_var.set(user_id)
        return user_id
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}") from e


CurrentUser = Annotated[str, Depends(get_current_user)]
