"""Claude (Anthropic) LLM provider with native tool calling."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from config import settings
from core.exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMContentFilterError,
)
from core.retry import llm_retry
from llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Claude (Anthropic) LLM provider with native tool calling."""

    def __init__(self, model: str | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or settings.ANTHROPIC_MODEL

    @llm_retry
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Generate completion via Claude Messages API with tool use."""
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": messages,
                "temperature": 0.9,
            }
            if tools:
                kwargs["tools"] = [{"type": "custom", **t} for t in tools]
                kwargs["tool_choice"] = {"type": "auto"}

            response = await self.client.messages.create(**kwargs)

            message_text = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    message_text += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            return LLMResponse(
                message=message_text,
                tool_calls=tool_calls,
                raw_response=response,
            )
        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(f"Claude request timed out: {e}") from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(f"Claude rate limit: {e}") from e
        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(f"Claude auth error: {e}") from e
        except anthropic.BadRequestError as e:
            raise LLMContentFilterError(f"Claude bad request: {e}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Claude API error: {e}") from e

    @llm_retry
    async def complete_with_tool_result(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_use_id: str,
        tool_result: dict,
    ) -> LLMResponse:
        """Submit tool result to Claude and get interpretation."""
        # Build messages with tool use + tool result appended
        augmented_messages = list(messages)

        # The last assistant message should contain the tool_use block
        # Append the tool result as a user message
        augmented_messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(tool_result),
                }
            ],
        })

        return await self.complete(system_prompt, augmented_messages)

    async def complete_stream(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Stream text chunks from Claude."""
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                temperature=0.9,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIStatusError as e:
            logger.error(f"Claude streaming error: {e}", exc_info=True)
            raise LLMError(f"Claude streaming error: {e}") from e
