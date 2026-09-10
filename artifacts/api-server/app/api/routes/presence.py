from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.database.database import get_session
from app.schemas.presence import PresenceCheckRequest, PresenceCheckResponse, PresenceResponse
from app.services.presence_service import PresenceService
from app.api.routes.roblox import get_roblox_service


router = APIRouter(prefix="/api/v1/roblox/presence", tags=["Presence"], dependencies=[Depends(require_api_key)])


def get_presence_service(request: Request) -> PresenceService:
    return PresenceService(get_roblox_service(request))


@router.post("/check", response_model=PresenceCheckResponse)
async def check_presence(
    payload: PresenceCheckRequest,
    session: AsyncSession = Depends(get_session),
    service: PresenceService = Depends(get_presence_service),
) -> PresenceCheckResponse:
    return await service.check_and_record(session, payload)


@router.get("/{roblox_id}", response_model=PresenceResponse)
async def get_presence(roblox_id: int, service: PresenceService = Depends(get_presence_service)) -> PresenceResponse:
    return await service.get(roblox_id)