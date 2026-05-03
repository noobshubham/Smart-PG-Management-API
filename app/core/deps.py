"""Shared FastAPI dependencies — auth, tenant scoping, etc."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.modules.auth.models import PgOwner
from app.modules.auth.repository import OwnerRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


@dataclass(frozen=True)
class TenantContext:
    """Resolved per-request identity. `pg_id` is the tenant boundary."""

    owner_id: int
    pg_id: int


def _credentials_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_owner(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> PgOwner:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise _credentials_error()

    sub = payload.get("sub")
    if sub is None:
        raise _credentials_error()

    try:
        owner_id = int(sub)
    except (TypeError, ValueError):
        raise _credentials_error()

    owner = OwnerRepository(db).get_by_id(owner_id)
    if owner is None:
        raise _credentials_error("Owner no longer exists")
    return owner


def get_tenant(owner: PgOwner = Depends(get_current_owner)) -> TenantContext:
    """Inject this into any tenant-scoped route to obtain `pg_id`.

    `pg_id` is derived from the authenticated owner — never trust it from
    the request body or query string.
    """
    return TenantContext(owner_id=owner.id, pg_id=owner.id)
