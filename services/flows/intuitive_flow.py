"""Intuitive reading flow — warm, conversational, story-based interpretation."""

import logging

from agents.reader_agent import ReaderAgent
from config import settings
from models.card_schemas import DeckState
from models.reading_schemas import ReadingMessageRequest, ReadingResponse, ReadingState
from services.card_service import CardService
from services.spread_service import SpreadService

logger = logging.getLogger(__name__)


class IntuitiveFlow:
    """
    Orchestrates the intuitive reading mode.

    Handles:
    - RAG retrieval for card meanings (when available)
    - Tool call detection and execution (drawCards, setReadingState)
    - Card draw via CardService
    - Tool result submission back to LLM
    - Response assembly into ReadingResponse
    """

    def __init__(self):
        self.card_service = CardService()
        self.spread_service = SpreadService()

    async def process(
        self,
        agent: ReaderAgent,
        request: ReadingMessageRequest,
        personalization: str = "",
        memory_context: str = "",
        deck_state: DeckState | None = None,
    ) -> ReadingResponse:
        """
        Process a single message in a reading conversation.

        Steps:
        1. Call agent.complete() with full context
        2. Handle tool calls (drawCards -> card_service.draw())
        3. Submit tool results for interpretation
        4. Return assembled ReadingResponse
        """
        # Agent completion
        agent_response = await agent.complete(
            messages=request.conversation_history,
            mode="intuitive",
            personalization=personalization,
            memory_context=memory_context,
        )

        # Handle tool calls
        drawn_cards = None
        reading_state = None

        for tool_call in agent_response.get("tool_calls", []):
            if tool_call["name"] == "drawCards":
                spread_id = tool_call["input"].get("spread_type", "three_card")
                spread = self.spread_service.get_spread(spread_id)
                deck_state = deck_state or self.card_service.create_deck_state()
                drawn_cards = self.card_service.draw(
                    deck_state=deck_state,
                    positions=spread.positions,
                    reversal_probability=0.25,  # Intuitive mode: lower reversal rate
                )

                # Build tool result and get interpretation
                tool_result = self.card_service.get_llm_context(drawn_cards)

                # Rebuild messages with the assistant's tool_use response
                messages_with_tool = list(request.conversation_history)
                # Add the assistant message containing the tool use
                raw = agent_response.get("raw_message")
                if raw:
                    messages_with_tool.append({
                        "role": "assistant",
                        "content": raw.content,
                    })

                interpretation_response = await agent.complete_with_tool_result(
                    messages=messages_with_tool,
                    tool_use_id=tool_call["id"],
                    tool_result=tool_result,
                    mode="intuitive",
                    personalization=personalization,
                    memory_context=memory_context,
                )
                agent_response = interpretation_response

            elif tool_call["name"] == "setReadingState":
                reading_state = ReadingState(
                    phase=tool_call["input"]["phase"],
                    reveal_card_index=tool_call["input"].get("reveal_card_index"),
                )

        return ReadingResponse(
            message=agent_response["message"],
            cards=drawn_cards,
            reading_state=reading_state or ReadingState(phase="gathering"),
            deck_state=deck_state,
        )
