"""Pydantic models for reading state and responses."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from models.card_schemas import DrawnCard, DeckState


class ReadingState(BaseModel):
    """Current phase of a reading for frontend state management."""

    phase: Literal[
        "gathering", "drawing", "revealing", "interpreting", "reflecting", "closing"
    ]
    reveal_card_index: int | None = None


class ReadingMessageRequest(BaseModel):
    """Internal request model for processing a reading message."""

    message: str
    conversation_history: list[dict]
    reading_id: UUID | None = None
    mode: str = "intuitive"
    spread_preference: str | None = None


class ReadingResponse(BaseModel):
    """Response from a reading flow processing step."""

    message: str
    cards: list[DrawnCard] | None = None
    reading_state: ReadingState
    deck_state: DeckState | None = None
    metadata: dict | None = None
