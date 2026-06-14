"""Integración Lemon Squeezy: checkout, webhooks y gestión de suscripciones."""

from __future__ import annotations

import hashlib
import hmac
from datetime import date, datetime
from uuid import UUID

import httpx
from sqlmodel import Session, select

from app.config import get_settings
from app.models.billing import (
    BillingCycle,
    LemonSqueezyPayment,
    LsPaymentStatus,
    PricingPlan,
    Subscription,
    SubscriptionStatus,
)
from app.models.tenant import Tenant

_LS_API = "https://api.lemonsqueezy.com/v1"


def ls_configured() -> bool:
    return bool(get_settings().lemon_squeezy_api_key.strip())


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().lemon_squeezy_api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def get_ls_variant_id(plan: PricingPlan, cycle: str) -> str | None:
    if cycle == BillingCycle.ANNUAL:
        return plan.ls_variant_id_annual
    return plan.ls_variant_id_monthly


def sync_plan_to_ls(session: Session, plan: PricingPlan) -> PricingPlan:
    """Crea o actualiza producto y variantes en Lemon Squeezy."""
    if not ls_configured():
        raise RuntimeError("Lemon Squeezy no está configurado")

    store_id = get_settings().lemon_squeezy_store_id

    # ── 1. Producto ───────────────────────────────────────────────────────────
    if not plan.ls_product_id:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{_LS_API}/products",
                headers=_headers(),
                json={
                    "data": {
                        "type": "products",
                        "attributes": {
                            "name": plan.name,
                            "description": plan.description or f"Plan alcurro — {plan.code}",
                            "status": "published",
                        },
                        "relationships": {
                            "store": {"data": {"type": "stores", "id": str(store_id)}},
                        },
                    }
                },
            )
            resp.raise_for_status()
        plan.ls_product_id = str(resp.json()["data"]["id"])

    # ── 2. Variante mensual ───────────────────────────────────────────────────
    if not plan.ls_variant_id_monthly:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{_LS_API}/variants",
                headers=_headers(),
                json={
                    "data": {
                        "type": "variants",
                        "attributes": {
                            "name": f"{plan.name} — Mensual",
                            "price": plan.monthly_price_cents,
                            "is_subscription": True,
                            "interval": "month",
                            "interval_count": 1,
                            "status": "active",
                        },
                        "relationships": {
                            "product": {
                                "data": {"type": "products", "id": plan.ls_product_id}
                            }
                        },
                    }
                },
            )
            resp.raise_for_status()
        plan.ls_variant_id_monthly = str(resp.json()["data"]["id"])

    # ── 3. Variante anual ─────────────────────────────────────────────────────
    if not plan.ls_variant_id_annual:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{_LS_API}/variants",
                headers=_headers(),
                json={
                    "data": {
                        "type": "variants",
                        "attributes": {
                            "name": f"{plan.name} — Anual",
                            "price": plan.annual_price_cents,
                            "is_subscription": True,
                            "interval": "year",
                            "interval_count": 1,
                            "status": "active",
                        },
                        "relationships": {
                            "product": {
                                "data": {"type": "products", "id": plan.ls_product_id}
                            }
                        },
                    }
                },
            )
            resp.raise_for_status()
        plan.ls_variant_id_annual = str(resp.json()["data"]["id"])

    session.add(plan)
    session.flush()
    return plan


def create_checkout(
    session: Session,
    tenant: Tenant,
    subscription: Subscription,
    variant_id: str,
    customer_email: str,
    success_url: str,
    *,
    custom_price_cents: int | None = None,
) -> str | None:
    """Crea un checkout de Lemon Squeezy y devuelve la URL.

    Si se pasa custom_price_cents se sobreescribe el precio de la variante
    (útil para aplicar descuentos calculados en Alcurro).
    """
    if not ls_configured():
        return None

    store_id = get_settings().lemon_squeezy_store_id
    checkout_attrs: dict = {
        "checkout_data": {
            "email": customer_email,
            "custom": {
                "tenant_id": str(tenant.id),
                "subscription_id": str(subscription.id),
            },
        },
        "product_options": {
            "redirect_url": success_url,
        },
    }

    if custom_price_cents is not None:
        checkout_attrs["custom_price"] = custom_price_cents

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": checkout_attrs,
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(store_id)}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        }
    }

    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{_LS_API}/checkouts", headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()

    checkout_url: str | None = data["data"]["attributes"].get("url")
    return checkout_url


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = get_settings().lemon_squeezy_webhook_secret
    if not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_webhook_event(session: Session, payload: dict) -> None:
    meta = payload.get("meta", {})
    event_name = meta.get("event_name", "")
    data = payload.get("data", {})

    if event_name == "subscription_created":
        _on_subscription_created(session, meta, data)
    elif event_name == "subscription_updated":
        _on_subscription_updated(session, meta, data)
    elif event_name in ("subscription_cancelled", "subscription_expired"):
        _on_subscription_cancelled(session, meta, data)
    elif event_name == "subscription_payment_success":
        _on_subscription_payment_success(session, meta, data)
    elif event_name == "subscription_payment_failed":
        _on_subscription_payment_failed(session, meta, data)
    elif event_name == "subscription_payment_recovered":
        _on_subscription_payment_recovered(session, meta, data)
    elif event_name == "subscription_payment_refunded":
        _on_subscription_payment_refunded(session, meta, data)

    session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve(session: Session, meta: dict) -> tuple[Tenant | None, Subscription | None]:
    custom = meta.get("custom_data") or {}
    tenant: Tenant | None = None
    sub: Subscription | None = None
    tid = custom.get("tenant_id")
    if tid:
        try:
            tenant = session.get(Tenant, UUID(tid))
        except Exception:
            pass
    sid = custom.get("subscription_id")
    if sid:
        try:
            sub = session.get(Subscription, UUID(sid))
        except Exception:
            pass
    return tenant, sub


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


# ── Event handlers ────────────────────────────────────────────────────────────

def _on_subscription_created(session: Session, meta: dict, data: dict) -> None:
    tenant, sub = _resolve(session, meta)
    attrs = data.get("attributes", {})
    ls_sub_id = str(data.get("id", ""))

    if sub:
        sub.status = SubscriptionStatus.ACTIVE
        sub.ls_subscription_id = ls_sub_id
        period_end = _parse_date(attrs.get("renews_at"))
        if period_end:
            sub.current_period_end = period_end
            sub.current_period_start = date.today()
        session.add(sub)

    portal_url = (attrs.get("urls") or {}).get("customer_portal")
    if tenant:
        if portal_url:
            tenant.ls_customer_portal_url = portal_url
        ls_cid = attrs.get("customer_id")
        if ls_cid:
            tenant.ls_customer_id = str(ls_cid)
        session.add(tenant)


def _on_subscription_updated(session: Session, meta: dict, data: dict) -> None:
    tenant, sub = _resolve(session, meta)
    attrs = data.get("attributes", {})

    portal_url = (attrs.get("urls") or {}).get("customer_portal")
    if tenant and portal_url:
        tenant.ls_customer_portal_url = portal_url
        session.add(tenant)

    if sub:
        ls_status = attrs.get("status", "")
        if ls_status in ("active", "on_trial"):
            sub.status = SubscriptionStatus.ACTIVE
        elif ls_status == "past_due":
            sub.status = SubscriptionStatus.PAST_DUE
        elif ls_status in ("cancelled", "expired"):
            sub.status = SubscriptionStatus.CANCELLED
        period_end = _parse_date(attrs.get("renews_at"))
        if period_end:
            sub.current_period_end = period_end
        session.add(sub)


def _on_subscription_cancelled(session: Session, meta: dict, data: dict) -> None:
    _, sub = _resolve(session, meta)
    if sub:
        sub.status = SubscriptionStatus.CANCELLED
        session.add(sub)


def _on_subscription_payment_success(session: Session, meta: dict, data: dict) -> None:
    tenant, sub = _resolve(session, meta)
    attrs = data.get("attributes", {})

    if sub:
        sub.payment_failure_count = 0
        sub.status = SubscriptionStatus.ACTIVE
        session.add(sub)

    amount_cents = int(attrs.get("total", 0))
    currency = (attrs.get("currency") or "EUR").upper()
    ls_invoice_id = str(data.get("id", ""))
    receipt_url = (attrs.get("urls") or {}).get("invoice_url") or ""

    payment = _record_ls_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=sub.id if sub else None,
        amount_cents=amount_cents,
        currency=currency,
        status=LsPaymentStatus.PAID,
        ls_invoice_id=ls_invoice_id,
        description="Suscripción Lemon Squeezy",
        receipt_url=receipt_url,
    )

    if tenant:
        _notify_payment(session, tenant, payment)

    if payment.amount_cents > 0:
        _auto_generate_invoice(session, payment)


def _on_subscription_payment_failed(session: Session, meta: dict, data: dict) -> None:
    tenant, sub = _resolve(session, meta)
    attrs = data.get("attributes", {})

    amount_cents = int(attrs.get("total", 0))
    currency = (attrs.get("currency") or "EUR").upper()
    ls_invoice_id = str(data.get("id", ""))

    _record_ls_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=sub.id if sub else None,
        amount_cents=amount_cents,
        currency=currency,
        status=LsPaymentStatus.FAILED,
        ls_invoice_id=ls_invoice_id,
        description="Pago fallido",
    )

    failure_count = 1
    if sub:
        sub.payment_failure_count = (sub.payment_failure_count or 0) + 1
        sub.last_payment_failure_at = datetime.utcnow()
        failure_count = sub.payment_failure_count

        if failure_count >= 3:
            sub.status = SubscriptionStatus.CANCELLED
            if tenant:
                tenant.is_active = False
                session.add(tenant)
        else:
            sub.status = SubscriptionStatus.PAST_DUE

        session.add(sub)

    if tenant:
        _notify_payment_failed(
            session,
            tenant,
            attempt=failure_count,
            amount_cents=amount_cents,
            currency=currency,
        )


def _on_subscription_payment_refunded(session: Session, meta: dict, data: dict) -> None:
    from app.models.invoice import Invoice
    from app.services.invoice_service import create_credit_note

    attrs = data.get("attributes", {})
    ls_invoice_id = str(data.get("id", ""))

    # Buscar el pago original por ls_invoice_id
    payment = session.exec(
        select(LemonSqueezyPayment).where(LemonSqueezyPayment.ls_invoice_id == ls_invoice_id)
    ).first()

    if not payment:
        tenant, sub = _resolve(session, meta)
        amount_cents = int(attrs.get("total", 0))
        currency = (attrs.get("currency") or "EUR").upper()
        payment = _record_ls_payment(
            session,
            tenant_id=tenant.id if tenant else None,
            subscription_id=sub.id if sub else None,
            amount_cents=amount_cents,
            currency=currency,
            status=LsPaymentStatus.REFUNDED,
            ls_invoice_id=ls_invoice_id,
            description="Reembolso suscripción",
        )
    else:
        payment.status = LsPaymentStatus.REFUNDED
        session.add(payment)
        session.flush()

    # Generar factura de abono si existe factura original
    original_invoice = session.exec(
        select(Invoice).where(Invoice.ls_payment_id == payment.id)
    ).first()
    if original_invoice:
        existing_cn = session.exec(
            select(Invoice).where(Invoice.credit_note_for_id == original_invoice.id)
        ).first()
        if not existing_cn:
            try:
                create_credit_note(session, original_invoice.id, ls_payment_id=payment.id)
            except Exception:
                pass


def _on_subscription_payment_recovered(session: Session, meta: dict, data: dict) -> None:
    tenant, sub = _resolve(session, meta)
    attrs = data.get("attributes", {})

    if sub:
        sub.payment_failure_count = 0
        sub.status = SubscriptionStatus.ACTIVE
        session.add(sub)

    if tenant and not tenant.is_active:
        tenant.is_active = True
        session.add(tenant)

    amount_cents = int(attrs.get("total", 0))
    currency = (attrs.get("currency") or "EUR").upper()
    ls_invoice_id = str(data.get("id", ""))
    receipt_url = (attrs.get("urls") or {}).get("invoice_url") or ""

    payment = _record_ls_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=sub.id if sub else None,
        amount_cents=amount_cents,
        currency=currency,
        status=LsPaymentStatus.PAID,
        ls_invoice_id=ls_invoice_id,
        description="Recobro suscripción",
        receipt_url=receipt_url,
    )

    if tenant:
        _notify_payment(session, tenant, payment)

    if payment.amount_cents > 0:
        _auto_generate_invoice(session, payment)


# ── Payment recording ─────────────────────────────────────────────────────────

def _record_ls_payment(
    session: Session,
    *,
    tenant_id: UUID | None,
    subscription_id: UUID | None,
    amount_cents: int,
    currency: str,
    status: LsPaymentStatus,
    ls_invoice_id: str | None = None,
    ls_subscription_id: str | None = None,
    ls_order_id: str | None = None,
    description: str | None = None,
    receipt_url: str | None = None,
) -> LemonSqueezyPayment:
    if ls_invoice_id:
        existing = session.exec(
            select(LemonSqueezyPayment).where(
                LemonSqueezyPayment.ls_invoice_id == ls_invoice_id
            )
        ).first()
        if existing:
            return existing

    row = LemonSqueezyPayment(
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        ls_order_id=ls_order_id,
        ls_subscription_id=ls_subscription_id,
        ls_invoice_id=ls_invoice_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        description=description,
        receipt_url=receipt_url,
        paid_at=datetime.utcnow() if status == LsPaymentStatus.PAID else None,
    )
    session.add(row)
    session.flush()
    return row


def _auto_generate_invoice(session: Session, payment: LemonSqueezyPayment) -> None:
    try:
        from app.services.invoice_service import generate_invoice_for_ls_payment
        generate_invoice_for_ls_payment(session, payment)
    except Exception:
        pass


# ── Notifications ─────────────────────────────────────────────────────────────

def _notify_payment(
    session: Session,
    tenant: Tenant,
    payment: LemonSqueezyPayment,
) -> None:
    from app.services.mail_service import MailService
    from app.services.gowa_service import GoWAService

    settings = get_settings()
    amount_str = f"{payment.amount_cents / 100:.2f} {payment.currency}"
    receipt_url = payment.receipt_url or ""
    portal = tenant.ls_customer_portal_url or f"{settings.public_app_url.rstrip('/')}/cuenta"

    email = tenant.billing_email
    if email:
        subject = f"Pago confirmado — alcurro ({amount_str})"
        body = (
            f"Hola {tenant.legal_name or tenant.name},\n\n"
            f"Te confirmamos que hemos recibido tu pago de {amount_str}.\n\n"
        )
        if receipt_url:
            body += f"Descarga tu factura aquí:\n{receipt_url}\n\n"
        body += (
            f"Gestiona tu suscripción desde tu portal de cliente:\n{portal}\n\n"
            f"Gracias por confiar en alcurro.\n"
        )
        try:
            MailService(session).send(
                email, subject, body, event_type="invoice", tenant_id=tenant.id
            )
        except Exception:
            pass

    phone = tenant.billing_phone
    if phone and receipt_url:
        msg = (
            f"✅ *Pago recibido — alcurro*\n\n"
            f"Hemos recibido tu pago de *{amount_str}*.\n"
            f"📄 Factura: {receipt_url}"
        )
        try:
            GoWAService(session).send_text_sync(phone, msg)
        except Exception:
            pass


def update_ls_customer_name(tenant: "Tenant", new_name: str) -> None:
    """Actualiza el nombre del cliente en Lemon Squeezy cuando cambia la razón social."""
    if not ls_configured() or not tenant.ls_customer_id:
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.patch(
                f"{_LS_API}/customers/{tenant.ls_customer_id}",
                headers=_headers(),
                json={
                    "data": {
                        "type": "customers",
                        "id": str(tenant.ls_customer_id),
                        "attributes": {"name": new_name},
                    }
                },
            )
    except Exception:
        pass


def update_ls_subscription_variant(
    session: Session,
    tenant: "Tenant",
    sub: Subscription,
    new_plan: PricingPlan,
    new_cycle: str,
) -> None:
    """Cambia la variante de la suscripción en Lemon Squeezy cuando cambia el plan o ciclo."""
    if not ls_configured() or not sub.ls_subscription_id:
        return
    variant_id = get_ls_variant_id(new_plan, new_cycle)
    if not variant_id:
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.patch(
                f"{_LS_API}/subscriptions/{sub.ls_subscription_id}",
                headers=_headers(),
                json={
                    "data": {
                        "type": "subscriptions",
                        "id": str(sub.ls_subscription_id),
                        "attributes": {"variant_id": int(variant_id)},
                    }
                },
            )
    except Exception:
        pass


def issue_refund_credit_note(
    session: Session, payment_id: UUID
) -> tuple["LemonSqueezyPayment", "Invoice"]:
    """Marca un pago como reembolsado y genera la factura de abono correspondiente.

    El reembolso monetario real debe hacerse desde el panel de Lemon Squeezy.
    Esta función solo crea el registro contable en Alcurro.
    """
    from app.models.invoice import Invoice
    from app.services.invoice_service import create_credit_note

    payment = session.get(LemonSqueezyPayment, payment_id)
    if not payment:
        raise ValueError("Pago no encontrado")
    if payment.status == LsPaymentStatus.REFUNDED:
        raise ValueError("Este pago ya está marcado como reembolsado")
    if payment.status != LsPaymentStatus.PAID:
        raise ValueError("Solo se pueden reembolsar pagos completados (estado: paid)")

    original_invoice = session.exec(
        select(Invoice).where(Invoice.ls_payment_id == payment.id)
    ).first()
    if not original_invoice:
        raise ValueError(
            "No existe factura asociada a este pago. "
            "Genera la factura primero desde el panel de Facturas."
        )

    payment.status = LsPaymentStatus.REFUNDED
    session.add(payment)
    session.flush()

    credit_note = create_credit_note(session, original_invoice.id, ls_payment_id=payment.id)
    return payment, credit_note


def _notify_payment_failed(
    session: Session,
    tenant: Tenant,
    *,
    attempt: int,
    amount_cents: int,
    currency: str,
) -> None:
    from app.services.mail_service import MailService
    from app.services.gowa_service import GoWAService

    settings = get_settings()
    amount_str = f"{amount_cents / 100:.2f} {currency}"
    portal = tenant.ls_customer_portal_url or f"{settings.public_app_url.rstrip('/')}/cuenta"

    if attempt >= 3:
        subject = "Cuenta suspendida por impago — alcurro"
        body = (
            f"Hola {tenant.legal_name or tenant.name},\n\n"
            f"Tras {attempt} intentos fallidos de cobro de {amount_str}, "
            f"tu cuenta en alcurro ha sido suspendida.\n\n"
            f"Para reactivarla, actualiza tu método de pago en:\n{portal}\n\n"
            f"Si necesitas ayuda, contáctanos.\n"
        )
        wa_msg = (
            f"⛔ *Cuenta suspendida — alcurro*\n\n"
            f"Tras {attempt} cobros fallidos de *{amount_str}*, "
            f"tu cuenta ha sido suspendida.\n\n"
            f"Actualiza tu método de pago:\n{portal}"
        )
    else:
        remaining = 3 - attempt
        subject = f"Pago fallido (intento {attempt}/3) — alcurro"
        body = (
            f"Hola {tenant.legal_name or tenant.name},\n\n"
            f"No hemos podido cobrar {amount_str} (intento {attempt} de 3). "
            f"Quedan {remaining} intentos antes de la suspensión de la cuenta.\n\n"
            f"Actualiza tu método de pago en:\n{portal}\n\n"
            f"Si ya lo has actualizado, el próximo intento se realizará automáticamente.\n"
        )
        wa_msg = (
            f"⚠️ *Pago fallido — alcurro*\n\n"
            f"No pudimos cobrar *{amount_str}* (intento {attempt}/3). "
            f"Quedan {remaining} intentos.\n"
            f"Actualiza tu método de pago:\n{portal}"
        )

    email = tenant.billing_email
    if email:
        try:
            MailService(session).send(
                email, subject, body, event_type="payment_failed", tenant_id=tenant.id
            )
        except Exception:
            pass

    phone = tenant.billing_phone
    if phone:
        try:
            GoWAService(session).send_text_sync(phone, wa_msg)
        except Exception:
            pass
