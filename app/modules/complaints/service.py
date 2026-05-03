import logging

from app.integrations.ai.base import AIProvider, AIUnavailableError
from app.integrations.whatsapp.base import WhatsAppClient, WhatsAppError
from app.modules.complaints.exceptions import ComplaintNotFoundError
from app.modules.complaints.models import Complaint, ComplaintCategory, ComplaintUrgency
from app.modules.complaints.repository import ComplaintRepository
from app.modules.residents.models import Resident

logger = logging.getLogger(__name__)


class ComplaintService:
    def __init__(self, repo: ComplaintRepository) -> None:
        self.repo = repo

    def list_complaints(
        self,
        pg_id: int,
        *,
        is_resolved: bool | None = None,
        urgency: ComplaintUrgency | None = None,
    ) -> list[Complaint]:
        return self.repo.list_for_tenant(pg_id, is_resolved=is_resolved, urgency=urgency)

    def get_complaint(self, pg_id: int, complaint_id: int) -> Complaint:
        c = self.repo.get(pg_id, complaint_id)
        if c is None:
            raise ComplaintNotFoundError(complaint_id)
        return c

    def set_resolved(self, pg_id: int, complaint_id: int, is_resolved: bool) -> Complaint:
        c = self.get_complaint(pg_id, complaint_id)
        c.is_resolved = is_resolved
        return self.repo.save(c)

    def ingest_inbound(
        self,
        resident: Resident,
        raw_text: str,
        provider_message_id: str,
        ai: AIProvider,
        whatsapp: WhatsAppClient,
    ) -> Complaint:
        """Persist a complaint, parse it via AI, send acknowledgment.

        On AI failure we still save the row with `needs_review=True` so nothing
        is lost. WhatsApp send failures are logged but don't roll back the
        complaint — we already have it on file.
        """
        if existing := self.repo.get_by_provider_message_id(provider_message_id):
            return existing  # idempotent: webhook redelivery is common

        complaint = Complaint(
            pg_id=resident.pg_id,
            resident_id=resident.id,
            raw_whatsapp_msg=raw_text,
            provider_message_id=provider_message_id,
            category=ComplaintCategory.OTHER,
            urgency=ComplaintUrgency.MEDIUM,
            needs_review=True,
        )

        try:
            extracted = ai.parse_complaint(raw_text)
            complaint.parsed_issue = extracted.issue_description
            complaint.room_number = extracted.room_number
            complaint.category = ComplaintCategory(extracted.category)
            complaint.urgency = ComplaintUrgency(extracted.urgency)
            complaint.needs_review = False
        except AIUnavailableError:
            logger.warning("AI parse failed for msg=%s — saving for manual review",
                           provider_message_id)

        complaint = self.repo.add(complaint)
        self._send_acknowledgment(whatsapp, resident.phone_number, complaint)
        return complaint

    @staticmethod
    def _send_acknowledgment(
        whatsapp: WhatsAppClient, phone: str, complaint: Complaint
    ) -> None:
        if complaint.needs_review:
            body = (
                "Thanks — we received your message and our team will review it shortly."
            )
        else:
            body = (
                f"Got it. We've logged your {complaint.category.value} issue "
                f"(urgency: {complaint.urgency.value}). Reference #C{complaint.id}."
            )
        try:
            whatsapp.send_text(phone, body)
        except WhatsAppError:
            logger.exception("ack send failed for complaint=%s", complaint.id)
