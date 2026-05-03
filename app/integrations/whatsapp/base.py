"""Provider-agnostic WhatsApp interface.

Domain code only ever imports from here. The webhook router accepts the raw
provider payload, hands it to the provider's `parse_inbound`, and downstream
services consume the normalised `InboundMessage`.
"""
from dataclasses import dataclass
from typing import Any, Literal, Protocol


class WhatsAppError(Exception):
    """Base for messaging errors (send failure, invalid signature, etc)."""


@dataclass(frozen=True)
class InboundMessage:
    """Provider-neutral inbound WhatsApp message.

    `from_phone` is normalised to the format stored on residents (E.164
    without leading "+" or "whatsapp:" prefix).
    """

    provider_message_id: str
    from_phone: str
    text: str | None
    media_url: str | None
    media_mime_type: str | None
    kind: Literal["text", "image", "other"]


class WhatsAppClient(Protocol):
    """Stable contract for sending and receiving WhatsApp messages."""

    def send_text(self, to_phone: str, body: str) -> None: ...

    def parse_inbound(self, raw_payload: dict[str, Any]) -> list[InboundMessage]: ...

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """For Meta's GET-verification handshake. Return challenge on success."""
        ...
