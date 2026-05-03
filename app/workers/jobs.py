"""Pure system-level job functions invoked by Celery tasks.

Kept Celery-free so they can be unit-tested with a fake session and a
fake WhatsApp client.
"""
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.integrations.whatsapp.base import WhatsAppClient, WhatsAppError
from app.modules.finance.repository import LedgerRepository
from app.modules.meals.repository import MealLogRepository
from app.modules.meals.service import MealService
from app.modules.residents.repository import ResidentRepository

logger = logging.getLogger(__name__)


def run_daily_meal_polls(
    db: Session, whatsapp: WhatsAppClient, *, on_date: date | None = None
) -> dict[str, int]:
    """Send today's dinner poll to every active resident across all tenants."""
    on_date = on_date or date.today()
    residents = ResidentRepository(db).list_active_global()
    meals = MealService(MealLogRepository(db))

    sent = skipped = 0
    for resident in residents:
        log = meals.send_daily_poll(resident, on_date, whatsapp)
        if log.prompted_at is not None:
            sent += 1
        else:
            skipped += 1

    logger.info("daily meal polls: sent=%s skipped=%s on=%s", sent, skipped, on_date)
    return {"sent": sent, "skipped": skipped}


def run_monthly_rent_reminders(
    db: Session,
    whatsapp: WhatsAppClient,
    *,
    month_year: str,
) -> dict[str, int]:
    """Message every resident with an unpaid balance for the given month."""
    entries = LedgerRepository(db).list_unpaid_global(month_year)
    residents_repo = ResidentRepository(db)

    sent = failed = 0
    for entry in entries:
        resident = residents_repo.get(entry.pg_id, entry.resident_id)
        if resident is None or not resident.is_active:
            continue
        balance = entry.amount_due - entry.amount_paid
        body = (
            f"Hi {resident.name.split()[0] if resident.name else 'there'}, "
            f"your rent of Rs.{balance} for {month_year} is still pending. "
            "Please clear the dues at your earliest."
        )
        try:
            whatsapp.send_text(resident.phone_number, body)
            sent += 1
        except WhatsAppError:
            logger.exception("rent reminder failed resident=%s", resident.id)
            failed += 1

    logger.info("rent reminders %s: sent=%s failed=%s", month_year, sent, failed)
    return {"sent": sent, "failed": failed}
