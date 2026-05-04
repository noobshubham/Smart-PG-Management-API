import logging
from datetime import date, datetime, timezone

from app.integrations.ai.base import AIProvider, AIUnavailableError
from app.integrations.whatsapp.base import WhatsAppClient, WhatsAppError
from app.modules.meals.models import MealLog
from app.modules.meals.repository import MealLogRepository
from app.modules.residents.models import Resident

logger = logging.getLogger(__name__)

_POLL_PROMPT = (
    "Hi {name}! Will you be having dinner at the PG tonight? "
    "Please reply YES or NO. Mention any preferences (e.g. 'less spice')."
)


class MealService:
    def __init__(self, repo: MealLogRepository) -> None:
        self.repo = repo

    def list_for_date(self, pg_id: int, on_date: date) -> list[MealLog]:
        return self.repo.list_for_date(pg_id, on_date)

    def headcount(self, pg_id: int, on_date: date) -> dict[str, int]:
        return self.repo.headcount_for_date(pg_id, on_date)

    def send_daily_poll(
        self,
        resident: Resident,
        on_date: date,
        whatsapp: WhatsAppClient,
    ) -> tuple[MealLog, bool]:
        """Insert a meal_log row for today and dispatch the WhatsApp poll.

        Returns (log, sent). `sent` is True only when a new prompt was just
        dispatched — False when the resident was already prompted today or
        when the WhatsApp send failed.
        """
        log = self.repo.get_or_create(resident.pg_id, resident.id, on_date)
        if log.prompted_at is not None:
            return log, False

        try:
            whatsapp.send_text(
                resident.phone_number,
                _POLL_PROMPT.format(name=resident.name.split()[0]),
            )
        except WhatsAppError:
            logger.exception("meal poll send failed resident=%s", resident.id)
            return log, False

        log.prompted_at = datetime.now(timezone.utc)
        return self.repo.save(log), True

    def try_record_response(
        self,
        resident: Resident,
        raw_text: str,
        ai: AIProvider,
        on_date: date,
    ) -> MealLog | None:
        """Parse a reply against today's open poll. Return the updated log,
        or None if the resident has no open poll today, or if AI cannot tell
        whether the message is a meal answer (caller falls back to complaint).
        """
        log = self.repo.find_open_for_resident(resident.id, on_date)
        if log is None:
            return None

        try:
            extracted = ai.parse_meal_response(raw_text)
        except AIUnavailableError:
            return None  # let caller fall back to complaint flow

        if extracted.will_eat_dinner is None:
            return None  # AI couldn't classify — treat as not a meal answer

        log.will_eat_dinner = extracted.will_eat_dinner
        log.special_instructions = extracted.special_instructions
        log.responded_at = datetime.now(timezone.utc)
        return self.repo.save(log)
