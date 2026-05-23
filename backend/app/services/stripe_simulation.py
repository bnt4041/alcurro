"""Cobro y checkout simulados (sin cuenta Stripe real)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.config import get_settings
from app.models.billing import (
    StripePaymentStatus,
    Subscription,
    SubscriptionStatus,
)
from app.models.tenant import GoWAStatus, Tenant
from app.services.gowa_provisioner import provision_gowa
from app.services.stripe_service import record_payment, stripe_configured


SIM_SESSION_PREFIX = "sim_"


def stripe_simulation_enabled() -> bool:
    """Activo si está forzado por env o si no hay Stripe real configurado."""
    settings = get_settings()
    if settings.stripe_simulation_mode:
        return True
    return not stripe_configured()


def use_real_stripe() -> bool:
    return stripe_configured() and not get_settings().stripe_simulation_mode


def create_simulation_checkout_token(session: Session, subscription: Subscription) -> str:
    token = f"{SIM_SESSION_PREFIX}{uuid4().hex}"
    subscription.stripe_checkout_session_id = token
    session.add(subscription)
    session.flush()
    return token


def get_pending_simulation(session: Session, token: str) -> tuple[Tenant, Subscription] | None:
    if not token.startswith(SIM_SESSION_PREFIX):
        return None
    sub = session.exec(
        select(Subscription).where(Subscription.stripe_checkout_session_id == token)
    ).first()
    if not sub:
        return None
    tenant = session.get(Tenant, sub.tenant_id)
    if not tenant:
        return None
    return tenant, sub


def complete_simulated_checkout(
    session: Session,
    token: str,
    *,
    provision_whatsapp: bool = False,
) -> dict:
    pending = get_pending_simulation(session, token)
    if not pending:
        raise ValueError("Sesión de pago simulado no válida o expirada")
    tenant, sub = pending

    if sub.status == SubscriptionStatus.ACTIVE and tenant.gowa_status == GoWAStatus.RUNNING:
        return _build_result(tenant, sub, already_completed=True)

    sim_id = uuid4().hex[:16]
    if not tenant.stripe_customer_id:
        tenant.stripe_customer_id = f"cus_sim_{sim_id}"
    if not sub.stripe_subscription_id:
        sub.stripe_subscription_id = f"sub_sim_{sim_id}"

    sub.status = SubscriptionStatus.ACTIVE
    session.add(sub)
    session.add(tenant)

    record_payment(
        session,
        tenant_id=tenant.id,
        subscription_id=sub.id,
        amount_cents=sub.amount_cents,
        currency=sub.currency,
        status=StripePaymentStatus.SUCCEEDED,
        description="Pago simulado (modo prueba)",
        stripe_payment_intent_id=f"pi_sim_{sim_id}",
        stripe_checkout_session_id=token,
    )

    gowa_error: str | None = None
    if provision_whatsapp:
        try:
            tenant = provision_gowa(session, tenant.id)
            if tenant.gowa_status == GoWAStatus.ERROR:
                gowa_error = tenant.gowa_error
        except Exception as exc:
            gowa_error = str(exc)[:500]

    session.commit()
    session.refresh(tenant)
    session.refresh(sub)

    result = _build_result(tenant, sub, already_completed=False)
    if gowa_error:
        result["gowa_error"] = gowa_error
    return result


def simulate_payment_for_tenant(
    session: Session,
    tenant_id: UUID,
    *,
    provision_whatsapp: bool = False,
) -> dict:
    """Simula cobro + activación para un tenant existente (admin)."""
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Cuenta no encontrada")

    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).first()
    if not sub:
        raise ValueError("La cuenta no tiene suscripción")

    if not sub.stripe_checkout_session_id or not sub.stripe_checkout_session_id.startswith(
        SIM_SESSION_PREFIX
    ):
        token = create_simulation_checkout_token(session, sub)
    else:
        token = sub.stripe_checkout_session_id

    session.commit()
    return complete_simulated_checkout(
        session, token, provision_whatsapp=provision_whatsapp
    )


def _build_result(
    tenant: Tenant,
    sub: Subscription,
    *,
    already_completed: bool,
) -> dict:
    return {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "company_name": tenant.name,
        "subscription_status": sub.status,
        "amount_cents": sub.amount_cents,
        "currency": sub.currency,
        "already_completed": already_completed,
        "gowa_status": tenant.gowa_status,
        "gowa_ui_url": tenant.gowa_ui_url or None,
        "gowa_port": tenant.gowa_port,
        "gowa_container_name": tenant.gowa_container_name,
        "gowa_error": tenant.gowa_error,
        "simulated": True,
    }
