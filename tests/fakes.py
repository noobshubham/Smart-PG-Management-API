"""Fake AI / WhatsApp implementations used across tests.

Both implement the same Protocols the production code depends on, so the
swap is transparent — services and routers can't tell the difference.
"""
from collections import defaultdict
from typing import Any

from app.integrations.ai.base import (
    AIProvider,
    AIUnavailableError,
    ComplaintExtraction,
    IdCardExtraction,
    MealResponseExtraction,
)
from app.integrations.whatsapp.base import InboundMessage, WhatsAppClient


class FakeAIProvider(AIProvider):
    """Returns canned responses set by the test. Defaults are intentionally
    boring so tests fail loudly if they forget to configure a response.
    """

    def __init__(self) -> None:
        self.complaint_response: ComplaintExtraction | None = ComplaintExtraction(
            room_number=None,
            issue_description="generic",
            category="other",
            urgency="medium",
        )
        self.meal_response: MealResponseExtraction | None = MealResponseExtraction(
            will_eat_dinner=None, special_instructions=None
        )
        self.id_response: IdCardExtraction | None = IdCardExtraction(
            name=None, date_of_birth=None, id_number=None, address=None, id_type="other"
        )
        self.raise_on_complaint = False
        self.raise_on_meal = False
        self.raise_on_id = False
        self.complaint_calls: list[str] = []
        self.meal_calls: list[str] = []
        self.id_calls: list[tuple[bytes, str]] = []

    def parse_complaint(self, raw_text: str) -> ComplaintExtraction:
        self.complaint_calls.append(raw_text)
        if self.raise_on_complaint:
            raise AIUnavailableError("test")
        assert self.complaint_response is not None
        return self.complaint_response

    def parse_meal_response(self, raw_text: str) -> MealResponseExtraction:
        self.meal_calls.append(raw_text)
        if self.raise_on_meal:
            raise AIUnavailableError("test")
        assert self.meal_response is not None
        return self.meal_response

    def extract_id_card(self, image_bytes: bytes, mime_type: str) -> IdCardExtraction:
        self.id_calls.append((image_bytes, mime_type))
        if self.raise_on_id:
            raise AIUnavailableError("test")
        assert self.id_response is not None
        return self.id_response


class FakeWhatsAppClient(WhatsAppClient):
    def __init__(self, *, verify_token: str = "test-verify") -> None:
        self.sent: list[tuple[str, str]] = []
        self.fail_for_phones: set[str] = set()
        self._verify_token = verify_token
        self.inbound_to_return: list[InboundMessage] = []
        self.calls_per_phone: dict[str, int] = defaultdict(int)

    def send_text(self, to_phone: str, body: str) -> None:
        self.calls_per_phone[to_phone] += 1
        if to_phone in self.fail_for_phones:
            from app.integrations.whatsapp.base import WhatsAppError

            raise WhatsAppError("forced failure for test")
        self.sent.append((to_phone, body))

    def parse_inbound(self, raw_payload: dict[str, Any]) -> list[InboundMessage]:
        return self.inbound_to_return

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None
