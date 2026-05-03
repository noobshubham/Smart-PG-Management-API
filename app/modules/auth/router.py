from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_owner
from app.modules.auth.exceptions import InvalidCredentialsError, OwnerAlreadyExistsError
from app.modules.auth.models import PgOwner
from app.modules.auth.repository import OwnerRepository
from app.modules.auth.schemas import (
    OwnerLoginRequest,
    OwnerRegisterRequest,
    OwnerResponse,
    OwnerUpdateProfile,
    TokenResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(OwnerRepository(db))


@router.post(
    "/register",
    response_model=OwnerResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_owner(
    payload: OwnerRegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> OwnerResponse:
    try:
        owner = service.register(payload)
    except OwnerAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return OwnerResponse.model_validate(owner)


@router.post("/login", response_model=TokenResponse)
def login_owner(
    payload: OwnerLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return service.login(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.patch("/me", response_model=OwnerResponse)
def update_profile(
    payload: OwnerUpdateProfile,
    owner: PgOwner = Depends(get_current_owner),
    service: AuthService = Depends(get_auth_service),
) -> OwnerResponse:
    updated = service.update_profile(owner, payload)
    return OwnerResponse.model_validate(updated)
