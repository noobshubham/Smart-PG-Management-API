from dataclasses import dataclass
from decimal import Decimal

from app.modules.auth.models import PgOwner
from app.modules.finance.exceptions import (
    InvoiceAlreadyPaidError,
    LedgerEntryNotFoundError,
    OverpaymentError,
    UpiVpaNotConfiguredError,
)
from app.modules.finance.models import LedgerEntry, LedgerStatus
from app.modules.finance.repository import LedgerRepository
from app.modules.finance.upi import build_upi_uri
from app.modules.residents.repository import ResidentRepository


@dataclass(frozen=True)
class GenerateInvoicesResult:
    month_year: str
    created: int
    skipped_existing: int
    skipped_no_rent: int


@dataclass(frozen=True)
class UpiLink:
    uri: str
    payee_vpa: str
    amount: Decimal
    note: str


class FinanceService:
    def __init__(
        self,
        ledger_repo: LedgerRepository,
        residents_repo: ResidentRepository,
    ) -> None:
        self.ledger = ledger_repo
        self.residents = residents_repo

    def generate_monthly_invoices(self, pg_id: int, month_year: str) -> GenerateInvoicesResult:
        active = self.residents.list_for_tenant(pg_id, active_only=True)
        already_billed = self.ledger.get_existing_resident_ids_for_month(pg_id, month_year)

        new_entries: list[LedgerEntry] = []
        skipped_existing = 0
        skipped_no_rent = 0

        for resident in active:
            if resident.id in already_billed:
                skipped_existing += 1
                continue
            if resident.monthly_rent <= 0:
                skipped_no_rent += 1
                continue
            new_entries.append(
                LedgerEntry(
                    pg_id=pg_id,
                    resident_id=resident.id,
                    month_year=month_year,
                    amount_due=resident.monthly_rent,
                    amount_paid=Decimal("0"),
                    status=LedgerStatus.PENDING,
                )
            )

        self.ledger.bulk_add(new_entries)
        return GenerateInvoicesResult(
            month_year=month_year,
            created=len(new_entries),
            skipped_existing=skipped_existing,
            skipped_no_rent=skipped_no_rent,
        )

    def list_ledger(
        self,
        pg_id: int,
        *,
        month_year: str | None = None,
        resident_id: int | None = None,
        status: LedgerStatus | None = None,
    ) -> list[LedgerEntry]:
        return self.ledger.list_for_tenant(
            pg_id, month_year=month_year, resident_id=resident_id, status=status
        )

    def log_payment(
        self,
        pg_id: int,
        ledger_id: int,
        amount: Decimal,
        transaction_ref_id: str | None,
    ) -> LedgerEntry:
        entry = self._must_get(pg_id, ledger_id)
        if entry.status == LedgerStatus.PAID:
            raise InvoiceAlreadyPaidError(ledger_id)

        remaining = entry.amount_due - entry.amount_paid
        if amount > remaining:
            raise OverpaymentError(amount, remaining)

        entry.amount_paid = entry.amount_paid + amount
        if transaction_ref_id:
            entry.transaction_ref_id = transaction_ref_id
        entry.status = self._status_for(entry.amount_due, entry.amount_paid)
        return self.ledger.save(entry)

    def build_payment_link(
        self, pg_id: int, ledger_id: int, owner: PgOwner
    ) -> UpiLink:
        if not owner.upi_vpa:
            raise UpiVpaNotConfiguredError()

        entry = self._must_get(pg_id, ledger_id)
        if entry.status == LedgerStatus.PAID:
            raise InvoiceAlreadyPaidError(ledger_id)

        remaining = entry.amount_due - entry.amount_paid
        note = f"Rent {entry.month_year} - {owner.pg_name}"
        txn_ref = f"PG{owner.id}-LED{entry.id}"
        uri = build_upi_uri(
            payee_vpa=owner.upi_vpa,
            payee_name=owner.pg_name,
            amount=remaining,
            note=note,
            txn_ref=txn_ref,
        )
        return UpiLink(uri=uri, payee_vpa=owner.upi_vpa, amount=remaining, note=note)

    def _must_get(self, pg_id: int, ledger_id: int) -> LedgerEntry:
        entry = self.ledger.get(pg_id, ledger_id)
        if entry is None:
            raise LedgerEntryNotFoundError(ledger_id)
        return entry

    @staticmethod
    def _status_for(amount_due: Decimal, amount_paid: Decimal) -> LedgerStatus:
        if amount_paid <= 0:
            return LedgerStatus.PENDING
        if amount_paid >= amount_due:
            return LedgerStatus.PAID
        return LedgerStatus.PARTIAL
