from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.core.permissions import Permission, require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.tenant import Company, Tenant
from app.schemas.billing import TenantAccountBillingRead
from app.schemas.tenant import (
    CompanyCreate,
    CompanyRead,
    TenantBillingUpdate,
    TenantBrandingRead,
    TenantCreate,
    TenantRead,
    TenantUpdate,
    TenantWhatsAppStatusRead,
)
from app.services.billing_read import tenant_account_billing
from app.services.gowa_client import get_shared_whatsapp_session
from app.services.org_service import (
    clone_groups_for_tenant,
    ensure_group_templates,
    seed_tenant_organization,
)

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


@router.get("/current/billing-summary", response_model=TenantAccountBillingRead)
def current_billing_summary(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> TenantAccountBillingRead:
    data = tenant_account_billing(session, ctx.tenant.id)
    session.commit()
    return TenantAccountBillingRead(**data)


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


@router.get("/current/whatsapp/status", response_model=TenantWhatsAppStatusRead)
async def tenant_whatsapp_status(
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> TenantWhatsAppStatusRead:
    """Estado del WhatsApp compartido de alcurro (solo lectura para cuentas cliente)."""
    data = await get_shared_whatsapp_session(session)
    linked = data.get("connected", False)
    configured = data.get("configured", False)
    if linked:
        msg = (
            "WhatsApp de alcurro está activo. Tus empleados pueden fichar "
            "desde su móvil si tienen el teléfono registrado."
        )
    elif configured:
        msg = (
            "WhatsApp de alcurro pendiente de vincular. "
            "El administrador de la plataforma debe escanear el código QR."
        )
    else:
        msg = "WhatsApp de alcurro aún no está configurado en la plataforma."
    return TenantWhatsAppStatusRead(
        connected=linked,
        configured=configured,
        message=msg,
    )


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
    from app.services.legal_service import seed_default_legal_documents

    seed_default_legal_documents(session, tenant.id)
    session.commit()
    session.refresh(tenant)
    return tenant
