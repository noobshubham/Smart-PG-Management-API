import logging

from app.integrations.whatsapp.base import WhatsAppClient, WhatsAppError
from app.modules.notices.models import Notice
from app.modules.notices.repository import NoticeRepository
from app.modules.residents.repository import ResidentRepository

logger = logging.getLogger(__name__)


class NoticeService:
    def __init__(self, repo: NoticeRepository, residents: ResidentRepository) -> None:
        self.repo = repo
        self.residents = residents

    def create_pending(self, pg_id: int, message: str) -> tuple[Notice, list[str]]:
        """Persist a Notice row and return it along with target phone numbers.

        Run synchronously inside the request so the response can echo the
        Notice id and recipient count. The actual sends are dispatched
        afterwards via a background task.
        """
        active = self.residents.list_for_tenant(pg_id, active_only=True)
        phones = [r.phone_number for r in active if r.phone_number]

        notice = Notice(pg_id=pg_id, message=message, recipient_count=len(phones))
        notice = self.repo.add(notice)
        return notice, phones

    def deliver(
        self,
        pg_id: int,
        notice_id: int,
        phones: list[str],
        whatsapp: WhatsAppClient,
    ) -> None:
        """Send the broadcast and update delivery counters. Background-safe."""
        notice = self.repo.get(pg_id, notice_id)
        if notice is None:
            logger.warning("notice %s vanished before delivery", notice_id)
            return

        delivered = failed = 0
        for phone in phones:
            try:
                whatsapp.send_text(phone, notice.message)
                delivered += 1
            except WhatsAppError:
                logger.exception("notice send failed phone=%s", phone)
                failed += 1

        notice.delivered_count = delivered
        notice.failed_count = failed
        self.repo.save(notice)

    def list_notices(self, pg_id: int) -> list[Notice]:
        return self.repo.list_for_tenant(pg_id)
