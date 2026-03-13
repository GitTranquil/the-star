# Tarot Agent — Master Development Roadmap

## Product Vision

**Tarot Agent** is a premium AI-powered tarot reading web application. It delivers deeply
personalized readings where users feel genuinely seen — not through gimmicks, but through
persistent memory that weaves past insights, life context, and recurring patterns into every
new reading.

### What Makes This Different

Most tarot apps generate isolated readings. Tarot Agent builds a relationship:

- **First reading:** A stranger gives you a thoughtful reading.
- **Fifth reading:** A trusted reader who remembers your job transition, your partner's name,
  the recurring Cups cards, and that The Tower kept appearing during your move.
- **Twentieth reading:** Someone who knows your story — who can say "last time we talked about
  your mother, The Empress came up again" and help you see the thread.

### Three Reading Modes

| Mode | Voice | Interpretation Style | Best For |
|------|-------|---------------------|----------|
| **Traditional (Rider-Waite)** | Formal, classical, reverent | Strict symbolism, positional meaning, traditional associations | Users who want "real" tarot, study the craft |
| **Modern / Intuitive** | Warm, conversational, emotionally attuned | Fluid interpretation, emotional resonance, contemporary framing | Most users, especially newcomers |
| **Custom Deck** | Adaptive, visually descriptive | AI interprets uploaded card images without pre-loaded meanings | Collectors, creators, niche deck enthusiasts |

### Core User Journey

```
Sign up → Choose mode → Ask question (optional) → Select spread →
Cards drawn → AI interprets → Reflection prompts → Save reading →
Return later → AI remembers everything
```

---

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                       │
│  (consumer web app — Vercel)                             │
│                                                           │
│  ┌──────────┐  ┌───────────┐  ┌───────────────────────┐ │
│  │ Reading   │  │ Card      │  │ History / Profile     │ │
│  │ Interface │  │ Visuals   │  │ Dashboard             │ │
│  └─────┬─────┘  └─────┬─────┘  └──────────┬───────────┘ │
└────────┼──────────────┼────────────────────┼─────────────┘
         │              │                    │
         ▼              ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Railway)                │
│                                                           │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │ ReadingService   │  │ MemoryService                │  │
│  │ (orchestrator)   │  │ (extraction → storage →      │  │
│  │                  │  │  context selection)           │  │
│  └────────┬─────────┘  └──────────────┬───────────────┘  │
│           │                           │                   │
│  ┌────────┴─────────┐  ┌─────────────┴───────────────┐  │
│  │ CardService      │  │ KnowledgeService             │  │
│  │ SpreadService    │  │ (card meanings RAG)           │  │
│  │ Reading Flows    │  │                               │  │
│  └────────┬─────────┘  └─────────────┬───────────────┘  │
│           │                           │                   │
│  ┌────────┴───────────────────────────┴───────────────┐  │
│  │           ReaderAgent → Claude (LLM)               │  │
│  │           Tool calling: drawCards, setReadingState  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Supabase                               │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌─────────┐ │
│  │ Auth     │ │ Postgres  │ │ pgvector   │ │ Storage │ │
│  │          │ │ (tables)  │ │ (embeddings│ │ (custom │ │
│  │          │ │           │ │  for RAG)  │ │  decks) │ │
│  └──────────┘ └───────────┘ └────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python / FastAPI | Async-native, excellent for LLM streaming, type-safe with Pydantic |
| Frontend | Next.js 14+ (App Router) | SSR for SEO, React Server Components, Vercel-native deployment |
| Database | Supabase (Postgres) | Auth built-in, pgvector for embeddings, RLS for security, real-time subscriptions |
| LLM | Claude (Anthropic) | Best creative writing quality, native tool calling, large context window |
| Embeddings | OpenAI `text-embedding-3-small` | Cost-effective, 1536-dim, good semantic quality |
| Hosting | Railway (backend) + Vercel (frontend) | Simple deployment, good DX, auto-scaling |
| File Storage | Supabase Storage | Custom deck image uploads, integrated with auth |

---

## Module Design

### 1. Card System (`services/card_service.py`)

**Purpose:** Manage the 78-card tarot deck — data, draws, reversals, deck state.

**Source inspiration:** Gnosis `SymbolService` — loads data from CSV at init, provides generation + metadata retrieval.

**Key classes:**
- `CardService` — Loads `data/cards.csv` once in `__init__`. Provides `draw()`, `get_card()`, `get_cards_by_suit()`, `get_major_arcana()`, `get_minor_arcana()`.
- `DeckState` — Per-session deck tracker. Ensures no duplicate draws within a reading. Tracks drawn cards, remaining cards, shuffle seed.

**Card data model:**
```python
class TarotCard:
    id: int                    # 0-77
    name: str                  # "The Fool", "Three of Cups"
    arcana: str                # "major" | "minor"
    suit: str | None           # None for major, "wands"|"cups"|"swords"|"pentacles"
    number: int                # 0-21 for major, 1-14 for minor (ace=1, page=11, knight=12, queen=13, king=14)
    keywords_upright: list[str]
    keywords_reversed: list[str]
    element: str | None        # Fire, Water, Air, Earth
    planet_or_sign: str | None # Astrological correspondence
```

**Draw logic:**
- Shuffle deck using `random.shuffle()` with optional seed for reproducibility
- Draw N cards from top of shuffled deck
- For each drawn card, determine reversal: `random.random() < reversal_probability` (default 0.3)
- Return `DrawnCard` objects with position index, card data, and `is_reversed` flag

**Reversal probability by mode:**
| Mode | Reversal % | Rationale |
|------|-----------|-----------|
| Traditional | 40% | Traditional practice includes frequent reversals |
| Intuitive | 25% | Focus on upright meaning, reversals when especially relevant |
| Custom | 30% | Balanced default for unknown decks |

---

### 2. Spread Engine (`services/spread_service.py`)

**Purpose:** Define and manage tarot spreads — positions, meanings, layouts.

**Key class:** `SpreadService` — Loads spread definitions from `data/spreads.json`. Provides `get_spread()`, `list_spreads()`, `get_position_meaning()`.

**Built-in spreads:**

| Spread | Cards | Difficulty | Description |
|--------|-------|-----------|-------------|
| Single Card | 1 | Beginner | Quick daily guidance |
| Three Card | 3 | Beginner | Past / Present / Future (or Situation / Challenge / Advice) |
| Five Card Cross | 5 | Intermediate | Central theme with 4 surrounding influences |
| Horseshoe | 7 | Intermediate | Past → Present → Future with hidden influences |
| Celtic Cross | 10 | Advanced | Comprehensive life reading |
| Relationship | 6 | Intermediate | Two-person dynamic with bridge cards |

**Spread data model:**
```python
class SpreadDefinition:
    id: str                     # "three_card", "celtic_cross"
    name: str                   # Display name
    card_count: int
    description: str
    difficulty: str             # "beginner" | "intermediate" | "advanced"
    positions: list[SpreadPosition]
    layout: SpreadLayoutInfo    # x,y coordinates for frontend rendering

class SpreadPosition:
    index: int                  # 0-based position
    name: str                   # "Past", "Present", "The Crossing"
    meaning: str                # What this position represents
    interpretation_prompt: str  # Hint for the AI: "This card represents what is crossing you..."
```

---

### 3. Reading Flow (`services/flows/`)

**Purpose:** Orchestrate the conversation flow for each reading mode.

**Source inspiration:** Gnosis `ProductFlow` — processes agent responses, handles tool calls, builds final response.

**Three flow implementations:**

#### `traditional_flow.py`
```
1. Greeting (formal) → 2. Question gathering → 3. Spread selection →
4. Invocation / ritual framing → 5. Card draw (tool call) →
6. Position-by-position interpretation → 7. Synthesis →
8. Advice / action steps → 9. Closing ritual
```

#### `intuitive_flow.py`
```
1. Check-in (warm, personal) → 2. Theme exploration (conversational) →
3. Spread suggestion (or question) → 4. Card draw (tool call) →
5. Holistic interpretation (story-based) → 6. Emotional reflection →
7. Integration prompts → 8. Gentle closing
```

#### `custom_flow.py`
```
1. Deck acknowledgment → 2. Question / intention →
3. Spread selection → 4. Card draw (tool call) →
5. Visual description of each card → 6. Intuitive interpretation →
7. Synthesis → 8. Closing
```

**Flow orchestration pattern:**
Each flow's `process()` method:
1. Fetches knowledge context (card meanings from RAG)
2. Injects memory context (user's past readings, life events, patterns)
3. Calls `reader_agent.complete()` with assembled prompt
4. Handles tool calls (`drawCards` → `card_service.draw()`)
5. Submits tool results back to LLM for interpretation
6. Returns `ReadingResponse` with message, cards, state

---

### 4. Reader Personalities (`agents/reader_agent.py`)

**Purpose:** Thin LLM wrapper that assembles prompts with the right personality.

**Source inspiration:** Gnosis `SpiritGuideAgent` — loads prompts from files, appends personalization + memory context, delegates to LLM provider.

**Three distinct voices:**

#### Traditional Reader
- **Tone:** Reverent, scholarly, precise
- **References:** Rider-Waite symbolism, elemental dignities, numerological correspondences
- **Example:** "The Three of Swords appears in your foundation position, reversed. In the Rider-Waite tradition, this reversal suggests the beginning of recovery from heartbreak — the swords are being withdrawn. Given the Cups dominance in your recent readings, your emotional landscape is actively healing."

#### Intuitive Reader
- **Tone:** Warm, conversational, emotionally attuned
- **References:** Emotional resonance, personal narrative, archetypal themes
- **Example:** "Oh — there's The Empress again. She's been showing up a lot for you lately, and I think she's really trying to get your attention. Last time, she appeared when you were talking about your creative block. How does nurturing and abundance feel in your life right now?"

#### Custom Deck Reader
- **Tone:** Curious, visually descriptive, adaptive
- **References:** Visual elements in uploaded card images, color theory, composition
- **Example:** "This card is striking — the deep blues and golds, the figure reaching upward. There's a sense of aspiration here, of reaching beyond current limits. The circular motif in the background suggests cycles and completeness."

**Prompt assembly:**
```
[System prompt — personality + instructions]
[Memory context — entities, past readings, patterns]
[Knowledge context — card meanings, spread positions]
[Conversation history]
[User message]
```

---

### 5. Memory System (`services/memory_service.py`)

**Purpose:** Extract, store, and recall user context across readings. The core differentiator.

**Source inspiration:** Gnosis `MemoryOrchestrator` + `EntityExtractionService` + `ContextSelectionService` — the full extraction → storage → context selection lifecycle.

**Three-stage pipeline:**

#### Stage 1: Entity Extraction
After each completed reading, extract structured data from the conversation:
- **Entities:** People (partner, mother, boss), places (new apartment, hometown), things (job, project, health condition)
- **Life events:** Transitions, decisions, milestones mentioned
- **Reading-specific:** Cards drawn, spreads used, themes discussed, user reactions
- **Emotional state:** Emotional arc of the reading, dominant feelings

Uses Claude (`claude-haiku-4-5-20251001`) with structured JSON output, `temperature=0.3`.

Extraction prompt template:
```
Given this tarot reading conversation, extract:
1. entities: people, places, things, events mentioned with confidence scores
2. reading_memory: cards drawn, spread used, dominant themes, user reactions
3. patterns: any recurring elements (cards, suits, themes) observed
4. session_summary: 2-3 sentence summary of the reading
```

#### Stage 2: Entity Storage
- Upsert entities by name/alias (merge, don't duplicate)
- Store entity relationships (e.g., "Alex" → partner_of → user)
- Store reading memory as episodic record
- Track card appearance frequency per user
- Confidence threshold: only store attributes with confidence >= 0.7

#### Stage 3: Context Selection
When building context for a new reading:
1. Fetch active entities for the user (sorted by recency + mention count)
2. Fetch recent reading memories (last 5-10 readings)
3. Fetch card pattern data (most drawn cards, dominant suits)
4. If semantic search enabled: embed current question, find relevant past context
5. Format into a context block injected into the system prompt

**Memory decay:**
- Active → Aging after 90 days without mention
- Aging → Archived after 180 days
- Core entities (family, partners) decay at 2x threshold
- Card patterns never decay (they're statistical, not episodic)

---

### 6. Knowledge Base (`services/knowledge_service.py`)

**Purpose:** Semantic search over card meanings, spread contexts, and tarot tradition documents.

**Source inspiration:** Gnosis `KnowledgeService` — pgvector semantic search + RPC functions + full-text fallback.

**Document types in `knowledge_documents` table:**

| Type | Category | Count | Description |
|------|----------|-------|-------------|
| `card_meaning` | `upright` | 78 | Upright interpretation for each card |
| `card_meaning` | `reversed` | 78 | Reversed interpretation for each card |
| `card_meaning` | `symbolism` | 78 | Visual symbolism deep-dive (Rider-Waite) |
| `spread_context` | `position` | ~40 | Position meaning for each spread position |
| `tradition` | `major_arcana` | ~10 | Major arcana journey / Fool's Journey |
| `tradition` | `suits` | 4 | Suit element associations and themes |
| `tradition` | `numerology` | 10 | Number meanings in tarot (Ace through 10) |
| `tradition` | `court_cards` | 4 | Court card archetype meanings |
| **Total** | | **~300** | |

**Key methods:**
- `get_card_interpretation(card_id, is_reversed)` — RPC call for specific card meaning
- `search_relevant_context(query, limit, threshold)` — pgvector semantic search across all documents
- `search_by_keywords(query, limit)` — Full-text fallback using `websearch_to_tsquery`
- `get_spread_position_context(spread_id, position_index)` — Position-specific meaning

**Embedding pipeline:**
- Generate embeddings via OpenAI `text-embedding-3-small` (1536 dimensions)
- Store in `knowledge_documents.embedding` column (pgvector)
- IVFFlat cosine index for fast similarity search
- GIN index on `title || content` for full-text fallback

---

### 7. User Profiles & Auth (`services/user_service.py`)

**Purpose:** User management, profile data, preferences.

**Auth:** Supabase Auth (email/password + OAuth providers: Google, Apple).

**Profile data:**
```python
class UserProfile:
    id: UUID
    email: str
    display_name: str | None
    preferred_mode: str          # "traditional" | "intuitive" | "custom"
    preferred_spread: str | None # Default spread selection
    reversal_preference: str     # "enabled" | "disabled" | "default"
    readings_completed: int
    last_reading_at: datetime | None
    created_at: datetime
    subscription_tier: str       # "free" | "premium"
```

**Free vs Premium:**
| Feature | Free | Premium |
|---------|------|---------|
| Readings per month | 3 | Unlimited |
| Spread types | Single, Three Card | All spreads |
| Reading modes | Intuitive only | All 3 modes |
| Memory / personalization | Last 3 readings | Full history |
| Custom deck | No | Yes |
| Reading history | Last 5 | Full history |

---

### 8. Session Storage & Reading History (`services/session_service.py`)

**Purpose:** Persist readings, track history, enable reading recall.

**Source inspiration:** Gnosis `SessionStorageService` — creates session on first message, updates throughout, stores conversation history as JSONB.

**Session lifecycle:**
1. `create_reading()` — New row in `readings` table when reading begins
2. `update_reading()` — Save conversation messages, card draws as they happen
3. `complete_reading()` — Mark as complete, trigger memory extraction
4. `get_reading_history(user_id, limit)` — Paginated past readings
5. `get_reading(reading_id)` — Full reading detail with conversation

**Reading record includes:**
- Conversation history (JSONB)
- Cards drawn with positions and orientations
- Spread used
- Mode used
- AI-generated summary
- User's question/intention
- Duration
- Memory extracted flag

---

### 9. Analytics (`services/analytics_service.py`)

**Purpose:** Track reading patterns, card frequencies, engagement metrics.

**Tracked events:**
- `reading_started` — mode, spread, time of day
- `reading_completed` — duration, card count, mode
- `card_drawn` — card_id, position, is_reversed, spread_type
- `pattern_detected` — recurring card/suit/theme for a user

**User-facing analytics (premium):**
- Most drawn cards (all time + last 30 days)
- Dominant suits and what they suggest
- Reading frequency patterns
- Theme evolution over time

---

### 10. LLM Layer (`llm/`)

**Purpose:** Abstract LLM provider with tool calling support.

**Source inspiration:** Gnosis `llm/` — `LLMProvider` ABC, `ClaudeProvider`, factory pattern.

**Tool definitions:**

```python
TOOLS = [
    {
        "name": "drawCards",
        "description": "Draw tarot cards for the reading. Call this when you're ready to reveal cards to the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spread_type": {
                    "type": "string",
                    "description": "The spread to use (e.g., 'three_card', 'celtic_cross')"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of cards to draw (must match spread's card_count)"
                }
            },
            "required": ["spread_type", "count"]
        }
    },
    {
        "name": "setReadingState",
        "description": "Update the reading UI state for the frontend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["gathering", "drawing", "revealing", "interpreting", "reflecting", "closing"]
                },
                "reveal_card_index": {
                    "type": "integer",
                    "description": "Index of the next card to reveal (for sequential reveal animation)"
                }
            },
            "required": ["phase"]
        }
    }
]
```

**Provider interface:**
```python
class LLMProvider(ABC):
    async def complete(self, system_prompt: str, messages: list, tools: list | None) -> LLMResponse
    async def complete_stream(self, system_prompt: str, messages: list) -> AsyncIterator[str]
    async def complete_with_tool_result(self, messages: list, tool_use_id: str, tool_result: dict) -> LLMResponse
```

---

### 11. Core Infrastructure (`core/`)

**Purpose:** Shared infrastructure — exceptions, retries, logging.

**Source inspiration:** Gnosis `core/` — exception hierarchy with HTTP status codes, tenacity retry decorators, structured JSON logging.

#### Exception Hierarchy
```
TarotAgentError (base, 500)
├── LLMError (502, retryable=True)
│   ├── LLMTimeoutError (504)
│   ├── LLMRateLimitError (429, retry_after)
│   ├── LLMAuthenticationError (502, retryable=False)
│   └── LLMContentFilterError (400, retryable=False)
├── DatabaseError (503, retryable=True)
│   ├── DatabaseConnectionError
│   ├── DatabaseTimeoutError
│   └── RecordNotFoundError (404, retryable=False)
├── MemoryError (503, retryable=True)
│   ├── MemoryExtractionError
│   └── MemoryConnectionError
├── CardError (400, retryable=False)
│   ├── InsufficientCardsError
│   └── InvalidSpreadError
├── AuthenticationError (401, retryable=False)
├── AuthorizationError (403, retryable=False)
└── ValidationError (400, retryable=False)
```

#### Retry Decorators
```python
@llm_retry       # 3 attempts, 1-10s exponential backoff
@database_retry  # 3 attempts, 0.5-5s exponential backoff
@memory_retry    # 2 attempts, 0.5-2s exponential backoff
```

#### Logging
- JSON format in production (structured for log aggregation)
- Text format in development (human-readable)
- Request context propagation via `ContextVar` (request_id, user_id, reading_id)
- Exception logging extracts `TarotAgentError` fields automatically

---

## Database Schema

### Full SQL Schema

```sql
-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- PROFILES (extends Supabase auth.users)
-- ============================================================
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT,
    preferred_mode TEXT DEFAULT 'intuitive' CHECK (preferred_mode IN ('traditional', 'intuitive', 'custom')),
    preferred_spread TEXT,
    reversal_preference TEXT DEFAULT 'default' CHECK (reversal_preference IN ('enabled', 'disabled', 'default')),
    readings_completed INTEGER DEFAULT 0,
    last_reading_at TIMESTAMPTZ,
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'premium')),
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- READINGS (session records)
-- ============================================================
CREATE TABLE public.readings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('traditional', 'intuitive', 'custom')),
    spread_type TEXT,
    question TEXT,
    intention TEXT,
    cards_drawn JSONB DEFAULT '[]'::jsonb,
    -- Each card: {card_id, position_index, position_name, is_reversed, card_name}
    conversation_history JSONB DEFAULT '[]'::jsonb,
    summary TEXT,
    dominant_theme TEXT,
    emotional_tone TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    memory_extracted_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER
);

CREATE INDEX idx_readings_user_id ON public.readings(user_id);
CREATE INDEX idx_readings_user_started ON public.readings(user_id, started_at DESC);
CREATE INDEX idx_readings_status ON public.readings(status);
CREATE INDEX idx_readings_memory ON public.readings(user_id, memory_extracted_at)
    WHERE memory_extracted_at IS NULL;

-- ============================================================
-- CARD APPEARANCES (for pattern tracking)
-- ============================================================
CREATE TABLE public.card_appearances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reading_id UUID NOT NULL REFERENCES public.readings(id) ON DELETE CASCADE,
    card_id INTEGER NOT NULL,          -- 0-77
    card_name TEXT NOT NULL,
    is_reversed BOOLEAN DEFAULT FALSE,
    position_index INTEGER,
    position_name TEXT,
    spread_type TEXT,
    appeared_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_card_appearances_user ON public.card_appearances(user_id);
CREATE INDEX idx_card_appearances_card ON public.card_appearances(user_id, card_id);
CREATE INDEX idx_card_appearances_reading ON public.card_appearances(reading_id);

-- ============================================================
-- ENTITIES (memory — people, places, things)
-- ============================================================
CREATE TABLE public.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('person', 'pet', 'place', 'job', 'project', 'relationship', 'health', 'event', 'thing')),
    name TEXT NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    attributes JSONB DEFAULT '{}'::jsonb,
    -- Each attribute: {value, confidence, source_reading_id, added_at}
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'aging', 'archived')),
    first_mentioned_reading_id UUID REFERENCES public.readings(id),
    last_updated_reading_id UUID REFERENCES public.readings(id),
    last_mentioned_at TIMESTAMPTZ DEFAULT NOW(),
    mentioned_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entities_user ON public.entities(user_id);
CREATE INDEX idx_entities_user_status ON public.entities(user_id, status);
CREATE INDEX idx_entities_user_type ON public.entities(user_id, type);
CREATE UNIQUE INDEX idx_entities_user_name ON public.entities(user_id, LOWER(name));

-- ============================================================
-- ENTITY RELATIONSHIPS
-- ============================================================
CREATE TABLE public.entity_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES public.entities(id) ON DELETE CASCADE,
    related_entity_id UUID REFERENCES public.entities(id) ON DELETE SET NULL,
    relationship_type TEXT NOT NULL,    -- "partner_of", "child_of", "colleague_of", "pet_of"
    relationship_to_user TEXT,          -- "partner", "mother", "boss", "pet"
    confidence REAL DEFAULT 1.0,
    source_reading_id UUID REFERENCES public.readings(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entity_rels_user ON public.entity_relationships(user_id);
CREATE INDEX idx_entity_rels_entity ON public.entity_relationships(entity_id);

-- ============================================================
-- READING MEMORIES (episodic memory per reading)
-- ============================================================
CREATE TABLE public.reading_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reading_id UUID NOT NULL REFERENCES public.readings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    core_theme TEXT,
    emotional_arc TEXT,
    key_insights TEXT[] DEFAULT '{}',
    dominant_cards TEXT[] DEFAULT '{}',  -- Card names that were most significant
    dominant_suit TEXT,                   -- If one suit dominated
    unfinished_threads TEXT[] DEFAULT '{}',
    user_reaction TEXT,                  -- How user responded to the reading
    session_summary TEXT,
    extraction_model TEXT,
    confidence_score REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reading_memories_user ON public.reading_memories(user_id);
CREATE INDEX idx_reading_memories_reading ON public.reading_memories(reading_id);

-- ============================================================
-- CARD PATTERNS (aggregated per user)
-- ============================================================
CREATE TABLE public.card_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('recurring_card', 'dominant_suit', 'recurring_theme', 'arcana_balance')),
    pattern_key TEXT NOT NULL,          -- card name, suit name, theme text
    occurrence_count INTEGER DEFAULT 1,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    readings_involved UUID[] DEFAULT '{}',
    notes TEXT,                          -- AI-generated insight about the pattern
    UNIQUE(user_id, pattern_type, pattern_key)
);

CREATE INDEX idx_card_patterns_user ON public.card_patterns(user_id);
CREATE INDEX idx_card_patterns_user_type ON public.card_patterns(user_id, pattern_type);

-- ============================================================
-- KNOWLEDGE DOCUMENTS (RAG — card meanings, spread contexts, tradition)
-- ============================================================
CREATE TABLE public.knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_type TEXT NOT NULL CHECK (document_type IN ('card_meaning', 'spread_context', 'tradition')),
    category TEXT NOT NULL,
    -- card_meaning: 'upright', 'reversed', 'symbolism'
    -- spread_context: 'position'
    -- tradition: 'major_arcana', 'suits', 'numerology', 'court_cards'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    card_id INTEGER,                    -- For card_meaning docs (0-77)
    card_name TEXT,
    spread_id TEXT,                     -- For spread_context docs
    position_index INTEGER,             -- For spread_context docs
    tags TEXT[] DEFAULT '{}',
    embedding VECTOR(1536),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_type ON public.knowledge_documents(document_type);
CREATE INDEX idx_knowledge_card ON public.knowledge_documents(card_id) WHERE card_id IS NOT NULL;
CREATE INDEX idx_knowledge_active ON public.knowledge_documents(is_active) WHERE is_active = TRUE;

-- Semantic search index
CREATE INDEX idx_knowledge_embedding ON public.knowledge_documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);

-- Full-text search index
CREATE INDEX idx_knowledge_fulltext ON public.knowledge_documents
    USING gin (to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, '')));

-- ============================================================
-- CUSTOM DECKS
-- ============================================================
CREATE TABLE public.custom_decks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    card_count INTEGER DEFAULT 0,
    card_back_url TEXT,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_custom_decks_user ON public.custom_decks(user_id);

CREATE TABLE public.custom_deck_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES public.custom_decks(id) ON DELETE CASCADE,
    card_index INTEGER NOT NULL,        -- Position in the deck
    name TEXT,                          -- Optional user-provided name
    image_url TEXT NOT NULL,            -- Supabase Storage URL
    ai_description TEXT,               -- AI-generated description of the card image
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(deck_id, card_index)
);

CREATE INDEX idx_custom_cards_deck ON public.custom_deck_cards(deck_id);

-- ============================================================
-- RPC FUNCTIONS
-- ============================================================

-- Semantic search over knowledge documents
CREATE OR REPLACE FUNCTION search_knowledge(
    p_query_embedding VECTOR(1536),
    p_limit INTEGER DEFAULT 5,
    p_similarity_threshold REAL DEFAULT 0.4,
    p_document_type TEXT DEFAULT NULL,
    p_card_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_type TEXT,
    category TEXT,
    title TEXT,
    content TEXT,
    card_id INTEGER,
    card_name TEXT,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kd.id,
        kd.document_type,
        kd.category,
        kd.title,
        kd.content,
        kd.card_id,
        kd.card_name,
        1 - (kd.embedding <=> p_query_embedding) AS similarity
    FROM public.knowledge_documents kd
    WHERE kd.is_active = TRUE
        AND (p_document_type IS NULL OR kd.document_type = p_document_type)
        AND (p_card_id IS NULL OR kd.card_id = p_card_id)
        AND kd.embedding IS NOT NULL
        AND 1 - (kd.embedding <=> p_query_embedding) >= p_similarity_threshold
    ORDER BY kd.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- Get card-specific knowledge
CREATE OR REPLACE FUNCTION get_card_knowledge(
    p_card_id INTEGER,
    p_include_reversed BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    id UUID,
    category TEXT,
    title TEXT,
    content TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT kd.id, kd.category, kd.title, kd.content
    FROM public.knowledge_documents kd
    WHERE kd.card_id = p_card_id
        AND kd.is_active = TRUE
        AND kd.document_type = 'card_meaning'
        AND (p_include_reversed = TRUE OR kd.category != 'reversed')
    ORDER BY
        CASE kd.category
            WHEN 'upright' THEN 1
            WHEN 'reversed' THEN 2
            WHEN 'symbolism' THEN 3
        END;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- Full-text search fallback
CREATE OR REPLACE FUNCTION search_knowledge_fulltext(
    p_query TEXT,
    p_limit INTEGER DEFAULT 5,
    p_document_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_type TEXT,
    category TEXT,
    title TEXT,
    content TEXT,
    card_id INTEGER,
    card_name TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kd.id,
        kd.document_type,
        kd.category,
        kd.title,
        kd.content,
        kd.card_id,
        kd.card_name,
        ts_rank(
            to_tsvector('english', COALESCE(kd.title, '') || ' ' || COALESCE(kd.content, '')),
            websearch_to_tsquery('english', p_query)
        ) AS rank
    FROM public.knowledge_documents kd
    WHERE kd.is_active = TRUE
        AND (p_document_type IS NULL OR kd.document_type = p_document_type)
        AND to_tsvector('english', COALESCE(kd.title, '') || ' ' || COALESCE(kd.content, ''))
            @@ websearch_to_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- Get user card patterns
CREATE OR REPLACE FUNCTION get_user_card_stats(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    card_id INTEGER,
    card_name TEXT,
    total_appearances BIGINT,
    reversed_count BIGINT,
    last_appeared TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ca.card_id,
        ca.card_name,
        COUNT(*) AS total_appearances,
        COUNT(*) FILTER (WHERE ca.is_reversed = TRUE) AS reversed_count,
        MAX(ca.appeared_at) AS last_appeared
    FROM public.card_appearances ca
    WHERE ca.user_id = p_user_id
    GROUP BY ca.card_id, ca.card_name
    ORDER BY total_appearances DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.card_appearances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reading_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.card_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_decks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_deck_cards ENABLE ROW LEVEL SECURITY;

-- Profiles: users can read/update own profile
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Readings: users can CRUD own readings
CREATE POLICY "Users can view own readings"
    ON public.readings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own readings"
    ON public.readings FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own readings"
    ON public.readings FOR UPDATE USING (auth.uid() = user_id);

-- Card appearances: users can read/create own
CREATE POLICY "Users can view own card appearances"
    ON public.card_appearances FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own card appearances"
    ON public.card_appearances FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Entities: users can CRUD own
CREATE POLICY "Users can view own entities"
    ON public.entities FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own entities"
    ON public.entities FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own entities"
    ON public.entities FOR UPDATE USING (auth.uid() = user_id);

-- Entity relationships: users can read/create own
CREATE POLICY "Users can view own entity relationships"
    ON public.entity_relationships FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own entity relationships"
    ON public.entity_relationships FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Reading memories: users can read/create own
CREATE POLICY "Users can view own reading memories"
    ON public.reading_memories FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own reading memories"
    ON public.reading_memories FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Card patterns: users can read/create/update own
CREATE POLICY "Users can view own card patterns"
    ON public.card_patterns FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own card patterns"
    ON public.card_patterns FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own card patterns"
    ON public.card_patterns FOR UPDATE USING (auth.uid() = user_id);

-- Knowledge documents: readable by all authenticated users
CREATE POLICY "Authenticated users can read knowledge"
    ON public.knowledge_documents FOR SELECT
    USING (auth.role() = 'authenticated');

-- Custom decks: users can CRUD own
CREATE POLICY "Users can view own decks"
    ON public.custom_decks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own decks"
    ON public.custom_decks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own decks"
    ON public.custom_decks FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own decks"
    ON public.custom_decks FOR DELETE USING (auth.uid() = user_id);

-- Custom deck cards: users can CRUD own (via deck ownership)
CREATE POLICY "Users can view own deck cards"
    ON public.custom_deck_cards FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.custom_decks WHERE id = deck_id AND user_id = auth.uid()));
CREATE POLICY "Users can create own deck cards"
    ON public.custom_deck_cards FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM public.custom_decks WHERE id = deck_id AND user_id = auth.uid()));
CREATE POLICY "Users can update own deck cards"
    ON public.custom_deck_cards FOR UPDATE
    USING (EXISTS (SELECT 1 FROM public.custom_decks WHERE id = deck_id AND user_id = auth.uid()));
CREATE POLICY "Users can delete own deck cards"
    ON public.custom_deck_cards FOR DELETE
    USING (EXISTS (SELECT 1 FROM public.custom_decks WHERE id = deck_id AND user_id = auth.uid()));

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_knowledge_updated_at
    BEFORE UPDATE ON public.knowledge_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_custom_decks_updated_at
    BEFORE UPDATE ON public.custom_decks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## Architecture Decisions

### 1. Claude as Primary LLM (not GPT-4)

**Decision:** Use Claude (Anthropic) for all reading interpretations.

**Rationale:**
- Superior creative writing quality — readings are fundamentally a creative writing task
- Native tool calling support for `drawCards` and `setReadingState`
- Large context window (200K) handles full reading history + memory context
- Better at maintaining consistent personality across long conversations

**Trade-off:** Entity extraction uses `claude-haiku-4-5-20251001` for cost efficiency (structured JSON output, low temperature). Interpretive readings use `claude-sonnet-4-5-20250929` for quality.

### 2. Supabase Over Custom Auth + Postgres

**Decision:** Use Supabase for auth, database, storage, and real-time.

**Rationale:**
- Auth is complex and security-critical — don't build it
- Row Level Security gives us per-user data isolation for free
- pgvector extension for semantic search without a separate vector DB
- Storage API for custom deck image uploads
- Real-time subscriptions for future live reading features

### 3. Per-Mode Flows (Not Single Generic Flow)

**Decision:** Separate flow implementations for Traditional, Intuitive, and Custom modes.

**Rationale:**
- Each mode has genuinely different conversation dynamics
- Traditional flow has ritual framing that would feel forced in Intuitive
- Custom flow requires image analysis that other modes don't
- Shared logic lives in the base `ReadingFlow` class — DRY where it matters

### 4. Card Patterns as First-Class Data

**Decision:** Dedicated `card_appearances` + `card_patterns` tables, not just derived from reading history.

**Rationale:**
- Querying "which cards appear most for this user" across hundreds of readings is expensive
- Pre-computed pattern table makes context injection fast
- Pattern detection runs asynchronously after reading completion
- Enables "The Tower has appeared in your last 3 readings" without scanning all history

### 5. Entity Memory Adapted from Gnosis

**Decision:** Port Gnosis's entity extraction → storage → context selection pattern.

**Rationale:**
- Proven pattern for remembering user context across sessions
- Entity model (people, places, things with attributes + confidence + decay) maps perfectly to tarot use case
- Adding tarot-specific entity types: `job`, `relationship`, `event`
- Adding reading-specific memory: `reading_memories` table with card/theme/emotional data
- Confidence threshold (0.7) prevents hallucinated entities from polluting memory

### 6. Consumer Web App (Not Mobile-First)

**Decision:** Next.js web app, responsive but web-first.

**Rationale:**
- Faster to market than React Native
- SEO matters for organic discovery ("free tarot reading online")
- PWA capabilities for mobile-like experience without app store friction
- Can always wrap in Capacitor/Tauri later if needed

---

## Reading Flow Design

### Traditional Mode — Detailed Flow

```
Phase 1: OPENING (1-2 messages)
├── Reader introduces themselves formally
├── Acknowledges returning user + past reading context (from memory)
└── Asks what brings them to the cards today

Phase 2: QUESTION (1-3 messages)
├── Helps user formulate a clear question
├── May reference past themes: "Last time you asked about career..."
└── Confirms the question before proceeding

Phase 3: SPREAD SELECTION (1 message)
├── Suggests appropriate spread based on question complexity
├── Explains why this spread fits their question
└── User confirms or chooses different spread

Phase 4: RITUAL FRAMING (1 message)
├── Brief centering moment
├── "Take a breath. Focus on your question."
└── Sets the tone for the card reveal

Phase 5: CARD DRAW (tool call: drawCards)
├── AI calls drawCards tool with spread_type + count
├── Backend draws cards, returns positions + orientations
├── AI calls setReadingState with phase="revealing"
└── Frontend begins card reveal animation

Phase 6: INTERPRETATION (3-7 messages, depending on spread size)
├── Position-by-position interpretation
├── References Rider-Waite symbolism specifically
├── Notes reversals with traditional meaning
├── Connects to user's question
├── Weaves in memory context where relevant
│   └── "The Queen of Cups appeared reversed last month too — there's a pattern here"
└── Synthesis across all positions

Phase 7: GUIDANCE (1-2 messages)
├── Concrete advice drawn from the reading
├── Action steps if appropriate
└── Timeline guidance (traditional readers often note timing)

Phase 8: CLOSING (1 message)
├── Summarizes the core message
├── Invites reflection
└── Formal closing
```

### Intuitive Mode — Detailed Flow

```
Phase 1: CHECK-IN (1-2 messages)
├── Warm, personal greeting
├── Memory-driven: "How did things go with [entity from last reading]?"
└── Opens space for whatever's present

Phase 2: EXPLORATION (2-4 messages)
├── Conversational theme exploration
├── Helps user arrive at what they really need guidance on
├── May not require a formal "question" — a feeling is enough
└── AI decides when the moment is right for cards

Phase 3: CARD DRAW (tool call: drawCards)
├── Organic transition: "I think the cards have something for you..."
├── AI calls drawCards
├── Frontend reveals cards with gentle animation
└── Brief pause for user to take in the imagery

Phase 4: READING (3-5 messages)
├── Story-based interpretation (not position-by-position)
├── Emotional resonance over doctrine
├── "What stands out to you?" — invites user participation
├── Pattern callbacks: "You've been drawing a lot of Cups lately..."
└── Synthesizes into a cohesive narrative

Phase 5: REFLECTION (1-2 messages)
├── Integration prompts
├── "What does this stir up for you?"
├── Connects reading to user's current life context
└── Gentle, non-prescriptive

Phase 6: CLOSING (1 message)
├── Affirming summary
├── Leaves door open for return
└── Warm sign-off
```

### Custom Deck Mode — Detailed Flow

```
Phase 1: DECK ACKNOWLEDGMENT (1 message)
├── Acknowledges the user's custom deck
├── Notes visual style if AI has seen cards before
└── Adapts language to the deck's aesthetic

Phase 2: INTENTION (1-2 messages)
├── Similar to Intuitive — conversational
├── Question or feeling is sufficient
└── Spread selection

Phase 3: CARD DRAW (tool call: drawCards)
├── Draws from user's custom deck
├── Each card includes image_url for AI visual analysis
└── Frontend displays user's custom card images

Phase 4: VISUAL READING (3-5 messages)
├── AI describes what it sees in each card image
├── Interprets colors, figures, symbols, composition
├── Builds interpretation from visual analysis (no pre-loaded meanings)
├── Connects to user's question/intention
└── Synthesis

Phase 5: REFLECTION + CLOSING (1-2 messages)
├── Reflection prompts
└── Closing
```

---

## Phase Overview

### Phase 1: Foundation
**Goal:** A working end-to-end tarot reading with auth and session persistence.
**Deliverable:** Authenticated user gets a personalized 3-card reading, saved to their history.
**Details:** [`docs/Tarot_Dev_Roadmap_Phase1.md`](Tarot_Dev_Roadmap_Phase1.md)

### Phase 2: Full Experience
**Goal:** The complete premium tarot reading experience.
**Deliverable:** All spreads, all modes, full memory system, reading history, patterns, custom decks.
**Details:** [`docs/Tarot_Dev_Roadmap_Phase2.md`](Tarot_Dev_Roadmap_Phase2.md)

---

## API Endpoints Overview

### Phase 1 Endpoints

```
POST   /api/reading              # Start a new reading (returns reading_id)
POST   /api/reading/{id}/message # Send message in a reading
POST   /api/reading/{id}/stream  # SSE streaming version
GET    /api/reading/{id}         # Get reading details
GET    /api/readings             # List user's past readings (paginated)
GET    /api/health               # Health check

POST   /api/auth/signup          # Supabase auth passthrough
POST   /api/auth/login           # Supabase auth passthrough
POST   /api/auth/logout          # Supabase auth passthrough
GET    /api/profile              # Get user profile
PATCH  /api/profile              # Update user profile
```

### Phase 2 Endpoints

```
GET    /api/spreads              # List available spreads
GET    /api/spreads/{id}         # Get spread details + positions
GET    /api/cards/{id}           # Get card details + meanings
GET    /api/patterns             # Get user's card patterns
GET    /api/analytics            # Get user's reading analytics

POST   /api/decks                # Create custom deck
POST   /api/decks/{id}/cards     # Upload card to custom deck
GET    /api/decks                # List user's custom decks
GET    /api/decks/{id}           # Get deck details + cards
DELETE /api/decks/{id}           # Delete custom deck
```

---

## Frontend Page Structure

```
/                          # Landing page (SEO-optimized)
/login                     # Auth page (login + signup)
/reading                   # New reading page (mode selection → reading flow)
/reading/[id]              # Active reading (chat + card display)
/history                   # Reading history list
/history/[id]              # Past reading detail view
/profile                   # User profile + preferences
/patterns                  # Card patterns + analytics (premium)
/decks                     # Custom deck management (premium)
/decks/[id]                # Custom deck detail + card upload
```

---

## Configuration (Settings)

```python
class Settings(BaseSettings):
    # LLM
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"
    EXTRACTION_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_TIMEOUT_SECONDS: int = 60

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str

    # Embeddings
    OPENAI_API_KEY: str              # For text-embedding-3-small only
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Features
    RAG_ENABLED: bool = True
    SEMANTIC_MEMORY_ENABLED: bool = False
    CUSTOM_DECKS_ENABLED: bool = False

    # Reading defaults
    DEFAULT_MODE: str = "intuitive"
    DEFAULT_REVERSAL_PROBABILITY: float = 0.3
    MEMORY_EXTRACTION_MIN_MESSAGES: int = 4

    # Infrastructure
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

---

**Last Updated:** 2026-03-13
**Version:** 1.0
