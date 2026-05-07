import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TenantMixin, TimestampMixin


class ComplaintCategory(str, enum.Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    CLEANING = "cleaning"
    APPLIANCE = "appliance"
    SECURITY = "security"
    INTERNET = "internet"
    OTHER = "other"


class ComplaintUrgency(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Complaint(Base, TenantMixin, TimestampMixin):
    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_pg_resolved", "pg_id", "is_resolved"),
        Index("ix_complaints_pg_urgency", "pg_id", "urgency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resident_id: Mapped[int | None] = mapped_column(
        ForeignKey("residents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    raw_whatsapp_msg: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_issue: Mapped[str | None] = mapped_column(Text, nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[ComplaintCategory] = mapped_column(
        Enum(
            ComplaintCategory,
            name="complaint_category",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ComplaintCategory.OTHER,
    )
    urgency: Mapped[ComplaintUrgency] = mapped_column(
        Enum(
            ComplaintUrgency,
            name="complaint_urgency",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ComplaintUrgency.MEDIUM,
    )

    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    provider_message_id: Mapped[str | None] = mapped_column(
        String(80), unique=True, nullable=True
    )
