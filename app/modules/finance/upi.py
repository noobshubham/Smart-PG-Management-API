"""UPI deep link generation (NPCI spec).

Format: upi://pay?pa=<vpa>&pn=<payee_name>&am=<amount>&cu=INR&tn=<note>&tr=<txn_ref>

All values must be URL-encoded. Amount is always 2 decimals.
"""
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote


def _format_amount(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_upi_uri(
    *,
    payee_vpa: str,
    payee_name: str,
    amount: Decimal,
    note: str,
    txn_ref: str | None = None,
) -> str:
    parts = [
        f"pa={quote(payee_vpa, safe='@.')}",
        f"pn={quote(payee_name)}",
        f"am={_format_amount(amount)}",
        "cu=INR",
        f"tn={quote(note)}",
    ]
    if txn_ref:
        parts.append(f"tr={quote(txn_ref)}")
    return "upi://pay?" + "&".join(parts)
