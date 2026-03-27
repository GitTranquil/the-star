"""Tests for CardService."""

from services.card_service import CardService
from models.card_schemas import SpreadPosition


def _make_positions(count: int) -> list[SpreadPosition]:
    """Helper to create test positions."""
    names = ["Past", "Present", "Future", "Theme", "Outcome", "Self", "Other", "Bridge", "Challenge", "Crown"]
    return [
        SpreadPosition(index=i, name=names[i % len(names)], meaning="test", interpretation_prompt="test")
        for i in range(count)
    ]


def test_card_loading():
    """All 78 cards load from CSV."""
    service = CardService()
    assert len(service.cards) == 78


def test_major_arcana_count():
    """22 Major Arcana cards."""
    service = CardService()
    major = service.get_major_arcana()
    assert len(major) == 22


def test_minor_arcana_count():
    """56 Minor Arcana cards."""
    service = CardService()
    minor = service.get_minor_arcana()
    assert len(minor) == 56


def test_suits():
    """Each suit has 14 cards."""
    service = CardService()
    for suit in ["wands", "cups", "swords", "pentacles"]:
        cards = service.get_cards_by_suit(suit)
        assert len(cards) == 14, f"{suit} has {len(cards)} cards, expected 14"


def test_draw_no_duplicates():
    """Drawing cards never produces duplicates."""
    service = CardService()
    state = service.create_deck_state()
    positions = _make_positions(10)
    drawn = service.draw(state, positions)
    card_ids = [d.card.id for d in drawn]
    assert len(card_ids) == len(set(card_ids))


def test_draw_updates_deck_state():
    """Drawing cards updates remaining and drawn lists."""
    service = CardService()
    state = service.create_deck_state()
    positions = _make_positions(3)
    drawn = service.draw(state, positions)
    assert len(state.drawn_card_ids) == 3
    assert len(state.remaining_card_ids) == 75
    for d in drawn:
        assert d.card.id in state.drawn_card_ids
        assert d.card.id not in state.remaining_card_ids


def test_draw_reversal_probability():
    """Reversal rate is roughly correct over many draws."""
    service = CardService()
    reversed_count = 0
    trials = 1000
    for _ in range(trials):
        state = service.create_deck_state()
        positions = _make_positions(1)
        drawn = service.draw(state, positions, reversal_probability=0.3)
        if drawn[0].is_reversed:
            reversed_count += 1
    rate = reversed_count / trials
    assert 0.22 < rate < 0.38, f"Reversal rate {rate} outside expected range"


def test_draw_position_assignment():
    """Drawn cards are assigned to correct positions."""
    service = CardService()
    state = service.create_deck_state(seed=42)
    positions = _make_positions(3)
    drawn = service.draw(state, positions)
    for i, d in enumerate(drawn):
        assert d.position_index == i
        assert d.position_name == positions[i].name


def test_get_card():
    """Can retrieve a specific card by ID."""
    service = CardService()
    fool = service.get_card(0)
    assert fool.name == "The Fool"
    assert fool.arcana == "major"


def test_get_llm_context():
    """LLM context includes card info for each drawn card."""
    service = CardService()
    state = service.create_deck_state(seed=42)
    positions = _make_positions(3)
    drawn = service.draw(state, positions)
    ctx = service.get_llm_context(drawn)
    assert "cards_drawn" in ctx
    assert len(ctx["cards_drawn"]) == 3
    for card_ctx in ctx["cards_drawn"]:
        assert "position" in card_ctx
        assert "card" in card_ctx
        assert "orientation" in card_ctx
        assert "keywords" in card_ctx


def test_seed_reproducibility():
    """Same seed produces same card order."""
    service = CardService()
    state1 = service.create_deck_state(seed=123)
    state2 = service.create_deck_state(seed=123)
    assert state1.remaining_card_ids == state2.remaining_card_ids
