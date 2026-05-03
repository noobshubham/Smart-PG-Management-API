from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.finance.models import LedgerEntry, LedgerStatus


class LedgerRepository:
    """Tenant-scoped data access for ledger entries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, pg_id: int, ledger_id: int) -> LedgerEntry | None:
        stmt = select(LedgerEntry).where(
            LedgerEntry.id == ledger_id, LedgerEntry.pg_id == pg_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_tenant(
        self,
        pg_id: int,
        *,
        month_year: str | None = None,
        resident_id: int | None = None,
        status: LedgerStatus | None = None,
    ) -> list[LedgerEntry]:
        stmt = select(LedgerEntry).where(LedgerEntry.pg_id == pg_id)
        if month_year is not None:
            stmt = stmt.where(LedgerEntry.month_year == month_year)
        if resident_id is not None:
            stmt = stmt.where(LedgerEntry.resident_id == resident_id)
        if status is not None:
            stmt = stmt.where(LedgerEntry.status == status)
        stmt = stmt.order_by(LedgerEntry.month_year.desc(), LedgerEntry.resident_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_existing_resident_ids_for_month(
        self, pg_id: int, month_year: str
    ) -> set[int]:
        stmt = select(LedgerEntry.resident_id).where(
            LedgerEntry.pg_id == pg_id, LedgerEntry.month_year == month_year
        )
        return {row[0] for row in self.db.execute(stmt).all()}

    def bulk_add(self, entries: list[LedgerEntry]) -> None:
        if not entries:
            return
        self.db.add_all(entries)
        self.db.commit()

    def save(self, entry: LedgerEntry) -> LedgerEntry:
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_unpaid_global(self, month_year: str) -> list[LedgerEntry]:
        """Cross-tenant scan of pending/partial ledger entries for a month.

        ONLY for system-level cron jobs (rent reminders). Never call from
        request-scoped code.
        """
        stmt = (
            select(LedgerEntry)
            .where(
                LedgerEntry.month_year == month_year,
                LedgerEntry.status != LedgerStatus.PAID,
            )
            .order_by(LedgerEntry.pg_id, LedgerEntry.resident_id)
        )
        return list(self.db.execute(stmt).scalars().all())
