from datetime import date
from decimal import Decimal

from app.core.security import hash_password
from app.modules.auth.models import PgOwner
from app.modules.finance.models import LedgerEntry, LedgerStatus
from app.modules.meals.models import MealLog
from app.modules.residents.models import Resident
from app.workers import jobs


def _seed_active_resident(db, *, phone, name="Resident"):
    owner = PgOwner(
        pg_name="PG", owner_name="O", phone_number=phone,
        hashed_password=hash_password("supersecret"),
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    r = Resident(
        pg_id=owner.id,
        name=name,
        phone_number=phone,
        monthly_rent=Decimal("5000"),
        security_deposit=Decimal("0"),
        joined_date=date(2026, 5, 1),
        is_active=True,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return owner, r


def test_daily_meal_polls_idempotent(db_session, fake_whatsapp):
    _seed_active_resident(db_session, phone="919000010001")
    _seed_active_resident(db_session, phone="919000010002", name="R2")

    first = jobs.run_daily_meal_polls(db_session, fake_whatsapp, on_date=date(2026, 5, 4))
    assert first["sent"] == 2
    assert first["skipped"] == 0
    assert len(fake_whatsapp.sent) == 2

    # Second call same day: rows already prompted, should send nothing more.
    second = jobs.run_daily_meal_polls(db_session, fake_whatsapp, on_date=date(2026, 5, 4))
    assert second["skipped"] == 2
    assert len(fake_whatsapp.sent) == 2  # unchanged

    assert db_session.query(MealLog).count() == 2


def test_rent_reminders_skip_paid_entries(db_session, fake_whatsapp):
    _, r1 = _seed_active_resident(db_session, phone="919000010001", name="One")
    _, r2 = _seed_active_resident(db_session, phone="919000010002", name="Two")

    db_session.add(
        LedgerEntry(
            pg_id=r1.pg_id,
            resident_id=r1.id,
            month_year="2026-04",
            amount_due=Decimal("5000"),
            amount_paid=Decimal("0"),
            status=LedgerStatus.PENDING,
        )
    )
    db_session.add(
        LedgerEntry(
            pg_id=r2.pg_id,
            resident_id=r2.id,
            month_year="2026-04",
            amount_due=Decimal("5000"),
            amount_paid=Decimal("5000"),
            status=LedgerStatus.PAID,
        )
    )
    db_session.commit()

    result = jobs.run_monthly_rent_reminders(
        db_session, fake_whatsapp, month_year="2026-04"
    )
    assert result["sent"] == 1
    # Only the unpaid resident gets the reminder.
    assert fake_whatsapp.sent[0][0] == "919000010001"


def test_rent_reminder_send_failure_counted(db_session, fake_whatsapp):
    _, r = _seed_active_resident(db_session, phone="919000010001")
    db_session.add(
        LedgerEntry(
            pg_id=r.pg_id,
            resident_id=r.id,
            month_year="2026-04",
            amount_due=Decimal("5000"),
            amount_paid=Decimal("0"),
            status=LedgerStatus.PENDING,
        )
    )
    db_session.commit()

    fake_whatsapp.fail_for_phones.add("919000010001")

    result = jobs.run_monthly_rent_reminders(
        db_session, fake_whatsapp, month_year="2026-04"
    )
    assert result["sent"] == 0
    assert result["failed"] == 1
