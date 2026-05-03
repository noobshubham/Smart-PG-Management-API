from decimal import Decimal

from app.modules.finance.upi import build_upi_uri


def test_upi_uri_format_and_encoding():
    uri = build_upi_uri(
        payee_vpa="merchant@bank",
        payee_name="Sunrise PG",
        amount=Decimal("1234.5"),
        note="Rent 2026-05",
        txn_ref="PG1-LED7",
    )
    assert uri.startswith("upi://pay?")
    assert "pa=merchant@bank" in uri  # safe='@.' preserves these
    assert "pn=Sunrise%20PG" in uri
    assert "am=1234.50" in uri  # always 2 decimal places
    assert "cu=INR" in uri
    assert "tr=PG1-LED7" in uri


def test_upi_uri_amount_rounding():
    uri = build_upi_uri(
        payee_vpa="x@upi",
        payee_name="X",
        amount=Decimal("99.999"),
        note="x",
    )
    # 99.999 → 100.00 with HALF_UP rounding.
    assert "am=100.00" in uri
