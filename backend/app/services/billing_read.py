"""Serialización de facturación para APIs de lectura."""

from uuid import UUID

from sqlmodel import Session, select

from app.models.billing import LemonSqueezyPayment, LsPaymentStatus, PricingPlan, StripePayment, Subscription
from app.models.models import Employee
from app.models.tenant import Company, Tenant
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


def _stripe_to_invoice_read(inv: StripePayment) -> InvoiceRead:
    return InvoiceRead(
        id=inv.id,
        amount_cents=inv.amount_cents,
        currency=inv.currency,
        status=inv.status.value if hasattr(inv.status, "value") else str(inv.status),
        description=inv.description,
        stripe_invoice_id=inv.stripe_invoice_id,
        invoice_number=inv.invoice_number,
        invoice_pdf_url=inv.invoice_pdf_url,
        invoice_url=inv.invoice_url,
        paid_at=inv.paid_at,
        created_at=inv.created_at,
    )


def _ls_to_invoice_read(inv: LemonSqueezyPayment) -> InvoiceRead:
    # Mapear estado LS al vocabulario de la UI (succeeded/failed/pending)
    status_map = {
        LsPaymentStatus.PAID: "succeeded",
        LsPaymentStatus.FAILED: "failed",
        LsPaymentStatus.PENDING: "pending",
        LsPaymentStatus.REFUNDED: "refunded",
    }
    status = status_map.get(inv.status, str(inv.status))
    return InvoiceRead(
        id=inv.id,
        amount_cents=inv.amount_cents,
        currency=inv.currency,
        status=status,
        description=inv.description,
        stripe_invoice_id=inv.ls_invoice_id,  # reutilizar campo como ref externa
        invoice_number=inv.invoice_number,
        invoice_pdf_url=inv.receipt_url,
        invoice_url=inv.receipt_url,
        paid_at=inv.paid_at,
        created_at=inv.created_at,
    )


def tenant_account_billing(session: Session, tenant_id: UUID) -> dict:
    sub, company = get_primary_subscription(session, tenant_id)
    tenant = session.get(Tenant, tenant_id)

    stripe_invoices = list_tenant_invoices(session, tenant_id)
    ls_payments = list(
        session.exec(
            select(LemonSqueezyPayment)
            .where(LemonSqueezyPayment.tenant_id == tenant_id)
            .order_by(LemonSqueezyPayment.created_at.desc())  # type: ignore[attr-defined]
            .limit(200)
        ).all()
    )

    all_invoices: list[InvoiceRead] = [
        _stripe_to_invoice_read(inv) for inv in stripe_invoices
    ] + [
        _ls_to_invoice_read(inv) for inv in ls_payments
    ]
    all_invoices.sort(key=lambda x: x.created_at, reverse=True)

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
