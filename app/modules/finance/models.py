import enum
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TenantMixin, TimestampMixin


class LedgerStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"


class LedgerEntry(Base, TenantMixin, TimestampMixin):
    """One row per resident per billing month (YYYY-MM)."""

    __tablename__ = "ledger"
    __table_args__ = (
        UniqueConstraint(
            "pg_id", "resident_id", "month_year", name="uq_ledger_resident_month"
        ),
        CheckConstraint("amount_due >= 0", name="ck_ledger_due_nonneg"),
        CheckConstraint("amount_paid >= 0", name="ck_ledger_paid_nonneg"),
        Index("ix_ledger_pg_status", "pg_id", "status"),
        Index("ix_ledger_pg_month", "pg_id", "month_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resident_id: Mapped[int] = mapped_column(
        ForeignKey("residents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    month_year: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    amount_due: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    transaction_ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[LedgerStatus] = mapped_column(
        Enum(LedgerStatus, name="ledger_status"),
        nullable=False,
        default=LedgerStatus.PENDING,
    )
