"""Celery task wrappers — thin orchestration over `jobs.py`.

Tasks open a fresh DB session each run, instantiate the WhatsApp client
from settings, and delegate the actual work. Logic lives in `jobs.py` so
it can be unit-tested without Celery or a broker.
"""
import logging
from datetime import date

from app.core.db import SessionLocal
from app.integrations.whatsapp import get_whatsapp_client
from app.workers import jobs
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.send_daily_meal_polls")
def send_daily_meal_polls() -> dict[str, int]:
    db = SessionLocal()
    try:
        return jobs.run_daily_meal_polls(db, get_whatsapp_client())
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.send_monthly_rent_reminders")
def send_monthly_rent_reminders(month_year: str | None = None) -> dict[str, int]:
    """Run on the 1st — bill the *previous* month by default."""
    target = month_year or _previous_month_iso(date.today())
    db = SessionLocal()
    try:
        return jobs.run_monthly_rent_reminders(db, get_whatsapp_client(), month_year=target)
    finally:
        db.close()


def _previous_month_iso(today: date) -> str:
    year = today.year if today.month > 1 else today.year - 1
    month = today.month - 1 if today.month > 1 else 12
    return f"{year:04d}-{month:02d}"
