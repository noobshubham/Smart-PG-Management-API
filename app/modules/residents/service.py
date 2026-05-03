from datetime import date

from app.core.phone import normalise_phone
from app.modules.properties.repository import RoomRepository
from app.modules.residents.exceptions import (
    InvalidMoveOutDateError,
    InvalidRoomError,
    ResidentAlreadyInactiveError,
    ResidentNotFoundError,
    RoomFullError,
)
from app.modules.residents.models import Resident
from app.modules.residents.repository import ResidentRepository
from app.modules.residents.schemas import ResidentCreate, ResidentUpdate


class ResidentService:
    def __init__(self, repo: ResidentRepository, rooms: RoomRepository) -> None:
        self.repo = repo
        self.rooms = rooms

    def list_residents(
        self,
        pg_id: int,
        *,
        active_only: bool = False,
        room_id: int | None = None,
    ) -> list[Resident]:
        return self.repo.list_for_tenant(pg_id, active_only=active_only, room_id=room_id)

    def get_resident(self, pg_id: int, resident_id: int) -> Resident:
        return self._must_get(pg_id, resident_id)

    def create_resident(self, pg_id: int, payload: ResidentCreate) -> Resident:
        if payload.room_id is not None:
            self._validate_room_capacity(pg_id, payload.room_id)

        resident = Resident(
            pg_id=pg_id,
            room_id=payload.room_id,
            name=payload.name.strip(),
            phone_number=normalise_phone(payload.phone_number),
            monthly_rent=payload.monthly_rent,
            security_deposit=payload.security_deposit,
            joined_date=payload.joined_date,
            is_active=True,
        )
        return self.repo.add(resident)

    def update_resident(
        self, pg_id: int, resident_id: int, payload: ResidentUpdate
    ) -> Resident:
        resident = self._must_get(pg_id, resident_id)

        if payload.room_id is not None and payload.room_id != resident.room_id:
            self._validate_room_capacity(pg_id, payload.room_id)
            resident.room_id = payload.room_id

        if payload.name is not None:
            resident.name = payload.name.strip()
        if payload.phone_number is not None:
            resident.phone_number = normalise_phone(payload.phone_number)
        if payload.monthly_rent is not None:
            resident.monthly_rent = payload.monthly_rent
        if payload.security_deposit is not None:
            resident.security_deposit = payload.security_deposit
        if payload.joined_date is not None:
            resident.joined_date = payload.joined_date

        return self.repo.save(resident)

    def move_out(self, pg_id: int, resident_id: int, move_out_date: date) -> Resident:
        resident = self._must_get(pg_id, resident_id)
        if not resident.is_active:
            raise ResidentAlreadyInactiveError(resident_id)
        if move_out_date < resident.joined_date:
            raise InvalidMoveOutDateError()

        resident.is_active = False
        resident.move_out_date = move_out_date
        return self.repo.save(resident)

    def _must_get(self, pg_id: int, resident_id: int) -> Resident:
        resident = self.repo.get(pg_id, resident_id)
        if resident is None:
            raise ResidentNotFoundError(resident_id)
        return resident

    def _validate_room_capacity(self, pg_id: int, room_id: int) -> None:
        room = self.rooms.get(pg_id, room_id)
        if room is None:
            raise InvalidRoomError(room_id)
        occupied = self.rooms.count_active_residents(pg_id, room_id)
        if occupied >= room.total_capacity:
            raise RoomFullError(room_id)
