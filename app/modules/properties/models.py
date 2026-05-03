from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TenantMixin, TimestampMixin


class Room(Base, TenantMixin, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("pg_id", "room_number", name="uq_rooms_pg_room_number"),
        CheckConstraint("total_capacity > 0", name="ck_rooms_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    total_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
