"""Provider-agnostic AI interface.

Domain code depends on `AIProvider` and the DTOs below. Swapping Gemini for
another provider only requires implementing this Protocol and updating the
factory.
"""
from dataclasses import dataclass
from typing import Literal, Protocol


class AIUnavailableError(Exception):
    """Raised when the AI call fails or returns unparseable output.

    Callers should handle this gracefully (e.g. fall back to "manual review").
    """


ComplaintCategory = Literal[
    "plumbing", "electrical", "cleaning", "appliance", "security", "internet", "other"
]
Urgency = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ComplaintExtraction:
    room_number: str | None
    issue_description: str
    category: ComplaintCategory
    urgency: Urgency


@dataclass(frozen=True)
class IdCardExtraction:
    name: str | None
    date_of_birth: str | None  # ISO YYYY-MM-DD when extractable
    id_number: str | None
    address: str | None
    id_type: Literal["aadhar", "pan", "other"]


@dataclass(frozen=True)
class MealResponseExtraction:
    will_eat_dinner: bool | None
    special_instructions: str | None


class AIProvider(Protocol):
    """Stable contract — domain services depend on this, not on Gemini."""

    def parse_complaint(self, raw_text: str) -> ComplaintExtraction: ...

    def parse_meal_response(self, raw_text: str) -> MealResponseExtraction: ...

    def extract_id_card(self, image_bytes: bytes, mime_type: str) -> IdCardExtraction: ...
