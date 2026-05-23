from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.core.permissions import Permission, require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.tenant import Company, Tenant
from app.schemas.tenant import (
    CompanyCreate,
    CompanyRead,
    TenantBillingUpdate,
    TenantBrandingRead,
    TenantCreate,
    TenantRead,
    TenantUpdate,
)
from app.services.org_service import (
    clone_groups_for_tenant,
    ensure_group_templates,
    seed_tenant_organization,
)
from app.services.gowa_provisioner import provision_gowa, stop_gowa

router = APIRouter(prefix="/tenants", tags=["tenants"])


def public_branding(slug: str, session: Session = Depends(get_session)) -> Tenant:
    tenant = session.exec(select(Tenant).where(Tenant.slug == slug.lower())).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return tenant


@router.get("/current", response_model=TenantRead)
def current_tenant(
    ctx: TenantContext = Depends(get_tenant_context),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> Tenant:
    return ctx.tenant


@router.patch("/current/branding", response_model=TenantRead)
def update_current_branding(
    data: TenantUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    tenant = ctx.tenant
    for key, value in data.model_dump(exclude_unset=True).items():
        if key in ("name", "logo_url", "primary_color", "secondary_color", "accent_color"):
            setattr(tenant, key, value)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.patch("/current/billing", response_model=TenantRead)
def update_current_billing(
    data: TenantBillingUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    tenant = ctx.tenant
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "billing_email" and value is not None:
            value = str(value)
        setattr(tenant, key, value)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.get("/current/companies", response_model=list[CompanyRead])
def list_companies(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
) -> list[Company]:
    return list(
        session.exec(
            select(Company).where(Company.tenant_id == ctx.tenant.id)
        ).all()
    )


@router.post("/current/companies", response_model=CompanyRead, status_code=201)
def create_company(
    data: CompanyCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "companies")),
) -> Company:
    row = Company(tenant_id=ctx.tenant.id, name=data.name, tax_id=data.tax_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.post("/current/provision-gowa", response_model=TenantRead)
def provision_current_gowa(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "tenant")),
) -> Tenant:
    return provision_gowa(session, ctx.tenant.id)


@router.post("/current/stop-gowa", response_model=TenantRead)
def stop_current_gowa(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "tenant")),
) -> Tenant:
    return stop_gowa(session, ctx.tenant.id)


# --- Plataforma: crear nuevas cuentas tenant (solo super-admin del tenant demo) ---


@router.post("", response_model=TenantRead, status_code=201)
def create_tenant(
    data: TenantCreate,
    session: Session = Depends(get_session),
    x_platform_key: str | None = Header(default=None, alias="X-Platform-Key"),
) -> Tenant:
    if x_platform_key != get_settings().platform_setup_key:
        raise HTTPException(status_code=403, detail="Clave de plataforma inválida")
    from app.services.slug import resolve_tenant_slug

    slug = resolve_tenant_slug(session, data.name, data.slug)
    tenant = Tenant(
        slug=slug,
        name=data.name,
        legal_name=data.legal_name,
        tax_id=data.tax_id,
        billing_email=str(data.billing_email) if data.billing_email else None,
        billing_phone=data.billing_phone,
        billing_address=data.billing_address,
        billing_city=data.billing_city,
        billing_postal_code=data.billing_postal_code,
        billing_province=data.billing_province,
        billing_country=data.billing_country or "ES",
        primary_color=data.primary_color,
        secondary_color=data.secondary_color,
        accent_color=data.accent_color,
        gowa_basic_auth=data.gowa_basic_auth,
        gowa_webhook_path=f"/webhook/whatsapp/{slug}",
    )
    session.add(tenant)
    session.flush()
    ensure_group_templates(session)
    seed_tenant_organization(session, tenant, data.name)
    clone_groups_for_tenant(session, tenant.id)
    session.commit()
    session.refresh(tenant)
    return tenant
