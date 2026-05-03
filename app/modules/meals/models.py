from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TenantMixin, TimestampMixin


class MealLog(Base, TenantMixin, TimestampMixin):
    """One row per resident per day for the dinner-headcount poll.

    Lifecycle:
      1. Daily scheduled task creates rows with prompted_at=now, will_eat_dinner=null
         and sends a WhatsApp poll message.
      2. Resident replies → AI parses → row updated with will_eat_dinner + notes.
      3. Cook's dashboard reads `will_eat_dinner=true` rows for today.

    A row with prompted_at set and will_eat_dinner null is "open" — that's how
    the inbound dispatcher knows to route the next message as a meal answer.
    """

    __tablename__ = "meal_logs"
    __table_args__ = (
        UniqueConstraint("pg_id", "resident_id", "date", name="uq_meal_logs_resident_date"),
        Index("ix_meal_logs_pg_date", "pg_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resident_id: Mapped[int] = mapped_column(
        ForeignKey("residents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)
    prompted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    will_eat_dinner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
