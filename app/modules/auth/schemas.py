from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OwnerRegisterRequest(BaseModel):
    pg_name: str = Field(min_length=2, max_length=120)
    owner_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class OwnerLoginRequest(BaseModel):
    phone_number: str
    password: str


class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pg_name: str
    owner_name: str
    phone_number: str
    upi_vpa: str | None
    created_at: datetime


class OwnerUpdateProfile(BaseModel):
    pg_name: str | None = Field(default=None, min_length=2, max_length=120)
    owner_name: str | None = Field(default=None, min_length=2, max_length=120)
    upi_vpa: str | None = Field(default=None, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
