from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    OwnerAlreadyExistsError,
)
from app.modules.auth.models import PgOwner
from app.modules.auth.repository import OwnerRepository
from app.modules.auth.schemas import (
    OwnerLoginRequest,
    OwnerRegisterRequest,
    OwnerUpdateProfile,
    TokenResponse,
)


class AuthService:
    def __init__(self, repo: OwnerRepository) -> None:
        self.repo = repo
        self.settings = get_settings()

    def register(self, payload: OwnerRegisterRequest) -> PgOwner:
        if self.repo.get_by_phone(payload.phone_number):
            raise OwnerAlreadyExistsError(payload.phone_number)

        owner = PgOwner(
            pg_name=payload.pg_name.strip(),
            owner_name=payload.owner_name.strip(),
            phone_number=payload.phone_number.strip(),
            hashed_password=hash_password(payload.password),
        )
        return self.repo.create(owner)

    def login(self, payload: OwnerLoginRequest) -> TokenResponse:
        owner = self.repo.get_by_phone(payload.phone_number)
        if not owner or not verify_password(payload.password, owner.hashed_password):
            raise InvalidCredentialsError()

        token = create_access_token(
            subject=owner.id,
            extra_claims={"pg_id": owner.id},
        )
        return TokenResponse(
            access_token=token,
            expires_in_minutes=self.settings.jwt_access_token_expire_minutes,
        )

    def update_profile(self, owner: PgOwner, payload: OwnerUpdateProfile) -> PgOwner:
        if payload.pg_name is not None:
            owner.pg_name = payload.pg_name.strip()
        if payload.owner_name is not None:
            owner.owner_name = payload.owner_name.strip()
        if payload.upi_vpa is not None:
            owner.upi_vpa = payload.upi_vpa.strip() or None
        return self.repo.save(owner)
