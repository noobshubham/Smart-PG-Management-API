from dataclasses import dataclass

from app.modules.properties.exceptions import (
    CapacityBelowOccupancyError,
    DuplicateRoomNumberError,
    RoomNotFoundError,
    RoomOccupiedError,
)
from app.modules.properties.models import Room
from app.modules.properties.repository import RoomRepository
from app.modules.properties.schemas import RoomCreate, RoomUpdate


@dataclass(frozen=True)
class RoomView:
    """Service-layer DTO bundling a Room with its computed availability."""

    room: Room
    available_capacity: int


class PropertyService:
    def __init__(self, repo: RoomRepository) -> None:
        self.repo = repo

    def list_rooms(self, pg_id: int) -> list[RoomView]:
        rooms = self.repo.list_for_tenant(pg_id)
        occupancy = self.repo.occupancy_map(pg_id)
        return [
            RoomView(room=r, available_capacity=r.total_capacity - occupancy.get(r.id, 0))
            for r in rooms
        ]

    def get_room(self, pg_id: int, room_id: int) -> RoomView:
        room = self._must_get(pg_id, room_id)
        occupied = self.repo.count_active_residents(pg_id, room_id)
        return RoomView(room=room, available_capacity=room.total_capacity - occupied)

    def create_room(self, pg_id: int, payload: RoomCreate) -> RoomView:
        if self.repo.get_by_number(pg_id, payload.room_number):
            raise DuplicateRoomNumberError(payload.room_number)
        room = Room(
            pg_id=pg_id,
            room_number=payload.room_number.strip(),
            total_capacity=payload.total_capacity,
        )
        room = self.repo.add(room)
        return RoomView(room=room, available_capacity=room.total_capacity)

    def update_room(self, pg_id: int, room_id: int, payload: RoomUpdate) -> RoomView:
        room = self._must_get(pg_id, room_id)

        if payload.room_number and payload.room_number != room.room_number:
            if self.repo.get_by_number(pg_id, payload.room_number):
                raise DuplicateRoomNumberError(payload.room_number)
            room.room_number = payload.room_number.strip()

        occupied = self.repo.count_active_residents(pg_id, room_id)
        if payload.total_capacity is not None:
            if payload.total_capacity < occupied:
                raise CapacityBelowOccupancyError(payload.total_capacity, occupied)
            room.total_capacity = payload.total_capacity

        room = self.repo.save(room)
        return RoomView(room=room, available_capacity=room.total_capacity - occupied)

    def delete_room(self, pg_id: int, room_id: int) -> None:
        room = self._must_get(pg_id, room_id)
        if self.repo.count_active_residents(pg_id, room_id) > 0:
            raise RoomOccupiedError(room_id)
        self.repo.delete(room)

    def _must_get(self, pg_id: int, room_id: int) -> Room:
        room = self.repo.get(pg_id, room_id)
        if room is None:
            raise RoomNotFoundError(room_id)
        return room
