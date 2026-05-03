from functools import lru_cache

from app.core.config import get_settings
from app.integrations.whatsapp.base import WhatsAppClient
from app.integrations.whatsapp.meta import MetaWhatsAppClient


@lru_cache(maxsize=1)
def get_whatsapp_client() -> WhatsAppClient:
    settings = get_settings()
    if settings.whatsapp_provider == "meta":
        return MetaWhatsAppClient(
            api_token=settings.whatsapp_api_token,
            phone_number_id=settings.whatsapp_phone_number_id,
            verify_token=settings.whatsapp_verify_token,
        )
    raise NotImplementedError(
        f"WhatsApp provider '{settings.whatsapp_provider}' not implemented"
    )
