"""API route handlers for Tarot Agent."""

from uuid import UUID

from fastapi import APIRouter

from api.middleware import CurrentUser
from models.schemas import CreateReadingRequest, SendMessageRequest, UpdateProfileRequest
from services.reading_service import ReadingService

router = APIRouter()
reading_service = ReadingService()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@router.post("/api/reading")
async def create_reading(
    request: CreateReadingRequest,
    user_id: str = CurrentUser,
):
    """Start a new reading."""
    return await reading_service.create_reading(user_id, mode=request.mode)


@router.post("/api/reading/{reading_id}/message")
async def send_message(
    reading_id: str,
    request: SendMessageRequest,
    user_id: str = CurrentUser,
):
    """Send a message in a reading."""
    response = await reading_service.process_message(reading_id, user_id, request.message)
    return response


@router.post("/api/reading/{reading_id}/complete")
async def complete_reading(
    reading_id: str,
    user_id: str = CurrentUser,
):
    """Mark a reading as complete."""
    await reading_service.complete_reading(reading_id, user_id)
    return {"status": "completed"}


@router.get("/api/reading/{reading_id}")
async def get_reading(
    reading_id: str,
    user_id: str = CurrentUser,
):
    """Get full reading detail."""
    return await reading_service.get_reading(reading_id, user_id)


@router.get("/api/readings")
async def list_readings(
    limit: int = 20,
    offset: int = 0,
    user_id: str = CurrentUser,
):
    """List user's reading history (paginated)."""
    return await reading_service.get_reading_history(user_id, limit, offset)


@router.get("/api/profile")
async def get_profile(user_id: str = CurrentUser):
    """Get user profile."""
    supabase = reading_service.supabase
    if not supabase:
        return {"error": "Database not configured"}
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return result.data


@router.patch("/api/profile")
async def update_profile(
    request: UpdateProfileRequest,
    user_id: str = CurrentUser,
):
    """Update user profile."""
    supabase = reading_service.supabase
    if not supabase:
        return {"error": "Database not configured"}
    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        return {"error": "No fields to update"}
    supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    return {"status": "updated"}
