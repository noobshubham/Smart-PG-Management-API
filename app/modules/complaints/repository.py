from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.complaints.models import Complaint, ComplaintUrgency


class ComplaintRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, pg_id: int, complaint_id: int) -> Complaint | None:
        stmt = select(Complaint).where(
            Complaint.id == complaint_id, Complaint.pg_id == pg_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_tenant(
        self,
        pg_id: int,
        *,
        is_resolved: bool | None = None,
        urgency: ComplaintUrgency | None = None,
    ) -> list[Complaint]:
        stmt = select(Complaint).where(Complaint.pg_id == pg_id)
        if is_resolved is not None:
            stmt = stmt.where(Complaint.is_resolved.is_(is_resolved))
        if urgency is not None:
            stmt = stmt.where(Complaint.urgency == urgency)
        stmt = stmt.order_by(Complaint.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def add(self, complaint: Complaint) -> Complaint:
        self.db.add(complaint)
        self.db.commit()
        self.db.refresh(complaint)
        return complaint

    def save(self, complaint: Complaint) -> Complaint:
        self.db.commit()
        self.db.refresh(complaint)
        return complaint

    def get_by_provider_message_id(self, provider_message_id: str) -> Complaint | None:
        stmt = select(Complaint).where(
            Complaint.provider_message_id == provider_message_id
        )
        return self.db.execute(stmt).scalar_one_or_none()
