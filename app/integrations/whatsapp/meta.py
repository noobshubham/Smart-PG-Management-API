"""Meta (Facebook) WhatsApp Business Cloud API adapter.

API ref: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import logging
from typing import Any

import httpx

from app.integrations.whatsapp.base import InboundMessage, WhatsAppClient, WhatsAppError

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v21.0"


class MetaWhatsAppClient(WhatsAppClient):
    def __init__(
        self,
        api_token: str,
        phone_number_id: str,
        verify_token: str,
        *,
        http_client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._token = api_token
        self._phone_number_id = phone_number_id
        self._verify_token = verify_token
        self._http = http_client or httpx.Client(timeout=timeout)

    def send_text(self, to_phone: str, body: str) -> None:
        if not self._token or not self._phone_number_id:
            raise WhatsAppError("Meta WhatsApp credentials not configured")

        url = f"{_GRAPH_BASE}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": _normalise_phone(to_phone),
            "type": "text",
            "text": {"body": body},
        }
        try:
            resp = self._http.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("whatsapp send failed to=%s", to_phone)
            raise WhatsAppError(f"Send failed: {exc}") from exc

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None

    def parse_inbound(self, raw_payload: dict[str, Any]) -> list[InboundMessage]:
        """Walk Meta's nested webhook envelope and yield normalised messages.

        Envelope shape (simplified):
          { "entry": [ { "changes": [ { "value": { "messages": [...] } } ] } ] }
        """
        out: list[InboundMessage] = []
        for entry in raw_payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for msg in value.get("messages") or []:
                    parsed = _parse_one(msg)
                    if parsed is not None:
                        out.append(parsed)
        return out


def _parse_one(msg: dict[str, Any]) -> InboundMessage | None:
    msg_id = msg.get("id")
    sender = msg.get("from")
    if not msg_id or not sender:
        return None

    msg_type = msg.get("type")
    if msg_type == "text":
        return InboundMessage(
            provider_message_id=str(msg_id),
            from_phone=_normalise_phone(sender),
            text=(msg.get("text") or {}).get("body"),
            media_url=None,
            media_mime_type=None,
            kind="text",
        )
    if msg_type == "image":
        image = msg.get("image") or {}
        return InboundMessage(
            provider_message_id=str(msg_id),
            from_phone=_normalise_phone(sender),
            text=(image.get("caption") or None),
            media_url=image.get("id"),  # caller must download via Graph
            media_mime_type=image.get("mime_type"),
            kind="image",
        )
    return InboundMessage(
        provider_message_id=str(msg_id),
        from_phone=_normalise_phone(sender),
        text=None,
        media_url=None,
        media_mime_type=None,
        kind="other",
    )


def _normalise_phone(raw: str) -> str:
    """Strip 'whatsapp:' prefix and leading '+' so we can match residents.phone_number."""
    s = raw.strip()
    if s.startswith("whatsapp:"):
        s = s[len("whatsapp:"):]
    return s.lstrip("+")
