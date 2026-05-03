class FinanceError(Exception):
    """Base finance-domain error."""


class LedgerEntryNotFoundError(FinanceError):
    def __init__(self, ledger_id: int) -> None:
        super().__init__(f"Ledger entry {ledger_id} not found")
        self.ledger_id = ledger_id


class OverpaymentError(FinanceError):
    def __init__(self, attempted: object, remaining: object) -> None:
        super().__init__(
            f"Payment of {attempted} exceeds remaining balance {remaining}"
        )


class UpiVpaNotConfiguredError(FinanceError):
    def __init__(self) -> None:
        super().__init__("Owner has not configured a UPI VPA — set it on the profile first")


class InvoiceAlreadyPaidError(FinanceError):
    def __init__(self, ledger_id: int) -> None:
        super().__init__(f"Ledger entry {ledger_id} is already fully paid")
        self.ledger_id = ledger_id
