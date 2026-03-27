"""Exception hierarchy for Tarot Agent."""


class TarotAgentError(Exception):
    """Base exception for all Tarot Agent errors."""

    status_code: int = 500
    retryable: bool = False

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(self.message)


# --- LLM Errors ---

class LLMError(TarotAgentError):
    """LLM provider error."""

    status_code = 502
    retryable = True


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    status_code = 504


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    status_code = 429

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(message)


class LLMAuthenticationError(LLMError):
    """LLM authentication failed."""

    status_code = 502
    retryable = False


class LLMContentFilterError(LLMError):
    """LLM content filter triggered."""

    status_code = 400
    retryable = False


# --- Database Errors ---

class DatabaseError(TarotAgentError):
    """Database operation error."""

    status_code = 503
    retryable = True


class DatabaseConnectionError(DatabaseError):
    """Failed to connect to database."""


class DatabaseTimeoutError(DatabaseError):
    """Database query timed out."""


class RecordNotFoundError(DatabaseError):
    """Requested record not found."""

    status_code = 404
    retryable = False


# --- Memory Errors ---

class MemoryError(TarotAgentError):
    """Memory system error."""

    status_code = 503
    retryable = True


class MemoryExtractionError(MemoryError):
    """Entity extraction failed."""


class MemoryConnectionError(MemoryError):
    """Memory storage connection failed."""


# --- Card Errors ---

class CardError(TarotAgentError):
    """Card system error."""

    status_code = 400
    retryable = False


class InsufficientCardsError(CardError):
    """Not enough cards remaining in deck."""


class InvalidSpreadError(CardError):
    """Invalid spread type requested."""


# --- Auth Errors ---

class AuthenticationError(TarotAgentError):
    """Authentication required or failed."""

    status_code = 401
    retryable = False


class AuthorizationError(TarotAgentError):
    """Insufficient permissions."""

    status_code = 403
    retryable = False


# --- Validation ---

class ValidationError(TarotAgentError):
    """Request validation error."""

    status_code = 400
    retryable = False
