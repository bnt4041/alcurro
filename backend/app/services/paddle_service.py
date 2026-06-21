"""Integración Paddle (Billing API v2): checkout overlay, webhooks y suscripciones.

Reemplaza la antigua integración de Lemon Squeezy. El checkout se hace en el
frontend con Paddle.js (overlay); aquí solo damos de alta productos/precios,
gestionamos suscripciones por API y procesamos los webhooks.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import date, datetime
from uuid import UUID

import httpx
from sqlmodel import Session, or_, select

from app.config import get_settings
from app.models.billing import (
    BillingCycle,
    PaddlePayment,
    PaddlePaymentStatus,
    PricingPlan,
    Subscription,
    SubscriptionStatus,
)
from app.models.tenant import Tenant

_log = logging.getLogger(__name__)


def _api() -> str:
    return get_settings().paddle_api_base


def paddle_configured() -> bool:
    return bool(get_settings().paddle_api_key.strip())


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().paddle_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_paddle_price_id(plan: PricingPlan, cycle: str) -> str | None:
    if cycle == BillingCycle.ANNUAL:
        return plan.paddle_price_id_annual
    return plan.paddle_price_id_monthly


# ── Alta de productos / precios ─────────────────────────────────────────────────

def sync_plan_to_paddle(session: Session, plan: PricingPlan) -> PricingPlan:
    """Crea producto y precios (mensual/anual) en Paddle. Idempotente."""
    if not paddle_configured():
        raise RuntimeError("Paddle no está configurado")

    # ── 1. Producto ───────────────────────────────────────────────────────────
    if not plan.paddle_product_id:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{_api()}/products",
                headers=_headers(),
                json={
                    "name": plan.name,
                    "description": plan.description or f"Plan alcurro — {plan.code}",
                    "tax_category": "standard",
                },
            )
            resp.raise_for_status()
        plan.paddle_product_id = str(resp.json()["data"]["id"])

    # ── 2. Precio mensual ─────────────────────────────────────────────────────
    if not plan.paddle_price_id_monthly:
        plan.paddle_price_id_monthly = _create_price(
            plan.paddle_product_id,
            description=f"{plan.name} — Mensual",
            amount_cents=plan.monthly_price_cents,
            currency=plan.currency,
            interval="month",
        )

    # ── 3. Precio anual ───────────────────────────────────────────────────────
    if not plan.paddle_price_id_annual:
        plan.paddle_price_id_annual = _create_price(
            plan.paddle_product_id,
            description=f"{plan.name} — Anual",
            amount_cents=plan.annual_price_cents,
            currency=plan.currency,
            interval="year",
        )

    session.add(plan)
    session.flush()
    return plan


def _create_price(
    product_id: str, *, description: str, amount_cents: int, currency: str, interval: str
) -> str:
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{_api()}/prices",
            headers=_headers(),
            json={
                "description": description,
                "product_id": product_id,
                "unit_price": {"amount": str(amount_cents), "currency_code": currency},
                "billing_cycle": {"interval": interval, "frequency": 1},
                "quantity": {"minimum": 1, "maximum": 1},
            },
        )
        resp.raise_for_status()
    return str(resp.json()["data"]["id"])


# ── Webhooks ────────────────────────────────────────────────────────────────────

def verify_webhook_signature(body: bytes, signature_header: str) -> bool:
    """Verifica la cabecera Paddle-Signature (formato `ts=...;h1=...`)."""
    secret = get_settings().paddle_webhook_secret
    if not secret or not signature_header:
        return False
    ts = ""
    h1 = ""
    for part in signature_header.split(";"):
        if part.startswith("ts="):
            ts = part[3:]
        elif part.startswith("h1="):
            h1 = part[3:]
    if not ts or not h1:
        return False
    signed_payload = f"{ts}:".encode() + body
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, h1)


def handle_webhook_event(session: Session, payload: dict) -> None:
    event_type = payload.get("event_type", "")
    data = payload.get("data", {})

    if event_type == "subscription.created":
        _on_subscription_created(session, data)
    elif event_type == "subscription.updated":
        _on_subscription_updated(session, data)
    elif event_type in ("subscription.canceled", "subscription.paused"):
        _on_subscription_cancelled(session, data)
    elif event_type == "transaction.completed":
        _on_transaction_completed(session, data)
    elif event_type == "transaction.payment_failed":
        _on_transaction_payment_failed(session, data)
    elif event_type in ("adjustment.created", "adjustment.updated"):
        _on_adjustment(session, data)

    session.commit()


# ── Helpers de resolución ───────────────────────────────────────────────────────

def _resolve(
    session: Session, data: dict, *, paddle_sub_id: str | None = None
) -> tuple[Tenant | None, Subscription | None]:
    """Resuelve tenant y suscripción a partir del payload de Paddle.

    Estrategia (en orden): custom_data.tenant_id / subscription_id →
    paddle_sub_id (ID de suscripción de Paddle) → custom_data.pending_signup_id →
    derivar tenant de la suscripción. Necesario porque en altas vía PendingSignup
    el custom_data solo contiene pending_signup_id (no existían tenant/sub al pagar).
    """
    from app.models.billing import PendingSignup

    custom = data.get("custom_data") or {}
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

    # Fallback: por ID de suscripción de Paddle (renovaciones y primer cobro)
    if sub is None and paddle_sub_id:
        sub = session.exec(
            select(Subscription).where(Subscription.paddle_subscription_id == paddle_sub_id)
        ).first()

    # Fallback: por pending_signup_id → tenant creado
    if tenant is None:
        pending_id = custom.get("pending_signup_id")
        if pending_id:
            try:
                pending = session.get(PendingSignup, UUID(pending_id))
            except Exception:
                pending = None
            if pending and pending.tenant_id:
                tenant = session.get(Tenant, pending.tenant_id)

    # Derivar tenant de la suscripción si aún no lo tenemos
    if tenant is None and sub is not None:
        tenant = session.get(Tenant, sub.tenant_id)

    return tenant, sub


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _first_price_id(data: dict) -> str:
    items = data.get("items") or []
    if items:
        price = items[0].get("price") or {}
        return str(price.get("id", ""))
    return ""


def _period_end(data: dict) -> date | None:
    period = data.get("current_billing_period") or {}
    return _parse_date(period.get("ends_at")) or _parse_date(data.get("next_billed_at"))


# ── Event handlers: suscripción ──────────────────────────────────────────────────

def _on_subscription_created(session: Session, data: dict) -> None:
    paddle_sub_id = str(data.get("id", ""))
    custom = data.get("custom_data") or {}
    customer_id = data.get("customer_id")

    # ── PendingSignup flow ────────────────────────────────────────────────────
    pending_id_raw = custom.get("pending_signup_id")
    if pending_id_raw:
        from app.models.billing import PendingSignup, PendingSignupStatus
        from app.schemas.public import PublicSignupRequest
        from app.services.signup_service import register_tenant

        try:
            pending = session.get(PendingSignup, UUID(pending_id_raw))
        except Exception:
            pending = None

        if pending and pending.status == PendingSignupStatus.PENDING:
            pending.paddle_subscription_id = paddle_sub_id
            try:
                signup_data = PublicSignupRequest.model_validate_json(pending.data_json)
                resp = register_tenant(session, signup_data)
                pending.tenant_id = resp.tenant_id
                pending.status = PendingSignupStatus.ACTIVE
                session.add(pending)

                if resp.tenant_id:
                    sub = session.exec(
                        select(Subscription).where(Subscription.tenant_id == resp.tenant_id)
                    ).first()
                    if sub:
                        sub.paddle_subscription_id = paddle_sub_id
                        sub.status = SubscriptionStatus.ACTIVE
                        period_end = _period_end(data)
                        if period_end:
                            sub.current_period_end = period_end
                            sub.current_period_start = date.today()
                        session.add(sub)

                    tenant_obj = session.get(Tenant, resp.tenant_id)
                    if tenant_obj and customer_id:
                        tenant_obj.paddle_customer_id = str(customer_id)
                        tenant_obj.paddle_customer_portal_url = create_customer_portal_url(
                            str(customer_id)
                        )
                        session.add(tenant_obj)

            except Exception as exc:
                _log.error(
                    "Error creando tenant desde PendingSignup %s: %s",
                    pending_id_raw, exc, exc_info=True,
                )
                pending.status = PendingSignupStatus.FAILED
                pending.error_message = str(exc)[:500]
                session.add(pending)
        return

    # ── Flujo normal (tenant ya existe) ───────────────────────────────────────
    tenant, sub = _resolve(session, data)

    if sub:
        sub.status = SubscriptionStatus.ACTIVE
        sub.paddle_subscription_id = paddle_sub_id
        period_end = _period_end(data)
        if period_end:
            sub.current_period_end = period_end
            sub.current_period_start = date.today()
        session.add(sub)

    if tenant and customer_id:
        tenant.paddle_customer_id = str(customer_id)
        tenant.paddle_customer_portal_url = create_customer_portal_url(str(customer_id))
        session.add(tenant)


def _on_subscription_updated(session: Session, data: dict) -> None:
    from app.services.pricing_service import calculate_subscription_amount, get_active_discount

    tenant, sub = _resolve(session, data, paddle_sub_id=str(data.get("id") or "") or None)
    if not sub:
        return

    status = data.get("status", "")
    if status in ("active", "trialing"):
        sub.status = SubscriptionStatus.ACTIVE
    elif status == "past_due":
        sub.status = SubscriptionStatus.PAST_DUE
    elif status in ("canceled", "paused"):
        sub.status = SubscriptionStatus.CANCELLED

    period_end = _period_end(data)
    if period_end:
        sub.current_period_end = period_end

    # Aplicar cambio de plan si Paddle cambió el precio
    new_price_id = _first_price_id(data)
    if new_price_id:
        plan = session.exec(
            select(PricingPlan).where(
                or_(
                    PricingPlan.paddle_price_id_monthly == new_price_id,
                    PricingPlan.paddle_price_id_annual == new_price_id,
                )
            )
        ).first()
        if plan:
            new_cycle = (
                BillingCycle.ANNUAL
                if plan.paddle_price_id_annual == new_price_id
                else BillingCycle.MONTHLY
            )
            discount = (
                get_active_discount(session, sub.discount_id, plan.id)
                if sub.discount_id
                else None
            )
            sub.pricing_plan_id = plan.id
            sub.plan_code = plan.code
            sub.plan_name = plan.name
            sub.billing_cycle = new_cycle
            sub.amount_cents = calculate_subscription_amount(plan, new_cycle, discount)
            sub.currency = plan.currency
            sub.pending_plan_id = None
            sub.pending_billing_cycle = None

    session.add(sub)


def _on_subscription_cancelled(session: Session, data: dict) -> None:
    _, sub = _resolve(session, data, paddle_sub_id=str(data.get("id") or "") or None)
    if sub:
        sub.status = SubscriptionStatus.CANCELLED
        session.add(sub)


# ── Event handlers: transacciones (cobros) ──────────────────────────────────────

def _on_transaction_completed(session: Session, data: dict) -> None:
    tenant, sub = _resolve(session, data, paddle_sub_id=str(data.get("subscription_id") or "") or None)

    if sub:
        sub.payment_failure_count = 0
        sub.status = SubscriptionStatus.ACTIVE
        session.add(sub)

    txn_id = str(data.get("id", ""))
    amount_cents, currency = _transaction_total(data)
    receipt_url = get_transaction_invoice_url(txn_id) or ""

    payment = _record_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=sub.id if sub else None,
        amount_cents=amount_cents,
        currency=currency,
        status=PaddlePaymentStatus.PAID,
        paddle_transaction_id=txn_id,
        paddle_subscription_id=str(data.get("subscription_id") or "") or None,
        description="Suscripción Paddle",
        receipt_url=receipt_url,
    )

    if tenant:
        _notify_payment(session, tenant, payment)

    if payment.amount_cents > 0:
        _auto_generate_invoice(session, payment)


def _on_transaction_payment_failed(session: Session, data: dict) -> None:
    tenant, sub = _resolve(session, data, paddle_sub_id=str(data.get("subscription_id") or "") or None)
    amount_cents, currency = _transaction_total(data)
    txn_id = str(data.get("id", ""))

    _record_payment(
        session,
        tenant_id=tenant.id if tenant else None,
        subscription_id=sub.id if sub else None,
        amount_cents=amount_cents,
        currency=currency,
        status=PaddlePaymentStatus.FAILED,
        paddle_transaction_id=txn_id,
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
            session, tenant, attempt=failure_count, amount_cents=amount_cents, currency=currency
        )


def _on_adjustment(session: Session, data: dict) -> None:
    """Procesa reembolsos (adjustment action=refund) aprobados."""
    from app.models.invoice import Invoice
    from app.services.invoice_service import create_credit_note

    if data.get("action") != "refund":
        return
    if data.get("status") not in ("approved", None):
        return

    txn_id = str(data.get("transaction_id", ""))
    payment = session.exec(
        select(PaddlePayment).where(PaddlePayment.paddle_transaction_id == txn_id)
    ).first()

    if not payment:
        return

    if payment.status != PaddlePaymentStatus.REFUNDED:
        payment.status = PaddlePaymentStatus.REFUNDED
        session.add(payment)
        session.flush()

    original_invoice = session.exec(
        select(Invoice).where(Invoice.paddle_payment_id == payment.id)
    ).first()
    if original_invoice:
        existing_cn = session.exec(
            select(Invoice).where(Invoice.credit_note_for_id == original_invoice.id)
        ).first()
        if not existing_cn:
            try:
                create_credit_note(session, original_invoice.id, paddle_payment_id=payment.id)
            except Exception:
                pass


def _transaction_total(data: dict) -> tuple[int, str]:
    details = data.get("details") or {}
    totals = details.get("totals") or {}
    amount = totals.get("grand_total") or data.get("grand_total") or 0
    try:
        amount_cents = int(amount)
    except (TypeError, ValueError):
        amount_cents = 0
    currency = (data.get("currency_code") or "EUR").upper()
    return amount_cents, currency


# ── Registro de pagos ─────────────────────────────────────────────────────────

def _record_payment(
    session: Session,
    *,
    tenant_id: UUID | None,
    subscription_id: UUID | None,
    amount_cents: int,
    currency: str,
    status: PaddlePaymentStatus,
    paddle_transaction_id: str | None = None,
    paddle_subscription_id: str | None = None,
    paddle_invoice_id: str | None = None,
    description: str | None = None,
    receipt_url: str | None = None,
) -> PaddlePayment:
    if paddle_transaction_id:
        existing = session.exec(
            select(PaddlePayment).where(
                PaddlePayment.paddle_transaction_id == paddle_transaction_id
            )
        ).first()
        if existing:
            return existing

    row = PaddlePayment(
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        paddle_invoice_id=paddle_invoice_id,
        paddle_subscription_id=paddle_subscription_id,
        paddle_transaction_id=paddle_transaction_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        description=description,
        receipt_url=receipt_url,
        paid_at=datetime.utcnow() if status == PaddlePaymentStatus.PAID else None,
    )
    session.add(row)
    session.flush()
    return row


def _auto_generate_invoice(session: Session, payment: PaddlePayment) -> None:
    try:
        from app.services.invoice_service import generate_invoice_for_paddle_payment
        generate_invoice_for_paddle_payment(session, payment)
    except Exception:
        pass


# ── Gestión de suscripciones por API ────────────────────────────────────────────

def create_customer_portal_url(customer_id: str) -> str | None:
    """Crea una sesión de portal de cliente y devuelve la URL general."""
    if not paddle_configured() or not customer_id:
        return None
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{_api()}/customers/{customer_id}/portal-sessions",
                headers=_headers(),
                json={},
            )
            if resp.status_code in (200, 201):
                urls = (resp.json().get("data") or {}).get("urls") or {}
                return (urls.get("general") or {}).get("overview")
    except Exception:
        pass
    return None


def get_transaction_invoice_url(transaction_id: str) -> str | None:
    """Devuelve la URL de la factura PDF de una transacción de Paddle."""
    if not paddle_configured() or not transaction_id:
        return None
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{_api()}/transactions/{transaction_id}/invoice",
                headers=_headers(),
            )
            if resp.status_code == 200:
                return (resp.json().get("data") or {}).get("url")
    except Exception:
        pass
    return None


def update_paddle_customer_name(tenant: Tenant, new_name: str) -> None:
    """Actualiza el nombre del cliente en Paddle cuando cambia la razón social."""
    if not paddle_configured() or not tenant.paddle_customer_id:
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.patch(
                f"{_api()}/customers/{tenant.paddle_customer_id}",
                headers=_headers(),
                json={"name": new_name},
            )
    except Exception:
        pass


def patch_paddle_subscription_variant(
    paddle_sub_id: str, price_id: str, *, invoice_immediately: bool = False
) -> None:
    """Cambia el precio (tarifa/ciclo) de una suscripción en Paddle.

    invoice_immediately=False → el cambio se aplica sin cobrar de inmediato.
    """
    proration = "prorated_immediately" if invoice_immediately else "do_not_bill"
    with httpx.Client(timeout=15) as client:
        resp = client.patch(
            f"{_api()}/subscriptions/{paddle_sub_id}",
            headers=_headers(),
            json={
                "items": [{"price_id": price_id, "quantity": 1}],
                "proration_billing_mode": proration,
            },
        )
        resp.raise_for_status()


def update_paddle_subscription_variant(
    session: Session,
    tenant: Tenant,
    sub: Subscription,
    new_plan: PricingPlan,
    new_cycle: str,
) -> None:
    """Cambia el precio de la suscripción en Paddle cuando cambia el plan o ciclo."""
    if not paddle_configured() or not sub.paddle_subscription_id:
        return
    price_id = get_paddle_price_id(new_plan, new_cycle)
    if not price_id:
        return
    try:
        patch_paddle_subscription_variant(sub.paddle_subscription_id, price_id)
    except Exception:
        pass


def _resolve_discount_id(code: str) -> str | None:
    """Busca el ID de un descuento de Paddle a partir de su código."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{_api()}/discounts",
                headers=_headers(),
                params={"code": code.upper()},
            )
            if resp.status_code == 200:
                items = resp.json().get("data") or []
                if items:
                    return str(items[0]["id"])
    except Exception:
        pass
    return None


def apply_paddle_discount_to_subscription(
    paddle_subscription_id: str, discount_code: str | None
) -> bool:
    """Aplica o elimina un descuento en una suscripción de Paddle."""
    if not paddle_configured():
        return False
    body: dict
    if discount_code:
        discount_id = _resolve_discount_id(discount_code)
        if not discount_id:
            return False
        body = {"discount": {"id": discount_id, "effective_from": "immediately"}}
    else:
        body = {"discount": None}
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.patch(
                f"{_api()}/subscriptions/{paddle_subscription_id}",
                headers=_headers(),
                json=body,
            )
            return resp.status_code == 200
    except Exception:
        return False


def cancel_paddle_subscription(paddle_subscription_id: str) -> bool:
    """Cancela la suscripción en Paddle al final del período actual."""
    if not paddle_configured():
        return False
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{_api()}/subscriptions/{paddle_subscription_id}/cancel",
                headers=_headers(),
                json={"effective_from": "next_billing_period"},
            )
            return resp.status_code in (200, 202)
    except Exception:
        return False


def sync_discount_to_paddle(discount: "Discount") -> str | None:  # noqa: F821
    """Crea o actualiza un descuento en Paddle. Devuelve el ID o None."""
    from app.models.billing import DiscountType

    if not paddle_configured():
        return None
    is_percent = discount.discount_type == DiscountType.PERCENT
    attrs: dict = {
        "description": discount.name,
        "type": "percentage" if is_percent else "flat",
        "amount": str(discount.value),
        "enabled_for_checkout": True,
        "code": discount.code.upper(),
        "recur": True,
        "expires_at": discount.valid_until.isoformat() + "T23:59:59Z",
    }
    if not is_percent:
        attrs["currency_code"] = "EUR"
    try:
        with httpx.Client(timeout=15) as client:
            if discount.paddle_discount_id:
                resp = client.patch(
                    f"{_api()}/discounts/{discount.paddle_discount_id}",
                    headers=_headers(),
                    json=attrs,
                )
            else:
                resp = client.post(
                    f"{_api()}/discounts", headers=_headers(), json=attrs
                )
            if resp.status_code in (200, 201):
                return str(resp.json()["data"]["id"])
    except Exception:
        pass
    return None


def paddle_refund_transaction(transaction_id: str, amount_cents: int | None = None) -> bool:
    """Reembolsa una transacción de Paddle. Si amount_cents es None, reembolso total."""
    if not paddle_configured() or not transaction_id:
        return False
    # Obtener los line items de la transacción para construir el adjustment
    try:
        with httpx.Client(timeout=15) as client:
            txn_resp = client.get(
                f"{_api()}/transactions/{transaction_id}", headers=_headers()
            )
            if txn_resp.status_code != 200:
                return False
            txn = txn_resp.json().get("data") or {}
            line_items = txn.get("details", {}).get("line_items") or txn.get("items") or []
            items = [
                {"item_id": li["id"], "type": "full"}
                for li in line_items
                if li.get("id")
            ]
            if not items:
                return False

            resp = client.post(
                f"{_api()}/adjustments",
                headers=_headers(),
                json={
                    "action": "refund",
                    "transaction_id": transaction_id,
                    "reason": "Reembolso solicitado por el administrador",
                    "items": items,
                },
            )
            return resp.status_code in (200, 201)
    except Exception:
        return False


def issue_refund_credit_note(
    session: Session, payment_id: UUID
) -> tuple[PaddlePayment, "Invoice"]:  # noqa: F821
    """Marca un pago como reembolsado, ejecuta el reembolso en Paddle y genera el abono."""
    from app.models.invoice import Invoice
    from app.services.invoice_service import create_credit_note

    payment = session.get(PaddlePayment, payment_id)
    if not payment:
        raise ValueError("Pago no encontrado")
    if payment.status == PaddlePaymentStatus.REFUNDED:
        raise ValueError("Este pago ya está marcado como reembolsado")
    if payment.status != PaddlePaymentStatus.PAID:
        raise ValueError("Solo se pueden reembolsar pagos completados (estado: paid)")

    original_invoice = session.exec(
        select(Invoice).where(Invoice.paddle_payment_id == payment.id)
    ).first()
    if not original_invoice:
        raise ValueError(
            "No existe factura asociada a este pago. "
            "Genera la factura primero desde el panel de Facturas."
        )

    if payment.paddle_transaction_id:
        ok = paddle_refund_transaction(payment.paddle_transaction_id)
        if not ok:
            raise ValueError(
                "El reembolso en Paddle no se pudo completar. "
                "Comprueba la configuración de la API o hazlo manualmente desde el panel de Paddle."
            )

    payment.status = PaddlePaymentStatus.REFUNDED
    session.add(payment)
    session.flush()

    credit_note = create_credit_note(session, original_invoice.id, paddle_payment_id=payment.id)
    return payment, credit_note


# ── Notificaciones ──────────────────────────────────────────────────────────────

def _notify_payment(session: Session, tenant: Tenant, payment: PaddlePayment) -> None:
    from app.services.mail_service import MailService
    from app.services.gowa_service import GoWAService

    settings = get_settings()
    amount_str = f"{payment.amount_cents / 100:.2f} {payment.currency}"
    receipt_url = payment.receipt_url or ""
    portal = tenant.paddle_customer_portal_url or f"{settings.public_app_url.rstrip('/')}/cuenta"

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
    portal = tenant.paddle_customer_portal_url or f"{settings.public_app_url.rstrip('/')}/cuenta"

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
