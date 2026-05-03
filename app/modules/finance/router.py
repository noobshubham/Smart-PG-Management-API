from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import TenantContext, get_current_owner, get_tenant
from app.modules.auth.models import PgOwner
from app.modules.finance.exceptions import (
    InvoiceAlreadyPaidError,
    LedgerEntryNotFoundError,
    OverpaymentError,
    UpiVpaNotConfiguredError,
)
from app.modules.finance.models import LedgerStatus
from app.modules.finance.repository import LedgerRepository
from app.modules.finance.schemas import (
    GenerateInvoicesRequest,
    GenerateInvoicesResponse,
    LedgerResponse,
    LogPaymentRequest,
    UpiLinkResponse,
)
from app.modules.finance.service import FinanceService
from app.modules.residents.repository import ResidentRepository

router = APIRouter(prefix="/finance", tags=["finance"])


def get_finance_service(db: Session = Depends(get_db)) -> FinanceService:
    return FinanceService(LedgerRepository(db), ResidentRepository(db))


@router.post(
    "/invoices/generate",
    response_model=GenerateInvoicesResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_invoices(
    payload: GenerateInvoicesRequest,
    tenant: TenantContext = Depends(get_tenant),
    service: FinanceService = Depends(get_finance_service),
) -> GenerateInvoicesResponse:
    result = service.generate_monthly_invoices(tenant.pg_id, payload.month_year)
    return GenerateInvoicesResponse(
        month_year=result.month_year,
        created=result.created,
        skipped_existing=result.skipped_existing,
        skipped_no_rent=result.skipped_no_rent,
    )


@router.get("/ledger", response_model=list[LedgerResponse])
def list_ledger(
    month_year: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    resident_id: int | None = Query(default=None),
    status_filter: LedgerStatus | None = Query(default=None, alias="status"),
    tenant: TenantContext = Depends(get_tenant),
    service: FinanceService = Depends(get_finance_service),
) -> list[LedgerResponse]:
    entries = service.list_ledger(
        tenant.pg_id,
        month_year=month_year,
        resident_id=resident_id,
        status=status_filter,
    )
    return [LedgerResponse.model_validate(e) for e in entries]


@router.post("/ledger/{ledger_id}/payments", response_model=LedgerResponse)
def log_payment(
    ledger_id: int,
    payload: LogPaymentRequest,
    tenant: TenantContext = Depends(get_tenant),
    service: FinanceService = Depends(get_finance_service),
) -> LedgerResponse:
    try:
        entry = service.log_payment(
            tenant.pg_id, ledger_id, payload.amount, payload.transaction_ref_id
        )
    except LedgerEntryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvoiceAlreadyPaidError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except OverpaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return LedgerResponse.model_validate(entry)


@router.get("/ledger/{ledger_id}/upi-link", response_model=UpiLinkResponse)
def get_upi_link(
    ledger_id: int,
    tenant: TenantContext = Depends(get_tenant),
    owner: PgOwner = Depends(get_current_owner),
    service: FinanceService = Depends(get_finance_service),
) -> UpiLinkResponse:
    try:
        link = service.build_payment_link(tenant.pg_id, ledger_id, owner)
    except LedgerEntryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UpiVpaNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except InvoiceAlreadyPaidError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return UpiLinkResponse(
        upi_uri=link.uri,
        payee_vpa=link.payee_vpa,
        amount=link.amount,
        note=link.note,
    )
