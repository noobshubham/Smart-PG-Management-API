from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.complaints.models import ComplaintCategory, ComplaintUrgency


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resident_id: int | None
    raw_whatsapp_msg: str
    parsed_issue: str | None
    room_number: str | None
    category: ComplaintCategory
    urgency: ComplaintUrgency
    needs_review: bool
    is_resolved: bool
    created_at: datetime


class ResolveComplaintRequest(BaseModel):
    is_resolved: bool = True
