from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResidentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(min_length=8, max_length=20)
    room_id: int | None = None
    monthly_rent: Decimal = Field(ge=0, decimal_places=2)
    security_deposit: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    joined_date: date


class ResidentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, min_length=8, max_length=20)
    room_id: int | None = None
    monthly_rent: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    security_deposit: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    joined_date: date | None = None


class ResidentMoveOut(BaseModel):
    move_out_date: date


class ResidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone_number: str
    room_id: int | None
    monthly_rent: Decimal
    security_deposit: Decimal
    joined_date: date
    move_out_date: date | None
    is_active: bool
    created_at: datetime


class ResidentDraftFromId(BaseModel):
    """Pre-fill payload returned by the ID-OCR onboarding endpoint."""

    name: str | None
    date_of_birth: str | None
    id_number: str | None
    address: str | None
    id_type: str


class _MoveOutDateAfterJoinValidator(BaseModel):
    """Internal helper — used at service layer, not exposed."""

    joined_date: date
    move_out_date: date

    @model_validator(mode="after")
    def _check(self) -> "_MoveOutDateAfterJoinValidator":
        if self.move_out_date < self.joined_date:
            raise ValueError("move_out_date cannot be before joined_date")
        return self
