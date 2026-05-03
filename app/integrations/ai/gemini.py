"""Gemini implementation of `AIProvider`.

Uses Gemini's structured-output mode (`response_mime_type=application/json`)
so the result is guaranteed parseable JSON.
"""
import json
import logging
from typing import Any

from app.integrations.ai.base import (
    AIProvider,
    AIUnavailableError,
    ComplaintExtraction,
    IdCardExtraction,
    MealResponseExtraction,
)

logger = logging.getLogger(__name__)

_COMPLAINT_PROMPT = """You are a property-management assistant. Extract a JSON object from the resident's WhatsApp message describing a problem in their PG.

Return ONLY this JSON shape (no prose):
{
  "room_number": "<string or null>",
  "issue_description": "<one short sentence summarising the issue>",
  "category": "plumbing | electrical | cleaning | appliance | security | internet | other",
  "urgency": "low | medium | high"
}

Rules:
- room_number is null if not mentioned.
- urgency=high if water leak, gas, fire, no power, safety risk; medium for hot water / AC / wifi outage; low otherwise.
- Pick the closest category; use "other" only if nothing fits.

Resident message:
\"\"\"{message}\"\"\"
"""

_MEAL_PROMPT = """A resident has replied to a WhatsApp poll asking whether they will eat dinner tonight at the PG.

Return ONLY this JSON:
{
  "will_eat_dinner": true | false | null,
  "special_instructions": "<string or null>"
}

- true if they confirm they will eat / are coming.
- false if they decline / will be out / not eating.
- null if you cannot tell.
- special_instructions: e.g. "no spice", "less rice", "extra roti" — null if none.

Reply:
\"\"\"{message}\"\"\"
"""

_ID_PROMPT = """Extract identity information from this Indian government ID card image.

Return ONLY this JSON:
{
  "name": "<full name as printed, or null>",
  "date_of_birth": "<YYYY-MM-DD or null>",
  "id_number": "<the ID number as printed, or null>",
  "address": "<address as printed, or null>",
  "id_type": "aadhar | pan | other"
}

Rules:
- Aadhar IDs have a 12-digit number. PAN IDs are 10 alphanumeric chars.
- If date is in DD/MM/YYYY format, convert to ISO YYYY-MM-DD.
- Use null for fields that aren't legible or not present.
"""


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash") -> None:
        if not api_key:
            raise AIUnavailableError("GEMINI_API_KEY not configured")
        # Lazy import so unit tests can stub without the SDK installed.
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model = genai.GenerativeModel(model_name)

    def parse_complaint(self, raw_text: str) -> ComplaintExtraction:
        data = self._json_call(_COMPLAINT_PROMPT.replace("{message}", raw_text))
        return ComplaintExtraction(
            room_number=_str_or_none(data.get("room_number")),
            issue_description=str(data.get("issue_description") or "").strip()
            or raw_text[:200],
            category=_norm_category(data.get("category")),
            urgency=_norm_urgency(data.get("urgency")),
        )

    def parse_meal_response(self, raw_text: str) -> MealResponseExtraction:
        data = self._json_call(_MEAL_PROMPT.replace("{message}", raw_text))
        return MealResponseExtraction(
            will_eat_dinner=_bool_or_none(data.get("will_eat_dinner")),
            special_instructions=_str_or_none(data.get("special_instructions")),
        )

    def extract_id_card(self, image_bytes: bytes, mime_type: str) -> IdCardExtraction:
        try:
            response = self._model.generate_content(
                [
                    _ID_PROMPT,
                    {"mime_type": mime_type, "data": image_bytes},
                ],
                generation_config={"response_mime_type": "application/json"},
            )
            data = json.loads(response.text)
        except Exception as exc:  # noqa: BLE001 - any SDK failure → AIUnavailable
            logger.exception("gemini id-card extraction failed")
            raise AIUnavailableError("ID extraction failed") from exc

        return IdCardExtraction(
            name=_str_or_none(data.get("name")),
            date_of_birth=_str_or_none(data.get("date_of_birth")),
            id_number=_str_or_none(data.get("id_number")),
            address=_str_or_none(data.get("address")),
            id_type=_norm_id_type(data.get("id_type")),
        )

    def _json_call(self, prompt: str) -> dict[str, Any]:
        try:
            response = self._model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            return json.loads(response.text)
        except Exception as exc:  # noqa: BLE001
            logger.exception("gemini call failed")
            raise AIUnavailableError("Gemini call failed") from exc


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _bool_or_none(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    if isinstance(v, str):
        low = v.strip().lower()
        if low in {"true", "yes", "y"}:
            return True
        if low in {"false", "no", "n"}:
            return False
    return None


_VALID_CATEGORIES = {"plumbing", "electrical", "cleaning", "appliance", "security", "internet", "other"}
_VALID_URGENCY = {"low", "medium", "high"}
_VALID_ID_TYPES = {"aadhar", "pan", "other"}


def _norm_category(v: Any) -> str:
    s = str(v or "").strip().lower()
    return s if s in _VALID_CATEGORIES else "other"


def _norm_urgency(v: Any) -> str:
    s = str(v or "").strip().lower()
    return s if s in _VALID_URGENCY else "medium"


def _norm_id_type(v: Any) -> str:
    s = str(v or "").strip().lower()
    return s if s in _VALID_ID_TYPES else "other"
