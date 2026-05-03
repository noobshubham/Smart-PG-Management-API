from datetime import date, datetime, timezone

from app.core.security import hash_password
from app.integrations.ai.base import (
    ComplaintExtraction,
    MealResponseExtraction,
)
from app.integrations.whatsapp.base import InboundMessage
from app.modules.auth.models import PgOwner
from app.modules.complaints.models import Complaint
from app.modules.inbound.dispatcher import dispatch_inbound
from app.modules.meals.models import MealLog
from app.modules.residents.models import Resident


def _seed_owner_and_resident(db, *, phone="919999000111"):
    owner = PgOwner(
        pg_name="PG", owner_name="O", phone_number="918111111111",
        hashed_password=hash_password("supersecret"),
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    resident = Resident(
        pg_id=owner.id,
        room_id=None,
        name="Asha",
        phone_number=phone,
        monthly_rent=5000,
        security_deposit=0,
        joined_date=date(2026, 5, 1),
        is_active=True,
    )
    db.add(resident)
    db.commit()
    db.refresh(resident)
    return owner, resident


def _msg(text, *, phone="919999000111", mid="wamid.1"):
    return InboundMessage(
        provider_message_id=mid,
        from_phone=phone,
        text=text,
        media_url=None,
        media_mime_type=None,
        kind="text",
    )


def test_unknown_phone_drops_message(db_session, fake_ai, fake_whatsapp):
    dispatch_inbound(
        db_session,
        _msg("hi", phone="000000000000"),
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )
    assert fake_whatsapp.sent == []
    assert db_session.query(Complaint).count() == 0


def test_complaint_persisted_with_ai_extraction(db_session, fake_ai, fake_whatsapp):
    _seed_owner_and_resident(db_session)
    fake_ai.complaint_response = ComplaintExtraction(
        room_number="101",
        issue_description="Tap leaking",
        category="plumbing",
        urgency="high",
    )

    dispatch_inbound(
        db_session,
        _msg("Tap is leaking in room 101"),
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    saved = db_session.query(Complaint).all()
    assert len(saved) == 1
    assert saved[0].category.value == "plumbing"
    assert saved[0].urgency.value == "high"
    assert saved[0].needs_review is False
    # Acknowledgment sent.
    assert len(fake_whatsapp.sent) == 1


def test_ai_failure_falls_back_to_manual_review(db_session, fake_ai, fake_whatsapp):
    _seed_owner_and_resident(db_session)
    fake_ai.raise_on_complaint = True

    dispatch_inbound(
        db_session,
        _msg("something broke"),
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    saved = db_session.query(Complaint).one()
    assert saved.needs_review is True
    # Generic ack still goes out.
    assert len(fake_whatsapp.sent) == 1


def test_webhook_idempotent_on_provider_message_id(db_session, fake_ai, fake_whatsapp):
    _seed_owner_and_resident(db_session)

    msg = _msg("issue", mid="wamid.dup")
    dispatch_inbound(db_session, msg, ai=fake_ai, whatsapp=fake_whatsapp)
    dispatch_inbound(db_session, msg, ai=fake_ai, whatsapp=fake_whatsapp)

    assert db_session.query(Complaint).count() == 1


def test_meal_reply_consumes_message_when_open_poll_exists(
    db_session, fake_ai, fake_whatsapp
):
    _, resident = _seed_owner_and_resident(db_session)
    db_session.add(
        MealLog(
            pg_id=resident.pg_id,
            resident_id=resident.id,
            date=date.today(),
            prompted_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    fake_ai.meal_response = MealResponseExtraction(
        will_eat_dinner=True, special_instructions="less spice"
    )

    dispatch_inbound(
        db_session,
        _msg("yes, less spice please"),
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    # No complaint created — message was consumed by meal flow.
    assert db_session.query(Complaint).count() == 0
    log = db_session.query(MealLog).one()
    assert log.will_eat_dinner is True
    assert log.special_instructions == "less spice"


def test_meal_reply_falls_through_when_ambiguous(db_session, fake_ai, fake_whatsapp):
    _, resident = _seed_owner_and_resident(db_session)
    db_session.add(
        MealLog(
            pg_id=resident.pg_id,
            resident_id=resident.id,
            date=date.today(),
            prompted_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    # Ambiguous reply — AI cannot tell.
    fake_ai.meal_response = MealResponseExtraction(
        will_eat_dinner=None, special_instructions=None
    )
    fake_ai.complaint_response = ComplaintExtraction(
        room_number=None,
        issue_description="unclear",
        category="other",
        urgency="medium",
    )

    dispatch_inbound(
        db_session,
        _msg("the wifi is super slow"),
        ai=fake_ai,
        whatsapp=fake_whatsapp,
    )

    # Falls through to complaint.
    assert db_session.query(Complaint).count() == 1
    assert db_session.query(MealLog).one().will_eat_dinner is None
