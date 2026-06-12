from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.routers import (
    auth,
    breaks,
    clock_ins,
    clock_settings,
    dashboard,
    developer,
    incidents,
    incidents_public,
    documents,
    employees,
    groups,
    leave_balances,
    leave_requests,
    leave_types,
    legal,
    notifications,
    organization,
    projects,
    platform,
    platform_billing,
    platform_catalog,
    platform_invoices,
    platform_settings,
    platform_stripe,
    platform_whatsapp,
    platform_mail,
    platform_ai,
    platform_policy,
    public,
    reports,
    settings,
    shifts,
    signatures,
    signatures_public,
    stripe_webhook,
    tenants,
)
from app.schemas.tenant import TenantBrandingRead

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(incidents_public.router)
api_router.include_router(signatures_public.router)
api_router.include_router(stripe_webhook.router)
api_router.include_router(platform.router)
api_router.include_router(platform_billing.router)
api_router.include_router(platform_catalog.router)
api_router.include_router(platform_invoices.router)
api_router.include_router(platform_settings.router)
api_router.include_router(platform_stripe.router)
api_router.include_router(platform_whatsapp.router)
api_router.include_router(platform_mail.router)
api_router.include_router(platform_ai.router)
api_router.include_router(platform_policy.router)
api_router.include_router(legal.public_router)

# Vista previa pública de documentos (imágenes) — sin autenticación
api_router.add_api_route(
    "/documents/{doc_id}/preview",
    documents.preview_document,
    methods=["GET"],
    tags=["documents"],
)

# Avatar público del empleado — sin autenticación (usado en <img>)
api_router.add_api_route(
    "/employees/{employee_id}/avatar",
    employees.public_employee_avatar,
    methods=["GET"],
    tags=["employees"],
)
api_router.add_api_route(
    "/tenants/public/{slug}/branding",
    tenants.public_branding,
    methods=["GET"],
    response_model=TenantBrandingRead,
    tags=["tenants"],
)

protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(dashboard.router)
protected.include_router(developer.router)
protected.include_router(tenants.router)
protected.include_router(notifications.router)  # antes de employees para evitar conflicto con /{employee_id}
protected.include_router(employees.router)
protected.include_router(clock_ins.router)
protected.include_router(clock_settings.router)
protected.include_router(incidents.router)
protected.include_router(breaks.router)
protected.include_router(legal.router)
protected.include_router(leave_requests.router)
protected.include_router(leave_types.router)
protected.include_router(leave_balances.router)
protected.include_router(shifts.router)
protected.include_router(documents.router)
protected.include_router(signatures.router)
protected.include_router(settings.router)
protected.include_router(groups.router)
protected.include_router(organization.router)
protected.include_router(projects.router)
protected.include_router(reports.router)
api_router.include_router(protected)
