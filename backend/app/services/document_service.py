"""Gestión de tipos, etiquetas y entregas documentales."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.documents import (
    DocumentDelivery,
    DocumentDeliveryTag,
    DocumentExpiryNotificationLog,
    DocumentTag,
    DocumentType,
)
from app.models.signature import SignatureEnvelope
from app.models.models import Employee
from app.models.tenant import Company
from app.schemas.documents import DocumentDeliveryRead, DocumentTagRead, DocumentTypeRead


def ensure_default_types(session: Session, tenant_id: UUID) -> None:
    defaults = [
        ("nomina", "Nómina", 0),
        ("contrato", "Contrato", 1),
        ("certificado", "Certificado", 2),
        ("comunicado", "Comunicado", 3),
        ("otro", "Otro", 4),
    ]
    for code, name, order in defaults:
        exists = session.exec(
            select(DocumentType).where(
                DocumentType.tenant_id == tenant_id,
                DocumentType.code == code,
            )
        ).first()
        if not exists:
            session.add(
                DocumentType(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    sort_order=order,
                )
            )
    session.flush()


def get_type_or_404(session: Session, tenant_id: UUID, type_id: UUID) -> DocumentType:
    row = session.get(DocumentType, type_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Tipología no encontrada")
    return row


def get_type_by_code(
    session: Session, tenant_id: UUID, code: str
) -> DocumentType | None:
    return session.exec(
        select(DocumentType).where(
            DocumentType.tenant_id == tenant_id,
            DocumentType.code == code,
            DocumentType.is_active == True,  # noqa: E712
        )
    ).first()


def validate_target(
    session: Session,
    tenant_id: UUID,
    *,
    company_id: UUID | None,
    employee_id: UUID | None,
) -> tuple[UUID | None, UUID | None]:
    if bool(company_id) == bool(employee_id):
        raise HTTPException(
            status_code=400,
            detail="Indica empresa o empleado (uno de los dos, no ambos)",
        )
    if company_id:
        company = session.get(Company, company_id)
        if not company or company.tenant_id != tenant_id:
            raise HTTPException(status_code=400, detail="Empresa no válida")
        return company_id, None
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=400, detail="Empleado no válido")
    company = session.get(Company, emp.company_id)
    if not company or company.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="Empleado fuera de la cuenta")
    return None, employee_id


def set_document_tags(
    session: Session, document_id: UUID, tenant_id: UUID, tag_ids: list[UUID]
) -> None:
    for link in session.exec(
        select(DocumentDeliveryTag).where(
            DocumentDeliveryTag.document_delivery_id == document_id
        )
    ).all():
        session.delete(link)
    if not tag_ids:
        return
    valid = session.exec(
        select(DocumentTag).where(
            DocumentTag.tenant_id == tenant_id,
            DocumentTag.id.in_(tag_ids),  # type: ignore[attr-defined]
        )
    ).all()
    if len(valid) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="Etiquetas no válidas")
    for tag in valid:
        session.add(DocumentDeliveryTag(document_delivery_id=document_id, tag_id=tag.id))


def delivery_to_read(session: Session, row: DocumentDelivery) -> DocumentDeliveryRead:
    today = date.today()
    type_name: str | None = None
    if row.document_type_id:
        dt = session.get(DocumentType, row.document_type_id)
        type_name = dt.name if dt else None
    tag_links = session.exec(
        select(DocumentDeliveryTag).where(
            DocumentDeliveryTag.document_delivery_id == row.id
        )
    ).all()
    tags: list[DocumentTagRead] = []
    tag_ids: list[UUID] = []
    for link in tag_links:
        tag = session.get(DocumentTag, link.tag_id)
        if tag:
            tags.append(DocumentTagRead.model_validate(tag))
            tag_ids.append(tag.id)
    return DocumentDeliveryRead(
        id=row.id,
        tenant_id=row.tenant_id,
        company_id=row.company_id,
        employee_id=row.employee_id,
        document_type_id=row.document_type_id,
        document_type=row.document_type,
        document_type_name=type_name,
        file_path=row.file_path,
        file_name=row.file_name,
        title=row.title,
        expires_at=row.expires_at,
        is_expired=bool(row.expires_at and row.expires_at < today),
        tag_ids=tag_ids,
        tags=tags,
        requires_acknowledgment=row.requires_acknowledgment,
        sent_at=row.sent_at,
        acknowledged_at=row.acknowledged_at,
        acknowledgment_text=row.acknowledgment_text,
        created_at=row.created_at,
    )


def store_upload_file(upload_dir: Path, filename: str, content: bytes) -> tuple[str, str]:
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name or "documento.pdf"
    stored = upload_dir / f"{uuid4()}_{safe}"
    stored.write_bytes(content)
    return str(stored), safe


def create_delivery(
    session: Session,
    *,
    tenant_id: UUID,
    company_id: UUID | None,
    employee_id: UUID | None,
    document_type_id: UUID | None,
    document_type_code: str,
    file_path: str,
    file_name: str,
    title: str | None = None,
    expires_at: date | None = None,
    requires_acknowledgment: bool = True,
    tag_ids: list[UUID] | None = None,
) -> DocumentDelivery:
    company_id, employee_id = validate_target(
        session, tenant_id, company_id=company_id, employee_id=employee_id
    )
    row = DocumentDelivery(
        tenant_id=tenant_id,
        company_id=company_id,
        employee_id=employee_id,
        document_type_id=document_type_id,
        document_type=document_type_code,
        file_path=file_path,
        file_name=file_name,
        title=title,
        expires_at=expires_at,
        requires_acknowledgment=requires_acknowledgment,
    )
    session.add(row)
    session.flush()
    if tag_ids:
        set_document_tags(session, row.id, tenant_id, tag_ids)
    return row


def delete_delivery(session: Session, row: DocumentDelivery) -> None:
    """Elimina entrega documental y dependencias (firmas conservan su PDF)."""
    for envelope in session.exec(
        select(SignatureEnvelope).where(
            SignatureEnvelope.document_delivery_id == row.id
        )
    ).all():
        envelope.document_delivery_id = None
        session.add(envelope)

    for link in session.exec(
        select(DocumentDeliveryTag).where(
            DocumentDeliveryTag.document_delivery_id == row.id
        )
    ).all():
        session.delete(link)

    for log in session.exec(
        select(DocumentExpiryNotificationLog).where(
            DocumentExpiryNotificationLog.document_delivery_id == row.id
        )
    ).all():
        session.delete(log)

    file_path = Path(row.file_path)
    session.delete(row)
    session.flush()
    if file_path.is_file():
        file_path.unlink()
