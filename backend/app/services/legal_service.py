"""Textos legales y comprobación de aceptaciones."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.legal import LegalAcceptance, LegalDocument
from app.models.models import Employee
from app.schemas.legal import EmployeeLegalStatusItem


def seed_default_legal_documents(session: Session, tenant_id: UUID) -> None:
    defaults = [
        (
            "time_tracking",
            "Registro de jornada laboral",
            (
                "Declaro haber sido informado/a de la obligación de registrar la jornada "
                "laboral conforme al Real Decreto-ley 8/2019 y al reglamento interno de la "
                "empresa. Autorizo el tratamiento de mis datos de fichaje para fines "
                "laborales y de cumplimiento legal."
            ),
            0,
        ),
        (
            "privacy",
            "Política de privacidad y protección de datos",
            (
                "He leído y acepto la política de privacidad y el tratamiento de mis datos "
                "personales conforme al RGPD y la LOPDGDD, para la gestión de la relación "
                "laboral, nóminas, comunicaciones y servicios de recursos humanos."
            ),
            1,
        ),
        (
            "internal_rules",
            "Normativa interna y uso de medios digitales",
            (
                "Acepto conocer y cumplir la normativa interna de la empresa, incluido el "
                "uso responsable de herramientas digitales, WhatsApp corporativo para "
                "fichajes cuando aplique, y las políticas de seguridad de la información."
            ),
            2,
        ),
    ]
    for code, title, body, order in defaults:
        exists = session.exec(
            select(LegalDocument).where(
                LegalDocument.tenant_id == tenant_id,
                LegalDocument.code == code,
            )
        ).first()
        if exists:
            continue
        session.add(
            LegalDocument(
                tenant_id=tenant_id,
                code=code,
                title=title,
                body=body,
                sort_order=order,
                is_active=True,
                is_required=True,
                version=1,
            )
        )
    session.flush()


def employee_legal_status(
    session: Session, tenant_id: UUID, employee_id: UUID
) -> tuple[list[EmployeeLegalStatusItem], bool]:
    docs = list(
        session.exec(
            select(LegalDocument)
            .where(
                LegalDocument.tenant_id == tenant_id,
                LegalDocument.is_active == True,  # noqa: E712
            )
            .order_by(LegalDocument.sort_order, LegalDocument.title)
        ).all()
    )
    acceptances = {
        a.legal_document_id: a
        for a in session.exec(
            select(LegalAcceptance).where(LegalAcceptance.employee_id == employee_id)
        ).all()
    }

    items: list[EmployeeLegalStatusItem] = []
    all_ok = True
    for doc in docs:
        acc = acceptances.get(doc.id)
        accepted = acc is not None and acc.document_version >= doc.version
        needs_reaccept = acc is not None and acc.document_version < doc.version
        if doc.is_required and not accepted:
            all_ok = False
        items.append(
            EmployeeLegalStatusItem(
                document_id=doc.id,
                code=doc.code,
                title=doc.title,
                body=doc.body,
                version=doc.version,
                is_required=doc.is_required,
                accepted=accepted,
                accepted_at=acc.accepted_at if acc else None,
                accepted_version=acc.document_version if acc else None,
                needs_reaccept=needs_reaccept,
            )
        )
    return items, all_ok


def accept_document(
    session: Session,
    employee_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
) -> LegalAcceptance:
    emp = session.get(Employee, employee_id)
    if not emp:
        raise ValueError("Empleado no encontrado")
    doc = session.get(LegalDocument, document_id)
    if not doc or doc.tenant_id != tenant_id or not doc.is_active:
        raise ValueError("Documento legal no encontrado")

    existing = session.exec(
        select(LegalAcceptance).where(
            LegalAcceptance.employee_id == employee_id,
            LegalAcceptance.legal_document_id == document_id,
        )
    ).first()

    if existing:
        existing.document_version = doc.version
        existing.accepted_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = LegalAcceptance(
        employee_id=employee_id,
        legal_document_id=document_id,
        document_version=doc.version,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
