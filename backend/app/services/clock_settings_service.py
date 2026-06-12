"""Configuración de fichajes por tenant."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.clock_settings import ClockSettings
from app.models.documents import DocumentDelivery
from app.models.tenant import Company
from app.schemas.clock_settings import (
    ClockSettingsRead,
    ClockSettingsUpdate,
    CompanySignatureDocumentRead,
    InboundDocumentTypeRead,
)

INBOUND_DOCUMENT_CATALOG: list[tuple[str, str, str, bool]] = [
    ("dni", "DNI / NIE", "Documento de identidad (foto o PDF)", False),
    ("photo", "Foto del empleado", "Fotografía reciente", False),
    (
        "driving_license",
        "Carnet de conducir",
        "Solo si el puesto lo requiere",
        True,
    ),
    (
        "legal_terms",
        "Condiciones generales",
        "Aceptación / firma de textos legales",
        False,
    ),
]

CATALOG_BY_CODE = {c[0]: c for c in INBOUND_DOCUMENT_CATALOG}
SIG_PREFIX = "sig:"


def is_signature_code(code: str) -> bool:
    return code.startswith(SIG_PREFIX)


def signature_delivery_id_from_code(code: str) -> UUID | None:
    if not is_signature_code(code):
        return None
    try:
        return UUID(code[len(SIG_PREFIX) :])
    except ValueError:
        return None


def signature_code_for_delivery(delivery_id: UUID) -> str:
    return f"{SIG_PREFIX}{delivery_id}"


def catalog_reads(codes: list[str] | None = None) -> list[InboundDocumentTypeRead]:
    items = INBOUND_DOCUMENT_CATALOG
    if codes is not None:
        items = [CATALOG_BY_CODE[c] for c in codes if c in CATALOG_BY_CODE]
    return [
        InboundDocumentTypeRead(
            code=code,
            name=name,
            description=desc,
            optional=optional,
            kind="catalog",
        )
        for code, name, desc, optional in items
    ]


def list_company_signature_documents(
    session: Session, tenant_id: UUID
) -> list[CompanySignatureDocumentRead]:
    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tenant_id)
        ).all()
    ]
    if not company_ids:
        return []
    rows = session.exec(
        select(DocumentDelivery)
        .where(
            DocumentDelivery.tenant_id == tenant_id,
            DocumentDelivery.employee_id.is_(None),  # type: ignore[union-attr]
            DocumentDelivery.company_id.in_(company_ids),  # type: ignore[attr-defined]
        )
        .order_by(DocumentDelivery.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    result: list[CompanySignatureDocumentRead] = []
    for row in rows:
        company = session.get(Company, row.company_id) if row.company_id else None
        result.append(
            CompanySignatureDocumentRead(
                id=row.id,
                company_id=row.company_id,
                company_name=company.name if company else None,
                title=row.title or row.file_name,
                file_name=row.file_name,
                document_type=row.document_type,
            )
        )
    return result


def effective_inbound_codes(settings: ClockSettings) -> list[str]:
    codes = [
        c
        for c in (settings.inbound_document_codes or [])
        if c in CATALOG_BY_CODE
    ]
    for raw in settings.inbound_signature_delivery_ids or []:
        try:
            did = UUID(str(raw))
        except ValueError:
            continue
        codes.append(signature_code_for_delivery(did))
    return codes


def get_or_create_settings(session: Session, tenant_id: UUID) -> ClockSettings:
    row = session.get(ClockSettings, tenant_id)
    if row:
        return row
    row = ClockSettings(tenant_id=tenant_id)
    session.add(row)
    session.flush()
    return row


def settings_to_read(session: Session, row: ClockSettings) -> ClockSettingsRead:
    catalog_codes = [
        c for c in (row.inbound_document_codes or []) if c in CATALOG_BY_CODE
    ]
    sig_ids: list[UUID] = []
    for raw in row.inbound_signature_delivery_ids or []:
        try:
            sig_ids.append(UUID(str(raw)))
        except ValueError:
            pass
    return ClockSettingsRead(
        tenant_id=row.tenant_id,
        require_geolocation=row.require_geolocation,
        clock_reminder_minutes=row.clock_reminder_minutes,
        clock_exit_reminder_minutes=row.clock_exit_reminder_minutes,
        incident_reminder_enabled=row.incident_reminder_enabled,
        incident_reminder_minutes=row.incident_reminder_minutes,
        inbound_documents_enabled=row.inbound_documents_enabled,
        inbound_document_codes=catalog_codes,
        inbound_signature_delivery_ids=sig_ids,
        send_welcome_with_documents=row.send_welcome_with_documents,
        welcome_message_extra=row.welcome_message_extra,
        daily_summary_enabled=row.daily_summary_enabled,
        require_project_on_clock_in=row.require_project_on_clock_in,
        updated_at=row.updated_at,
        available_inbound_types=catalog_reads(),
        company_signature_documents=list_company_signature_documents(
            session, row.tenant_id
        ),
    )


def update_settings(
    session: Session, tenant_id: UUID, data: ClockSettingsUpdate
) -> ClockSettingsRead:
    row = get_or_create_settings(session, tenant_id)
    payload = data.model_dump(exclude_unset=True)

    if "inbound_document_codes" in payload and payload["inbound_document_codes"]:
        payload["inbound_document_codes"] = [
            c for c in payload["inbound_document_codes"] if c in CATALOG_BY_CODE
        ]

    if "inbound_signature_delivery_ids" in payload:
        valid_sig: list[str] = []
        company_ids = {
            c.id
            for c in session.exec(
                select(Company).where(Company.tenant_id == tenant_id)
            ).all()
        }
        for raw in payload["inbound_signature_delivery_ids"] or []:
            try:
                did = UUID(str(raw))
            except (ValueError, TypeError):
                continue
            doc = session.get(DocumentDelivery, did)
            if (
                doc
                and doc.tenant_id == tenant_id
                and doc.employee_id is None
                and doc.company_id in company_ids
            ):
                valid_sig.append(str(did))
        payload["inbound_signature_delivery_ids"] = valid_sig

    if "clock_reminder_minutes" in payload and payload["clock_reminder_minutes"] == 0:
        payload["clock_reminder_minutes"] = None
    if "clock_exit_reminder_minutes" in payload and payload["clock_exit_reminder_minutes"] == 0:
        payload["clock_exit_reminder_minutes"] = None

    for key, value in payload.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.flush()
    return settings_to_read(session, row)


def inbound_name(session: Session, code: str) -> str:
    if is_signature_code(code):
        did = signature_delivery_id_from_code(code)
        if did:
            doc = session.get(DocumentDelivery, did)
            if doc:
                return doc.title or doc.file_name
        return "Documento para firmar"
    item = CATALOG_BY_CODE.get(code)
    return item[1] if item else code
