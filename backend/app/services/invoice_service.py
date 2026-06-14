"""Lógica de negocio de facturas: numeración, generación, PDF y email."""

from __future__ import annotations

import io
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select

from app.models.invoice import Invoice, InvoiceStatus
from app.models.platform_settings import PLATFORM_SETTINGS_ID, PlatformSettings
from app.models.billing import LemonSqueezyPayment, StripePayment
from app.models.tenant import Tenant

UPLOAD_DIR = Path("/app/uploads/invoices")


def get_platform_settings(session: Session) -> PlatformSettings:
    """Devuelve la configuración de plataforma; la crea si no existe."""
    row = session.get(PlatformSettings, PLATFORM_SETTINGS_ID)
    if not row:
        row = PlatformSettings()
        session.add(row)
        session.flush()
    return row


def next_invoice_number(session: Session, settings: PlatformSettings) -> str:
    """Genera el próximo número de factura y actualiza el contador."""
    current_year = datetime.utcnow().year

    if settings.invoice_current_year != current_year:
        settings.invoice_current_year = current_year
        settings.invoice_next_number = 1

    number = f"{settings.invoice_prefix}-{current_year}-{settings.invoice_next_number:04d}"
    settings.invoice_next_number += 1
    settings.updated_at = datetime.utcnow()
    session.add(settings)
    session.flush()
    return number


def next_credit_note_number(session: Session, settings: PlatformSettings) -> str:
    """Genera el próximo número de factura de abono y actualiza el contador."""
    current_year = datetime.utcnow().year

    if settings.credit_note_current_year != current_year:
        settings.credit_note_current_year = current_year
        settings.credit_note_next_number = 1

    number = f"{settings.credit_note_prefix}-{current_year}-{settings.credit_note_next_number:04d}"
    settings.credit_note_next_number += 1
    settings.updated_at = datetime.utcnow()
    session.add(settings)
    session.flush()
    return number


def _snapshot_tenant(tenant: Tenant) -> dict:
    return {
        "recipient_legal_name": tenant.legal_name or tenant.name,
        "recipient_tax_id": tenant.tax_id,
        "recipient_address": tenant.billing_address,
        "recipient_city": tenant.billing_city,
        "recipient_postal_code": tenant.billing_postal_code,
        "recipient_province": tenant.billing_province,
        "recipient_country": tenant.billing_country or "ES",
        "recipient_email": tenant.billing_email,
    }


def _compute_amounts(base_cents: int, vat_rate: int) -> tuple[int, int]:
    """Devuelve (vat_cents, total_cents)."""
    vat_cents = round(base_cents * vat_rate / 100)
    return vat_cents, base_cents + vat_cents


def generate_invoice_for_payment(
    session: Session,
    payment: StripePayment,
    *,
    concept: str | None = None,
    vat_rate: int | None = None,
) -> Invoice | None:
    """Genera una factura a partir de un StripePayment. Idempotente."""
    # Si ya existe factura para este pago, devolverla
    existing = session.exec(
        select(Invoice).where(Invoice.stripe_payment_id == payment.id)
    ).first()
    if existing:
        return existing

    if not payment.tenant_id:
        return None

    tenant = session.get(Tenant, payment.tenant_id)
    if not tenant:
        return None

    settings = get_platform_settings(session)
    effective_vat = vat_rate if vat_rate is not None else settings.vat_rate

    # Si el pago ya incluye IVA (importes con IVA), calculamos la base
    # alcurro factura con IVA incluido en amount_cents → base = total / (1 + vat/100)
    total_cents = payment.amount_cents
    base_cents = round(total_cents * 100 / (100 + effective_vat))
    vat_cents = total_cents - base_cents

    number = next_invoice_number(session, settings)

    invoice = Invoice(
        tenant_id=payment.tenant_id,
        number=number,
        concept=concept or payment.description or "Suscripción alcurro",
        base_cents=base_cents,
        vat_rate=effective_vat,
        vat_cents=vat_cents,
        total_cents=total_cents,
        currency=payment.currency,
        issue_date=date.today(),
        status=InvoiceStatus.PAID,
        stripe_payment_id=payment.id,
        **_snapshot_tenant(tenant),
    )
    session.add(invoice)
    session.flush()

    # Guardar PDF
    _save_invoice_pdf(session, invoice, settings)

    if settings.auto_send_invoice_email and invoice.recipient_email:
        _send_invoice_email_internal(session, invoice, settings, tenant)

    return invoice


def generate_invoice_for_ls_payment(
    session: Session,
    payment: LemonSqueezyPayment,
    *,
    concept: str | None = None,
    vat_rate: int | None = None,
) -> Invoice | None:
    """Genera una factura interna a partir de un LemonSqueezyPayment. Idempotente."""
    existing = session.exec(
        select(Invoice).where(Invoice.ls_payment_id == payment.id)
    ).first()
    if existing:
        return existing

    if not payment.tenant_id:
        return None

    tenant = session.get(Tenant, payment.tenant_id)
    if not tenant:
        return None

    settings = get_platform_settings(session)
    effective_vat = vat_rate if vat_rate is not None else settings.vat_rate

    total_cents = payment.amount_cents
    base_cents = round(total_cents * 100 / (100 + effective_vat))
    vat_cents = total_cents - base_cents

    number = next_invoice_number(session, settings)

    invoice = Invoice(
        tenant_id=payment.tenant_id,
        number=number,
        concept=concept or payment.description or "Suscripción alcurro",
        base_cents=base_cents,
        vat_rate=effective_vat,
        vat_cents=vat_cents,
        total_cents=total_cents,
        currency=payment.currency,
        issue_date=date.today(),
        status=InvoiceStatus.PAID,
        ls_payment_id=payment.id,
        **_snapshot_tenant(tenant),
    )
    session.add(invoice)
    session.flush()

    _save_invoice_pdf(session, invoice, settings)

    if settings.auto_send_invoice_email and invoice.recipient_email:
        _send_invoice_email_internal(session, invoice, settings, tenant)

    return invoice


def generate_invoice_manually(
    session: Session,
    *,
    tenant_id: UUID,
    concept: str,
    total_cents: int,
    currency: str = "EUR",
    vat_rate: int | None = None,
    due_date: date | None = None,
    stripe_payment_id: UUID | None = None,
) -> Invoice:
    """Crea una factura manualmente desde el panel de plataforma."""
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Cuenta no encontrada")

    settings = get_platform_settings(session)
    effective_vat = vat_rate if vat_rate is not None else settings.vat_rate
    base_cents = round(total_cents * 100 / (100 + effective_vat))
    vat_cents = total_cents - base_cents

    number = next_invoice_number(session, settings)

    invoice = Invoice(
        tenant_id=tenant_id,
        number=number,
        concept=concept,
        base_cents=base_cents,
        vat_rate=effective_vat,
        vat_cents=vat_cents,
        total_cents=total_cents,
        currency=currency,
        issue_date=date.today(),
        due_date=due_date,
        status=InvoiceStatus.DRAFT,
        stripe_payment_id=stripe_payment_id,
        **_snapshot_tenant(tenant),
    )
    session.add(invoice)
    session.flush()
    _save_invoice_pdf(session, invoice, settings)
    return invoice


def create_credit_note(
    session: Session,
    invoice_id: UUID,
    *,
    ls_payment_id: UUID | None = None,
) -> Invoice:
    """Genera una factura rectificativa (abono) para una factura existente."""
    original = session.get(Invoice, invoice_id)
    if not original:
        raise ValueError("Factura no encontrada")

    # Impedir doble rectificativa
    existing = session.exec(
        select(Invoice).where(Invoice.credit_note_for_id == invoice_id)
    ).first()
    if existing:
        raise ValueError(f"Ya existe una factura rectificativa ({existing.number}) para esta factura")

    settings = get_platform_settings(session)
    number = next_credit_note_number(session, settings)

    credit = Invoice(
        tenant_id=original.tenant_id,
        number=number,
        concept=f"Rectificativa de {original.number} — {original.concept}",
        base_cents=-original.base_cents,
        vat_rate=original.vat_rate,
        vat_cents=-original.vat_cents,
        total_cents=-original.total_cents,
        currency=original.currency,
        issue_date=date.today(),
        status=InvoiceStatus.CREDIT_NOTE,
        credit_note_for_id=original.id,
        ls_payment_id=ls_payment_id,
        recipient_legal_name=original.recipient_legal_name,
        recipient_tax_id=original.recipient_tax_id,
        recipient_address=original.recipient_address,
        recipient_city=original.recipient_city,
        recipient_postal_code=original.recipient_postal_code,
        recipient_province=original.recipient_province,
        recipient_country=original.recipient_country,
        recipient_email=original.recipient_email,
    )
    session.add(credit)
    session.flush()
    _save_invoice_pdf(session, credit, settings)
    return credit


def get_invoice_pdf_bytes(session: Session, invoice_id: UUID) -> bytes | None:
    """Devuelve los bytes del PDF de una factura (genera al vuelo si falta)."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        return None

    # Intentar leer del disco
    if invoice.pdf_url:
        path = Path(invoice.pdf_url.lstrip("/").replace("uploads/", "/app/uploads/", 1))
        if path.exists():
            return path.read_bytes()

    # Generar al vuelo
    settings = get_platform_settings(session)
    return _build_pdf(invoice, settings)


def send_invoice_email(session: Session, invoice_id: UUID) -> bool:
    """Envía la factura por email al receptor. Devuelve True si se envió."""
    invoice = session.get(Invoice, invoice_id)
    if not invoice or not invoice.recipient_email:
        return False

    tenant = session.get(Tenant, invoice.tenant_id)
    settings = get_platform_settings(session)
    return _send_invoice_email_internal(session, invoice, settings, tenant)


# ── Helpers privados ─────────────────────────────────────────────────────────

def _build_pdf(invoice: Invoice, settings: PlatformSettings) -> bytes:
    from app.services.invoice_pdf_service import generate_invoice_pdf
    return generate_invoice_pdf(invoice, settings)


def _save_invoice_pdf(
    session: Session, invoice: Invoice, settings: PlatformSettings
) -> None:
    try:
        pdf_bytes = _build_pdf(invoice, settings)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{invoice.number.replace('/', '-')}.pdf"
        path = UPLOAD_DIR / filename
        path.write_bytes(pdf_bytes)
        invoice.pdf_url = f"/uploads/invoices/{filename}"
        session.add(invoice)
        session.flush()
    except Exception:
        pass


def _send_invoice_email_internal(
    session: Session,
    invoice: Invoice,
    settings: PlatformSettings,
    tenant: Tenant | None,
) -> bool:
    try:
        from app.services.mail_service import MailService
        from app.services.invoice_pdf_service import generate_invoice_pdf

        email = invoice.recipient_email
        if not email:
            return False

        pdf_bytes = _build_pdf(invoice, settings)
        amount_str = f"{invoice.total_cents / 100:.2f} {invoice.currency}"
        name = invoice.recipient_legal_name or (tenant.name if tenant else email)
        subject = f"Factura {invoice.number} — alcurro"
        body = (
            f"Hola {name},\n\n"
            f"Adjuntamos la factura {invoice.number} por importe de {amount_str}.\n\n"
            f"Concepto: {invoice.concept}\n\n"
            f"Puedes consultarla también en tu panel de cuenta:\n"
            f"https://app.alcurro.es/app/cuenta\n\n"
            f"Gracias por confiar en alcurro.\n\n"
            f"— {settings.legal_name}"
        )

        mail = MailService(session)
        # Enviar con adjunto PDF
        _send_with_attachment(mail, email, subject, body, pdf_bytes, f"{invoice.number}.pdf")

        invoice.email_sent_at = datetime.utcnow()
        invoice.status = InvoiceStatus.SENT if invoice.status == InvoiceStatus.DRAFT else invoice.status
        session.add(invoice)
        session.flush()
        return True
    except Exception:
        return False


def _send_with_attachment(
    mail_service: object,
    to: str,
    subject: str,
    body: str,
    attachment_bytes: bytes,
    attachment_name: str,
) -> None:
    """Envía email con adjunto usando smtplib directamente."""
    import smtplib
    import ssl
    from email.message import EmailMessage

    s = mail_service._settings  # type: ignore[attr-defined]
    if not s.smtp_host or not s.mail_from_address:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = (
        f"{s.mail_from_name} <{s.mail_from_address}>"
        if s.mail_from_name
        else s.mail_from_address
    )
    msg["To"] = to
    msg.set_content(body)
    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="pdf",
        filename=attachment_name,
    )

    port = s.smtp_port or 587
    context = ssl.create_default_context() if s.smtp_use_tls else None
    with smtplib.SMTP(s.smtp_host, port) as server:
        if s.smtp_use_tls:
            server.starttls(context=context)
        if s.smtp_user and s.smtp_password:
            server.login(s.smtp_user, s.smtp_password)
        server.send_message(msg)
