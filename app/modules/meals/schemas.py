from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MealLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resident_id: int
    date: date
    prompted_at: datetime | None
    responded_at: datetime | None
    will_eat_dinner: bool | None
    special_instructions: str | None


class HeadcountResponse(BaseModel):
    date: date
    eating: int
    skipping: int
    not_responded: int
    total_polled: int
