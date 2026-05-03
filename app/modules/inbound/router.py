"""WhatsApp webhook entrypoint.

Contract (per SRS): always return 200 OK promptly. Heavy work (AI calls,
DB writes, outbound sends) is offloaded to FastAPI BackgroundTasks so the
provider isn't kept waiting and won't retry.
"""
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse, Response

from app.core.db import SessionLocal
from app.integrations.ai import AIProvider, get_ai_provider
from app.integrations.whatsapp import WhatsAppClient, get_whatsapp_client
from app.integrations.whatsapp.base import InboundMessage
from app.modules.inbound.dispatcher import dispatch_inbound

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


@router.get("", response_class=PlainTextResponse)
def verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
    whatsapp: WhatsAppClient = Depends(get_whatsapp_client),
) -> str:
    """Meta verification handshake. Echoes the challenge if our token matches."""
    challenge = whatsapp.verify_webhook(hub_mode, hub_token, hub_challenge)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="verification failed")
    return challenge


@router.post("", status_code=status.HTTP_200_OK)
async def receive(
    request: Request,
    background: BackgroundTasks,
    whatsapp: WhatsAppClient = Depends(get_whatsapp_client),
    ai: AIProvider = Depends(get_ai_provider),
) -> Response:
    payload: dict[str, Any] = await request.json()
    try:
        messages = whatsapp.parse_inbound(payload)
    except Exception:  # noqa: BLE001
        logger.exception("malformed inbound payload")
        return Response(status_code=status.HTTP_200_OK)

    for msg in messages:
        background.add_task(_handle_one, msg, ai, whatsapp)

    return Response(status_code=status.HTTP_200_OK)


def _handle_one(msg: InboundMessage, ai: AIProvider, whatsapp: WhatsAppClient) -> None:
    """Open a fresh DB session per background task — request session is gone."""
    db = SessionLocal()
    try:
        dispatch_inbound(db, msg, ai=ai, whatsapp=whatsapp)
    finally:
        db.close()
