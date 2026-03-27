"""Reading service — main orchestrator for tarot readings."""

import logging
from uuid import UUID

from agents.reader_agent import ReaderAgent
from core.exceptions import RecordNotFoundError
from models.card_schemas import DeckState
from models.reading_schemas import ReadingMessageRequest, ReadingResponse, ReadingState
from services.flows.intuitive_flow import IntuitiveFlow

logger = logging.getLogger(__name__)


class ReadingService:
    """
    Main orchestrator for tarot readings.

    Owns:
    - Reading lifecycle (create -> messages -> complete)
    - Session persistence (Supabase readings table)
    - Context building (personalization, memory in Phase 2)
    - Flow delegation (intuitive_flow in Phase 1)
    """

    def __init__(self, supabase_client=None):
        self.flow = IntuitiveFlow()
        self.agent = ReaderAgent()
        self.supabase = supabase_client

    async def create_reading(self, user_id: str, mode: str = "intuitive") -> dict:
        """
        Start a new reading.

        Creates a row in the readings table, builds initial personalization.
        Returns reading_id + initial AI greeting.
        """
        # Create reading record
        reading = await self._create_reading_record(user_id, mode)
        reading_id = reading["id"]

        # Build personalization
        personalization = await self._build_personalization(user_id)

        # Get AI greeting (first message)
        greeting_response = await self.flow.process(
            agent=self.agent,
            request=ReadingMessageRequest(
                message="",
                conversation_history=[],
                reading_id=reading_id,
                mode=mode,
            ),
            personalization=personalization,
        )

        # Save conversation state
        await self._update_reading(reading_id, {
            "conversation_history": [
                {"role": "assistant", "content": greeting_response.message}
            ],
        })

        return {
            "reading_id": reading_id,
            "message": greeting_response.message,
            "reading_state": greeting_response.reading_state.model_dump(),
        }

    async def process_message(
        self, reading_id: str, user_id: str, message: str
    ) -> ReadingResponse:
        """
        Process a user message within an existing reading.

        Steps:
        1. Load reading state from DB
        2. Build conversation history
        3. Build personalization context
        4. Delegate to flow
        5. Save updated state
        6. Return response
        """
        # Load reading
        reading = await self._get_reading(reading_id, user_id)

        # Build conversation
        history = reading.get("conversation_history", [])
        history.append({"role": "user", "content": message})

        # Personalization
        personalization = await self._build_personalization(user_id)

        # Reconstruct deck state if cards already drawn
        deck_state = self._reconstruct_deck_state(reading)

        # Delegate to flow
        response = await self.flow.process(
            agent=self.agent,
            request=ReadingMessageRequest(
                message=message,
                conversation_history=history,
                reading_id=reading_id,
                mode=reading.get("mode", "intuitive"),
            ),
            personalization=personalization,
            deck_state=deck_state,
        )

        # Save state
        history.append({"role": "assistant", "content": response.message})
        update_data: dict = {
            "conversation_history": history,
            "last_message_at": "now()",
        }
        if response.cards:
            update_data["cards_drawn"] = [card.model_dump() for card in response.cards]
            update_data["spread_type"] = (
                response.cards[0].position_name.split()[0] if response.cards else None
            )

        await self._update_reading(reading_id, update_data)

        return response

    async def complete_reading(self, reading_id: str, user_id: str) -> None:
        """Mark a reading as complete. Triggers memory extraction in Phase 2."""
        await self._update_reading(reading_id, {
            "status": "completed",
            "completed_at": "now()",
        })

    async def get_reading_history(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """Get paginated reading history for a user."""
        result = (
            self.supabase.table("readings")
            .select(
                "id, mode, spread_type, question, summary, dominant_theme, status, started_at, completed_at"
            )
            .eq("user_id", user_id)
            .order("started_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data

    async def get_reading(self, reading_id: str, user_id: str) -> dict:
        """Get full reading detail."""
        return await self._get_reading(reading_id, user_id)

    async def _build_personalization(self, user_id: str) -> str:
        """Build personalization context from user profile."""
        if not self.supabase:
            return ""
        try:
            result = (
                self.supabase.table("profiles")
                .select("display_name, readings_completed, preferred_mode")
                .eq("id", user_id)
                .single()
                .execute()
            )
            p = result.data
            parts = []
            if p.get("display_name"):
                parts.append(f"Name: {p['display_name']}")
            count = p.get("readings_completed", 0)
            if count == 0:
                parts.append("This is their first reading — make it special.")
            elif count < 5:
                parts.append(
                    f"They've had {count} readings — still getting to know them."
                )
            elif count < 20:
                parts.append(
                    f"Returning reader ({count} readings). They're familiar with the process."
                )
            else:
                parts.append(
                    f"Dedicated reader ({count} readings). Treat them as a regular."
                )
            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"Failed to build personalization: {e}")
            return ""

    async def _create_reading_record(self, user_id: str, mode: str) -> dict:
        """Create a new reading row in the database."""
        if not self.supabase:
            # Dev fallback: return a mock reading
            import uuid
            return {"id": str(uuid.uuid4()), "mode": mode, "user_id": user_id}

        result = (
            self.supabase.table("readings")
            .insert({"user_id": user_id, "mode": mode, "status": "active"})
            .execute()
        )
        return result.data[0]

    async def _get_reading(self, reading_id: str, user_id: str) -> dict:
        """Get a reading, verifying ownership."""
        if not self.supabase:
            raise RecordNotFoundError(f"Reading {reading_id} not found (no DB)")

        result = (
            self.supabase.table("readings")
            .select("*")
            .eq("id", reading_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise RecordNotFoundError(f"Reading {reading_id} not found")
        return result.data

    async def _update_reading(self, reading_id: str, data: dict) -> None:
        """Update a reading record."""
        if not self.supabase:
            return
        self.supabase.table("readings").update(data).eq("id", reading_id).execute()

    def _reconstruct_deck_state(self, reading: dict) -> DeckState | None:
        """Reconstruct deck state from previously drawn cards."""
        cards_drawn = reading.get("cards_drawn", [])
        if not cards_drawn:
            return None
        drawn_ids = [c["card"]["id"] for c in cards_drawn]
        all_ids = list(range(78))
        remaining = [i for i in all_ids if i not in drawn_ids]
        return DeckState(
            remaining_card_ids=remaining, drawn_card_ids=drawn_ids, shuffle_seed=None
        )
