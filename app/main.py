from fastapi import Depends, FastAPI

from app.core.config import get_settings
from app.core.deps import TenantContext, get_current_owner, get_tenant
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.modules.auth.models import PgOwner
from app.modules.auth.router import router as auth_router
from app.modules.auth.schemas import OwnerResponse
from app.modules.complaints.router import router as complaints_router
from app.modules.finance.router import router as finance_router
from app.modules.inbound.router import router as inbound_router
from app.modules.meals.router import router as meals_router
from app.modules.notices.router import router as notices_router
from app.modules.properties.router import router as properties_router
from app.modules.residents.router import router as residents_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Smart PG Management API",
        version="0.4.0",
        debug=settings.app_debug,
    )

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(properties_router)
    app.include_router(residents_router)
    app.include_router(finance_router)
    app.include_router(complaints_router)
    app.include_router(notices_router)
    app.include_router(meals_router)
    app.include_router(inbound_router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    @app.get("/me", response_model=OwnerResponse, tags=["auth"])
    def whoami(owner: PgOwner = Depends(get_current_owner)) -> OwnerResponse:
        return OwnerResponse.model_validate(owner)

    @app.get("/_tenant", tags=["meta"])
    def tenant_probe(tenant: TenantContext = Depends(get_tenant)) -> dict[str, int]:
        return {"owner_id": tenant.owner_id, "pg_id": tenant.pg_id}

    return app


app = create_app()
