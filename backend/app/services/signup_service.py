"""Alta pública de nuevos clientes (tenant)."""

import json
import logging
from uuid import UUID

from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.billing import BillingCycle, PendingSignup, PendingSignupStatus, PricingPlan, SubscriptionStatus
from app.models.models import Employee, Role
from app.models.tenant import Tenant
from app.schemas.public import PublicSignupRequest, PublicSignupResponse
from app.services.billing_service import copy_tenant_billing_to_company
from app.services.org_service import clone_groups_for_tenant, ensure_group_templates, seed_tenant_organization
from app.services.pricing_service import (
    get_active_discount_by_code,
    sync_subscription_pricing,
)
from app.services.legal_service import seed_default_legal_documents
from app.services.rbac_service import assign_role_default_group, ensure_system_groups
from app.services.slug import resolve_tenant_slug
from app.config import get_settings
from app.services.paddle_service import (
    get_paddle_price_id,
    paddle_configured,
)

_log = logging.getLogger(__name__)


def register_tenant(session: Session, data: PublicSignupRequest) -> PublicSignupResponse:
    """Crea el tenant inmediatamente (sin LS o desde webhook de PendingSignup)."""
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
    tenant.billing_company_id = company.id
    session.add(company)
    session.add(tenant)
    clone_groups_for_tenant(session, tenant.id)
    ensure_system_groups(session, tenant.id)
    seed_default_legal_documents(session, tenant.id)

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

    return PublicSignupResponse(
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        company_name=tenant.name,
        checkout_url=None,
        admin_login_hint=f"Accede en {base}/acceso-cliente con cuenta «{tenant.slug}» y usuario ADM001",
    )


def initiate_signup(session: Session, data: PublicSignupRequest) -> PublicSignupResponse:
    """Punto de entrada público. Si Paddle está configurado, crea PendingSignup y
    devuelve los parámetros para abrir el overlay de checkout; si no, crea el tenant."""
    plan = session.get(PricingPlan, data.pricing_plan_id)
    if not plan or not plan.is_active:
        raise ValueError("Tarifa no válida")

    cycle = (
        data.billing_cycle.value
        if hasattr(data.billing_cycle, "value")
        else str(data.billing_cycle)
    )
    price_id = get_paddle_price_id(plan, cycle)

    if not paddle_configured() or not price_id:
        # Sin Paddle: crear cuenta inmediatamente
        resp = register_tenant(session, data)
        session.commit()
        return resp

    # Con Paddle: guardar PendingSignup y devolver parámetros del overlay.
    # El código de descuento se pasa al overlay para que Paddle lo aplique en el
    # checkout y lo herede en los renewals posteriores.
    discount = get_active_discount_by_code(session, data.discount_code, plan.id)

    pending = PendingSignup(
        data_json=data.model_dump_json(),
        status=PendingSignupStatus.PENDING,
    )
    session.add(pending)
    session.flush()

    settings = get_settings()
    base = settings.public_app_url.rstrip("/")
    success_url = f"{base}/registro/ok?pending={pending.id}"

    session.commit()

    return PublicSignupResponse(
        pending_signup_id=pending.id,
        company_name=data.company_name.strip(),
        paddle_price_id=price_id,
        paddle_client_token=settings.paddle_client_token,
        paddle_env=settings.paddle_env,
        paddle_discount_code=discount.code if discount else None,
        customer_email=data.billing_email,
        success_url=success_url,
    )
