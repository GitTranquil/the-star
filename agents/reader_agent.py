"""Reader agent — assembles prompts with personality and delegates to LLM provider."""

import logging
from collections.abc import AsyncIterator
from pathlib import Path

from llm.base import LLMProvider
from llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


class ReaderAgent:
    """
    Assembles prompts with personality + context and delegates to LLM provider.

    Prompt assembly order:
    1. Base personality prompt (from file)
    2. Personalization (name, reading count tier)
    3. Memory context (entities, past readings, patterns)
    4. Knowledge context (card meanings, spread positions)
    """

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or get_llm_provider()
        self._prompt_cache: dict[str, str] = {}

    async def complete(
        self,
        messages: list[dict],
        mode: str = "intuitive",
        personalization: str = "",
        memory_context: str = "",
        knowledge_context: str = "",
        custom_prompt: str | None = None,
    ) -> dict:
        """
        Generate a reading response with tool calling support.

        Returns:
            Dict with message, tool_calls, and raw_message keys
        """
        system_prompt = self._assemble_prompt(
            mode=mode,
            personalization=personalization,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
            custom_prompt=custom_prompt,
        )
        response = await self.provider.complete(
            system_prompt, messages, self.provider.TOOLS
        )
        return {
            "message": response.message,
            "tool_calls": response.tool_calls,
            "raw_message": response.raw_response,
        }

    async def complete_with_tool_result(
        self,
        messages: list[dict],
        tool_use_id: str,
        tool_result: dict,
        mode: str = "intuitive",
        personalization: str = "",
        memory_context: str = "",
        knowledge_context: str = "",
    ) -> dict:
        """Submit tool result and get the reader's interpretation."""
        system_prompt = self._assemble_prompt(
            mode=mode,
            personalization=personalization,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
        )
        response = await self.provider.complete_with_tool_result(
            system_prompt, messages, tool_use_id, tool_result
        )
        return {
            "message": response.message,
            "tool_calls": response.tool_calls,
            "raw_message": response.raw_response,
        }

    async def complete_stream(
        self,
        messages: list[dict],
        mode: str = "intuitive",
        personalization: str = "",
        memory_context: str = "",
        knowledge_context: str = "",
    ) -> AsyncIterator[str]:
        """Stream reading response (no tool calling)."""
        system_prompt = self._assemble_prompt(
            mode=mode,
            personalization=personalization,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
        )
        async for chunk in self.provider.complete_stream(system_prompt, messages):
            yield chunk

    def _assemble_prompt(
        self,
        mode: str,
        personalization: str = "",
        memory_context: str = "",
        knowledge_context: str = "",
        custom_prompt: str | None = None,
    ) -> str:
        """Build the full system prompt from components."""
        base = custom_prompt or self._load_prompt(mode)
        parts = [base]
        if personalization:
            parts.append(f"\n\n## About This Person\n{personalization}")
        if memory_context:
            parts.append(f"\n\n## Memory Context\n{memory_context}")
        if knowledge_context:
            parts.append(f"\n\n## Card & Spread Knowledge\n{knowledge_context}")
        return "\n".join(parts)

    def _load_prompt(self, mode: str) -> str:
        """Load personality prompt from file with caching."""
        if mode not in self._prompt_cache:
            path = PROMPTS_DIR / f"{mode}.txt"
            if not path.exists():
                raise FileNotFoundError(f"No prompt file for mode: {mode}")
            self._prompt_cache[mode] = path.read_text()
        return self._prompt_cache[mode]
