from datetime import date, datetime, timedelta, timezone

from app.core.security import hash_password
from app.integrations.ai.base import ComplaintExtraction
from app.modules.auth.models import PgOwner
from app.modules.complaints.models import (
    Complaint,
    ComplaintCategory,
    ComplaintUrgency,
)
from app.modules.complaints.repository import ComplaintRepository
from app.modules.complaints.service import ComplaintService
from app.modules.residents.models import Resident


def _seed_complaint(
    db,
    *,
    pg_id,
    raw="leak",
    category=ComplaintCategory.PLUMBING,
    urgency=ComplaintUrgency.MEDIUM,
    is_resolved=False,
    needs_review=False,
    created_at=None,
    provider_message_id=None,
):
    c = Complaint(
        pg_id=pg_id,
        resident_id=None,
        raw_whatsapp_msg=raw,
        parsed_issue=raw,
        room_number=None,
        category=category,
        urgency=urgency,
        needs_review=needs_review,
        is_resolved=is_resolved,
        provider_message_id=provider_message_id,
    )
    if created_at is not None:
        c.created_at = created_at
        c.updated_at = created_at
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _seed_resident(db, *, pg_id, phone="919999000111"):
    r = Resident(
        pg_id=pg_id,
        room_id=None,
        name="Asha",
        phone_number=phone,
        monthly_rent=5000,
        security_deposit=0,
        joined_date=date(2026, 5, 1),
        is_active=True,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _seed_bare_owner(db, *, phone, name="Other PG"):
    o = PgOwner(
        pg_name=name,
        owner_name=name + " Owner",
        phone_number=phone,
        hashed_password=hash_password("supersecret"),
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


# --- API surface --------------------------------------------------------


def test_list_complaints_is_tenant_scoped(
    client, auth_headers, owner_token, db_session
):
    pg_a, _ = owner_token
    pg_b = _seed_bare_owner(db_session, phone="918222000002").id

    _seed_complaint(db_session, pg_id=pg_a, raw="A1")
    _seed_complaint(db_session, pg_id=pg_a, raw="A2")
    _seed_complaint(db_session, pg_id=pg_b, raw="B1")

    r = client.get("/complaints", headers=auth_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert {row["raw_whatsapp_msg"] for row in rows} == {"A1", "A2"}


def test_list_complaints_filters_by_is_resolved(
    client, auth_headers, owner_token, db_session
):
    pg_a, _ = owner_token
    _seed_complaint(db_session, pg_id=pg_a, raw="open", is_resolved=False)
    _seed_complaint(db_session, pg_id=pg_a, raw="closed", is_resolved=True)

    r = client.get("/complaints?is_resolved=true", headers=auth_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["raw_whatsapp_msg"] == "closed"

    r = client.get("/complaints?is_resolved=false", headers=auth_headers)
    rows = r.json()
    assert {row["raw_whatsapp_msg"] for row in rows} == {"open"}


def test_list_complaints_filters_by_urgency(
    client, auth_headers, owner_token, db_session
):
    pg_a, _ = owner_token
    _seed_complaint(db_session, pg_id=pg_a, raw="lo", urgency=ComplaintUrgency.LOW)
    _seed_complaint(db_session, pg_id=pg_a, raw="hi", urgency=ComplaintUrgency.HIGH)

    r = client.get("/complaints?urgency=high", headers=auth_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["urgency"] == "high"


def test_list_complaints_orders_by_created_at_desc(
    client, auth_headers, owner_token, db_session
):
    pg_a, _ = owner_token
    now = datetime.now(timezone.utc)
    _seed_complaint(
        db_session, pg_id=pg_a, raw="older", created_at=now - timedelta(hours=2)
    )
    _seed_complaint(
        db_session, pg_id=pg_a, raw="newer", created_at=now - timedelta(minutes=5)
    )

    rows = client.get("/complaints", headers=auth_headers).json()
    assert [r["raw_whatsapp_msg"] for r in rows] == ["newer", "older"]


def test_get_complaint_returns_404_when_missing(client, auth_headers):
    r = client.get("/complaints/9999", headers=auth_headers)
    assert r.status_code == 404


def test_get_complaint_other_tenant_is_404(
    client, auth_headers, db_session
):
    pg_b = _seed_bare_owner(db_session, phone="918222000003").id
    other = _seed_complaint(db_session, pg_id=pg_b, raw="not yours")

    r = client.get(f"/complaints/{other.id}", headers=auth_headers)
    # Tenant isolation must look identical to "doesn't exist" — never leak existence.
    assert r.status_code == 404


def test_resolve_complaint_toggles_flag(
    client, auth_headers, owner_token, db_session
):
    pg_a, _ = owner_token
    c = _seed_complaint(db_session, pg_id=pg_a)

    r = client.patch(
        f"/complaints/{c.id}/resolve",
        headers=auth_headers,
        json={"is_resolved": True},
    )
    assert r.status_code == 200
    assert r.json()["is_resolved"] is True

    r = client.patch(
        f"/complaints/{c.id}/resolve",
        headers=auth_headers,
        json={"is_resolved": False},
    )
    assert r.status_code == 200
    assert r.json()["is_resolved"] is False


def test_resolve_complaint_404_when_missing(client, auth_headers):
    r = client.patch(
        "/complaints/424242/resolve",
        headers=auth_headers,
        json={"is_resolved": True},
    )
    assert r.status_code == 404


def test_resolve_other_tenant_complaint_is_404(
    client, auth_headers, db_session
):
    pg_b = _seed_bare_owner(db_session, phone="918222000004").id
    other = _seed_complaint(db_session, pg_id=pg_b)

    r = client.patch(
        f"/complaints/{other.id}/resolve",
        headers=auth_headers,
        json={"is_resolved": True},
    )
    assert r.status_code == 404
    # Confirm row in DB was not mutated.
    db_session.refresh(other)
    assert other.is_resolved is False


def test_unauthenticated_list_returns_401(client):
    r = client.get("/complaints")
    assert r.status_code == 401


# --- Service edges ------------------------------------------------------


def test_ack_for_parsed_complaint_includes_category_urgency_and_ref(
    db_session, fake_ai, fake_whatsapp
):
    owner = _seed_bare_owner(db_session, phone="918333000001", name="PG")
    resident = _seed_resident(db_session, pg_id=owner.id, phone="919999000200")

    fake_ai.complaint_response = ComplaintExtraction(
        room_number="201",
        issue_description="AC not cooling",
        category="appliance",
        urgency="high",
    )

    service = ComplaintService(ComplaintRepository(db_session))
    c = service.ingest_inbound(
        resident=resident,
        raw_text="AC dead in 201",
        provider_message_id="wamid.ack.1",
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    assert len(fake_whatsapp.sent) == 1
    to_phone, body = fake_whatsapp.sent[0]
    assert to_phone == resident.phone_number
    assert "appliance" in body
    assert "high" in body
    assert f"#C{c.id}" in body


def test_ack_for_needs_review_uses_generic_body(
    db_session, fake_ai, fake_whatsapp
):
    owner = _seed_bare_owner(db_session, phone="918333000002", name="PG2")
    resident = _seed_resident(db_session, pg_id=owner.id, phone="919999000201")

    fake_ai.raise_on_complaint = True
    service = ComplaintService(ComplaintRepository(db_session))
    service.ingest_inbound(
        resident=resident,
        raw_text="??",
        provider_message_id="wamid.ack.2",
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    assert len(fake_whatsapp.sent) == 1
    _, body = fake_whatsapp.sent[0]
    # Generic copy must NOT leak placeholder category/urgency from the unparsed row.
    assert "team will review" in body.lower()
    assert "appliance" not in body
    assert "#C" not in body


def test_whatsapp_send_failure_does_not_lose_complaint(
    db_session, fake_ai, fake_whatsapp
):
    owner = _seed_bare_owner(db_session, phone="918333000003", name="PG3")
    phone = "919999000202"
    resident = _seed_resident(db_session, pg_id=owner.id, phone=phone)

    fake_whatsapp.fail_for_phones.add(phone)

    service = ComplaintService(ComplaintRepository(db_session))
    # Must not raise — ack failure is logged-and-swallowed.
    c = service.ingest_inbound(
        resident=resident,
        raw_text="leaky tap",
        provider_message_id="wamid.fail.1",
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    persisted = db_session.get(Complaint, c.id)
    assert persisted is not None
    assert fake_whatsapp.sent == []  # nothing got through
