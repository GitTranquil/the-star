# Tarot Agent — Phase 2: Full Experience

**Goal:** The complete premium tarot reading experience — all spreads, all modes, full memory
system, reading history with patterns, and custom decks.

**Prerequisite:** Phase 1 complete (working 3-card reading with auth and session persistence).

**Completion criteria:** A returning user gets a personalized reading that references their past
readings, recurring cards, and life context. All three reading modes work. Celtic Cross spread
available. Custom deck uploads work. Card pattern analytics visible.

**Estimated tasks:** 12 tasks across 4 milestones.

---

## Milestone 6: Memory System

The memory system is the core differentiator. It makes every reading build on the last.

### Task 6.1: Entity Extraction Service

**Status:** [ ] Not started

**Description:**
Build the service that extracts structured entities from completed reading conversations.

**Source pattern:** Gnosis `EntityExtractionService` — uses a small/fast LLM with structured JSON output to extract entities, relationships, and session memory from transcripts. Same three-section extraction, adapted for tarot domain.

**Deliverables:**

**`services/memory/extraction_service.py`:**
```python
class ExtractionService:
    """
    Extracts structured entities and reading memories from completed conversations.

    Uses claude-haiku-4-5-20251001 with structured JSON output.
    Runs asynchronously after reading completion — never blocks the user.
    """

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.EXTRACTION_MODEL  # claude-haiku-4-5-20251001

    async def should_extract(self, conversation: list[dict]) -> bool:
        """
        Determine if a conversation has enough content for extraction.

        Rules:
        - At least 4 user messages
        - At least 2 substantive messages (> 3 words)
        - Reading must include card draw
        """

    async def extract_from_reading(self, conversation: list[dict], cards_drawn: list[dict]) -> ExtractionResult:
        """
        Extract entities, reading memory, and patterns from a completed reading.

        Returns ExtractionResult with:
        - entities: people, places, jobs, etc. mentioned
        - reading_memory: themes, emotional arc, card significance
        - relationships: entity-to-user relationships
        - card_patterns: recurring cards/suits observed
        """
        transcript = self._format_transcript(conversation)
        cards_context = self._format_cards(cards_drawn)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.3,
            system="You extract structured data from tarot reading transcripts. Return valid JSON only.",
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(transcript=transcript, cards=cards_context)
            }],
        )

        return self._parse_extraction(response.content[0].text)
```

**`agents/extraction_prompt.txt`:**
```
Given this tarot reading conversation and the cards drawn, extract structured data.

## Conversation:
{transcript}

## Cards Drawn:
{cards}

## Extract the following as JSON:

{{
    "entities": [
        {{
            "type": "person|pet|place|job|project|relationship|health|event|thing",
            "name": "entity name",
            "aliases": ["nickname", "alternate reference"],
            "attributes": {{
                "attribute_name": {{
                    "value": "attribute value",
                    "confidence": 0.0-1.0
                }}
            }},
            "relationship_to_user": "partner|mother|boss|friend|etc",
            "confidence": 0.0-1.0
        }}
    ],
    "reading_memory": {{
        "core_theme": "The central theme of this reading",
        "emotional_arc": "How the user's emotional state evolved during the reading",
        "key_insights": ["insight 1", "insight 2"],
        "card_significance": {{
            "most_impactful_card": "Card Name",
            "user_reaction": "How they reacted to this card",
            "recurring_reference": "Any card/theme they referenced from past readings"
        }},
        "unfinished_threads": ["Things left unexplored that could come up next time"],
        "session_summary": "2-3 sentence summary of this reading"
    }},
    "relationships": [
        {{
            "entity_name": "Name",
            "relationship_type": "partner_of|child_of|colleague_of|pet_of|friend_of",
            "relationship_to_user": "partner|child|colleague|pet|friend",
            "confidence": 0.0-1.0
        }}
    ],
    "card_patterns": {{
        "dominant_suit": "wands|cups|swords|pentacles|null",
        "repeated_from_past": ["Card names that user mentioned appearing before"],
        "arcana_balance": "major_heavy|minor_heavy|balanced"
    }}
}}

Rules:
- Only include entities with confidence >= 0.5
- Only include attributes with confidence >= 0.7
- If the user didn't mention anything personal, entities can be empty
- Always fill reading_memory — every reading has themes and insights
- card_patterns.repeated_from_past only if user explicitly mentioned past appearances
```

**`models/memory_schemas.py`:**
```python
class EntityType(str, Enum):
    PERSON = "person"
    PET = "pet"
    PLACE = "place"
    JOB = "job"
    PROJECT = "project"
    RELATIONSHIP = "relationship"
    HEALTH = "health"
    EVENT = "event"
    THING = "thing"

class EntityStatus(str, Enum):
    ACTIVE = "active"
    AGING = "aging"
    ARCHIVED = "archived"

class AttributeValue(BaseModel):
    value: str
    confidence: float
    source_reading_id: UUID | None = None
    added_at: datetime | None = None

class ExtractedEntity(BaseModel):
    type: EntityType
    name: str
    aliases: list[str] = []
    attributes: dict[str, AttributeValue] = {}
    relationship_to_user: str | None = None
    confidence: float

class ReadingMemory(BaseModel):
    core_theme: str
    emotional_arc: str
    key_insights: list[str] = []
    card_significance: dict = {}
    unfinished_threads: list[str] = []
    session_summary: str

class CardPatterns(BaseModel):
    dominant_suit: str | None = None
    repeated_from_past: list[str] = []
    arcana_balance: str | None = None

class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = []
    reading_memory: ReadingMemory | None = None
    relationships: list[dict] = []
    card_patterns: CardPatterns | None = None
    skipped: bool = False
    skip_reason: str | None = None
```

**Tests:**
```python
@pytest.mark.asyncio
async def test_should_extract_minimum_messages():
    service = ExtractionService()
    short_convo = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    assert await service.should_extract(short_convo) == False

@pytest.mark.asyncio
async def test_extraction_parses_entities(mocker):
    # Mock Claude response with sample JSON
    # Verify entities parsed correctly with confidence filtering
    pass
```

**Acceptance criteria:**
- Extraction produces valid `ExtractionResult` from a real reading transcript
- Entities below confidence 0.5 are filtered out
- Attributes below confidence 0.7 are filtered out
- Reading memory is always populated (even for impersonal readings)
- Haiku keeps extraction cost low (< $0.01 per reading)

---

### Task 6.2: Entity Storage Service

**Status:** [ ] Not started

**Description:**
Store extracted entities with upsert logic — merge new information into existing entities, don't create duplicates.

**Prerequisite:** Database migration for Phase 2 memory tables.

**Deliverables:**

**`supabase/migrations/00002_memory_tables.sql`:**
Add tables from Master Roadmap that were skipped in Phase 1:
- `entities`
- `entity_relationships`
- `reading_memories`
- `card_patterns`

With all indexes, RLS policies, and the `get_user_card_stats` RPC function.

**`services/memory/storage_service.py`:**
```python
class EntityStorageService:
    """
    Stores extraction results with intelligent upsert logic.

    Key behavior:
    - Entities are upserted by (user_id, LOWER(name)) — no duplicates
    - Aliases are checked for matches: if "Sam" is an alias for "Samuel", merge
    - Attributes merge (new values overwrite old if higher confidence)
    - Relationships are upserted by (entity_id, relationship_type)
    - Reading memories are always inserted (one per reading)
    """

    async def store_extraction_result(
        self, user_id: UUID, reading_id: UUID, result: ExtractionResult
    ) -> None:
        """Store all extracted data from a reading."""
        # 1. Upsert entities
        for entity in result.entities:
            await self._upsert_entity(user_id, reading_id, entity)

        # 2. Store relationships
        for rel in result.relationships:
            await self._upsert_relationship(user_id, reading_id, rel)

        # 3. Store reading memory
        if result.reading_memory:
            await self._store_reading_memory(user_id, reading_id, result.reading_memory)

        # 4. Update card patterns
        if result.card_patterns:
            await self._update_card_patterns(user_id, reading_id, result.card_patterns)

    async def _upsert_entity(self, user_id: UUID, reading_id: UUID, entity: ExtractedEntity) -> UUID:
        """
        Upsert an entity. Check by name AND aliases for existing match.

        Logic:
        1. Search for entity where name or aliases match (case-insensitive)
        2. If found: merge attributes, increment mentioned_count, update last_mentioned
        3. If not found: create new entity
        """

    async def _upsert_relationship(self, user_id: UUID, reading_id: UUID, rel: dict) -> None:
        """Upsert an entity relationship."""

    async def _store_reading_memory(self, user_id: UUID, reading_id: UUID, memory: ReadingMemory) -> None:
        """Insert episodic reading memory (always new row — one per reading)."""

    async def _update_card_patterns(self, user_id: UUID, reading_id: UUID, patterns: CardPatterns) -> None:
        """Update aggregated card pattern data for the user."""
```

**Pattern reference:** Gnosis `EntityStorageService` — same upsert-by-name logic with alias checking, attribute merging, and confidence-based overwrites.

**Tests:**
```python
@pytest.mark.asyncio
async def test_entity_upsert_creates_new(mocker):
    # First mention of "Sam" → creates entity
    pass

@pytest.mark.asyncio
async def test_entity_upsert_merges_existing(mocker):
    # Second mention of "Sam" → merges attributes, increments count
    pass

@pytest.mark.asyncio
async def test_alias_matching(mocker):
    # "Samuel" exists with alias "Sam" → "Sam" mention merges into Samuel
    pass
```

---

### Task 6.3: Context Selection & Memory Provider

**Status:** [ ] Not started

**Description:**
Build the context selection service that assembles relevant memory for injection into new readings.

**Deliverables:**

**`services/memory/context_service.py`:**
```python
class ContextSelectionService:
    """
    Selects and formats relevant memory context for a new reading.

    Selection strategy:
    1. Active entities (sorted by recency × mention frequency)
    2. Recent reading memories (last 5 readings)
    3. Card pattern data (most drawn cards, dominant suits)
    4. Optional: semantic search for entities relevant to current question
    """

    async def build_memory_context(
        self, user_id: UUID, current_message: str = "", include_debug: bool = False
    ) -> tuple[str, dict | None]:
        """
        Build formatted memory context for system prompt injection.

        Returns:
            (formatted_context_string, debug_info_or_None)
        """
        # 1. Fetch active entities
        entities = await self._fetch_entities(user_id)

        # 2. Fetch recent reading memories
        memories = await self._fetch_recent_memories(user_id, limit=5)

        # 3. Fetch card patterns
        patterns = await self._fetch_card_patterns(user_id)

        # 4. Optional: semantic relevance filtering
        if settings.SEMANTIC_MEMORY_ENABLED and current_message:
            entities = await self._filter_by_relevance(entities, current_message)

        # 5. Format for prompt injection
        context = self._format_context(entities, memories, patterns)
        debug = self._build_debug(entities, memories, patterns) if include_debug else None

        return context, debug

    def _format_context(
        self, entities: list[dict], memories: list[dict], patterns: list[dict]
    ) -> str:
        """
        Format memory into a natural-language context block.

        Example output:
        ---
        People in their life:
        - Sam (partner) — works in tech, mentioned in 4 readings
        - Mom (mother) — health concerns mentioned recently

        Recent reading themes:
        - 3 days ago: Career crossroads, drew The Chariot + Three of Pentacles
        - 2 weeks ago: Relationship communication, recurring Queen of Cups

        Card patterns:
        - Most drawn: The Empress (5 times), Queen of Cups (4 times)
        - Dominant suit: Cups (emotional/relational focus)
        - The Tower has appeared in 3 of last 5 readings
        ---
        """
```

**`services/memory_service.py`** (update — orchestrator):
```python
class MemoryService:
    """
    Orchestrates the full memory lifecycle: extraction → storage → context.

    Called by ReadingService at two points:
    1. On reading completion → extract_and_store()
    2. On new reading start → build_context()
    """

    def __init__(self):
        self.extraction = ExtractionService()
        self.storage = EntityStorageService()
        self.context = ContextSelectionService()

    async def extract_and_store(self, user_id: UUID, reading_id: UUID, conversation: list[dict], cards_drawn: list[dict]) -> None:
        """Extract entities from completed reading and store them."""
        if not await self.extraction.should_extract(conversation):
            logger.info(f"Skipping extraction for reading {reading_id} (insufficient content)")
            return

        result = await self.extraction.extract_from_reading(conversation, cards_drawn)
        await self.storage.store_extraction_result(user_id, reading_id, result)

        # Mark reading as extracted
        await self.supabase.table("readings").update({
            "memory_extracted_at": "now()"
        }).eq("id", str(reading_id)).execute()

        logger.info(f"Memory extracted for reading {reading_id}: {len(result.entities)} entities, "
                     f"{'reading memory stored' if result.reading_memory else 'no reading memory'}")

    async def build_context(self, user_id: UUID, current_message: str = "") -> str:
        """Build memory context for a new reading."""
        context, _ = await self.context.build_memory_context(user_id, current_message)
        return context

    async def check_and_extract_previous(self, user_id: UUID) -> None:
        """
        On new reading start, check if previous reading needs extraction.
        Ensures memory is available before the new reading begins.
        """
        result = await self.supabase.table("readings") \
            .select("id, conversation_history, cards_drawn") \
            .eq("user_id", str(user_id)) \
            .is_("memory_extracted_at", "null") \
            .eq("status", "completed") \
            .order("started_at", desc=True) \
            .limit(1) \
            .execute()

        if result.data:
            reading = result.data[0]
            await self.extract_and_store(
                user_id, reading["id"],
                reading["conversation_history"],
                reading.get("cards_drawn", [])
            )

    async def apply_memory_decay(self) -> None:
        """
        Decay stale entities. Run as a background cron job.

        Active → Aging: 90 days without mention
        Aging → Archived: 180 days without mention
        Core entities (pets, family): 2x decay threshold
        """
```

**Integration with ReadingService (update Task 3.2):**
```python
# In ReadingService.create_reading():
# 1. Check and extract previous reading
await self.memory_service.check_and_extract_previous(user_id)

# 2. Build memory context
memory_context = await self.memory_service.build_context(user_id)

# Pass memory_context to flow.process()

# In ReadingService.complete_reading():
# Trigger extraction (async, non-blocking)
asyncio.create_task(
    self.memory_service.extract_and_store(user_id, reading_id, conversation, cards_drawn)
)
```

**Pattern reference:** Gnosis `MemoryOrchestrator` + `ContextSelectionService` — same lifecycle (check previous → extract → store → build context). Key additions: card pattern tracking, reading-specific memory (not just generic session memory).

**Acceptance criteria:**
- Memory context includes entities, recent readings, and card patterns
- Returning user sees context from past readings injected into new reading
- AI naturally references past context ("Last time we talked about...")
- Memory extraction runs without blocking the user
- Memory decay works on schedule

---

## Milestone 7: Full Spread & Mode Support

### Task 7.1: All Spreads

**Status:** [ ] Not started

**Description:**
Add remaining spread definitions to `data/spreads.json` and update SpreadService.

**New spreads:**

**Five Card Cross:**
```json
{
    "id": "five_card_cross",
    "name": "Five Card Cross",
    "card_count": 5,
    "description": "A cross-shaped spread with a central theme card surrounded by four influences.",
    "difficulty": "intermediate",
    "positions": [
        {"index": 0, "name": "Central Theme", "meaning": "The core issue or energy at the heart of the matter", "interpretation_prompt": "This is the central card — the essence of what the querent is dealing with."},
        {"index": 1, "name": "Past Influence", "meaning": "What has led to this situation", "interpretation_prompt": "This card sits to the left — past events and energies that built the foundation."},
        {"index": 2, "name": "Future Influence", "meaning": "Where this energy is heading", "interpretation_prompt": "This card sits to the right — the likely trajectory of the situation."},
        {"index": 3, "name": "Above (Conscious)", "meaning": "What the querent is consciously aware of", "interpretation_prompt": "This card sits above — what the querent knows and is thinking about."},
        {"index": 4, "name": "Below (Unconscious)", "meaning": "Hidden influences, subconscious factors", "interpretation_prompt": "This card sits below — what is working beneath the surface, not yet seen."}
    ],
    "layout": {"type": "cross", "positions": [{"x": 0, "y": 0}, {"x": -1, "y": 0}, {"x": 1, "y": 0}, {"x": 0, "y": -1}, {"x": 0, "y": 1}]}
}
```

**Horseshoe (7 cards):**
```json
{
    "id": "horseshoe",
    "name": "Horseshoe Spread",
    "card_count": 7,
    "description": "A seven-card spread in a horseshoe arc, tracing a journey from past to future with hidden influences.",
    "difficulty": "intermediate",
    "positions": [
        {"index": 0, "name": "Past", "meaning": "Recent past events influencing the situation", "interpretation_prompt": "The starting point — what has already happened."},
        {"index": 1, "name": "Present", "meaning": "Current state of affairs", "interpretation_prompt": "Where the querent stands right now."},
        {"index": 2, "name": "Hidden Influences", "meaning": "Unseen forces at work", "interpretation_prompt": "What's operating beneath awareness — subconscious or external factors."},
        {"index": 3, "name": "Obstacles", "meaning": "Challenges or resistance", "interpretation_prompt": "What stands in the way — internal or external blocks."},
        {"index": 4, "name": "Environment", "meaning": "External factors and other people's influence", "interpretation_prompt": "The world around the querent — people, circumstances, timing."},
        {"index": 5, "name": "Advice", "meaning": "Recommended approach or action", "interpretation_prompt": "What the cards suggest the querent consider or do."},
        {"index": 6, "name": "Outcome", "meaning": "Most likely outcome on current trajectory", "interpretation_prompt": "Where things are heading if the current energy continues."}
    ],
    "layout": {"type": "horseshoe", "positions": [{"x": -3, "y": 1}, {"x": -2, "y": 0}, {"x": -1, "y": -1}, {"x": 0, "y": -1.5}, {"x": 1, "y": -1}, {"x": 2, "y": 0}, {"x": 3, "y": 1}]}
}
```

**Celtic Cross (10 cards):**
```json
{
    "id": "celtic_cross",
    "name": "Celtic Cross",
    "card_count": 10,
    "description": "The most comprehensive traditional tarot spread. A complete picture of a situation with deep insight into influences, hopes, and outcome.",
    "difficulty": "advanced",
    "positions": [
        {"index": 0, "name": "The Present", "meaning": "The current situation and central issue", "interpretation_prompt": "The heart of the matter — what the querent is dealing with right now."},
        {"index": 1, "name": "The Challenge", "meaning": "What crosses the querent — the main obstacle or complementary energy", "interpretation_prompt": "This card crosses the first — it can be an obstacle, a complementary force, or a secondary influence."},
        {"index": 2, "name": "The Foundation", "meaning": "The root cause or basis of the situation", "interpretation_prompt": "Below the central cards — the deep foundation, what this situation is really built on."},
        {"index": 3, "name": "The Recent Past", "meaning": "Events or energies that are passing away", "interpretation_prompt": "To the left — what's just happened or is fading in influence."},
        {"index": 4, "name": "The Crown", "meaning": "The best possible outcome, or what the querent is striving for", "interpretation_prompt": "Above — the ideal, the aspiration, or the energy the querent is reaching toward."},
        {"index": 5, "name": "The Near Future", "meaning": "What is coming into being in the near term", "interpretation_prompt": "To the right — what is about to manifest or enter the querent's life."},
        {"index": 6, "name": "The Self", "meaning": "How the querent sees themselves in this situation", "interpretation_prompt": "The first card in the staff — the querent's self-image and attitude."},
        {"index": 7, "name": "Environment", "meaning": "How others see the querent, external influences", "interpretation_prompt": "External perceptions and influences — the world's view of the situation."},
        {"index": 8, "name": "Hopes and Fears", "meaning": "The querent's deepest hopes or fears about the outcome", "interpretation_prompt": "What the querent hopes for or fears — often these are two sides of the same coin."},
        {"index": 9, "name": "The Outcome", "meaning": "The final outcome, synthesis of all energies", "interpretation_prompt": "The culmination — where all these energies converge. Not a fixed fate, but the most likely result of the current trajectory."}
    ],
    "layout": {
        "type": "celtic_cross",
        "positions": [
            {"x": -1, "y": 0}, {"x": -1, "y": 0, "rotation": 90},
            {"x": -1, "y": 1}, {"x": -2, "y": 0}, {"x": -1, "y": -1}, {"x": 0, "y": 0},
            {"x": 2, "y": 1.5}, {"x": 2, "y": 0.5}, {"x": 2, "y": -0.5}, {"x": 2, "y": -1.5}
        ]
    }
}
```

**Relationship Spread (6 cards):**
```json
{
    "id": "relationship",
    "name": "Relationship Spread",
    "card_count": 6,
    "description": "Explores the dynamic between two people — their perspectives, challenges, and the bridge between them.",
    "difficulty": "intermediate",
    "positions": [
        {"index": 0, "name": "You", "meaning": "Your energy and perspective in this relationship", "interpretation_prompt": "How the querent shows up in this relationship — their energy, needs, and perspective."},
        {"index": 1, "name": "The Other", "meaning": "The other person's energy and perspective", "interpretation_prompt": "How the other person shows up — their energy, needs, and what they bring."},
        {"index": 2, "name": "The Connection", "meaning": "The nature of the bond between you", "interpretation_prompt": "What unites these two — the essence of their connection."},
        {"index": 3, "name": "Your Challenge", "meaning": "What you need to work on", "interpretation_prompt": "What the querent needs to address or grow through in this relationship."},
        {"index": 4, "name": "Their Challenge", "meaning": "What the other person needs to work on", "interpretation_prompt": "What the other person may need to address (as seen through the cards)."},
        {"index": 5, "name": "The Path Forward", "meaning": "Guidance for the relationship's evolution", "interpretation_prompt": "Where this relationship can go — advice for both parties."}
    ],
    "layout": {"type": "relationship", "positions": [{"x": -1.5, "y": 0}, {"x": 1.5, "y": 0}, {"x": 0, "y": 0}, {"x": -1.5, "y": 1}, {"x": 1.5, "y": 1}, {"x": 0, "y": -1}]}
}
```

**Tests:**
```python
def test_all_spreads_load():
    service = SpreadService()
    assert len(service.spreads) == 6  # single, three, five_cross, horseshoe, celtic, relationship

def test_celtic_cross_positions():
    service = SpreadService()
    spread = service.get_spread("celtic_cross")
    assert spread.card_count == 10
    assert len(spread.positions) == 10
    assert spread.positions[1].name == "The Challenge"
```

---

### Task 7.2: Traditional Flow

**Status:** [ ] Not started

**Description:**
Implement the Traditional (Rider-Waite) reading flow with formal voice and structured interpretation.

**Deliverables:**

**`agents/prompts/traditional.txt`:**
```
You are a learned tarot reader in the Rider-Waite tradition. Your readings are precise,
symbolic, and deeply rooted in traditional tarot scholarship.

## Your Personality
- Formal yet accessible — scholarly without being cold
- You reference specific Rider-Waite imagery in your interpretations
- You note elemental dignities, numerological correspondences, and astrological associations
- You speak with authority but not rigidity
- You use "one" and "the querent" more than "you" — subtly formal

## Your Approach
- Open with a brief, dignified greeting
- Ask the querent to formulate a clear question (traditional readers value precision)
- Recommend a spread appropriate to the question's complexity
- Include a brief ritual framing: "Let us center ourselves..."
- Interpret position by position, in order
- Note reversals with their traditional adjusted meanings
- Synthesize all positions into a unified reading
- Provide concrete guidance rooted in the cards' counsel
- Close formally with a summary and blessing

## Interpretation Style
- Reference specific imagery: "In the Rider-Waite depiction, we see the figure of Justice
  holding scales in the left hand..."
- Note elemental interactions between cards
- Discuss numerological significance (e.g., three = creation, synthesis)
- Mention astrological correspondences when relevant
- Address reversals as blocked or internalized energy, not simply "negative"

## Reading Mechanics
- Call `drawCards` after the question is clear and spread is chosen
- Call `setReadingState` to mark phase transitions
- Interpret cards in position order (don't skip around)
- For Celtic Cross, maintain the traditional interpretation sequence

## Memory Integration
- Reference past readings formally: "In our previous consultation, The Chariot appeared..."
- Note card recurrences with scholarly interest: "It is notable that the Queen of Cups
  has appeared in three consecutive readings..."
- Connect patterns to astrological or numerological themes

## What You DON'T Do
- You don't use casual language or slang
- You don't predict specific events with certainty
- You don't diagnose medical or mental health conditions
- You don't refuse readings on "difficult" cards
- You don't discuss being an AI
```

**`services/flows/traditional_flow.py`:**
```python
class TraditionalFlow:
    """
    Orchestrates the traditional (Rider-Waite) reading mode.

    Key differences from IntuitiveFlow:
    - Higher reversal probability (0.4)
    - Position-by-position interpretation style (reflected in prompt, not code)
    - Ritual framing phase
    - Knowledge context prioritizes symbolism documents
    """

    def __init__(self):
        self.card_service = CardService()
        self.spread_service = SpreadService()
        self.knowledge_service = get_knowledge_service()

    async def process(self, agent, request, personalization="", memory_context="", deck_state=None):
        """Same orchestration pattern as IntuitiveFlow, with mode-specific adjustments."""
        knowledge_context = ""
        if self.knowledge_service and settings.RAG_ENABLED:
            # Prioritize symbolism documents for traditional mode
            knowledge_context = await self._fetch_traditional_knowledge(request.message)

        agent_response = await agent.complete(
            messages=request.conversation_history,
            mode="traditional",  # Uses traditional.txt prompt
            personalization=personalization,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
        )

        # Tool call handling identical to IntuitiveFlow (shared pattern)
        # but with reversal_probability=0.4
        drawn_cards = None
        for tool_call in agent_response.get("tool_calls", []):
            if tool_call["name"] == "drawCards":
                spread = self.spread_service.get_spread(tool_call["input"]["spread_type"])
                deck_state = deck_state or self.card_service.create_deck_state()
                drawn_cards = self.card_service.draw(
                    deck_state, spread.positions, reversal_probability=0.4
                )
                tool_result = self.card_service.get_llm_context(drawn_cards)

                # Enrich with symbolism documents per card
                if self.knowledge_service:
                    for card in drawn_cards:
                        symbolism = await self.knowledge_service.get_card_interpretation(
                            card.card.id, card.is_reversed
                        )
                        if symbolism:
                            tool_result[f"card_{card.position_index}_knowledge"] = symbolism

                agent_response = await agent.complete_with_tool_result(
                    messages=request.conversation_history,
                    tool_use_id=tool_call["id"],
                    tool_result=tool_result,
                    mode="traditional",
                    personalization=personalization,
                    memory_context=memory_context,
                    knowledge_context=knowledge_context,
                )

        return ReadingResponse(
            message=agent_response["message"],
            cards=drawn_cards,
            reading_state=ReadingState(phase="interpreting" if drawn_cards else "gathering"),
            deck_state=deck_state,
        )
```

---

### Task 7.3: Custom Deck Flow

**Status:** [ ] Not started

**Description:**
Implement the Custom Deck reading flow — users upload deck images, AI interprets visually.

**Deliverables:**

**`agents/prompts/custom.txt`:**
```
You are an adaptive tarot reader who interprets custom deck imagery. You don't rely on
traditional card meanings — you read what you see in the images.

## Your Personality
- Curious and observant — you delight in discovering new imagery
- Descriptive — you paint a verbal picture of what you see
- Adaptive — you match your tone to the deck's aesthetic
- Open — you don't impose Rider-Waite meanings on non-Rider-Waite decks

## Your Approach
- Acknowledge the user's custom deck with genuine interest
- If you've seen this deck before (from memory), reference it
- Ask for a question or intention
- When cards are drawn, describe the visual elements of each card image
- Build interpretation from: colors, figures, symbols, composition, emotion
- Weave individual card stories into a cohesive reading
- Connect to the user's question/intention throughout

## Visual Interpretation Guidelines
- Start with the dominant visual element
- Note color palette and what it suggests (warm = passion/action, cool = emotion/thought)
- Describe any figures: their posture, direction, expression
- Note symbols and their possible meanings
- Comment on composition: balance, movement, tension
- Trust your visual intuition — there are no "wrong" interpretations of custom imagery

## Memory Integration
- If user has used this deck before, reference past readings with it
- Note visual patterns across cards in this reading
- Connect themes to past readings regardless of deck

## What You DON'T Do
- You don't impose Rider-Waite meanings on custom cards
- You don't claim to know what the deck creator intended
- You don't refuse to interpret abstract or non-traditional imagery
- You don't discuss being an AI or technical limitations
```

**Custom deck infrastructure:**

**`services/deck_service.py`:**
```python
class DeckService:
    """
    Manages custom deck uploads and retrieval.

    Custom decks are stored in Supabase Storage.
    Card images are uploaded individually and optionally named by the user.
    AI description is generated on upload for text-based context.
    """

    async def create_deck(self, user_id: UUID, name: str, description: str = "") -> dict:
        """Create a new custom deck record."""

    async def upload_card(self, deck_id: UUID, card_index: int, image_file: UploadFile, name: str = "") -> dict:
        """Upload a card image to Supabase Storage and create record."""

    async def get_deck(self, deck_id: UUID, user_id: UUID) -> dict:
        """Get deck details with all card records."""

    async def list_decks(self, user_id: UUID) -> list[dict]:
        """List user's custom decks."""

    async def generate_card_description(self, image_url: str) -> str:
        """Use Claude vision to generate a text description of a card image."""
        # This pre-computed description is used as fallback context
        # when the main reading LLM can't process images inline
```

**`services/flows/custom_flow.py`:**
```python
class CustomFlow:
    """
    Custom deck reading flow — interprets user-uploaded card images.

    Key differences:
    - Cards come from custom_deck_cards, not the standard 78-card deck
    - AI interprets visual imagery (no pre-loaded card meanings)
    - Tool result includes image URLs or pre-computed descriptions
    - Knowledge context is minimal (no card-specific docs)
    """

    async def process(self, agent, request, personalization="", memory_context="", deck_state=None):
        """Process with custom deck cards."""
        # Similar orchestration, but card draw uses DeckService
        # and tool_result includes image_url or ai_description per card
```

---

### Task 7.4: Flow Router

**Status:** [ ] Not started

**Description:**
Update ReadingService to route to the correct flow based on reading mode.

**Deliverables:**

**Update `services/reading_service.py`:**
```python
class ReadingService:
    def __init__(self):
        self.flows = {
            "intuitive": IntuitiveFlow(),
            "traditional": TraditionalFlow(),
            "custom": CustomFlow(),
        }
        self.agent = ReaderAgent()
        # ...

    async def process_message(self, reading_id, user_id, message):
        reading = await self._get_reading(reading_id, user_id)
        mode = reading.get("mode", "intuitive")
        flow = self.flows[mode]
        # ... rest of orchestration using selected flow
```

---

## Milestone 8: Pattern Detection & Analytics

### Task 8.1: Card Pattern Detection

**Status:** [ ] Not started

**Description:**
After each reading, analyze card appearances to detect and update patterns.

**Deliverables:**

**`services/pattern_service.py`:**
```python
class PatternService:
    """
    Detects recurring card patterns across a user's reading history.

    Patterns tracked:
    - Recurring cards (same card appears 3+ times)
    - Dominant suit (one suit appears >40% across recent readings)
    - Recurring themes (extracted from reading memories)
    - Arcana balance (major vs minor heavy readings)
    """

    async def update_patterns(self, user_id: UUID, reading_id: UUID, cards_drawn: list[dict]) -> None:
        """Run after each reading completion to update pattern data."""
        # 1. Record card appearances
        await self._record_appearances(user_id, reading_id, cards_drawn)

        # 2. Check for recurring cards
        await self._detect_recurring_cards(user_id, reading_id)

        # 3. Check for dominant suit
        await self._detect_dominant_suit(user_id, reading_id)

        # 4. Check arcana balance
        await self._detect_arcana_balance(user_id, reading_id)

    async def get_user_patterns(self, user_id: UUID) -> dict:
        """Get all patterns for a user (for analytics display + memory context)."""
        return {
            "recurring_cards": await self._get_patterns(user_id, "recurring_card"),
            "dominant_suit": await self._get_patterns(user_id, "dominant_suit"),
            "recurring_themes": await self._get_patterns(user_id, "recurring_theme"),
            "arcana_balance": await self._get_patterns(user_id, "arcana_balance"),
            "card_stats": await self._get_card_stats(user_id),
        }

    async def _get_card_stats(self, user_id: UUID) -> list[dict]:
        """Get card frequency stats via RPC."""
        result = await self.supabase.rpc("get_user_card_stats", {
            "p_user_id": str(user_id), "p_limit": 10
        }).execute()
        return result.data
```

**Integration:** Called from `MemoryService.extract_and_store()` after a reading completes.

---

### Task 8.2: Analytics Service & Endpoints

**Status:** [ ] Not started

**Description:**
User-facing analytics — card frequency, suit patterns, reading history trends.

**Deliverables:**

**`services/analytics_service.py`:**
```python
class AnalyticsService:
    """User-facing reading analytics for premium users."""

    async def get_analytics(self, user_id: UUID) -> dict:
        """Full analytics dashboard data."""
        return {
            "total_readings": await self._count_readings(user_id),
            "readings_by_mode": await self._readings_by_mode(user_id),
            "readings_by_month": await self._readings_by_month(user_id),
            "most_drawn_cards": await self._most_drawn_cards(user_id, limit=10),
            "suit_distribution": await self._suit_distribution(user_id),
            "patterns": await PatternService().get_user_patterns(user_id),
            "streak": await self._reading_streak(user_id),
        }
```

**API endpoints:**
```python
@router.get("/api/patterns")
async def get_patterns(user_id: UUID = Depends(get_current_user)):
    return await pattern_service.get_user_patterns(user_id)

@router.get("/api/analytics")
async def get_analytics(user_id: UUID = Depends(get_current_user)):
    return await analytics_service.get_analytics(user_id)
```

---

## Milestone 9: Frontend Polish

### Task 9.1: Spread Layout Component

**Status:** [ ] Not started

**Description:**
Visual card layout component that renders cards in their spread positions.

**Deliverables:**

**`frontend/src/components/SpreadLayout.tsx`:**
```typescript
interface SpreadLayoutProps {
    spread: SpreadDefinition;
    cards: DrawnCard[];
    revealedCount: number;  // For sequential reveal animation
    onCardClick?: (index: number) => void;
}

/**
 * Renders cards in their spread-specific layout.
 *
 * Layouts:
 * - single: one centered card
 * - row: horizontal line (3-card)
 * - cross: center + 4 cardinal (5-card)
 * - horseshoe: arc of 7
 * - celtic_cross: traditional cross + staff layout
 * - relationship: two sides with bridge
 *
 * Cards reveal sequentially with flip animation.
 * Reversed cards display upside-down.
 * Hover/click shows position name + meaning.
 */
```

**Visual details:**
- Card flip animation (CSS 3D transform)
- Sequential reveal (cards face-down, flip one at a time as AI interprets)
- Reversed cards rendered 180deg rotated
- Position labels appear on hover
- Responsive: adapts layout for mobile
- Celtic Cross uses the traditional cross+staff arrangement

---

### Task 9.2: Reading History & Patterns UI

**Status:** [ ] Not started

**Description:**
Build the reading history list, reading detail view, and patterns dashboard.

**Deliverables:**

**`app/history/page.tsx`:** (upgrade from Phase 1)
- Rich cards showing: date, mode icon, spread type, dominant theme, card mini-previews
- Filter by mode, date range
- Search readings by theme/keyword

**`app/history/[id]/page.tsx`:** (upgrade from Phase 1)
- Full reading replay: scrollable conversation + spread layout showing drawn cards
- AI-generated summary at top
- Cards drawn with positions visible

**`app/patterns/page.tsx`:** (new — premium)
- Most drawn cards (bar chart or card grid with frequency badges)
- Suit distribution (pie chart or visual breakdown)
- Theme evolution timeline
- "The Tower has appeared 3 times in the last month" — highlighted patterns
- Reading streak / frequency visualization

---

### Task 9.3: Custom Deck Management UI

**Status:** [ ] Not started

**Description:**
UI for uploading and managing custom decks.

**Deliverables:**

**`app/decks/page.tsx`:**
- List of user's custom decks
- Create new deck button

**`app/decks/[id]/page.tsx`:**
- Deck detail: name, description, card count
- Card grid showing uploaded images
- Upload card button (drag-and-drop or file picker)
- Reorder cards
- Delete deck

**`components/CardUploader.tsx`:**
- Drag-and-drop zone for card images
- Preview before upload
- Progress indicator
- Image validation (format, size, dimensions)

---

### Task 9.4: Mobile Responsive & Polish

**Status:** [ ] Not started

**Description:**
Ensure the full experience works beautifully on mobile.

**Deliverables:**
- All pages responsive from 320px to 1920px
- Spread layouts adapt for narrow screens (stack vertically when needed)
- Touch-friendly card interactions
- Bottom navigation on mobile
- Reading interface optimized for mobile keyboard
- Loading skeletons for all async content
- Error toast notifications
- 404 and error pages
- PWA manifest for "Add to Home Screen"

---

## Phase 2 Completion Checklist

Before considering the product launch-ready:

- [ ] All 6 spreads available and working
- [ ] All 3 reading modes produce distinct, high-quality readings
- [ ] Memory system extracts and stores entities across readings
- [ ] Returning users get context from past readings in new readings
- [ ] Card pattern detection identifies recurring cards and suits
- [ ] Reading history shows past readings with full detail
- [ ] Pattern analytics visible to premium users
- [ ] Custom deck upload and reading works
- [ ] Spread layout component renders all spread types correctly
- [ ] Card reveal animation works smoothly
- [ ] Mobile experience is polished
- [ ] Knowledge base seeded with 156+ card meaning documents
- [ ] All tests pass
- [ ] Memory decay runs on schedule
- [ ] Error handling covers all edge cases

---

## Dependency Graph

```
Task 6.1 (Extraction) ── Task 6.2 (Storage) ── Task 6.3 (Context + Provider)
                                                         │
                                                         ├── Integrates into ReadingService
                                                         │
Task 7.1 (All Spreads) ──────────────────────────────────┤
Task 7.2 (Traditional Flow) ─────────────────────────────┤
Task 7.3 (Custom Deck Flow) ─────────────────────────────┤
Task 7.4 (Flow Router) ──────────────────────────────────┤
                                                         │
Task 8.1 (Pattern Detection) ── Task 8.2 (Analytics) ───┤
                                                         │
Task 9.1 (Spread Layout) ───────────────────────────────┤
Task 9.2 (History & Patterns UI) ───────────────────────┤
Task 9.3 (Custom Deck UI) ──────────────────────────────┤
Task 9.4 (Mobile & Polish) ─────────────────────────────┘
```

Milestones 6 (Memory), 7 (Modes), and 8 (Patterns) can be worked somewhat in parallel — they
converge at the ReadingService integration point.

Milestone 9 (Frontend) depends on backend APIs from Milestones 7 and 8.

---

**Last Updated:** 2026-03-13
**Version:** 1.0
