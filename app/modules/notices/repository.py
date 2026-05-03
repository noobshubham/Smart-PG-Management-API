from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notices.models import Notice


class NoticeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, notice: Notice) -> Notice:
        self.db.add(notice)
        self.db.commit()
        self.db.refresh(notice)
        return notice

    def save(self, notice: Notice) -> Notice:
        self.db.commit()
        self.db.refresh(notice)
        return notice

    def get(self, pg_id: int, notice_id: int) -> Notice | None:
        stmt = select(Notice).where(Notice.id == notice_id, Notice.pg_id == pg_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_tenant(self, pg_id: int) -> list[Notice]:
        stmt = (
            select(Notice)
            .where(Notice.pg_id == pg_id)
            .order_by(Notice.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
