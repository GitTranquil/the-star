"""Card service — manages the 78-card tarot deck with draw logic and reversals."""

import random
import logging
from pathlib import Path

import pandas as pd

from models.card_schemas import TarotCard, DrawnCard, DeckState, SpreadPosition

logger = logging.getLogger(__name__)

CARDS_CSV_PATH = Path(__file__).parent.parent / "data" / "cards.csv"


class CardService:
    """
    Manages the 78-card tarot deck with draw logic and reversals.

    Handles:
    - Loading card data from CSV
    - Drawing cards with optional reversal probability
    - Deck state per session (no duplicate draws)
    - Card metadata retrieval
    """

    def __init__(self):
        self.cards_df = pd.read_csv(CARDS_CSV_PATH)
        self.cards: dict[int, TarotCard] = self._build_card_lookup()
        logger.info(f"CardService loaded {len(self.cards)} cards")

    def _build_card_lookup(self) -> dict[int, TarotCard]:
        """Parse CSV rows into TarotCard objects."""
        lookup = {}
        for _, row in self.cards_df.iterrows():
            card = TarotCard(
                id=int(row["id"]),
                name=row["name"],
                arcana=row["arcana"],
                suit=row["suit"] if pd.notna(row["suit"]) else None,
                number=int(row["number"]),
                keywords_upright=row["keywords_upright"].split(";"),
                keywords_reversed=row["keywords_reversed"].split(";"),
                element=row["element"] if pd.notna(row["element"]) else None,
                planet_or_sign=row["planet_or_sign"] if pd.notna(row["planet_or_sign"]) else None,
            )
            lookup[card.id] = card
        return lookup

    def create_deck_state(self, seed: int | None = None) -> DeckState:
        """Create a fresh shuffled deck state for a reading."""
        card_ids = list(self.cards.keys())
        rng = random.Random(seed)
        rng.shuffle(card_ids)
        return DeckState(
            remaining_card_ids=card_ids,
            drawn_card_ids=[],
            shuffle_seed=seed,
        )

    def draw(
        self,
        deck_state: DeckState,
        positions: list[SpreadPosition],
        reversal_probability: float = 0.3,
    ) -> list[DrawnCard]:
        """
        Draw cards from the deck, assigning to spread positions.

        Args:
            deck_state: Current deck state (mutated in place)
            positions: Spread positions to fill
            reversal_probability: Chance each card appears reversed

        Returns:
            List of DrawnCard with position, orientation, and full metadata
        """
        count = len(positions)
        if count > len(deck_state.remaining_card_ids):
            from core.exceptions import InsufficientCardsError
            raise InsufficientCardsError(
                f"Need {count} cards but only {len(deck_state.remaining_card_ids)} remain"
            )

        drawn: list[DrawnCard] = []
        for position in positions:
            card_id = deck_state.remaining_card_ids.pop(0)
            deck_state.drawn_card_ids.append(card_id)
            card = self.cards[card_id]
            is_reversed = random.random() < reversal_probability

            drawn.append(DrawnCard(
                card=card,
                position_index=position.index,
                position_name=position.name,
                is_reversed=is_reversed,
            ))

        logger.info(f"Drew {count} cards: {[d.card.name for d in drawn]}")
        return drawn

    def get_card(self, card_id: int) -> TarotCard:
        """Get a single card by ID."""
        if card_id not in self.cards:
            from core.exceptions import CardError
            raise CardError(f"Card ID {card_id} not found")
        return self.cards[card_id]

    def get_cards_by_suit(self, suit: str) -> list[TarotCard]:
        """Get all cards of a given suit."""
        return [c for c in self.cards.values() if c.suit == suit]

    def get_major_arcana(self) -> list[TarotCard]:
        """Get all 22 Major Arcana cards."""
        return [c for c in self.cards.values() if c.arcana == "major"]

    def get_minor_arcana(self) -> list[TarotCard]:
        """Get all 56 Minor Arcana cards."""
        return [c for c in self.cards.values() if c.arcana == "minor"]

    def get_llm_context(self, drawn_cards: list[DrawnCard]) -> dict:
        """
        Build minimal context dict for LLM tool result.

        Keeps token count low while giving the AI enough to interpret.
        """
        cards_context = []
        for dc in drawn_cards:
            orientation = "reversed" if dc.is_reversed else "upright"
            keywords = dc.card.keywords_reversed if dc.is_reversed else dc.card.keywords_upright
            card_info = {
                "position": dc.position_name,
                "card": dc.card.name,
                "orientation": orientation,
                "keywords": keywords,
            }
            if dc.card.element:
                card_info["element"] = dc.card.element
            cards_context.append(card_info)

        return {"cards_drawn": cards_context}
