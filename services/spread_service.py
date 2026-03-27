"""Spread service — manages spread definitions and position meanings."""

import json
import logging
from pathlib import Path

from models.card_schemas import SpreadDefinition, SpreadPosition
from core.exceptions import InvalidSpreadError

logger = logging.getLogger(__name__)

SPREADS_JSON_PATH = Path(__file__).parent.parent / "data" / "spreads.json"


class SpreadService:
    """
    Manages spread definitions and position meanings.

    Loads spread definitions from data/spreads.json at init.
    Phase 1 includes single_card and three_card spreads.
    """

    def __init__(self):
        self.spreads: dict[str, SpreadDefinition] = self._load_spreads()
        logger.info(f"SpreadService loaded {len(self.spreads)} spreads")

    def _load_spreads(self) -> dict[str, SpreadDefinition]:
        """Load spread definitions from JSON file."""
        with open(SPREADS_JSON_PATH) as f:
            raw = json.load(f)
        return {s["id"]: SpreadDefinition(**s) for s in raw}

    def get_spread(self, spread_id: str) -> SpreadDefinition:
        """Get a spread definition by ID."""
        if spread_id not in self.spreads:
            raise InvalidSpreadError(f"Unknown spread: {spread_id}")
        return self.spreads[spread_id]

    def list_spreads(self) -> list[SpreadDefinition]:
        """List all available spreads."""
        return list(self.spreads.values())

    def get_position_meaning(self, spread_id: str, position_index: int) -> SpreadPosition:
        """Get the meaning for a specific position in a spread."""
        spread = self.get_spread(spread_id)
        for pos in spread.positions:
            if pos.index == position_index:
                return pos
        raise InvalidSpreadError(
            f"Position {position_index} not found in spread {spread_id}"
        )
