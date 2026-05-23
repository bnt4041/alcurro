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
    session: Session, tenant: Tenant, company: Company
) -> Subscription:
    row = session.exec(
        select(Subscription).where(Subscription.company_id == company.id)
    ).first()
    if row:
        return row
    plan = get_default_plan(session)
    sub = Subscription(
        tenant_id=tenant.id,
        company_id=company.id,
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


def get_tenant_billing_overview(session: Session, tenant_id: UUID) -> dict:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        return {}

    companies = list(
        session.exec(
            select(Company).where(Company.tenant_id == tenant_id).order_by(Company.name)
        ).all()
    )
    methods = list(
        session.exec(
            select(BillingMethod).where(BillingMethod.tenant_id == tenant_id)
        ).all()
    )
    subscriptions = list(
        session.exec(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
        ).all()
    )

    subs_by_company = {s.company_id: s for s in subscriptions}
    methods_by_company: dict[UUID | None, list[BillingMethod]] = {}
    for m in methods:
        methods_by_company.setdefault(m.company_id, []).append(m)

    company_rows = []
    for c in companies:
        sub = subs_by_company.get(c.id)
        if not sub:
            sub = ensure_default_subscription(session, tenant, c)
        company_rows.append(
            {
                "company": c,
                "subscription": sub,
                "billing_methods": methods_by_company.get(c.id, [])
                + methods_by_company.get(None, []),
            }
        )

    return {
        "tenant": tenant,
        "account_methods": methods_by_company.get(None, []),
        "companies": company_rows,
    }


def get_primary_subscription(
    session: Session, tenant_id: UUID
) -> tuple[Subscription | None, Company | None]:
    """Suscripción de referencia (primera empresa activa de la cuenta)."""
    overview = get_tenant_billing_overview(session, tenant_id)
    companies = overview.get("companies") or []
    if not companies:
        return None, None
    row = companies[0]
    return row.get("subscription"), row.get("company")


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
