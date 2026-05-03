from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant
from app.modules.properties.exceptions import (
    CapacityBelowOccupancyError,
    DuplicateRoomNumberError,
    RoomNotFoundError,
    RoomOccupiedError,
)
from app.modules.properties.repository import RoomRepository
from app.modules.properties.schemas import RoomCreate, RoomResponse, RoomUpdate
from app.modules.properties.service import PropertyService, RoomView

router = APIRouter(prefix="/rooms", tags=["rooms"])


def get_property_service(db: Session = Depends(get_db)) -> PropertyService:
    return PropertyService(RoomRepository(db))


def _to_response(view: RoomView) -> RoomResponse:
    return RoomResponse(
        id=view.room.id,
        room_number=view.room.room_number,
        total_capacity=view.room.total_capacity,
        available_capacity=view.available_capacity,
        created_at=view.room.created_at,
    )


@router.get("", response_model=list[RoomResponse])
def list_rooms(
    tenant: TenantContext = Depends(get_tenant),
    service: PropertyService = Depends(get_property_service),
) -> list[RoomResponse]:
    return [_to_response(v) for v in service.list_rooms(tenant.pg_id)]


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    tenant: TenantContext = Depends(get_tenant),
    service: PropertyService = Depends(get_property_service),
) -> RoomResponse:
    try:
        view = service.create_room(tenant.pg_id, payload)
    except DuplicateRoomNumberError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_response(view)


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    tenant: TenantContext = Depends(get_tenant),
    service: PropertyService = Depends(get_property_service),
) -> RoomResponse:
    try:
        return _to_response(service.get_room(tenant.pg_id, room_id))
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    tenant: TenantContext = Depends(get_tenant),
    service: PropertyService = Depends(get_property_service),
) -> RoomResponse:
    try:
        view = service.update_room(tenant.pg_id, room_id, payload)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicateRoomNumberError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CapacityBelowOccupancyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_response(view)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    tenant: TenantContext = Depends(get_tenant),
    service: PropertyService = Depends(get_property_service),
) -> None:
    try:
        service.delete_room(tenant.pg_id, room_id)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RoomOccupiedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
