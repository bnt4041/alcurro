"""Serialización de facturación para APIs de lectura."""

from uuid import UUID

from sqlmodel import Session, select

from app.models.billing import PricingPlan, StripePayment, Subscription
from app.models.models import Employee
from app.models.tenant import Company
from app.schemas.billing import InvoiceRead, SubscriptionSummaryRead
from app.services.billing_service import (
    get_primary_subscription,
    list_tenant_invoices,
)


def subscription_to_summary(
    sub: Subscription | None, company: Company | None
) -> SubscriptionSummaryRead | None:
    if not sub:
        return None
    return SubscriptionSummaryRead(
        id=sub.id,
        plan_name=sub.plan_name,
        plan_code=sub.plan_code,
        status=sub.status,
        amount_cents=sub.amount_cents,
        currency=sub.currency,
        billing_cycle=sub.billing_cycle,
        company_name=company.name if company else None,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
    )


def tenant_account_billing(session: Session, tenant_id: UUID) -> dict:
    sub, company = get_primary_subscription(session, tenant_id)
    invoices = list_tenant_invoices(session, tenant_id)

    # Contar usuarios activos del tenant
    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tenant_id)
        ).all()
    ]
    active_users = 0
    if company_ids:
        active_users = len(
            session.exec(
                select(Employee).where(
                    Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
                    Employee.is_active == True,  # noqa: E712
                )
            ).all()
        )

    max_users = None
    if sub and sub.pricing_plan_id:
        plan = session.get(PricingPlan, sub.pricing_plan_id)
        if plan:
            max_users = plan.max_active_users

    return {
        "subscription": subscription_to_summary(sub, company),
        "invoices": [
            InvoiceRead(
                id=inv.id,
                amount_cents=inv.amount_cents,
                currency=inv.currency,
                status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
                description=inv.description,
                stripe_invoice_id=inv.stripe_invoice_id,
                paid_at=inv.paid_at,
                created_at=inv.created_at,
            )
            for inv in invoices
        ],
        "active_users": active_users,
        "max_users": max_users,
    }
