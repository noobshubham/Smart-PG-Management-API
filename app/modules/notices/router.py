from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.core.deps import TenantContext, get_tenant
from app.integrations.whatsapp import WhatsAppClient, get_whatsapp_client
from app.modules.notices.repository import NoticeRepository
from app.modules.notices.schemas import BroadcastRequest, NoticeResponse
from app.modules.notices.service import NoticeService
from app.modules.residents.repository import ResidentRepository

router = APIRouter(prefix="/notices", tags=["notices"])


def get_notice_service(db: Session = Depends(get_db)) -> NoticeService:
    return NoticeService(NoticeRepository(db), ResidentRepository(db))


@router.get("", response_model=list[NoticeResponse])
def list_notices(
    tenant: TenantContext = Depends(get_tenant),
    service: NoticeService = Depends(get_notice_service),
) -> list[NoticeResponse]:
    return [NoticeResponse.model_validate(n) for n in service.list_notices(tenant.pg_id)]


@router.post(
    "/broadcast",
    response_model=NoticeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def broadcast(
    payload: BroadcastRequest,
    background: BackgroundTasks,
    tenant: TenantContext = Depends(get_tenant),
    service: NoticeService = Depends(get_notice_service),
    whatsapp: WhatsAppClient = Depends(get_whatsapp_client),
) -> NoticeResponse:
    notice, phones = service.create_pending(tenant.pg_id, payload.message)
    background.add_task(_deliver, tenant.pg_id, notice.id, phones, whatsapp)
    return NoticeResponse.model_validate(notice)


def _deliver(
    pg_id: int, notice_id: int, phones: list[str], whatsapp: WhatsAppClient
) -> None:
    db = SessionLocal()
    try:
        NoticeService(NoticeRepository(db), ResidentRepository(db)).deliver(
            pg_id, notice_id, phones, whatsapp
        )
    finally:
        db.close()
