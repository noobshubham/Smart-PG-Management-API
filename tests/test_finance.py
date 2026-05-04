def _seed_room_and_resident(client, headers):
    room = client.post(
        "/rooms",
        headers=headers,
        json={"room_number": "101", "total_capacity": 2},
    ).json()
    resident = client.post(
        "/residents",
        headers=headers,
        json={
            "name": "Renter One",
            "phone_number": "919000099999",
            "room_id": room["id"],
            "monthly_rent": "10000.00",
            "joined_date": "2026-05-01",
        },
    ).json()
    return room, resident


def test_invoice_generation_is_idempotent(client, auth_headers):
    _seed_room_and_resident(client, auth_headers)

    first = client.post(
        "/finance/invoices/generate",
        headers=auth_headers,
        json={"month_year": "2026-05"},
    ).json()
    assert first["created"] == 1

    second = client.post(
        "/finance/invoices/generate",
        headers=auth_headers,
        json={"month_year": "2026-05"},
    ).json()
    # Re-running for the same month must skip — never duplicate.
    assert second["created"] == 0
    assert second["skipped_existing"] == 1


def test_partial_then_full_payment_status_transitions(client, auth_headers):
    _seed_room_and_resident(client, auth_headers)

    client.post(
        "/finance/invoices/generate",
        headers=auth_headers,
        json={"month_year": "2026-05"},
    )
    entries = client.get(
        "/finance/ledger?month_year=2026-05", headers=auth_headers
    ).json()
    ledger_id = entries[0]["id"]

    r = client.post(
        f"/finance/ledger/{ledger_id}/payments",
        headers=auth_headers,
        json={"amount": "4000.00", "transaction_ref_id": "UPI/0001"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "partial"

    r = client.post(
        f"/finance/ledger/{ledger_id}/payments",
        headers=auth_headers,
        json={"amount": "6000.00", "transaction_ref_id": "UPI/0002"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_overpayment_rejected(client, auth_headers):
    _seed_room_and_resident(client, auth_headers)
    client.post(
        "/finance/invoices/generate",
        headers=auth_headers,
        json={"month_year": "2026-05"},
    )
    entries = client.get(
        "/finance/ledger?month_year=2026-05", headers=auth_headers
    ).json()
    ledger_id = entries[0]["id"]

    r = client.post(
        f"/finance/ledger/{ledger_id}/payments",
        headers=auth_headers,
        json={"amount": "999999.00"},
    )
    assert r.status_code == 400


def test_upi_link_requires_vpa(client, auth_headers):
    _seed_room_and_resident(client, auth_headers)
    client.post(
        "/finance/invoices/generate",
        headers=auth_headers,
        json={"month_year": "2026-05"},
    )
    entries = client.get(
        "/finance/ledger?month_year=2026-05", headers=auth_headers
    ).json()
    ledger_id = entries[0]["id"]

    # Without a VPA configured, must fail with a clear 400.
    r = client.get(f"/finance/ledger/{ledger_id}/upi-link", headers=auth_headers)
    assert r.status_code == 400

    # Set VPA, retry — should succeed and produce a valid UPI URI.
    client.patch("/auth/me", headers=auth_headers, json={"upi_vpa": "owner@upi"})
    r = client.get(f"/finance/ledger/{ledger_id}/upi-link", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["upi_uri"].startswith("upi://pay?")
    assert "pa=owner@upi" in body["upi_uri"]
    assert "am=10000.00" in body["upi_uri"]
    assert "cu=INR" in body["upi_uri"]
