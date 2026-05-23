from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.routers import (
    auth,
    breaks,
    clock_ins,
    documents,
    employees,
    groups,
    leave_requests,
    legal,
    organization,
    platform,
    platform_billing,
    platform_catalog,
    platform_stripe,
    platform_whatsapp,
    public,
    settings,
    shifts,
    stripe_webhook,
    tenants,
)
from app.schemas.tenant import TenantBrandingRead

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(stripe_webhook.router)
api_router.include_router(platform.router)
api_router.include_router(platform_billing.router)
api_router.include_router(platform_catalog.router)
api_router.include_router(platform_stripe.router)
api_router.include_router(platform_whatsapp.router)
api_router.add_api_route(
    "/tenants/public/{slug}/branding",
    tenants.public_branding,
    methods=["GET"],
    response_model=TenantBrandingRead,
    tags=["tenants"],
)

protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(tenants.router)
protected.include_router(employees.router)
protected.include_router(clock_ins.router)
protected.include_router(breaks.router)
protected.include_router(legal.router)
protected.include_router(leave_requests.router)
protected.include_router(shifts.router)
protected.include_router(documents.router)
protected.include_router(settings.router)
protected.include_router(groups.router)
protected.include_router(organization.router)
api_router.include_router(protected)
