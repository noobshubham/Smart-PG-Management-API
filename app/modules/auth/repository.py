from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import PgOwner


class OwnerRepository:
    """Data access for PgOwner. Pure SQL/ORM, no business logic."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, owner_id: int) -> PgOwner | None:
        return self.db.get(PgOwner, owner_id)

    def get_by_phone(self, phone_number: str) -> PgOwner | None:
        stmt = select(PgOwner).where(PgOwner.phone_number == phone_number)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, owner: PgOwner) -> PgOwner:
        self.db.add(owner)
        self.db.commit()
        self.db.refresh(owner)
        return owner

    def save(self, owner: PgOwner) -> PgOwner:
        self.db.commit()
        self.db.refresh(owner)
        return owner
