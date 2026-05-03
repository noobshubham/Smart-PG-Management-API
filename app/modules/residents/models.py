from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TenantMixin, TimestampMixin


class Resident(Base, TenantMixin, TimestampMixin):
    __tablename__ = "residents"
    __table_args__ = (
        CheckConstraint("monthly_rent >= 0", name="ck_residents_rent_nonneg"),
        CheckConstraint("security_deposit >= 0", name="ck_residents_deposit_nonneg"),
        Index("ix_residents_pg_active", "pg_id", "is_active"),
        Index("ix_residents_pg_phone", "pg_id", "phone_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    security_deposit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    joined_date: Mapped[date] = mapped_column(Date, nullable=False)
    move_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
