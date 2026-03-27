"""Tests for SpreadService."""

import pytest

from services.spread_service import SpreadService
from core.exceptions import InvalidSpreadError


def test_spread_loading():
    """All Phase 1 spreads load."""
    service = SpreadService()
    assert len(service.spreads) >= 2


def test_three_card_positions():
    """Three Card spread has correct positions."""
    service = SpreadService()
    spread = service.get_spread("three_card")
    assert spread.card_count == 3
    assert len(spread.positions) == 3
    assert spread.positions[0].name == "Past"
    assert spread.positions[1].name == "Present"
    assert spread.positions[2].name == "Future"


def test_single_card():
    """Single Card spread has one position."""
    service = SpreadService()
    spread = service.get_spread("single_card")
    assert spread.card_count == 1
    assert len(spread.positions) == 1


def test_list_spreads():
    """List returns all spreads."""
    service = SpreadService()
    spreads = service.list_spreads()
    ids = [s.id for s in spreads]
    assert "single_card" in ids
    assert "three_card" in ids


def test_invalid_spread():
    """Requesting unknown spread raises error."""
    service = SpreadService()
    with pytest.raises(InvalidSpreadError):
        service.get_spread("nonexistent")


def test_get_position_meaning():
    """Can retrieve a specific position meaning."""
    service = SpreadService()
    pos = service.get_position_meaning("three_card", 1)
    assert pos.name == "Present"
