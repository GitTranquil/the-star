# Tarot Agent — Phase 1: Foundation

**Goal:** A working end-to-end tarot reading with authentication and session persistence.

**Completion criteria:** An authenticated user can start a 3-card reading, receive a personalized
AI interpretation via Claude, and find that reading saved in their history on next login.

**Estimated tasks:** 14 tasks across 5 milestones.

---

## Milestone 1: Project Scaffolding

### Task 1.1: FastAPI App Skeleton

**Status:** [ ] Not started

**Description:**
Set up the FastAPI application with proper project structure, configuration, and middleware.

**Deliverables:**
- `main.py` — FastAPI app with lifespan handler, CORS middleware, health endpoint
- `config.py` — Pydantic `Settings(BaseSettings)` with all env vars (see Master Roadmap for full list)
- `api/endpoints.py` — Empty router, placeholder `/health` returning `{"status": "ok", "version": "0.1.0"}`
- `api/middleware.py` — CORS configuration, request ID injection middleware
- `core/exceptions.py` — Full exception hierarchy (see Master Roadmap)
- `core/retry.py` — Tenacity retry decorators: `@llm_retry`, `@database_retry`
- `core/logging.py` — Structured logging setup (JSON for production, text for dev)
- `.env.example` — All required env vars with placeholder values
- `requirements.txt` — All dependencies
- `Dockerfile` + `docker-compose.yml` — Dev environment with hot reload

**Dependencies:**
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
httpx>=0.26.0
tenacity>=8.2.0
sentry-sdk[fastapi]>=1.40.0
```

**Acceptance criteria:**
```bash
uvicorn main:app --reload --port 8000
curl http://localhost:8000/health  # → {"status": "ok", "version": "0.1.0"}
```

**Pattern reference:** Gnosis `main.py` + `config.py` + `core/` — same structure, adapted for tarot domain.

---

### Task 1.2: Supabase Database Setup

**Status:** [ ] Not started

**Description:**
Create Supabase project and run initial database migrations for core tables.

**Deliverables:**
- Supabase project created (dev environment)
- `supabase/migrations/00001_initial_schema.sql` containing:
  - `profiles` table with auto-create trigger on `auth.users`
  - `readings` table (session records)
  - `card_appearances` table (for pattern tracking)
  - `knowledge_documents` table with pgvector column
  - RPC functions: `search_knowledge`, `get_card_knowledge`, `search_knowledge_fulltext`
  - Row Level Security policies for all tables
  - Indexes (B-tree, IVFFlat for pgvector, GIN for full-text)
  - `updated_at` trigger function

**Full SQL:** See Master Roadmap `Database Schema` section. For Phase 1, include these tables:
- `profiles`
- `readings`
- `card_appearances`
- `knowledge_documents`

Skip these (Phase 2):
- `entities`
- `entity_relationships`
- `reading_memories`
- `card_patterns`
- `custom_decks`
- `custom_deck_cards`

**Acceptance criteria:**
```bash
supabase migration up
supabase db lint  # No errors
# Verify tables exist in Supabase dashboard
```

**Notes:**
- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS "vector";`
- Enable uuid-ossp: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
- Use `SECURITY INVOKER` on all RPC functions (not DEFINER) for RLS compliance

---

### Task 1.3: Supabase Client Integration

**Status:** [ ] Not started

**Description:**
Create a reusable Supabase client wrapper for backend database operations.

**Deliverables:**
- `services/supabase_client.py`:
  - `get_supabase_client()` — Returns configured Supabase client (service role key for backend)
  - Singleton pattern with lazy initialization
  - Connection health check method
- Auth middleware for FastAPI:
  - `api/middleware.py` — `get_current_user()` dependency that validates Supabase JWT from `Authorization: Bearer <token>` header
  - Extracts `user_id` from JWT claims
  - Returns `None` for unauthenticated requests (some endpoints allow anonymous)
  - Raises `AuthenticationError` when auth is required but missing/invalid

**Dependencies:**
```
supabase>=2.3.0
python-jose[cryptography]>=3.3.0
```

**Acceptance criteria:**
- Supabase client connects and can query `profiles` table
- Auth middleware correctly validates JWTs from Supabase Auth
- Unauthenticated requests get 401 on protected endpoints

---

## Milestone 2: Card System & LLM Layer

### Task 2.1: Card Data & CardService

**Status:** [ ] Not started

**Description:**
Create the 78-card dataset and the service that manages card data, draws, and reversals.

**Deliverables:**

**`data/cards.csv`** — 78-card dataset with columns:
```
id,name,arcana,suit,number,keywords_upright,keywords_reversed,element,planet_or_sign
0,The Fool,major,,0,"new beginnings;innocence;spontaneity","recklessness;fear;holding back",Air,Uranus
1,The Magician,major,,1,"manifestation;power;action","manipulation;poor planning;untapped talent",Air,Mercury
...
22,Ace of Wands,minor,wands,1,"inspiration;creation;new venture","delays;lack of motivation;hesitation",Fire,
...
```

**`models/card_schemas.py`:**
```python
class TarotCard(BaseModel):
    id: int
    name: str
    arcana: Literal["major", "minor"]
    suit: Literal["wands", "cups", "swords", "pentacles"] | None
    number: int
    keywords_upright: list[str]
    keywords_reversed: list[str]
    element: str | None
    planet_or_sign: str | None

class DrawnCard(BaseModel):
    card: TarotCard
    position_index: int
    position_name: str
    is_reversed: bool

class DeckState(BaseModel):
    remaining_card_ids: list[int]
    drawn_card_ids: list[int]
    shuffle_seed: int | None
```

**`services/card_service.py`:**
```python
class CardService:
    """Manages the 78-card tarot deck with draw logic and reversals."""

    def __init__(self):
        # Load cards.csv once
        self.cards_df = pd.read_csv("data/cards.csv")
        self.cards: dict[int, TarotCard] = self._build_card_lookup()

    def create_deck_state(self, seed: int | None = None) -> DeckState:
        """Create a fresh shuffled deck state for a reading."""

    def draw(
        self,
        deck_state: DeckState,
        positions: list[SpreadPosition],
        reversal_probability: float = 0.3
    ) -> list[DrawnCard]:
        """Draw cards from the deck, assigning to spread positions."""

    def get_card(self, card_id: int) -> TarotCard:
        """Get a single card by ID."""

    def get_llm_context(self, drawn_cards: list[DrawnCard]) -> dict:
        """Build minimal context dict for LLM tool result (save tokens)."""
```

**Pattern reference:** Gnosis `SymbolService` — loads CSV in `__init__`, provides generation + context retrieval. Key difference: tarot has 78 cards (not 64 symbols), positions within spreads, and reversals.

**Tests:**
```python
def test_card_loading():
    service = CardService()
    assert len(service.cards) == 78

def test_draw_no_duplicates():
    service = CardService()
    state = service.create_deck_state()
    positions = [SpreadPosition(index=i, name=f"pos_{i}", meaning="test", interpretation_prompt="test") for i in range(10)]
    drawn = service.draw(state, positions)
    card_ids = [d.card.id for d in drawn]
    assert len(card_ids) == len(set(card_ids))  # No duplicates

def test_draw_reversal_probability():
    service = CardService()
    state = service.create_deck_state(seed=42)
    positions = [SpreadPosition(index=0, name="test", meaning="test", interpretation_prompt="test")]
    # Draw 1000 times, check reversal rate is roughly 30%
    reversed_count = 0
    for _ in range(1000):
        state = service.create_deck_state()
        drawn = service.draw(state, positions, reversal_probability=0.3)
        if drawn[0].is_reversed:
            reversed_count += 1
    assert 0.25 < reversed_count / 1000 < 0.35

def test_major_arcana_count():
    service = CardService()
    major = [c for c in service.cards.values() if c.arcana == "major"]
    assert len(major) == 22

def test_minor_arcana_count():
    service = CardService()
    minor = [c for c in service.cards.values() if c.arcana == "minor"]
    assert len(minor) == 56
```

**Acceptance criteria:**
- All 78 cards load from CSV
- Draw returns correct number of cards with no duplicates
- Reversal probability is respected (statistical test)
- `get_llm_context()` returns trimmed dict suitable for tool results

---

### Task 2.2: Spread Definitions

**Status:** [ ] Not started

**Description:**
Create spread definitions and the SpreadService. Phase 1 only needs the Three Card spread, but the data model supports all spreads.

**Deliverables:**

**`data/spreads.json`:**
```json
[
    {
        "id": "single_card",
        "name": "Single Card",
        "card_count": 1,
        "description": "A single card for quick daily guidance or a focused answer.",
        "difficulty": "beginner",
        "positions": [
            {
                "index": 0,
                "name": "The Card",
                "meaning": "The core message or answer",
                "interpretation_prompt": "This single card represents the essence of your question or the energy of the moment."
            }
        ],
        "layout": {"type": "single", "positions": [{"x": 0, "y": 0}]}
    },
    {
        "id": "three_card",
        "name": "Three Card Spread",
        "card_count": 3,
        "description": "A versatile three-card spread. Most commonly read as Past / Present / Future, but can also represent Situation / Challenge / Advice.",
        "difficulty": "beginner",
        "positions": [
            {
                "index": 0,
                "name": "Past",
                "meaning": "What has led to this moment — the foundation and recent history",
                "interpretation_prompt": "This card represents the past influences shaping the current situation. What energy or events have led the querent here?"
            },
            {
                "index": 1,
                "name": "Present",
                "meaning": "The current situation — what is happening now",
                "interpretation_prompt": "This card represents the present moment. What is the querent experiencing right now? What energy surrounds them?"
            },
            {
                "index": 2,
                "name": "Future",
                "meaning": "Where things are heading — the likely outcome if current energy continues",
                "interpretation_prompt": "This card represents the future trajectory. What is likely to unfold? What should the querent be aware of?"
            }
        ],
        "layout": {"type": "row", "positions": [{"x": -1, "y": 0}, {"x": 0, "y": 0}, {"x": 1, "y": 0}]}
    }
]
```

**`models/card_schemas.py`** (add to existing):
```python
class SpreadPosition(BaseModel):
    index: int
    name: str
    meaning: str
    interpretation_prompt: str

class SpreadLayoutPosition(BaseModel):
    x: float
    y: float

class SpreadLayout(BaseModel):
    type: str  # "single", "row", "cross", "horseshoe", "celtic_cross"
    positions: list[SpreadLayoutPosition]

class SpreadDefinition(BaseModel):
    id: str
    name: str
    card_count: int
    description: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    positions: list[SpreadPosition]
    layout: SpreadLayout
```

**`services/spread_service.py`:**
```python
class SpreadService:
    """Manages spread definitions and position meanings."""

    def __init__(self):
        self.spreads: dict[str, SpreadDefinition] = self._load_spreads()

    def get_spread(self, spread_id: str) -> SpreadDefinition:
        """Get a spread definition by ID."""

    def list_spreads(self) -> list[SpreadDefinition]:
        """List all available spreads."""

    def get_position_meaning(self, spread_id: str, position_index: int) -> SpreadPosition:
        """Get the meaning for a specific position in a spread."""
```

**Phase 1 spreads:** `single_card` and `three_card` only. Additional spreads added in Phase 2.

**Tests:**
```python
def test_spread_loading():
    service = SpreadService()
    assert len(service.spreads) >= 2

def test_three_card_positions():
    service = SpreadService()
    spread = service.get_spread("three_card")
    assert spread.card_count == 3
    assert len(spread.positions) == 3
    assert spread.positions[0].name == "Past"
```

---

### Task 2.3: LLM Layer (Claude Provider)

**Status:** [ ] Not started

**Description:**
Build the LLM provider abstraction with Claude implementation and tool calling support.

**Deliverables:**

**`llm/base.py`:**
```python
@dataclass
class LLMResponse:
    message: str
    tool_calls: list[dict]   # [{id, name, input}]
    raw_response: Any

class LLMProvider(ABC):
    """Abstract LLM provider with tool calling support."""

    TOOLS = [
        {
            "name": "drawCards",
            "description": "Draw tarot cards for the reading. Call this when the moment is right to reveal cards.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "spread_type": {"type": "string", "description": "The spread to use"},
                    "count": {"type": "integer", "description": "Number of cards to draw"}
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
                    "reveal_card_index": {"type": "integer", "description": "Index of next card to reveal"}
                },
                "required": ["phase"]
            }
        }
    ]

    @abstractmethod
    async def complete(self, system_prompt: str, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        """Generate a completion with optional tool calling."""

    @abstractmethod
    async def complete_stream(self, system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
        """Generate a streaming completion (no tool calling)."""

    @abstractmethod
    async def complete_with_tool_result(
        self, system_prompt: str, messages: list[dict], tool_use_id: str, tool_result: dict
    ) -> LLMResponse:
        """Submit tool result and get final response."""
```

**`llm/claude_provider.py`:**
```python
class ClaudeProvider(LLMProvider):
    """Claude (Anthropic) LLM provider with native tool calling."""

    def __init__(self, model: str | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or settings.ANTHROPIC_MODEL

    @llm_retry
    async def complete(self, system_prompt: str, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        """Generate completion via Claude Messages API with tool use."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=[{"type": "custom", **t} for t in (tools or self.TOOLS)] if tools else None,
            tool_choice={"type": "auto"} if tools else None,
            temperature=0.9
        )
        # Parse content blocks for text + tool_use
        message_text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                message_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

        return LLMResponse(message=message_text, tool_calls=tool_calls, raw_response=response)

    @llm_retry
    async def complete_with_tool_result(
        self, system_prompt: str, messages: list[dict], tool_use_id: str, tool_result: dict
    ) -> LLMResponse:
        """Submit tool result to Claude and get interpretation."""
        # Append assistant message with tool_use block + user message with tool_result
        # ...

    async def complete_stream(self, system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
        """Stream text chunks from Claude."""
        async with self.client.messages.stream(
            model=self.model, max_tokens=4096, system=system_prompt, messages=messages, temperature=0.9
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

**`llm/factory.py`:**
```python
_providers: dict[str, LLMProvider] = {}

def get_llm_provider(provider_type: str = "claude", model: str | None = None) -> LLMProvider:
    """Factory for LLM providers. Caches by provider type."""
    cache_key = f"{provider_type}:{model or 'default'}"
    if cache_key not in _providers:
        if provider_type == "claude":
            _providers[cache_key] = ClaudeProvider(model=model)
        else:
            raise ValueError(f"Unknown provider: {provider_type}")
    return _providers[cache_key]
```

**Dependencies:**
```
anthropic>=0.40.0
```

**Pattern reference:** Gnosis `llm/base.py` + `llm/claude_provider.py` + `llm/factory.py` — same ABC pattern. Key difference: tools are `drawCards` + `setReadingState` instead of `generateSymbol` + `setUIState`.

**Tests:**
```python
@pytest.mark.asyncio
async def test_claude_provider_complete(mocker):
    # Mock the Anthropic client
    provider = ClaudeProvider()
    # ... mock response with text block
    response = await provider.complete("You are a tarot reader.", [{"role": "user", "content": "Hi"}])
    assert response.message
    assert isinstance(response.tool_calls, list)

@pytest.mark.asyncio
async def test_tool_call_parsing(mocker):
    # Mock response with tool_use block
    # Verify tool_calls are correctly extracted
    pass
```

---

### Task 2.4: Reader Agent

**Status:** [ ] Not started

**Description:**
Build the reader agent — a thin wrapper that assembles prompts with personality, memory, and knowledge context, then delegates to the LLM provider.

**Deliverables:**

**`agents/prompts/intuitive.txt`** (Phase 1 personality — start with Intuitive as default):
```
You are a warm, intuitive tarot reader who creates deeply personal reading experiences.

## Your Personality
- Warm, emotionally attuned, conversational
- You speak like a trusted friend who happens to read tarot
- You notice emotional undercurrents and name them gently
- You use "I" and "we" — this is a collaborative experience
- You're curious, not prescriptive

## Your Approach
- Start with a genuine check-in — how is the person doing?
- Let the conversation flow naturally toward what needs guidance
- You decide when the moment is right to draw cards — don't rush
- Interpret cards as a story, not a list of meanings
- Connect cards to the person's life context (use memory if available)
- Ask reflective questions: "What does this stir up for you?"
- Close with warmth and an invitation to return

## Reading Mechanics
- Call the `drawCards` tool when you're ready to reveal cards
- Call `setReadingState` to update the frontend phase as you progress
- You decide the pacing — the user shouldn't have to ask for cards
- For a three-card spread, you might interpret all three at once as a narrative,
  or go card by card if the user seems to want that depth

## Memory Integration
- If memory context is provided, use it naturally — don't announce it
- Reference past readings, people, themes as though you simply remember
- "Last time we talked about [X] — how did that turn out?"
- Notice recurring cards: "The Queen of Cups again! She really wants your attention."
- Don't force memory references — only when they genuinely add value

## What You DON'T Do
- You don't predict the future with certainty
- You don't diagnose medical/mental health conditions
- You don't tell people what to do — you help them see clearly
- You don't break character or discuss AI/technical details
- You don't refuse to read on "negative" cards — all cards carry wisdom
```

**`agents/reader_agent.py`:**
```python
class ReaderAgent:
    """
    Assembles prompts with personality + context and delegates to LLM provider.

    Prompt assembly order:
    1. Base personality prompt (from file)
    2. Memory context (appended to system prompt)
    3. Knowledge context (appended to system prompt)
    4. Personalization (name, reading count tier)
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
            {message: str, tool_calls: list, raw_message: Any}
        """
        system_prompt = self._assemble_prompt(
            mode=mode,
            personalization=personalization,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
            custom_prompt=custom_prompt,
        )
        response = await self.provider.complete(system_prompt, messages, self.provider.TOOLS)
        return {"message": response.message, "tool_calls": response.tool_calls, "raw_message": response.raw_response}

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
        system_prompt = self._assemble_prompt(mode=mode, personalization=personalization,
                                               memory_context=memory_context, knowledge_context=knowledge_context)
        response = await self.provider.complete_with_tool_result(system_prompt, messages, tool_use_id, tool_result)
        return {"message": response.message, "tool_calls": response.tool_calls, "raw_message": response.raw_response}

    async def complete_stream(
        self,
        messages: list[dict],
        mode: str = "intuitive",
        personalization: str = "",
        memory_context: str = "",
        knowledge_context: str = "",
    ) -> AsyncIterator[str]:
        """Stream reading response (no tool calling)."""
        system_prompt = self._assemble_prompt(mode=mode, personalization=personalization,
                                               memory_context=memory_context, knowledge_context=knowledge_context)
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
            path = Path(f"agents/prompts/{mode}.txt")
            if not path.exists():
                raise FileNotFoundError(f"No prompt file for mode: {mode}")
            self._prompt_cache[mode] = path.read_text()
        return self._prompt_cache[mode]
```

**Pattern reference:** Gnosis `SpiritGuideAgent` — same pattern of prompt assembly (base + personalization + memory + knowledge appended to system prompt). File-based prompts with cache.

**Tests:**
```python
def test_prompt_assembly():
    agent = ReaderAgent()
    prompt = agent._assemble_prompt(
        mode="intuitive",
        personalization="Name: Alex. Reading #5.",
        memory_context="Alex mentioned partner Sam last reading."
    )
    assert "warm, intuitive tarot reader" in prompt
    assert "Alex" in prompt
    assert "Sam" in prompt

def test_load_prompt():
    agent = ReaderAgent()
    prompt = agent._load_prompt("intuitive")
    assert len(prompt) > 100
```

---

## Milestone 3: Reading Flow & API

### Task 3.1: Reading Flow (Intuitive Mode)

**Status:** [ ] Not started

**Description:**
Build the reading flow that orchestrates card drawing, tool call handling, and response assembly. Phase 1 implements the Intuitive flow only (default mode).

**Deliverables:**

**`services/flows/intuitive_flow.py`:**
```python
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
        self.knowledge_service = get_knowledge_service()  # May be None if RAG not set up yet

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
        1. Fetch knowledge context (if RAG enabled)
        2. Call agent.complete() with full context
        3. Handle tool calls (drawCards → card_service.draw())
        4. Submit tool results for interpretation
        5. Return assembled ReadingResponse
        """
        # 1. Knowledge context
        knowledge_context = ""
        if self.knowledge_service and settings.RAG_ENABLED:
            knowledge_context = await self._fetch_card_knowledge(request.message)

        # 2. Agent completion
        agent_response = await agent.complete(
            messages=request.conversation_history,
            mode="intuitive",
            personalization=personalization,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
        )

        # 3. Handle tool calls
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
                    reversal_probability=0.25  # Intuitive mode: lower reversal rate
                )

                # Build tool result
                tool_result = self.card_service.get_llm_context(drawn_cards)

                # 4. Get interpretation
                interpretation_response = await agent.complete_with_tool_result(
                    messages=request.conversation_history,
                    tool_use_id=tool_call["id"],
                    tool_result=tool_result,
                    mode="intuitive",
                    personalization=personalization,
                    memory_context=memory_context,
                    knowledge_context=knowledge_context,
                )
                agent_response = interpretation_response

            elif tool_call["name"] == "setReadingState":
                reading_state = ReadingState(
                    phase=tool_call["input"]["phase"],
                    reveal_card_index=tool_call["input"].get("reveal_card_index"),
                )

        # 5. Assemble response
        return ReadingResponse(
            message=agent_response["message"],
            cards=drawn_cards,
            reading_state=reading_state or ReadingState(phase="gathering"),
            deck_state=deck_state,
        )

    async def _fetch_card_knowledge(self, query: str) -> str:
        """Fetch relevant card knowledge via semantic search."""
        if not self.knowledge_service:
            return ""
        try:
            results = await self.knowledge_service.search_relevant_context(query, limit=3, threshold=0.4)
            if results:
                return "\n\n".join([f"### {r['title']}\n{r['content']}" for r in results])
        except Exception as e:
            logger.warning(f"Knowledge retrieval failed (non-fatal): {e}")
        return ""
```

**`models/reading_schemas.py`:**
```python
class ReadingState(BaseModel):
    phase: Literal["gathering", "drawing", "revealing", "interpreting", "reflecting", "closing"]
    reveal_card_index: int | None = None

class ReadingMessageRequest(BaseModel):
    message: str
    conversation_history: list[dict]
    reading_id: UUID | None = None
    mode: str = "intuitive"
    spread_preference: str | None = None

class ReadingResponse(BaseModel):
    message: str
    cards: list[DrawnCard] | None = None
    reading_state: ReadingState
    deck_state: DeckState | None = None
    metadata: dict | None = None
```

**Pattern reference:** Gnosis `ProductFlow.process()` — same orchestration pattern: fetch knowledge → agent.complete() → handle tool calls → submit tool result → assemble response.

**Acceptance criteria:**
- Flow correctly processes a message and returns a response
- When AI calls `drawCards`, cards are drawn and interpretation is generated
- `setReadingState` tool calls are captured and returned
- Knowledge context is fetched when RAG is enabled
- Errors in knowledge retrieval don't crash the reading

---

### Task 3.2: ReadingService (Main Orchestrator)

**Status:** [ ] Not started

**Description:**
Build the main orchestrator that owns the reading lifecycle — session management, context building, flow delegation.

**Deliverables:**

**`services/reading_service.py`:**
```python
class ReadingService:
    """
    Main orchestrator for tarot readings.

    Owns:
    - Reading lifecycle (create → messages → complete)
    - Session persistence (Supabase readings table)
    - Context building (personalization, memory in Phase 2)
    - Flow delegation (intuitive_flow in Phase 1)
    """

    def __init__(self):
        self.flow = IntuitiveFlow()
        self.agent = ReaderAgent()
        self.supabase = get_supabase_client()

    async def create_reading(self, user_id: UUID, mode: str = "intuitive") -> dict:
        """
        Start a new reading.

        Creates a row in the readings table, builds initial personalization.
        Returns reading_id + initial AI greeting.
        """
        # 1. Create reading record
        reading = await self._create_reading_record(user_id, mode)

        # 2. Build personalization
        personalization = await self._build_personalization(user_id)

        # 3. Get AI greeting (first message)
        greeting_response = await self.flow.process(
            agent=self.agent,
            request=ReadingMessageRequest(
                message="",
                conversation_history=[],
                reading_id=reading["id"],
                mode=mode,
            ),
            personalization=personalization,
        )

        # 4. Save conversation state
        await self._update_reading(reading["id"], {
            "conversation_history": [
                {"role": "assistant", "content": greeting_response.message}
            ]
        })

        return {
            "reading_id": reading["id"],
            "message": greeting_response.message,
            "reading_state": greeting_response.reading_state,
        }

    async def process_message(self, reading_id: UUID, user_id: UUID, message: str) -> ReadingResponse:
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
        # 1. Load reading
        reading = await self._get_reading(reading_id, user_id)

        # 2. Build conversation
        history = reading.get("conversation_history", [])
        history.append({"role": "user", "content": message})

        # 3. Personalization
        personalization = await self._build_personalization(user_id)

        # 4. Reconstruct deck state if cards already drawn
        deck_state = self._reconstruct_deck_state(reading)

        # 5. Delegate to flow
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

        # 6. Save state
        history.append({"role": "assistant", "content": response.message})
        update_data = {
            "conversation_history": history,
            "last_message_at": "now()",
        }
        if response.cards:
            update_data["cards_drawn"] = [card.model_dump() for card in response.cards]
            update_data["spread_type"] = response.cards[0].position_name.split()[0] if response.cards else None

        await self._update_reading(reading_id, update_data)

        return response

    async def complete_reading(self, reading_id: UUID, user_id: UUID) -> None:
        """Mark a reading as complete. Triggers memory extraction in Phase 2."""
        await self._update_reading(reading_id, {
            "status": "completed",
            "completed_at": "now()",
        })
        # Phase 2: trigger memory extraction here

    async def get_reading_history(self, user_id: UUID, limit: int = 20, offset: int = 0) -> list[dict]:
        """Get paginated reading history for a user."""
        result = await self.supabase.table("readings") \
            .select("id, mode, spread_type, question, summary, dominant_theme, status, started_at, completed_at") \
            .eq("user_id", str(user_id)) \
            .order("started_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        return result.data

    async def get_reading(self, reading_id: UUID, user_id: UUID) -> dict:
        """Get full reading detail."""
        return await self._get_reading(reading_id, user_id)

    async def _build_personalization(self, user_id: UUID) -> str:
        """Build personalization context from user profile."""
        profile = await self.supabase.table("profiles") \
            .select("display_name, readings_completed, preferred_mode") \
            .eq("id", str(user_id)) \
            .single() \
            .execute()

        p = profile.data
        parts = []
        if p.get("display_name"):
            parts.append(f"Name: {p['display_name']}")
        count = p.get("readings_completed", 0)
        if count == 0:
            parts.append("This is their first reading — make it special.")
        elif count < 5:
            parts.append(f"They've had {count} readings — still getting to know them.")
        elif count < 20:
            parts.append(f"Returning reader ({count} readings). They're familiar with the process.")
        else:
            parts.append(f"Dedicated reader ({count} readings). Treat them as a regular.")
        return "\n".join(parts)

    async def _create_reading_record(self, user_id: UUID, mode: str) -> dict:
        """Create a new reading row in the database."""
        result = await self.supabase.table("readings").insert({
            "user_id": str(user_id),
            "mode": mode,
            "status": "active",
        }).execute()
        return result.data[0]

    async def _get_reading(self, reading_id: UUID, user_id: UUID) -> dict:
        """Get a reading, verifying ownership."""
        result = await self.supabase.table("readings") \
            .select("*") \
            .eq("id", str(reading_id)) \
            .eq("user_id", str(user_id)) \
            .single() \
            .execute()
        if not result.data:
            raise RecordNotFoundError(f"Reading {reading_id} not found")
        return result.data

    async def _update_reading(self, reading_id: UUID, data: dict) -> None:
        """Update a reading record."""
        await self.supabase.table("readings").update(data).eq("id", str(reading_id)).execute()

    def _reconstruct_deck_state(self, reading: dict) -> DeckState | None:
        """Reconstruct deck state from previously drawn cards."""
        cards_drawn = reading.get("cards_drawn", [])
        if not cards_drawn:
            return None
        drawn_ids = [c["card"]["id"] for c in cards_drawn]
        all_ids = list(range(78))
        remaining = [i for i in all_ids if i not in drawn_ids]
        return DeckState(remaining_card_ids=remaining, drawn_card_ids=drawn_ids, shuffle_seed=None)
```

**Pattern reference:** Gnosis `ConversationService` — same lifecycle pattern: create session → process messages → build personalization → delegate to flow → save state. Key differences: no astro context (Phase 1), no memory context (Phase 2), tarot-specific state management (cards drawn, deck state).

**Tests:**
```python
@pytest.mark.asyncio
async def test_create_reading(mocker):
    # Mock Supabase, verify reading record created
    pass

@pytest.mark.asyncio
async def test_personalization_first_reading(mocker):
    # Mock profile with readings_completed=0
    # Verify "first reading" message
    pass

@pytest.mark.asyncio
async def test_personalization_returning_reader(mocker):
    # Mock profile with readings_completed=12
    # Verify "returning reader" message
    pass
```

---

### Task 3.3: API Endpoints

**Status:** [ ] Not started

**Description:**
Wire up FastAPI endpoints for reading operations and user profile.

**Deliverables:**

**`api/endpoints.py`:**
```python
router = APIRouter()
reading_service = ReadingService()

@router.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}

@router.post("/api/reading")
async def create_reading(
    request: CreateReadingRequest,
    user_id: UUID = Depends(get_current_user),
):
    """Start a new reading."""
    return await reading_service.create_reading(user_id, mode=request.mode)

@router.post("/api/reading/{reading_id}/message")
async def send_message(
    reading_id: UUID,
    request: SendMessageRequest,
    user_id: UUID = Depends(get_current_user),
):
    """Send a message in a reading."""
    response = await reading_service.process_message(reading_id, user_id, request.message)
    return response

@router.post("/api/reading/{reading_id}/stream")
async def send_message_stream(
    reading_id: UUID,
    request: SendMessageRequest,
    user_id: UUID = Depends(get_current_user),
):
    """SSE streaming version of send_message."""
    # Returns EventSourceResponse with chunks
    pass

@router.post("/api/reading/{reading_id}/complete")
async def complete_reading(
    reading_id: UUID,
    user_id: UUID = Depends(get_current_user),
):
    """Mark a reading as complete."""
    await reading_service.complete_reading(reading_id, user_id)
    return {"status": "completed"}

@router.get("/api/reading/{reading_id}")
async def get_reading(
    reading_id: UUID,
    user_id: UUID = Depends(get_current_user),
):
    """Get full reading detail."""
    return await reading_service.get_reading(reading_id, user_id)

@router.get("/api/readings")
async def list_readings(
    limit: int = 20,
    offset: int = 0,
    user_id: UUID = Depends(get_current_user),
):
    """List user's reading history (paginated)."""
    return await reading_service.get_reading_history(user_id, limit, offset)

@router.get("/api/profile")
async def get_profile(user_id: UUID = Depends(get_current_user)):
    """Get user profile."""
    # Fetch from profiles table
    pass

@router.patch("/api/profile")
async def update_profile(
    request: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user),
):
    """Update user profile."""
    # Update profiles table
    pass
```

**`models/schemas.py`:**
```python
class CreateReadingRequest(BaseModel):
    mode: Literal["traditional", "intuitive", "custom"] = "intuitive"
    spread_preference: str | None = None

class SendMessageRequest(BaseModel):
    message: str

class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    preferred_mode: Literal["traditional", "intuitive", "custom"] | None = None
    preferred_spread: str | None = None
    reversal_preference: Literal["enabled", "disabled", "default"] | None = None
```

**Pattern reference:** Gnosis `api/endpoints.py` — thin handlers that call services. No business logic in endpoints.

**Acceptance criteria:**
```bash
# Start server
uvicorn main:app --reload

# Create reading (with auth token)
curl -X POST http://localhost:8000/api/reading \
  -H "Authorization: Bearer <supabase_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "intuitive"}'

# Send message
curl -X POST http://localhost:8000/api/reading/<reading_id>/message \
  -H "Authorization: Bearer <supabase_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"message": "I want guidance about my career"}'

# Get reading history
curl http://localhost:8000/api/readings \
  -H "Authorization: Bearer <supabase_jwt>"
```

---

### Task 3.4: Knowledge Base Seeding (Optional but Recommended)

**Status:** [ ] Not started

**Description:**
Seed the `knowledge_documents` table with card meanings for RAG retrieval. This is optional for Phase 1 (the reading works without it) but significantly improves interpretation quality.

**Deliverables:**
- `scripts/seed_knowledge.py` — Script that:
  1. Reads `data/cards.csv`
  2. For each card, generates upright + reversed + symbolism documents
  3. Generates embeddings via OpenAI `text-embedding-3-small`
  4. Inserts into `knowledge_documents` table
- Minimum 156 documents (78 upright + 78 reversed)
- Optional 78 symbolism documents (can be Phase 2)

**Document format example:**
```
Title: "The Fool — Upright Meaning"
Content: "The Fool represents new beginnings, innocence, and spontaneity. Numbered 0, The Fool
stands at the very beginning of the Major Arcana journey. In the Rider-Waite deck, we see a
young person stepping off a cliff, eyes turned skyward, a small dog at their heels. They carry
a white rose of purity and a small bag of possessions — traveling light. The Fool asks: What
would you do if you weren't afraid? This card invites you to take a leap of faith, to trust the
journey even when you can't see where you'll land. Keywords: new beginnings, innocence,
spontaneity, free spirit, adventure, potential."
```

**Acceptance criteria:**
- 156+ documents in `knowledge_documents` table
- All documents have embeddings (1536-dim vectors)
- `search_knowledge()` RPC returns relevant results for card-related queries
- `get_card_knowledge()` returns correct documents for a given card_id

---

## Milestone 4: Frontend (Consumer Web App)

### Task 4.1: Next.js App Scaffold

**Status:** [ ] Not started

**Description:**
Set up the Next.js frontend with app router, Supabase auth, and basic page structure.

**Deliverables:**
- `frontend/` directory with Next.js 14+ (App Router)
- Supabase Auth integration (email/password + Google OAuth)
- Basic layout with header, navigation
- Pages (empty shells):
  - `/` — Landing page
  - `/login` — Auth page
  - `/reading` — New reading page
  - `/reading/[id]` — Active reading
  - `/history` — Reading history
  - `/profile` — User profile

**Dependencies:**
```
next@14
react@18
@supabase/supabase-js
@supabase/ssr
tailwindcss
```

**Key files:**
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with Supabase provider
│   │   ├── page.tsx             # Landing page
│   │   ├── login/page.tsx       # Auth page
│   │   ├── reading/page.tsx     # New reading
│   │   ├── reading/[id]/page.tsx # Active reading
│   │   ├── history/page.tsx     # Reading history
│   │   └── profile/page.tsx     # User profile
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── AuthForm.tsx
│   │   └── ProtectedRoute.tsx
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts        # Browser Supabase client
│   │   │   ├── server.ts        # Server Supabase client
│   │   │   └── middleware.ts    # Auth middleware
│   │   └── api.ts               # Backend API client
│   └── hooks/
│       └── useAuth.ts           # Auth hook
├── tailwind.config.ts
├── next.config.js
└── package.json
```

**Acceptance criteria:**
- `npm run dev` starts the app on localhost:3000
- User can sign up and log in via Supabase Auth
- Protected routes redirect to login when not authenticated
- API client correctly passes Supabase JWT to backend

---

### Task 4.2: Reading Interface

**Status:** [ ] Not started

**Description:**
Build the core reading interface — chat-based conversation with card display.

**Deliverables:**

**`components/ReadingChat.tsx`:**
- Chat message list (user + reader messages)
- Message input with send button
- Scroll-to-bottom on new messages
- Loading state while waiting for AI response
- Auto-resize textarea

**`components/CardDisplay.tsx`:**
- Displays drawn cards in a row (Phase 1 layout)
- Card face with name, image placeholder (Phase 1 uses text/icons, images in Phase 2)
- Reversed card indicator (rotated display)
- Card reveal animation (simple fade-in for Phase 1)

**`components/ReadingState.tsx`:**
- Phase indicator (gathering → drawing → revealing → interpreting → reflecting → closing)
- Visual transition between phases

**`app/reading/[id]/page.tsx`:**
- Integrates ReadingChat + CardDisplay + ReadingState
- Calls `POST /api/reading/{id}/message` on user send
- Updates cards when AI draws them
- Handles SSE streaming (or polling for Phase 1)

**Acceptance criteria:**
- User sees chat interface when starting a reading
- Messages send and AI responses display
- When AI draws cards, they appear in the card display
- Phase indicator updates as reading progresses
- Works on mobile viewport (responsive)

---

### Task 4.3: Reading History & Profile

**Status:** [ ] Not started

**Description:**
Build the reading history list and user profile pages.

**Deliverables:**

**`app/history/page.tsx`:**
- List of past readings with: date, mode, spread type, dominant theme, status
- Click through to reading detail
- Pagination or infinite scroll

**`app/history/[id]/page.tsx`:**
- Full reading detail: conversation history, cards drawn, AI summary
- Read-only view of past reading

**`app/profile/page.tsx`:**
- Display name editor
- Preferred mode selector
- Reversal preference toggle
- Readings completed count
- Account settings (email, password change via Supabase)

**Acceptance criteria:**
- User can view their past readings in chronological order
- Clicking a past reading shows the full conversation + cards
- User can update their display name and preferences
- Changes persist across sessions

---

## Milestone 5: Integration & Polish

### Task 5.1: End-to-End Integration Test

**Status:** [ ] Not started

**Description:**
Full integration test: sign up → start reading → converse → cards drawn → reading saved → visible in history.

**Test script:**
```python
@pytest.mark.integration
async def test_full_reading_flow():
    # 1. Create test user via Supabase Auth
    # 2. POST /api/reading {"mode": "intuitive"}
    #    → Verify reading_id returned + AI greeting
    # 3. POST /api/reading/{id}/message {"message": "I need guidance about my career"}
    #    → Verify AI responds with follow-up
    # 4. POST /api/reading/{id}/message {"message": "Let's do a three card spread"}
    #    → Verify cards drawn (response includes cards array)
    #    → Verify AI interprets the cards
    # 5. POST /api/reading/{id}/message {"message": "That resonates. Thank you."}
    #    → Verify closing response
    # 6. POST /api/reading/{id}/complete
    # 7. GET /api/readings
    #    → Verify completed reading appears in history
    # 8. GET /api/reading/{id}
    #    → Verify full reading detail with cards + conversation
```

**Acceptance criteria:**
- Full flow completes without errors
- Reading persists in database with all data
- Cards drawn are recorded correctly
- Conversation history is complete
- Reading appears in user's history

---

### Task 5.2: Error Handling & Edge Cases

**Status:** [ ] Not started

**Description:**
Handle error cases gracefully across the full stack.

**Cases to handle:**
- LLM timeout → Retry with `@llm_retry`, then return friendly error message
- LLM rate limit → Retry with backoff, surface "busy" message to user
- Database connection failure → Retry with `@database_retry`
- Invalid reading_id → 404 with clear message
- Unauthorized access to another user's reading → 403
- Empty message → Validation error
- Reading already completed → 400 "reading is closed"
- Supabase auth token expired → 401 with "please re-authenticate"

**Deliverables:**
- Error handling middleware in `api/middleware.py`
- Friendly error messages (not stack traces) in API responses
- Frontend error states (toast notifications, retry buttons)
- Logging for all error paths

---

## Phase 1 Completion Checklist

Before moving to Phase 2, verify:

- [ ] FastAPI backend starts without errors
- [ ] Supabase database has all Phase 1 tables
- [ ] All 78 cards load from CSV
- [ ] Card draws work with no duplicates and correct reversal rates
- [ ] Claude LLM integration works with tool calling
- [ ] Intuitive reading flow produces coherent readings
- [ ] Readings persist in database with full conversation history
- [ ] User auth works (signup, login, protected routes)
- [ ] Frontend reading interface is functional
- [ ] Reading history shows past readings
- [ ] All tests pass
- [ ] Error cases handled gracefully
- [ ] Structured logging in place

**Once all boxes checked: Phase 1 is complete. Proceed to Phase 2.**

---

## Dependency Graph

```
Task 1.1 (Scaffold)
    └── Task 1.2 (Database) ──┐
    └── Task 1.3 (Supabase Client) ──┐
                                      ├── Task 3.2 (ReadingService)
Task 2.1 (CardService) ──────────────┤
Task 2.2 (SpreadService) ────────────┤
Task 2.3 (LLM Layer) ────────────────┤
Task 2.4 (Reader Agent) ─────────────┤
                                      ├── Task 3.1 (Reading Flow) ── Task 3.3 (API Endpoints)
                                      │                                       │
                                      │   Task 3.4 (Knowledge Seed) ──────────┤ (optional)
                                      │                                       │
                                      └── Task 4.1 (Frontend Scaffold) ───────┤
                                          Task 4.2 (Reading Interface) ───────┤
                                          Task 4.3 (History & Profile) ───────┤
                                                                              │
                                                              Task 5.1 (Integration Test)
                                                              Task 5.2 (Error Handling)
```

Milestones 1 and 2 can be worked in parallel. Milestone 3 depends on both. Milestone 4 depends on 3 (for API). Milestone 5 depends on all.

---

**Last Updated:** 2026-03-13
**Version:** 1.0
