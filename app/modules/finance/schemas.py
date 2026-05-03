import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.finance.models import LedgerStatus

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class MonthYear(BaseModel):
    """Reusable validator for month_year strings (YYYY-MM)."""

    month_year: str

    @field_validator("month_year")
    @classmethod
    def _check(cls, v: str) -> str:
        if not _MONTH_RE.match(v):
            raise ValueError("month_year must be in YYYY-MM format")
        return v


class GenerateInvoicesRequest(BaseModel):
    month_year: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class LogPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    transaction_ref_id: str | None = Field(default=None, max_length=64)


class LedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resident_id: int
    month_year: str
    amount_due: Decimal
    amount_paid: Decimal
    transaction_ref_id: str | None
    status: LedgerStatus
    created_at: datetime


class GenerateInvoicesResponse(BaseModel):
    month_year: str
    created: int
    skipped_existing: int
    skipped_no_rent: int


class UpiLinkResponse(BaseModel):
    upi_uri: str
    payee_vpa: str
    amount: Decimal
    note: str
