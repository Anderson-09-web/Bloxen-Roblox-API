import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.database.database import get_session
from app.schemas.roblox import (
    LinkRequest,
    RobloxAccountResponse,
    RobloxUserResponse,
    UnlinkRequest,
    VerifyCheckRequest,
    VerifyCreateRequest,
    VerifyCreateResponse,
)
from app.services.roblox_service import RobloxService, RobloxServiceError
from app.services.verification_service import VerificationService


router = APIRouter(prefix="/api/v1/roblox", tags=["Roblox"], dependencies=[Depends(require_api_key)])


def get_roblox_service(request: Request) -> RobloxService:
    return RobloxService(request.app.state.http_client, request.app.state.settings, request.app.state.cache)


def get_verification_service(request: Request) -> VerificationService:
    return VerificationService(request.app.state.settings, get_roblox_service(request))


@router.get("/user/{username}", response_model=RobloxUserResponse)
async def lookup_user(username: str, service: RobloxService = Depends(get_roblox_service)) -> RobloxUserResponse:
    try:
        resolved = await service.resolve_username(username)
        if resolved is None:
            raise HTTPException(status_code=404, detail="Usuario de Roblox no encontrado.")
        return await service.get_user(resolved["id"])
    except RobloxServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/verify/create", response_model=VerifyCreateResponse)
async def create_verification_code(
    payload: VerifyCreateRequest,
    session: AsyncSession = Depends(get_session),
    service: VerificationService = Depends(get_verification_service),
) -> VerifyCreateResponse:
    return await service.create_code(session, payload)


@router.post("/verify/check")
async def check_verification_code(
    payload: VerifyCheckRequest,
    session: AsyncSession = Depends(get_session),
    service: VerificationService = Depends(get_verification_service),
):
    return await service.check_code(session, payload)


@router.post("/link", response_model=RobloxAccountResponse)
async def link_roblox(
    payload: LinkRequest,
    session: AsyncSession = Depends(get_session),
    service: VerificationService = Depends(get_verification_service),
) -> RobloxAccountResponse:
    return await service.link_existing(session, payload.discord_id, payload.roblox_id)


@router.delete("/unlink", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_roblox(
    payload: UnlinkRequest,
    session: AsyncSession = Depends(get_session),
    service: VerificationService = Depends(get_verification_service),
) -> None:
    await service.unlink(session, payload.discord_id)