from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Single declarative base for all ORM models."""


class TimestampMixin:
    """Adds created_at / updated_at columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Every multi-tenant table inherits this — enforces pg_id presence.

    The application layer is responsible for filtering queries by pg_id;
    this mixin only ensures the column exists and is indexed.
    """

    pg_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pg_owners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
