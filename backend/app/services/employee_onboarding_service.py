"""Alta de empleados: bienvenida WhatsApp y documentos inbound."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select

from app.models.clock_settings import EmployeeInboundDocument
from app.models.documents import DocumentDelivery
from app.models.models import Employee
from app.models.signature import EnvelopeStatus, SignatureEnvelope
from app.models.tenant import Company
from app.schemas.clock_settings import EmployeeInboundDocumentRead
from app.schemas.signature import SignatureEnvelopeCreate, SignerInput
from app.services.clock_settings_service import (
    effective_inbound_codes,
    get_or_create_settings,
    inbound_name,
    is_signature_code,
    signature_delivery_id_from_code,
)
from app.services.document_service import create_delivery, store_upload_file
from app.services.signature_service import create_envelope

UPLOAD_DIR = Path("/app/uploads")


def _sync_signature_inbound_status(session: Session, employee_id: UUID) -> None:
    rows = session.exec(
        select(EmployeeInboundDocument).where(
            EmployeeInboundDocument.employee_id == employee_id,
            EmployeeInboundDocument.signature_envelope_id.isnot(None),  # type: ignore[union-attr]
            EmployeeInboundDocument.status == "pending",
        )
    ).all()
    for row in rows:
        env = session.get(SignatureEnvelope, row.signature_envelope_id)
        if not env:
            continue
        if env.status == EnvelopeStatus.COMPLETED:
            row.status = "received"
            row.received_at = env.completed_at or datetime.utcnow()
            if env.document_delivery_id and not row.document_delivery_id:
                row.document_delivery_id = env.document_delivery_id
            session.add(row)
    session.flush()


def provision_inbound_signatures(
    session: Session, employee: Employee, tenant_id: UUID
) -> None:
    """Crea solicitudes de firma para documentos de empresa configurados en el alta."""
    company = session.get(Company, employee.company_id)
    if not company:
        return
    pending = session.exec(
        select(EmployeeInboundDocument).where(
            EmployeeInboundDocument.employee_id == employee.id,
            EmployeeInboundDocument.status == "pending",
        )
    ).all()
    for row in pending:
        if not is_signature_code(row.document_code):
            continue
        if row.signature_envelope_id:
            continue
        delivery_id = signature_delivery_id_from_code(row.document_code)
        if not delivery_id:
            continue
        doc = session.get(DocumentDelivery, delivery_id)
        if not doc or doc.company_id != company.id:
            continue
        try:
            envelope = create_envelope(
                session,
                tenant_id,
                company.id,
                SignatureEnvelopeCreate(
                    document_delivery_id=delivery_id,
                    title=inbound_name(session, row.document_code),
                    signers=[SignerInput(employee_id=employee.id, sign_order=1)],
                    send_notifications=True,
                ),
            )
            row.signature_envelope_id = envelope.id
            row.document_delivery_id = delivery_id
            session.add(row)
        except (ValueError, Exception):
            continue
    session.flush()
    _sync_signature_inbound_status(session, employee.id)


def seed_inbound_documents(session: Session, employee_id: UUID, tenant_id: UUID) -> None:
    settings = get_or_create_settings(session, tenant_id)
    if not settings.inbound_documents_enabled:
        return
    employee = session.get(Employee, employee_id)
    if not employee:
        return
    codes = effective_inbound_codes(settings)
    for code in codes:
        exists = session.exec(
            select(EmployeeInboundDocument).where(
                EmployeeInboundDocument.employee_id == employee_id,
                EmployeeInboundDocument.document_code == code,
            )
        ).first()
        if exists:
            continue
        delivery_id = signature_delivery_id_from_code(code)
        session.add(
            EmployeeInboundDocument(
                employee_id=employee_id,
                document_code=code,
                status="pending",
                document_delivery_id=delivery_id,
            )
        )
    session.flush()
    provision_inbound_signatures(session, employee, tenant_id)


def list_inbound_documents(
    session: Session, employee_id: UUID
) -> list[EmployeeInboundDocumentRead]:
    _sync_signature_inbound_status(session, employee_id)
    rows = session.exec(
        select(EmployeeInboundDocument)
        .where(EmployeeInboundDocument.employee_id == employee_id)
        .order_by(EmployeeInboundDocument.created_at)
    ).all()
    return [
        EmployeeInboundDocumentRead(
            id=r.id,
            employee_id=r.employee_id,
            document_code=r.document_code,
            document_name=inbound_name(session, r.document_code),
            status=r.status,
            document_delivery_id=r.document_delivery_id,
            signature_envelope_id=r.signature_envelope_id,
            received_at=r.received_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


def pending_inbound_codes(session: Session, employee_id: UUID) -> list[str]:
    _sync_signature_inbound_status(session, employee_id)
    return [
        r.document_code
        for r in session.exec(
            select(EmployeeInboundDocument).where(
                EmployeeInboundDocument.employee_id == employee_id,
                EmployeeInboundDocument.status == "pending",
            )
        ).all()
    ]


def build_welcome_message(
    session: Session, employee: Employee, tenant_name: str
) -> str:
    company = session.get(Company, employee.company_id)
    if not company:
        return f"¡Hola {employee.full_name}!"
    company_name = company.name
    settings = get_or_create_settings(session, company.tenant_id)
    lines = [
        f"¡Hola {employee.full_name}! Bienvenido/a a {company_name}.",
        "",
        "Por WhatsApp puedes:",
        "• Fichar ENTRADA o SALIDA (mensaje de texto)",
        "• Compartir tu ubicación para fichar con geolocalización",
        "• Gestionar paradas y vacaciones",
    ]
    if settings.require_geolocation:
        lines.append(
            "📍 Se recomienda compartir tu ubicación al fichar (más fiable)."
        )
    if settings.welcome_message_extra:
        lines.extend(["", settings.welcome_message_extra.strip()])
    if settings.inbound_documents_enabled and settings.send_welcome_with_documents:
        pending = pending_inbound_codes(session, employee.id)
        if pending:
            uploads = [c for c in pending if not is_signature_code(c)]
            signatures = [c for c in pending if is_signature_code(c)]
            if uploads:
                lines.extend(
                    [
                        "",
                        "📎 Documentación pendiente (envía foto o PDF por aquí):",
                    ]
                )
                for code in uploads:
                    opt = " (opcional)" if code == "driving_license" else ""
                    lines.append(f"  • {inbound_name(session, code)}{opt}")
            if signatures:
                lines.extend(
                    [
                        "",
                        "✍️ Documentos para firmar (recibirás el enlace por WhatsApp):",
                    ]
                )
                for code in signatures:
                    lines.append(f"  • {inbound_name(session, code)}")
    return "\n".join(lines)


def mark_welcome_sent(session: Session, employee: Employee) -> None:
    employee.welcome_sent_at = datetime.utcnow()
    session.add(employee)
    session.flush()


def should_send_welcome(employee: Employee) -> bool:
    return employee.welcome_sent_at is None


def receive_inbound_file(
    session: Session,
    employee: Employee,
    *,
    tenant_id: UUID,
    file_bytes: bytes,
    filename: str,
    document_code: str | None = None,
) -> tuple[bool, str]:
    """Guarda archivo y marca documento inbound. Devuelve (ok, mensaje)."""
    from app.services.whatsapp_format import format_inbound_received

    pending_rows = list(
        session.exec(
            select(EmployeeInboundDocument).where(
                EmployeeInboundDocument.employee_id == employee.id,
                EmployeeInboundDocument.status == "pending",
            )
        ).all()
    )
    file_pending = [r for r in pending_rows if not is_signature_code(r.document_code)]
    if not file_pending:
        sig_pending = [r for r in pending_rows if is_signature_code(r.document_code)]
        if sig_pending:
            return (
                False,
                "✍️ Tienes documentos pendientes de *firma*. "
                "Revisa el enlace enviado por WhatsApp.",
            )
        return False, "ℹ️ No tienes documentación pendiente."

    target: EmployeeInboundDocument | None = None
    if document_code and not is_signature_code(document_code):
        target = next(
            (r for r in file_pending if r.document_code == document_code), None
        )
    if not target:
        if len(file_pending) > 1:
            return (
                False,
                "NEEDS_PICKER",
            )
        target = file_pending[0]

    doc_type_map = {
        "dni": "certificado",
        "photo": "otro",
        "driving_license": "certificado",
        "legal_terms": "contrato",
    }
    type_code = doc_type_map.get(target.document_code, "otro")
    path, safe = store_upload_file(UPLOAD_DIR, filename, file_bytes)
    delivery = create_delivery(
        session,
        tenant_id=tenant_id,
        company_id=None,
        employee_id=employee.id,
        document_type_id=None,
        document_type_code=type_code,
        file_path=path,
        file_name=safe,
        title=inbound_name(session, target.document_code),
        requires_acknowledgment=target.document_code == "legal_terms",
    )
    target.status = "received"
    target.document_delivery_id = delivery.id
    target.received_at = datetime.utcnow()
    session.add(target)
    session.flush()

    doc_name = inbound_name(session, target.document_code)
    remaining = len(pending_inbound_codes(session, employee.id))
    return True, format_inbound_received(doc_name, remaining)


def complete_pending_upload(
    session: Session,
    employee: Employee,
    *,
    tenant_id: UUID,
    document_code: str,
) -> tuple[bool, str]:
    """Procesa archivo guardado en inbound_pending_uploads."""
    from app.services.inbound_pending_service import clear_pending_upload, get_pending_upload

    pending = get_pending_upload(session, employee.id)
    if not pending or not Path(pending.file_path).is_file():
        return False, "No hay archivo pendiente. Vuelve a enviar la foto o PDF."
    data = Path(pending.file_path).read_bytes()
    clear_pending_upload(session, employee.id)
    return receive_inbound_file(
        session,
        employee,
        tenant_id=tenant_id,
        file_bytes=data,
        filename=pending.filename,
        document_code=document_code,
    )
