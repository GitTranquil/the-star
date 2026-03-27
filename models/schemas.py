"""Request/response Pydantic models for API endpoints."""

from typing import Literal

from pydantic import BaseModel


class CreateReadingRequest(BaseModel):
    """Request to start a new reading."""

    mode: Literal["traditional", "intuitive", "custom"] = "intuitive"
    spread_preference: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message in an active reading."""

    message: str


class UpdateProfileRequest(BaseModel):
    """Request to update user profile settings."""

    display_name: str | None = None
    preferred_mode: Literal["traditional", "intuitive", "custom"] | None = None
    preferred_spread: str | None = None
    reversal_preference: Literal["enabled", "disabled", "default"] | None = None
