"""Abstract LLM provider with tool calling support."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM completion."""

    message: str
    tool_calls: list[dict] = field(default_factory=list)
    raw_response: Any = None


class LLMProvider(ABC):
    """Abstract LLM provider with tool calling support."""

    TOOLS = [
        {
            "name": "drawCards",
            "description": "Draw tarot cards for the reading. Call this when the moment is right to reveal cards.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "spread_type": {
                        "type": "string",
                        "description": "The spread to use (e.g., 'three_card', 'celtic_cross')",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of cards to draw (must match spread's card_count)",
                    },
                },
                "required": ["spread_type", "count"],
            },
        },
        {
            "name": "setReadingState",
            "description": "Update the reading UI state for the frontend.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "enum": [
                            "gathering",
                            "drawing",
                            "revealing",
                            "interpreting",
                            "reflecting",
                            "closing",
                        ],
                    },
                    "reveal_card_index": {
                        "type": "integer",
                        "description": "Index of the next card to reveal (for sequential reveal animation)",
                    },
                },
                "required": ["phase"],
            },
        },
    ]

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Generate a completion with optional tool calling."""

    @abstractmethod
    async def complete_stream(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Generate a streaming completion (no tool calling)."""

    @abstractmethod
    async def complete_with_tool_result(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_use_id: str,
        tool_result: dict,
    ) -> LLMResponse:
        """Submit tool result and get final response."""
