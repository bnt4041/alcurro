"""Integración Stripe: productos, checkout y webhooks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import stripe
from sqlmodel import Session, select

from app.config import get_settings
from app.models.billing import (
    BillingCycle,
    PricingPlan,
    StripePayment,
    StripePaymentStatus,
    Subscription,
    SubscriptionStatus,
)
from app.models.tenant import Tenant


def stripe_configured() -> bool:
    return bool(get_settings().stripe_secret_key.strip())


def _client() -> None:
    if not stripe_configured():
        raise RuntimeError("Stripe no está configurado")
    stripe.api_key = get_settings().stripe_secret_key


def sync_plan_to_stripe(session: Session, plan: PricingPlan) -> PricingPlan:
    """Crea o actualiza producto y precios en Stripe."""
    if not stripe_configured():
        return plan
    _client()
    if not plan.stripe_product_id:
        product = stripe.Product.create(
            name=plan.name,
            description=plan.description or f"Tarifa {plan.code}",
            metadata={"plan_code": plan.code, "plan_id": str(plan.id)},
        )
        plan.stripe_product_id = product.id
    else:
        stripe.Product.modify(
            plan.stripe_product_id,
            name=plan.name,
            description=plan.description,
        )

    if not plan.stripe_price_monthly_id:
        price = stripe.Price.create(
            product=plan.stripe_product_id,
            unit_amount=plan.monthly_price_cents,
            currency=plan.currency.lower(),
            recurring={"interval": "month"},
            metadata={"plan_code": plan.code, "cycle": "monthly"},
        )
        plan.stripe_price_monthly_id = price.id

    if not plan.stripe_price_annual_id:
        price = stripe.Price.create(
            product=plan.stripe_product_id,
            unit_amount=plan.annual_price_per_month_cents * 12,
            currency=plan.currency.lower(),
            recurring={"interval": "year"},
            metadata={"plan_code": plan.code, "cycle": "annual"},
        )
        plan.stripe_price_annual_id = price.id

    session.add(plan)
    session.flush()
    return plan


def get_stripe_price_id(plan: PricingPlan, cycle: str) -> str | None:
    if cycle == BillingCycle.ANNUAL:
        return plan.stripe_price_annual_id
    return plan.stripe_price_monthly_id


def ensure_stripe_customer(session: Session, tenant: Tenant, email: str) -> str:
    if tenant.stripe_customer_id:
        return tenant.stripe_customer_id
    if not stripe_configured():
        return ""
    _client()
    customer = stripe.Customer.create(
        email=email,
        name=tenant.legal_name or tenant.name,
        metadata={"tenant_id": str(tenant.id), "tenant_slug": tenant.slug},
    )
    tenant.stripe_customer_id = customer.id
    session.add(tenant)
    session.flush()
    return customer.id


def create_checkout_session(
    session: Session,
    tenant: Tenant,
    subscription: Subscription,
    plan: PricingPlan,
    customer_email: str,
    success_url: str,
    cancel_url: str,
) -> str | None:
    if not stripe_configured():
        return None
    sync_plan_to_stripe(session, plan)
    price_id = get_stripe_price_id(plan, subscription.billing_cycle)
    if not price_id:
        return None

    customer_id = ensure_stripe_customer(session, tenant, customer_email)
    _client()
    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "tenant_id": str(tenant.id),
            "subscription_id": str(subscription.id),
            "plan_code": plan.code,
        },
        subscription_data={
            "metadata": {
                "tenant_id": str(tenant.id),
                "subscription_id": str(subscription.id),
            }
        },
    )
    subscription.stripe_checkout_session_id = checkout.id
    session.add(subscription)
    session.flush()
    return checkout.url


def record_payment(
    session: Session,
    *,
    tenant_id: UUID | None,
    subscription_id: UUID | None,
    amount_cents: int,
    currency: str,
    status: StripePaymentStatus,
    description: str | None = None,
    stripe_payment_intent_id: str | None = None,
    stripe_invoice_id: str | None = None,
    stripe_checkout_session_id: str | None = None,
) -> StripePayment:
    existing = None
    if stripe_invoice_id:
        existing = session.exec(
            select(StripePayment).where(
                StripePayment.stripe_invoice_id == stripe_invoice_id
            )
        ).first()
    if existing:
        return existing

    row = StripePayment(
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        description=description,
        stripe_payment_intent_id=stripe_payment_intent_id,
        stripe_invoice_id=stripe_invoice_id,
        stripe_checkout_session_id=stripe_checkout_session_id,
        paid_at=datetime.utcnow() if status == StripePaymentStatus.SUCCEEDED else None,
    )
    session.add(row)
    session.flush()
    return row


def handle_webhook_event(session: Session, event: dict) -> None:
    etype = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        _on_checkout_completed(session, data)
    elif etype == "invoice.paid":
        _on_invoice_paid(session, data)
    elif etype == "invoice.payment_failed":
        _on_invoice_failed(session, data)
    elif etype == "customer.subscription.deleted":
        _on_subscription_deleted(session, data)

    session.commit()


def _tenant_from_meta(session: Session, meta: dict) -> Tenant | None:
    tid = meta.get("tenant_id")
    if not tid:
        return None
    return session.get(Tenant, UUID(tid))


def _sub_from_meta(session: Session, meta: dict) -> Subscription | None:
    sid = meta.get("subscription_id")
    if not sid:
        return None
    return session.get(Subscription, UUID(sid))


def _on_checkout_completed(session: Session, data: dict) -> None:
    meta = data.get("metadata") or {}
    tenant = _tenant_from_meta(session, meta)
    sub = _sub_from_meta(session, meta)
    stripe_sub_id = data.get("subscription")
    if sub:
        sub.status = SubscriptionStatus.ACTIVE
        if stripe_sub_id:
            sub.stripe_subscription_id = stripe_sub_id
        session.add(sub)
    if tenant:
        session.add(tenant)
    amount = int(data.get("amount_total") or 0)
    if amount > 0 and tenant:
        record_payment(
            session,
            tenant_id=tenant.id,
            subscription_id=sub.id if sub else None,
            amount_cents=amount,
            currency=(data.get("currency") or "eur").upper(),
            status=StripePaymentStatus.SUCCEEDED,
            description="Alta y primer pago (Checkout)",
            stripe_checkout_session_id=data.get("id"),
        )


def _on_invoice_paid(session: Session, data: dict) -> None:
    meta = data.get("subscription_details", {}).get("metadata") or {}
    if not meta:
        sub_id = data.get("subscription")
        if sub_id and stripe_configured():
            _client()
            stripe_sub = stripe.Subscription.retrieve(sub_id)
            meta = stripe_sub.get("metadata") or {}
    tenant = _tenant_from_meta(session, meta)
    sub = _sub_from_meta(session, meta)
    if sub:
        sub.status = SubscriptionStatus.ACTIVE
        session.add(sub)
    record_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=sub.id if sub else None,
        amount_cents=int(data.get("amount_paid") or 0),
        currency=(data.get("currency") or "eur").upper(),
        status=StripePaymentStatus.SUCCEEDED,
        description=f"Factura {data.get('number') or data.get('id')}",
        stripe_invoice_id=data.get("id"),
    )


def _on_invoice_failed(session: Session, data: dict) -> None:
    customer_id = data.get("customer")
    tenant = None
    if customer_id:
        tenant = session.exec(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        ).first()
    if tenant:
        sub = session.exec(
            select(Subscription).where(Subscription.tenant_id == tenant.id)
        ).first()
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            session.add(sub)
    record_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=None,
        amount_cents=int(data.get("amount_due") or 0),
        currency=(data.get("currency") or "eur").upper(),
        status=StripePaymentStatus.FAILED,
        description="Pago fallido",
        stripe_invoice_id=data.get("id"),
    )


def _on_subscription_deleted(session: Session, data: dict) -> None:
    stripe_sub_id = data.get("id")
    if not stripe_sub_id:
        return
    sub = session.exec(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    ).first()
    if sub:
        sub.status = SubscriptionStatus.CANCELLED
        session.add(sub)
