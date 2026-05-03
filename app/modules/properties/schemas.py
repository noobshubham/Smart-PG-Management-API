from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    total_capacity: int = Field(gt=0, le=20)


class RoomUpdate(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=20)
    total_capacity: int | None = Field(default=None, gt=0, le=20)


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    total_capacity: int
    available_capacity: int
    created_at: datetime
