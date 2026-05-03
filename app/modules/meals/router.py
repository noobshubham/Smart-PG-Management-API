from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant
from app.modules.meals.repository import MealLogRepository
from app.modules.meals.schemas import HeadcountResponse, MealLogResponse
from app.modules.meals.service import MealService

router = APIRouter(prefix="/meals", tags=["meals"])


def get_meal_service(db: Session = Depends(get_db)) -> MealService:
    return MealService(MealLogRepository(db))


@router.get("/logs", response_model=list[MealLogResponse])
def list_meal_logs(
    on: date_type = Query(..., description="Date in YYYY-MM-DD"),
    tenant: TenantContext = Depends(get_tenant),
    service: MealService = Depends(get_meal_service),
) -> list[MealLogResponse]:
    logs = service.list_for_date(tenant.pg_id, on)
    return [MealLogResponse.model_validate(log) for log in logs]


@router.get("/headcount", response_model=HeadcountResponse)
def headcount(
    on: date_type = Query(..., description="Date in YYYY-MM-DD"),
    tenant: TenantContext = Depends(get_tenant),
    service: MealService = Depends(get_meal_service),
) -> HeadcountResponse:
    counts = service.headcount(tenant.pg_id, on)
    return HeadcountResponse(date=on, **counts)
