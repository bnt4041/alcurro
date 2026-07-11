"""Comunicaciones: audiencia, creación, envío (abierto / con firma), cancelación."""

from __future__ import annotations

import mimetypes
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.communication import (
    Communication,
    CommunicationAttachment,
    CommunicationMode,
    CommunicationRecipient,
    CommunicationStatus,
    RecipientStatus,
)
from app.models.models import Employee
from app.models.signature import SignatureEnvelope, SignatureSigner
from app.models.tenant import Company
from app.services.communication_pdf import render_communication_pdf
from app.services.document_service import store_upload_file
from app.services.gowa_service import GoWAService
from app.services.org_service import employee_ids_in_scope
from app.services.signature_service import cancel_envelope, create_envelope_from_upload

UPLOAD_DIR = Path("/app/uploads") / "comunicaciones"


# ── Audiencia ────────────────────────────────────────────────────────────────
def _tenant_company_ids(session: Session, tenant_id: UUID) -> set[UUID]:
    return {
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tenant_id)
        ).all()
    }


def resolve_audience(session: Session, tenant_id: UUID, audience: dict | None) -> list[UUID]:
    """Resuelve el filtro de audiencia a una lista de empleados activos del tenant.

    audience = {company, company_ids, work_center_ids, department_ids,
    supervisor_ids, employee_ids}. Unión de todos los criterios.
    """
    audience = audience or {}
    ids: set[UUID] = set()

    if audience.get("company"):
        ids.update(employee_ids_in_scope(session, tenant_id))
    for cid in audience.get("company_ids") or []:
        ids.update(employee_ids_in_scope(session, tenant_id, company_id=UUID(str(cid))))
    for wc in audience.get("work_center_ids") or []:
        ids.update(employee_ids_in_scope(session, tenant_id, work_center_id=UUID(str(wc))))
    for dep in audience.get("department_ids") or []:
        ids.update(employee_ids_in_scope(session, tenant_id, department_id=UUID(str(dep))))
    for eid in audience.get("employee_ids") or []:
        ids.add(UUID(str(eid)))

    sup_ids = [UUID(str(s)) for s in (audience.get("supervisor_ids") or [])]
    if sup_ids:
        rows = session.exec(
            select(Employee.id).where(Employee.supervisor_id.in_(sup_ids))  # type: ignore[attr-defined]
        ).all()
        ids.update(rows)

    if not ids:
        return []

    # Filtro final: solo empleados activos del tenant.
    company_ids = _tenant_company_ids(session, tenant_id)
    valid: list[UUID] = []
    for emp in session.exec(select(Employee).where(Employee.id.in_(ids))).all():  # type: ignore[attr-defined]
        if emp.is_active and emp.company_id in company_ids:
            valid.append(emp.id)
    return valid


# ── Creación ─────────────────────────────────────────────────────────────────
def _recipient_from_employee(comm_id: UUID, emp: Employee) -> CommunicationRecipient:
    return CommunicationRecipient(
        communication_id=comm_id,
        employee_id=emp.id,
        is_external=False,
        full_name=emp.full_name,
        phone=emp.phone,
        email=emp.email,
        id_document=emp.id_document,
    )


def create_communication(
    session: Session,
    tenant_id: UUID,
    company_id: UUID,
    *,
    title: str,
    body: str,
    mode: str,
    audience: dict | None,
    externals: list[dict] | None,
    created_by_id: UUID | None,
    expires_in_days: int = 14,
) -> Communication:
    comm = Communication(
        tenant_id=tenant_id,
        company_id=company_id,
        title=title.strip()[:255],
        body=body,
        mode=mode if mode in (CommunicationMode.OPEN, CommunicationMode.SIGNATURE) else CommunicationMode.OPEN,
        status=CommunicationStatus.DRAFT,
        audience_filter=audience,
        created_by_id=created_by_id,
        expires_in_days=expires_in_days,
    )
    session.add(comm)
    session.flush()
    _materialize_recipients(session, comm, audience, externals)
    session.commit()
    session.refresh(comm)
    return comm


def _materialize_recipients(
    session: Session,
    comm: Communication,
    audience: dict | None,
    externals: list[dict] | None,
) -> int:
    existing_emp = {
        r.employee_id
        for r in session.exec(
            select(CommunicationRecipient).where(
                CommunicationRecipient.communication_id == comm.id
            )
        ).all()
        if r.employee_id
    }
    added = 0
    emp_ids = resolve_audience(session, comm.tenant_id, audience)
    for emp in session.exec(select(Employee).where(Employee.id.in_(emp_ids))).all():  # type: ignore[attr-defined]
        if emp.id in existing_emp:
            continue
        session.add(_recipient_from_employee(comm.id, emp))
        existing_emp.add(emp.id)
        added += 1
    for ext in externals or []:
        name = (ext.get("full_name") or "").strip()
        if not name:
            continue
        session.add(
            CommunicationRecipient(
                communication_id=comm.id,
                employee_id=None,
                is_external=True,
                full_name=name[:200],
                phone=(ext.get("phone") or "").strip() or None,
                email=(ext.get("email") or "").strip() or None,
                id_document=(ext.get("id_document") or "").strip() or None,
            )
        )
        added += 1
    session.flush()
    return added


def add_attachment(
    session: Session, comm: Communication, file_name: str, content: bytes
) -> CommunicationAttachment:
    path, safe = store_upload_file(UPLOAD_DIR, file_name, content)
    row = CommunicationAttachment(
        communication_id=comm.id,
        file_path=path,
        file_name=safe,
        mimetype=mimetypes.guess_type(safe)[0],
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def add_recipients(
    session: Session,
    comm: Communication,
    *,
    audience: dict | None,
    externals: list[dict] | None,
) -> int:
    if comm.status == CommunicationStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="La comunicación está cancelada")
    added = _materialize_recipients(session, comm, audience, externals)
    session.commit()
    # Si ya se había enviado, despachar a los nuevos (status pending).
    if comm.status in (CommunicationStatus.SENT, CommunicationStatus.SENDING):
        _dispatch_pending(session, comm)
        session.commit()
    return added


# ── Envío ────────────────────────────────────────────────────────────────────
def _attachments(session: Session, comm_id: UUID) -> list[CommunicationAttachment]:
    return list(
        session.exec(
            select(CommunicationAttachment).where(
                CommunicationAttachment.communication_id == comm_id
            )
        ).all()
    )


def _send_attachments(
    gowa: GoWAService, phone: str, attachments: list[CommunicationAttachment]
) -> None:
    for att in attachments:
        try:
            data = Path(att.file_path).read_bytes()
        except OSError:
            continue
        mime = att.mimetype or ""
        if mime.startswith("image/"):
            gowa.send_image_sync(phone, data, att.file_name)
        else:
            gowa.send_file_sync(phone, data, att.file_name)


def _dispatch_open(
    session: Session,
    comm: Communication,
    recipient: CommunicationRecipient,
    gowa: GoWAService,
    attachments: list[CommunicationAttachment],
) -> None:
    if not recipient.phone:
        recipient.status = RecipientStatus.FAILED
        recipient.error = "Sin teléfono"
        return
    text = f"*{comm.title}*\n\n{comm.body}"
    res = gowa.send_text_sync(recipient.phone, text)
    _send_attachments(gowa, recipient.phone, attachments)
    recipient.whatsapp_message_id = (res or {}).get("id") if isinstance(res, dict) else None
    recipient.status = RecipientStatus.SENT
    recipient.sent_at = datetime.utcnow()
    recipient.error = None


def _dispatch_signature(
    session: Session,
    comm: Communication,
    recipient: CommunicationRecipient,
    gowa: GoWAService,
    attachments: list[CommunicationAttachment],
    pdf_bytes: bytes,
) -> None:
    if not recipient.phone or not (recipient.id_document or "").strip():
        recipient.status = RecipientStatus.FAILED
        recipient.error = "Falta DNI/NIE o teléfono para firmar"
        return
    signer = {
        "employee_id": str(recipient.employee_id) if recipient.employee_id else None,
        "full_name": recipient.full_name,
        "email": recipient.email,
        "phone": recipient.phone,
        "id_document": recipient.id_document,
        "sign_order": 1,
    }
    envelope = create_envelope_from_upload(
        session,
        comm.tenant_id,
        comm.company_id,
        file_name=f"comunicado-{comm.id}.pdf",
        content=pdf_bytes,
        title=comm.title,
        signers_data=[signer],
        owner_employee_id=recipient.employee_id,
        send_notifications=True,
        expires_in_days=comm.expires_in_days,
    )
    signer_row = session.exec(
        select(SignatureSigner).where(SignatureSigner.envelope_id == envelope.id)
    ).first()
    recipient.envelope_id = envelope.id
    recipient.signer_id = signer_row.id if signer_row else None
    recipient.status = RecipientStatus.SENT
    recipient.sent_at = datetime.utcnow()
    recipient.error = None
    # Adjuntos extra por WhatsApp (el documento firmable es el comunicado).
    _send_attachments(gowa, recipient.phone, attachments)


def _dispatch_pending(session: Session, comm: Communication) -> None:
    """Envía a todos los destinatarios en estado pending."""
    pending = list(
        session.exec(
            select(CommunicationRecipient).where(
                CommunicationRecipient.communication_id == comm.id,
                CommunicationRecipient.status == RecipientStatus.PENDING,
            )
        ).all()
    )
    if not pending:
        return
    gowa = GoWAService(session)
    attachments = _attachments(session, comm.id)
    pdf_bytes = b""
    if comm.mode == CommunicationMode.SIGNATURE:
        company = session.get(Company, comm.company_id)
        pdf_bytes = render_communication_pdf(
            comm.title, comm.body, company_name=company.name if company else None
        )
    for r in pending:
        try:
            if comm.mode == CommunicationMode.SIGNATURE:
                _dispatch_signature(session, comm, r, gowa, attachments, pdf_bytes)
            else:
                _dispatch_open(session, comm, r, gowa, attachments)
        except Exception as exc:  # noqa: BLE001 — un fallo no debe parar el resto
            r.status = RecipientStatus.FAILED
            r.error = str(exc)[:500]
        session.add(r)
    session.flush()


def send_communication(session: Session, comm: Communication) -> Communication:
    if comm.status == CommunicationStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="La comunicación está cancelada")
    comm.status = CommunicationStatus.SENDING
    comm.updated_at = datetime.utcnow()
    session.add(comm)
    session.flush()
    _dispatch_pending(session, comm)
    comm.status = CommunicationStatus.SENT
    comm.sent_at = comm.sent_at or datetime.utcnow()
    comm.updated_at = datetime.utcnow()
    session.add(comm)
    session.commit()
    session.refresh(comm)
    return comm


def cancel_communication(
    session: Session, comm: Communication, reason: str | None
) -> Communication:
    if comm.status == CommunicationStatus.CANCELLED:
        return comm
    recipients = session.exec(
        select(CommunicationRecipient).where(
            CommunicationRecipient.communication_id == comm.id
        )
    ).all()
    for r in recipients:
        # Cancelar firmas aún no firmadas.
        if r.envelope_id and r.status != RecipientStatus.SIGNED:
            envelope = session.get(SignatureEnvelope, r.envelope_id)
            if envelope and envelope.status not in ("completado", "cancelado"):
                try:
                    cancel_envelope(session, envelope, reason or "Comunicación cancelada")
                except Exception:  # noqa: BLE001
                    pass
        if r.status in (RecipientStatus.PENDING, RecipientStatus.SENT, RecipientStatus.READ):
            r.status = RecipientStatus.CANCELLED
            session.add(r)
    comm.status = CommunicationStatus.CANCELLED
    comm.cancelled_at = datetime.utcnow()
    comm.cancel_reason = (reason or "").strip()[:500] or None
    comm.updated_at = datetime.utcnow()
    session.add(comm)
    session.commit()
    session.refresh(comm)
    return comm


# ── Trazabilidad ─────────────────────────────────────────────────────────────
def sync_recipient_statuses(session: Session, comm: Communication) -> None:
    """Refleja el estado del firmante en el destinatario (modo firma)."""
    if comm.mode != CommunicationMode.SIGNATURE:
        return
    changed = False
    for r in session.exec(
        select(CommunicationRecipient).where(
            CommunicationRecipient.communication_id == comm.id,
            CommunicationRecipient.signer_id.is_not(None),  # type: ignore[attr-defined]
        )
    ).all():
        if r.status in (RecipientStatus.CANCELLED, RecipientStatus.SIGNED):
            continue
        signer = session.get(SignatureSigner, r.signer_id)
        if not signer:
            continue
        if signer.status == "firmado" and r.status != RecipientStatus.SIGNED:
            r.status = RecipientStatus.SIGNED
            r.signed_at = signer.signed_at
            changed = True
        elif signer.status == "autenticado" and r.status == RecipientStatus.SENT:
            r.status = RecipientStatus.READ
            r.read_at = signer.otp_verified_at
            changed = True
        if changed:
            session.add(r)
    if changed:
        session.commit()


def list_recipients(session: Session, comm_id: UUID) -> list[CommunicationRecipient]:
    return list(
        session.exec(
            select(CommunicationRecipient)
            .where(CommunicationRecipient.communication_id == comm_id)
            .order_by(CommunicationRecipient.full_name)  # type: ignore[attr-defined]
        ).all()
    )
