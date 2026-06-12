"""Servicios de facturación y suscripciones."""

from uuid import UUID

from sqlmodel import Session, select

from app.models.billing import (
    BillingCycle,
    BillingMethod,
    StripePayment,
    Subscription,
    SubscriptionStatus,
)
from app.models.tenant import Company, Tenant
from app.services.pricing_service import get_default_plan, sync_subscription_pricing


def ensure_default_subscription(
    session: Session, tenant: Tenant, company: Company | None = None
) -> Subscription:
    """Obtiene o crea la suscripción de la cuenta (una por tenant)."""
    row = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant.id)
    ).first()
    if row:
        return row
    plan = get_default_plan(session)
    sub = Subscription(
        tenant_id=tenant.id,
        company_id=company.id if company else None,
        status=SubscriptionStatus.TRIALING,
    )
    if plan:
        sync_subscription_pricing(session, sub, plan, BillingCycle.MONTHLY, None)
    else:
        sub.plan_code = "basica"
        sub.plan_name = "Básica"
        sub.amount_cents = 0
        sub.currency = "EUR"
        sub.billing_cycle = BillingCycle.MONTHLY
    session.add(sub)
    session.flush()
    return sub


def copy_tenant_billing_to_company(tenant: Tenant, company: Company) -> None:
    """Copia datos de facturación del tenant a la empresa (solo si están vacíos)."""
    if not company.legal_name:
        company.legal_name = tenant.legal_name or tenant.name
    if not company.billing_email:
        company.billing_email = tenant.billing_email
    if not company.billing_phone:
        company.billing_phone = tenant.billing_phone
    if not company.billing_address:
        company.billing_address = tenant.billing_address
    if not company.billing_city:
        company.billing_city = tenant.billing_city
    if not company.billing_postal_code:
        company.billing_postal_code = tenant.billing_postal_code
    if not company.billing_province:
        company.billing_province = tenant.billing_province
    if not company.billing_country:
        company.billing_country = tenant.billing_country or "ES"


def resolve_billing_company(session: Session, tenant: Tenant) -> Company | None:
    """Devuelve la empresa de facturación de la cuenta.
    Prioridad: tenant.billing_company_id → primera empresa activa."""
    if tenant.billing_company_id:
        company = session.get(Company, tenant.billing_company_id)
        if company and company.tenant_id == tenant.id:
            return company
    return session.exec(
        select(Company)
        .where(Company.tenant_id == tenant.id, Company.is_active == True)
        .order_by(Company.name)
    ).first()


def get_tenant_billing_overview(session: Session, tenant_id: UUID) -> dict:
    """Vista unificada de facturación: una suscripción, una empresa principal."""
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        return {}

    # Empresas de la cuenta
    companies = list(
        session.exec(
            select(Company).where(Company.tenant_id == tenant_id).order_by(Company.name)
        ).all()
    )

    # Empresa principal de facturación
    billing_company = resolve_billing_company(session, tenant)

    # Única suscripción del tenant
    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).first()
    if not sub:
        sub = ensure_default_subscription(session, tenant, billing_company)

    # Métodos de pago del tenant (ignoramos company_id legacy)
    methods = list(
        session.exec(
            select(BillingMethod).where(BillingMethod.tenant_id == tenant_id)
        ).all()
    )

    company_rows = []
    for c in companies:
        company_rows.append({
            "company": c,
            "is_billing_company": billing_company is not None and c.id == billing_company.id,
        })

    return {
        "tenant": tenant,
        "billing_company": billing_company,
        "subscription": sub,
        "billing_methods": methods,
        "companies": company_rows,
    }


def get_primary_subscription(
    session: Session, tenant_id: UUID
) -> tuple[Subscription | None, Company | None]:
    """Suscripción de la cuenta + empresa de facturación principal."""
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        return None, None
    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).first()
    company = resolve_billing_company(session, tenant)
    return sub, company


def list_tenant_invoices(
    session: Session, tenant_id: UUID, *, limit: int = 50
) -> list[StripePayment]:
    return list(
        session.exec(
            select(StripePayment)
            .where(StripePayment.tenant_id == tenant_id)
            .order_by(StripePayment.created_at.desc())  # type: ignore[attr-defined]
            .limit(min(limit, 200))
        ).all()
    )


def subscription_summary_for_tenant(
    session: Session, tenant_id: UUID
) -> Subscription | None:
    sub, _company = get_primary_subscription(session, tenant_id)
    return sub


def check_employee_limit(
    session: Session, tenant_id: UUID, adding: int = 1
) -> dict:
    """
    Verifica el límite de empleados activos según la tarifa.
    Retorna {"ok": True} o {"ok": False, "message": str, "current": int, "max": int}.
    No lanza excepciones — el caller decide si bloquear o crear inactivo.
    """
    from app.models.models import Employee
    from app.models.tenant import Company
    from app.models.billing import PricingPlan

    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).first()
    if not sub or sub.status not in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
    ):
        return {"ok": True}  # sin suscripción activa, no limitamos

    plan = None
    max_users = 3  # default conservador
    if sub.pricing_plan_id:
        plan = session.get(PricingPlan, sub.pricing_plan_id)
    if plan and plan.max_active_users:
        max_users = plan.max_active_users

    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tenant_id)
        ).all()
    ]
    if not company_ids:
        return {"ok": True}

    current = session.exec(
        select(Employee).where(
            Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
            Employee.is_active == True,  # noqa: E712
        )
    ).all()
    current_count = len(current)

    if current_count + adding > max_users:
        return {
            "ok": False,
            "message": (
                f"Has alcanzado el límite de {max_users} usuarios activos de tu "
                f"tarifa «{sub.plan_name}». "
                f"Tienes {current_count} usuario(s). "
                f"El empleado se creará inactivo. "
                f"Para activarlo, cambia de tarifa en /app/cuenta."
            ),
            "current": current_count,
            "max": max_users,
        }
    return {"ok": True}
