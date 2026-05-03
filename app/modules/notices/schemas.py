from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BroadcastRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class NoticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    recipient_count: int
    delivered_count: int
    failed_count: int
    created_at: datetime
