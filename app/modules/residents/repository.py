from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.residents.models import Resident


class ResidentRepository:
    """Tenant-scoped data access for residents."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_tenant(
        self,
        pg_id: int,
        *,
        active_only: bool = False,
        room_id: int | None = None,
    ) -> list[Resident]:
        stmt = select(Resident).where(Resident.pg_id == pg_id)
        if active_only:
            stmt = stmt.where(Resident.is_active.is_(True))
        if room_id is not None:
            stmt = stmt.where(Resident.room_id == room_id)
        stmt = stmt.order_by(Resident.name)
        return list(self.db.execute(stmt).scalars().all())

    def get(self, pg_id: int, resident_id: int) -> Resident | None:
        stmt = select(Resident).where(Resident.id == resident_id, Resident.pg_id == pg_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, resident: Resident) -> Resident:
        self.db.add(resident)
        self.db.commit()
        self.db.refresh(resident)
        return resident

    def save(self, resident: Resident) -> Resident:
        self.db.commit()
        self.db.refresh(resident)
        return resident

    def list_active_global(self) -> list[Resident]:
        """Cross-tenant scan of all active residents.

        ONLY for system-level cron jobs (daily meal poll). Never call from
        request-scoped code.
        """
        stmt = select(Resident).where(Resident.is_active.is_(True)).order_by(Resident.pg_id)
        return list(self.db.execute(stmt).scalars().all())

    def find_active_by_phone_global(self, phone_number: str) -> Resident | None:
        """Cross-tenant lookup — ONLY for inbound webhook routing.

        The phone-number → tenant mapping is what makes inbound WhatsApp
        messages routable. Never use this in dashboard endpoints.
        """
        stmt = (
            select(Resident)
            .where(
                Resident.phone_number == phone_number,
                Resident.is_active.is_(True),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
