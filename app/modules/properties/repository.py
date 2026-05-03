from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.properties.models import Room
from app.modules.residents.models import Resident


class RoomRepository:
    """Tenant-scoped data access for rooms.

    Every method requires `pg_id` so cross-tenant access is impossible at this
    layer. Services must obtain `pg_id` from `TenantContext`.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_tenant(self, pg_id: int) -> list[Room]:
        stmt = select(Room).where(Room.pg_id == pg_id).order_by(Room.room_number)
        return list(self.db.execute(stmt).scalars().all())

    def get(self, pg_id: int, room_id: int) -> Room | None:
        stmt = select(Room).where(Room.id == room_id, Room.pg_id == pg_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_number(self, pg_id: int, room_number: str) -> Room | None:
        stmt = select(Room).where(Room.pg_id == pg_id, Room.room_number == room_number)
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, room: Room) -> Room:
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def save(self, room: Room) -> Room:
        self.db.commit()
        self.db.refresh(room)
        return room

    def delete(self, room: Room) -> None:
        self.db.delete(room)
        self.db.commit()

    def count_active_residents(self, pg_id: int, room_id: int) -> int:
        stmt = (
            select(func.count(Resident.id))
            .where(
                Resident.pg_id == pg_id,
                Resident.room_id == room_id,
                Resident.is_active.is_(True),
            )
        )
        return int(self.db.execute(stmt).scalar_one())

    def occupancy_map(self, pg_id: int) -> dict[int, int]:
        """Return {room_id: active_resident_count} for a tenant in one query."""
        stmt = (
            select(Resident.room_id, func.count(Resident.id))
            .where(Resident.pg_id == pg_id, Resident.is_active.is_(True))
            .group_by(Resident.room_id)
        )
        return {row[0]: int(row[1]) for row in self.db.execute(stmt).all() if row[0] is not None}
