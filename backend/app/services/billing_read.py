"""Serialización de facturación para APIs de lectura."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.billing import PricingPlan, Subscription
from app.models.invoice import Invoice, InvoiceStatus
from app.models.models import Employee
from app.models.tenant import Company, Tenant
from app.schemas.billing import InvoiceRead, SubscriptionSummaryRead
from app.services.billing_service import (
    get_primary_subscription,
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


_INV_STATUS_MAP = {
    InvoiceStatus.PAID: "succeeded",
    InvoiceStatus.SENT: "pending",
    InvoiceStatus.DRAFT: "pending",
    InvoiceStatus.CANCELLED: "cancelled",
    InvoiceStatus.CREDIT_NOTE: "refunded",
}


def _invoice_to_read(inv: Invoice) -> InvoiceRead:
    status = _INV_STATUS_MAP.get(inv.status, str(inv.status))
    return InvoiceRead(
        id=inv.id,
        amount_cents=inv.total_cents,
        currency=inv.currency,
        status=status,
        description=inv.concept,
        stripe_invoice_id=None,
        invoice_number=inv.number,
        invoice_pdf_url=f"/api/tenants/current/invoices/{inv.id}/pdf",
        invoice_url=None,
        paid_at=datetime.combine(inv.issue_date, datetime.min.time()) if inv.issue_date else None,
        created_at=inv.created_at,
    )


def tenant_account_billing(session: Session, tenant_id: UUID) -> dict:
    sub, company = get_primary_subscription(session, tenant_id)
    tenant = session.get(Tenant, tenant_id)

    invoices = list(
        session.exec(
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())  # type: ignore[attr-defined]
            .limit(200)
        ).all()
    )

    all_invoices: list[InvoiceRead] = [_invoice_to_read(inv) for inv in invoices]

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
        "invoices": all_invoices,
        "active_users": active_users,
        "max_users": max_users,
        "customer_portal_url": tenant.ls_customer_portal_url if tenant else None,
    }
