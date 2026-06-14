"""Gestión de facturas desde el panel de plataforma."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.billing import LemonSqueezyPayment, StripePayment
from app.models.invoice import Invoice, InvoiceStatus
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.schemas.invoice import InvoiceCreate, InvoiceDetail, InvoiceListItem, InvoiceStatusUpdate, InvoiceUpdate
from app.services.invoice_service import (
    create_credit_note,
    generate_invoice_for_payment,
    generate_invoice_manually,
    get_invoice_pdf_bytes,
    send_invoice_email,
)

router = APIRouter(prefix="/platform/invoices", tags=["platform-invoices"])


def _enrich(session: Session, invoice: Invoice) -> InvoiceListItem:
    tenant_name: str | None = None
    if invoice.tenant_id:
        t = session.get(Tenant, invoice.tenant_id)
        tenant_name = t.name if t else None
    ls_invoice_ref: str | None = None
    if invoice.ls_payment_id:
        lsp = session.get(LemonSqueezyPayment, invoice.ls_payment_id)
        if lsp and lsp.ls_invoice_id:
            ls_invoice_ref = lsp.ls_invoice_id
    data = InvoiceListItem.model_validate(invoice)
    data.tenant_name = tenant_name
    data.ls_invoice_ref = ls_invoice_ref
    return data


@router.get("", response_model=list[InvoiceListItem])
def list_invoices(
    tenant_id: UUID | None = None,
    status: InvoiceStatus | None = None,
    limit: int = 200,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[InvoiceListItem]:
    stmt = select(Invoice).order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())  # type: ignore[attr-defined]
    if tenant_id:
        stmt = stmt.where(Invoice.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    rows = list(session.exec(stmt.limit(min(limit, 1000))).all())
    return [_enrich(session, r) for r in rows]


@router.get("/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(
    invoice_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> InvoiceDetail:
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    tenant_name: str | None = None
    t = session.get(Tenant, invoice.tenant_id)
    tenant_name = t.name if t else None
    data = InvoiceDetail.model_validate(invoice)
    data.tenant_name = tenant_name
    return data


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Response:
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    pdf_bytes = get_invoice_pdf_bytes(session, invoice_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="No se pudo generar el PDF")
    filename = f"{invoice.number.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=InvoiceDetail, status_code=201)
def create_invoice(
    data: InvoiceCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> InvoiceDetail:
    try:
        invoice = generate_invoice_manually(
            session,
            tenant_id=data.tenant_id,
            concept=data.concept,
            total_cents=data.total_cents,
            currency=data.currency,
            vat_rate=data.vat_rate,
            due_date=data.due_date,
            stripe_payment_id=data.stripe_payment_id,
        )
        session.commit()
        session.refresh(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    t = session.get(Tenant, invoice.tenant_id)
    detail = InvoiceDetail.model_validate(invoice)
    detail.tenant_name = t.name if t else None
    return detail


@router.post("/from-payment/{payment_id}", response_model=InvoiceDetail, status_code=201)
def generate_from_payment(
    payment_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> InvoiceDetail:
    payment = session.get(StripePayment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    invoice = generate_invoice_for_payment(session, payment)
    if not invoice:
        raise HTTPException(status_code=400, detail="No se pudo generar la factura (falta tenant o datos)")
    session.commit()
    session.refresh(invoice)
    t = session.get(Tenant, invoice.tenant_id)
    detail = InvoiceDetail.model_validate(invoice)
    detail.tenant_name = t.name if t else None
    return detail


@router.post("/{invoice_id}/send-email")
def send_email(
    invoice_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> dict:
    sent = send_invoice_email(session, invoice_id)
    if not sent:
        raise HTTPException(status_code=400, detail="No se pudo enviar el email (comprueba configuración SMTP y email del cliente)")
    session.commit()
    return {"ok": True, "message": "Email enviado correctamente"}


@router.post("/{invoice_id}/credit-note", response_model=InvoiceDetail, status_code=201)
def make_credit_note(
    invoice_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> InvoiceDetail:
    try:
        credit = create_credit_note(session, invoice_id)
        session.commit()
        session.refresh(credit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    t = session.get(Tenant, credit.tenant_id)
    detail = InvoiceDetail.model_validate(credit)
    detail.tenant_name = t.name if t else None
    return detail


@router.patch("/{invoice_id}/status", response_model=InvoiceDetail)
def update_invoice_status(
    invoice_id: UUID,
    data: InvoiceStatusUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> InvoiceDetail:
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    invoice.status = data.status
    from datetime import datetime
    invoice.updated_at = datetime.utcnow()
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    t = session.get(Tenant, invoice.tenant_id)
    detail = InvoiceDetail.model_validate(invoice)
    detail.tenant_name = t.name if t else None
    return detail


@router.patch("/{invoice_id}", response_model=InvoiceDetail)
def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> InvoiceDetail:
    from datetime import datetime
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(invoice, key, value)
    invoice.updated_at = datetime.utcnow()
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    t = session.get(Tenant, invoice.tenant_id)
    detail = InvoiceDetail.model_validate(invoice)
    detail.tenant_name = t.name if t else None
    return detail
