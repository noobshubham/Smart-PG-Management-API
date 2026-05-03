"""Routes a normalised inbound WhatsApp message to the right domain handler.

Decision order:
  1. If the resident has an open meal poll for today and the message reads
     as a meal answer, record it and stop.
  2. Otherwise treat the message as a complaint.

Only one domain "consumes" any given inbound message — there's no fan-out.
"""
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.integrations.ai.base import AIProvider
from app.integrations.whatsapp.base import InboundMessage, WhatsAppClient
from app.modules.complaints.repository import ComplaintRepository
from app.modules.complaints.service import ComplaintService
from app.modules.meals.repository import MealLogRepository
from app.modules.meals.service import MealService
from app.modules.residents.models import Resident
from app.modules.residents.repository import ResidentRepository

logger = logging.getLogger(__name__)


def dispatch_inbound(
    db: Session,
    msg: InboundMessage,
    *,
    ai: AIProvider,
    whatsapp: WhatsAppClient,
) -> None:
    """Designed to run from a BackgroundTask. Logs and swallows any error
    since the webhook has already returned 200 to the provider.
    """
    try:
        resident = _resolve_resident(db, msg)
        if resident is None:
            return
        _route(db, resident, msg, ai=ai, whatsapp=whatsapp)
    except Exception:  # noqa: BLE001
        logger.exception("dispatch failed for msg=%s", msg.provider_message_id)


def _resolve_resident(db: Session, msg: InboundMessage) -> Resident | None:
    if msg.kind != "text" or not msg.text:
        logger.info("ignoring non-text id=%s kind=%s", msg.provider_message_id, msg.kind)
        return None
    resident = ResidentRepository(db).find_active_by_phone_global(msg.from_phone)
    if resident is None:
        logger.warning("inbound from unknown number %s — dropping", msg.from_phone)
    return resident


def _route(
    db: Session,
    resident: Resident,
    msg: InboundMessage,
    *,
    ai: AIProvider,
    whatsapp: WhatsAppClient,
) -> None:
    today = date.today()

    meals = MealService(MealLogRepository(db))
    consumed = meals.try_record_response(resident, msg.text or "", ai, today)
    if consumed is not None:
        logger.info("meal reply recorded resident=%s log=%s", resident.id, consumed.id)
        return

    complaints = ComplaintService(ComplaintRepository(db))
    complaints.ingest_inbound(
        resident=resident,
        raw_text=msg.text or "",
        provider_message_id=msg.provider_message_id,
        ai=ai,
        whatsapp=whatsapp,
    )
