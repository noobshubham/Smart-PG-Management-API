from functools import lru_cache

from app.core.config import get_settings
from app.integrations.ai.base import AIProvider
from app.integrations.ai.gemini import GeminiProvider


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Return the configured AI provider singleton.

    Today only Gemini is supported. Adding a provider = new impl + branch here.
    """
    settings = get_settings()
    return GeminiProvider(api_key=settings.gemini_api_key)
