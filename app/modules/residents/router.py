from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant
from app.integrations.ai import AIProvider, AIUnavailableError, get_ai_provider
from app.modules.properties.repository import RoomRepository
from app.modules.residents.exceptions import (
    InvalidMoveOutDateError,
    InvalidRoomError,
    ResidentAlreadyInactiveError,
    ResidentNotFoundError,
    RoomFullError,
)
from app.modules.residents.repository import ResidentRepository
from app.modules.residents.schemas import (
    ResidentCreate,
    ResidentDraftFromId,
    ResidentMoveOut,
    ResidentResponse,
    ResidentUpdate,
)
from app.modules.residents.service import ResidentService

_ALLOWED_ID_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_ID_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

router = APIRouter(prefix="/residents", tags=["residents"])


def get_resident_service(db: Session = Depends(get_db)) -> ResidentService:
    return ResidentService(ResidentRepository(db), RoomRepository(db))


@router.get("", response_model=list[ResidentResponse])
def list_residents(
    active_only: bool = Query(default=False),
    room_id: int | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant),
    service: ResidentService = Depends(get_resident_service),
) -> list[ResidentResponse]:
    residents = service.list_residents(
        tenant.pg_id, active_only=active_only, room_id=room_id
    )
    return [ResidentResponse.model_validate(r) for r in residents]


@router.post("", response_model=ResidentResponse, status_code=status.HTTP_201_CREATED)
def create_resident(
    payload: ResidentCreate,
    tenant: TenantContext = Depends(get_tenant),
    service: ResidentService = Depends(get_resident_service),
) -> ResidentResponse:
    try:
        resident = service.create_resident(tenant.pg_id, payload)
    except InvalidRoomError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RoomFullError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return ResidentResponse.model_validate(resident)


@router.get("/{resident_id}", response_model=ResidentResponse)
def get_resident(
    resident_id: int,
    tenant: TenantContext = Depends(get_tenant),
    service: ResidentService = Depends(get_resident_service),
) -> ResidentResponse:
    try:
        return ResidentResponse.model_validate(service.get_resident(tenant.pg_id, resident_id))
    except ResidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{resident_id}", response_model=ResidentResponse)
def update_resident(
    resident_id: int,
    payload: ResidentUpdate,
    tenant: TenantContext = Depends(get_tenant),
    service: ResidentService = Depends(get_resident_service),
) -> ResidentResponse:
    try:
        resident = service.update_resident(tenant.pg_id, resident_id, payload)
    except ResidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidRoomError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RoomFullError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return ResidentResponse.model_validate(resident)


@router.post("/onboarding/ocr", response_model=ResidentDraftFromId)
async def onboard_from_id(
    file: UploadFile = File(...),
    _tenant: TenantContext = Depends(get_tenant),
    ai: AIProvider = Depends(get_ai_provider),
) -> ResidentDraftFromId:
    """Extract name/DOB/ID/address from a government-ID image for form pre-fill."""
    mime = (file.content_type or "").lower()
    if mime not in _ALLOWED_ID_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {mime}",
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_ID_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds 5 MB limit",
        )

    try:
        extracted = ai.extract_id_card(image_bytes, mime_type=mime)
    except AIUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI extraction failed: {exc}",
        )

    return ResidentDraftFromId(
        name=extracted.name,
        date_of_birth=extracted.date_of_birth,
        id_number=extracted.id_number,
        address=extracted.address,
        id_type=extracted.id_type,
    )


@router.post("/{resident_id}/move-out", response_model=ResidentResponse)
def move_out_resident(
    resident_id: int,
    payload: ResidentMoveOut,
    tenant: TenantContext = Depends(get_tenant),
    service: ResidentService = Depends(get_resident_service),
) -> ResidentResponse:
    try:
        resident = service.move_out(tenant.pg_id, resident_id, payload.move_out_date)
    except ResidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ResidentAlreadyInactiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidMoveOutDateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ResidentResponse.model_validate(resident)
