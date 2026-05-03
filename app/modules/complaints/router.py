from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant
from app.modules.complaints.exceptions import ComplaintNotFoundError
from app.modules.complaints.models import ComplaintUrgency
from app.modules.complaints.repository import ComplaintRepository
from app.modules.complaints.schemas import ComplaintResponse, ResolveComplaintRequest
from app.modules.complaints.service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["complaints"])


def get_complaint_service(db: Session = Depends(get_db)) -> ComplaintService:
    return ComplaintService(ComplaintRepository(db))


@router.get("", response_model=list[ComplaintResponse])
def list_complaints(
    is_resolved: bool | None = Query(default=None),
    urgency: ComplaintUrgency | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant),
    service: ComplaintService = Depends(get_complaint_service),
) -> list[ComplaintResponse]:
    items = service.list_complaints(
        tenant.pg_id, is_resolved=is_resolved, urgency=urgency
    )
    return [ComplaintResponse.model_validate(c) for c in items]


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    tenant: TenantContext = Depends(get_tenant),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintResponse:
    try:
        return ComplaintResponse.model_validate(
            service.get_complaint(tenant.pg_id, complaint_id)
        )
    except ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{complaint_id}/resolve", response_model=ComplaintResponse)
def resolve_complaint(
    complaint_id: int,
    payload: ResolveComplaintRequest,
    tenant: TenantContext = Depends(get_tenant),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintResponse:
    try:
        c = service.set_resolved(tenant.pg_id, complaint_id, payload.is_resolved)
    except ComplaintNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ComplaintResponse.model_validate(c)
