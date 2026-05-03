from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TimestampMixin


class PgOwner(Base, TimestampMixin):
    __tablename__ = "pg_owners"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pg_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    upi_vpa: Mapped[str | None] = mapped_column(String(100), nullable=True)
