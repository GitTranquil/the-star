"""Pydantic models for cards, spreads, and deck state."""

from typing import Literal

from pydantic import BaseModel


class TarotCard(BaseModel):
    """A single tarot card with its metadata."""

    id: int
    name: str
    arcana: Literal["major", "minor"]
    suit: Literal["wands", "cups", "swords", "pentacles"] | None = None
    number: int
    keywords_upright: list[str]
    keywords_reversed: list[str]
    element: str | None = None
    planet_or_sign: str | None = None


class DrawnCard(BaseModel):
    """A card drawn into a specific spread position."""

    card: TarotCard
    position_index: int
    position_name: str
    is_reversed: bool


class DeckState(BaseModel):
    """Tracks deck state within a reading to prevent duplicate draws."""

    remaining_card_ids: list[int]
    drawn_card_ids: list[int]
    shuffle_seed: int | None = None


class SpreadPosition(BaseModel):
    """A single position within a spread."""

    index: int
    name: str
    meaning: str
    interpretation_prompt: str


class SpreadLayoutPosition(BaseModel):
    """X/Y coordinates for rendering a card position."""

    x: float
    y: float
    rotation: float | None = None


class SpreadLayout(BaseModel):
    """Layout metadata for frontend rendering."""

    type: str
    positions: list[SpreadLayoutPosition]


class SpreadDefinition(BaseModel):
    """A complete spread definition with positions and layout."""

    id: str
    name: str
    card_count: int
    description: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    positions: list[SpreadPosition]
    layout: SpreadLayout
