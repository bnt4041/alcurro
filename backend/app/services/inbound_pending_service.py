"""Archivo WhatsApp pendiente de asignar a un tipo de documento."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select

from app.models.clock_settings import EmployeeInboundDocument, InboundPendingUpload
from app.services.clock_settings_service import inbound_name
from app.services.document_service import store_upload_file
from app.services.employee_onboarding_service import is_signature_code

UPLOAD_DIR = Path("/app/uploads")


def get_pending_upload(
    session: Session, employee_id: UUID
) -> InboundPendingUpload | None:
    return session.get(InboundPendingUpload, employee_id)


def set_pending_upload(
    session: Session,
    *,
    employee_id: UUID,
    file_bytes: bytes,
    filename: str,
    whatsapp_message_id: str | None = None,
) -> InboundPendingUpload:
    path, safe = store_upload_file(
        UPLOAD_DIR / "inbound_pending", filename, file_bytes
    )
    row = session.get(InboundPendingUpload, employee_id)
    if row:
        row.file_path = path
        row.filename = safe
        row.whatsapp_message_id = whatsapp_message_id
        row.created_at = datetime.utcnow()
    else:
        row = InboundPendingUpload(
            employee_id=employee_id,
            file_path=path,
            filename=safe,
            whatsapp_message_id=whatsapp_message_id,
        )
        session.add(row)
    session.flush()
    return row


def clear_pending_upload(session: Session, employee_id: UUID) -> None:
    row = session.get(InboundPendingUpload, employee_id)
    if row:
        session.delete(row)
        session.flush()


def pending_file_documents(
    session: Session, employee_id: UUID
) -> list[EmployeeInboundDocument]:
    rows = list(
        session.exec(
            select(EmployeeInboundDocument).where(
                EmployeeInboundDocument.employee_id == employee_id,
                EmployeeInboundDocument.status == "pending",
            )
        ).all()
    )
    return [r for r in rows if not is_signature_code(r.document_code)]


def resolve_document_from_reply(
    session: Session, employee_id: UUID, text: str
) -> EmployeeInboundDocument | None:
    raw = (text or "").strip()
    if not raw:
        return None
    pending = pending_file_documents(session, employee_id)
    if not pending:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(pending):
            return pending[idx]
    lower = raw.lower()
    for row in pending:
        name = inbound_name(session, row.document_code).lower()
        if lower == name or lower == row.document_code.lower():
            return row
        if lower in name:
            return row
    return None
