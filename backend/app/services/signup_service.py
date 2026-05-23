"""Alta pública de nuevos clientes (tenant)."""

from uuid import UUID

from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.billing import BillingCycle, PricingPlan, SubscriptionStatus
from app.models.models import Employee, Role
from app.models.tenant import Tenant
from app.schemas.public import PublicSignupRequest, PublicSignupResponse
from app.services.billing_service import copy_tenant_billing_to_company
from app.services.org_service import clone_groups_for_tenant, ensure_group_templates, seed_tenant_organization
from app.services.pricing_service import (
    get_active_discount_by_code,
    sync_subscription_pricing,
)
from app.services.rbac_service import assign_role_default_group, ensure_system_groups
from app.services.slug import resolve_tenant_slug
from app.services.stripe_service import create_checkout_session, stripe_configured
from app.config import get_settings


def register_tenant(session: Session, data: PublicSignupRequest) -> PublicSignupResponse:
    plan = session.get(PricingPlan, data.pricing_plan_id)
    if not plan or not plan.is_active:
        raise ValueError("Tarifa no válida")

    slug = resolve_tenant_slug(session, data.company_name, data.account_code)
    if session.exec(select(Tenant).where(Tenant.slug == slug)).first():
        raise ValueError("Ya existe una cuenta con ese nombre")

    tenant = Tenant(
        slug=slug,
        name=data.company_name.strip(),
        legal_name=data.legal_name.strip(),
        tax_id=data.tax_id.strip(),
        billing_email=data.billing_email.strip().lower(),
        billing_phone=data.billing_phone.strip(),
        billing_address=data.billing_address,
        billing_city=data.billing_city,
        billing_postal_code=data.billing_postal_code,
        billing_province=data.billing_province,
        billing_country=data.billing_country or "ES",
        gowa_webhook_path=f"/webhook/whatsapp/{slug}",
    )
    session.add(tenant)
    session.flush()

    ensure_group_templates(session)
    company, _, _ = seed_tenant_organization(session, tenant, data.company_name)
    copy_tenant_billing_to_company(tenant, company)
    session.add(company)
    clone_groups_for_tenant(session, tenant.id)
    ensure_system_groups(session, tenant.id)

    admin = Employee(
        company_id=company.id,
        phone=data.admin_phone.strip(),
        email=data.admin_email.strip().lower(),
        full_name=data.admin_name.strip(),
        employee_code="ADM001",
        role=Role.TENANT_ADMIN,
        password_hash=hash_password(data.admin_password),
        is_active=True,
    )
    session.add(admin)
    session.flush()
    assign_role_default_group(session, admin, tenant.id)

    from app.services.billing_service import ensure_default_subscription

    sub = ensure_default_subscription(session, tenant, company)
    discount = get_active_discount_by_code(session, data.discount_code, plan.id)
    cycle = (
        data.billing_cycle.value
        if hasattr(data.billing_cycle, "value")
        else str(data.billing_cycle)
    )
    sync_subscription_pricing(session, sub, plan, cycle, discount)
    sub.status = SubscriptionStatus.TRIALING
    session.add(sub)
    session.flush()

    settings = get_settings()
    base = settings.public_app_url.rstrip("/")
    checkout_url = None
    if stripe_configured():
        checkout_url = create_checkout_session(
            session,
            tenant,
            sub,
            plan,
            customer_email=data.billing_email,
            success_url=f"{base}/registro/ok?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/registro?cancelled=1",
        )

    session.commit()

    return PublicSignupResponse(
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        company_name=tenant.name,
        checkout_url=checkout_url,
        stripe_enabled=stripe_configured(),
        admin_login_hint=f"Accede en {base}/acceso-cliente con cuenta «{tenant.slug}» y usuario ADM001",
    )
