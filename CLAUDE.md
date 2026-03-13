# Tarot Agent — Claude Code Instructions

## Project Overview

This is the backend + frontend for **Tarot Agent**, a premium AI-powered tarot reading web app.
Direct-to-consumer product where users receive deeply personalized readings with persistent
memory across sessions — returning users feel seen through contextual callbacks to past readings,
recurring themes, and life events.

**Three Reading Modes:**
1. **Traditional (Rider-Waite)** — Classical interpretations, formal reader voice, traditional spreads
2. **Modern / Intuitive** — Contemporary language, fluid interpretations, emotional resonance
3. **Custom Deck** — User-uploaded deck images with AI-driven interpretation

**Core Differentiator:** Memory. The app remembers your life context, tracks recurring card patterns,
and weaves past insights into new readings. Every session builds on the last.

**Tech Stack:**
- **Backend:** Python / FastAPI
- **Frontend:** Next.js (consumer web app)
- **Database:** Supabase (Postgres + pgvector + Auth)
- **LLM:** Claude (Anthropic) via tool calling
- **Hosting:** Vercel (frontend) + Railway (backend)

---

## Architecture Patterns

### File Structure (STRICT)

```
tarot-agent/
├── main.py                        # FastAPI app entry
├── config.py                      # Pydantic settings (BaseSettings)
├── api/
│   ├── endpoints.py              # Route handlers only
│   └── middleware.py             # CORS, auth, error handling
├── services/
│   ├── reading_service.py        # Main orchestrator (like Gnosis ConversationService)
│   ├── card_service.py           # 78-card management, draw logic, reversals
│   ├── spread_service.py         # Spread definitions, position meanings
│   ├── memory_service.py         # Entity extraction, storage, context selection
│   ├── knowledge_service.py      # Card meaning RAG, spread context retrieval
│   ├── session_service.py        # Session CRUD, reading history
│   ├── user_service.py           # Profile management
│   └── flows/
│       ├── traditional_flow.py   # Rider-Waite reading flow
│       ├── intuitive_flow.py     # Modern/intuitive reading flow
│       └── custom_flow.py        # Custom deck reading flow
├── agents/
│   ├── reader_agent.py           # LLM integration (like Gnosis SpiritGuideAgent)
│   ├── prompts/
│   │   ├── traditional.txt       # Classical reader personality
│   │   ├── intuitive.txt         # Modern reader personality
│   │   └── custom.txt            # Custom deck reader personality
│   └── extraction_prompt.txt     # Entity extraction prompt
├── llm/
│   ├── base.py                   # LLMProvider ABC, tool definitions
│   ├── claude_provider.py        # Claude implementation
│   └── factory.py                # Provider factory
├── core/
│   ├── exceptions.py             # Exception hierarchy
│   ├── retry.py                  # Tenacity retry decorators
│   └── logging.py                # Structured logging (JSON + text)
├── models/
│   ├── schemas.py                # Request/response Pydantic models
│   ├── card_schemas.py           # Card, Spread, Position models
│   ├── memory_schemas.py         # Entity, SessionMemory, MemoryContext
│   └── reading_schemas.py        # ReadingState, ReadingResult
├── data/
│   ├── cards.csv                 # 78-card dataset (name, suit, number, keywords, upright, reversed)
│   └── spreads.json              # Built-in spread definitions
├── supabase/
│   └── migrations/               # SQL migrations
├── frontend/                     # Next.js consumer app
│   ├── src/
│   │   ├── app/                  # App router pages
│   │   ├── components/           # React components
│   │   ├── lib/                  # API client, utils
│   │   └── hooks/                # Custom React hooks
│   └── ...
├── docs/
│   ├── Tarot_Dev_Roadmap.md
│   ├── Tarot_Dev_Roadmap_Phase1.md
│   └── Tarot_Dev_Roadmap_Phase2.md
└── tests/
    └── test_*.py                 # Pytest files
```

**NEVER put business logic in endpoints.** Endpoints should only:
- Accept request
- Call service
- Return response

### Naming Conventions

**Services:** `noun_service.py` (e.g., `card_service.py`, `spread_service.py`)
**Models:** `CapitalCase` (e.g., `ReadingRequest`, `CardData`, `SpreadLayout`)
**Functions:** `snake_case` (e.g., `draw_cards`, `interpret_spread`)
**Private methods:** `_snake_case` (e.g., `_shuffle_deck`, `_check_reversal`)
**Constants:** `UPPER_SNAKE_CASE` (e.g., `MAJOR_ARCANA_COUNT`, `CELTIC_CROSS_POSITIONS`)

### Import Order

```python
# 1. Standard library
import json
from pathlib import Path
from typing import Optional

# 2. Third-party
from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

# 3. Local
from models.schemas import ReadingRequest
from services.card_service import CardService
```

---

## Code Style Requirements

### Docstrings (MANDATORY)

Every class and public method needs a docstring:

```python
class CardService:
    """
    Manages the 78-card tarot deck with draw logic and reversals.

    Handles:
    - Loading card data from CSV
    - Drawing cards with optional reversal probability
    - Deck state per session (no duplicate draws)
    - Card metadata retrieval
    """

    def draw(self, count: int = 1, allow_reversals: bool = True) -> list[DrawnCard]:
        """
        Draw cards from the shuffled deck.

        Args:
            count: Number of cards to draw
            allow_reversals: Whether cards can appear reversed

        Returns:
            List of DrawnCard with position, orientation, and full metadata
        """
```

### Type Hints (MANDATORY)

Always use type hints on all function signatures.

### Error Handling

```python
try:
    response = await self.claude_client.messages.create(...)
except anthropic.APIStatusError as e:
    logger.error(f"Claude API error: {e}", exc_info=True)
    raise LLMError(f"Claude API error: {e}") from e
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Drawing {count} cards for reading {reading_id}")
logger.error(f"Failed to draw cards: {e}", exc_info=True)
```

---

## Domain Knowledge

### Card System

- **78 cards total:** 22 Major Arcana (0-XXI) + 56 Minor Arcana (4 suits x 14)
- **Suits:** Wands, Cups, Swords, Pentacles
- **Court cards:** Page, Knight, Queen, King
- **Reversals:** ~30% probability by default, configurable per mode
- **No duplicate draws** within a single reading

### Reading Modes

1. **Traditional:** Formal, classical interpretations. References Rider-Waite symbolism directly. Structured delivery.
2. **Intuitive:** Conversational, emotionally attuned. Focuses on resonance over doctrine. Fluid delivery.
3. **Custom Deck:** User uploads deck images. AI interprets visual symbolism without pre-loaded meanings.

### Memory System

The memory system is the core differentiator. It tracks:
- **Entities:** People, places, jobs, relationships mentioned across readings
- **Patterns:** Recurring cards, dominant suits, repeated themes
- **Life events:** Major transitions, decisions, outcomes mentioned
- **Reading history:** Past spreads, interpretations, user reactions

Memory flows into every reading as personalization context.

---

## LLM Tool Calling

Two primary tools the AI can call:

1. **`drawCards`** — Triggers card draw (count, spread_type). Returns drawn cards with positions.
2. **`setReadingState`** — Updates frontend state (phase, visual cues, card reveal animations).

The AI decides WHEN to call these. We don't force timing.

---

## Testing

```bash
# Run tests for a specific component
pytest tests/test_card_service.py -v

# Run all tests
pytest tests/ -v

# Start dev server
uvicorn main:app --reload --port 8000
```

Test each component as you build it. Don't batch testing to the end.

---

## Common Gotchas

- **Don't hardcode card meanings** — they come from CSV data + knowledge_documents table
- **Don't skip the reversal check** — reversed cards have distinct interpretations
- **Don't load card data per request** — load once in `__init__`, reuse
- **Don't force tool calls** — the AI decides when to draw cards
- **Don't forget async/await** — all LLM calls and DB queries are async
- **Don't put logic in endpoints** — endpoints call services, services contain logic

---

## Roadmap Docs

- `docs/Tarot_Dev_Roadmap.md` — Master architecture plan
- `docs/Tarot_Dev_Roadmap_Phase1.md` — Foundation (working 3-card reading with auth)
- `docs/Tarot_Dev_Roadmap_Phase2.md` — Full experience (memory, all spreads, all modes)

**Work sequentially through phases.** Phase 1 must be complete before Phase 2.

---

## Environments & Deployment

- **Development:** Local FastAPI + Next.js dev servers
- **Staging:** Railway (backend) + Vercel preview (frontend) + Supabase dev project
- **Production:** Railway (backend) + Vercel (frontend) + Supabase production project

Push migrations to all Supabase projects before deploying code.
Never edit an already-applied migration — create a new one instead.

---

**Last Updated:** 2026-03-13
**Version:** 1.0
