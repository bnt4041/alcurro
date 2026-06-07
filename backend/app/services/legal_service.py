"""Textos legales y comprobación de aceptaciones."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.models.legal import LegalAcceptance, LegalDocument, LegalToken
from app.models.models import Employee
from app.models.tenant import Tenant
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


def create_whatsapp_token(
    session: Session,
    *,
    employee_id: UUID,
    tenant_id: UUID,
) -> LegalToken:
    """Crea un token de 5 minutos para que el empleado acepte legales vía WhatsApp."""
    token = LegalToken(
        employee_id=employee_id,
        tenant_id=tenant_id,
        expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=5),
    )
    session.add(token)
    session.flush()
    return token


def validate_token(
    session: Session,
    raw_token: str,
) -> tuple[LegalToken, Employee, Tenant]:
    """Valida el token y devuelve (token, employee, tenant). Lanza ValueError si no es válido."""
    token = session.exec(
        select(LegalToken).where(LegalToken.token == raw_token)
    ).first()
    if not token:
        raise ValueError("Token no encontrado")
    if token.used_at is not None:
        raise ValueError("Token ya utilizado")
    now = datetime.now(tz=timezone.utc)
    expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)
    if now > expires:
        raise ValueError("Token expirado")
    employee = session.get(Employee, token.employee_id)
    if not employee:
        raise ValueError("Empleado no encontrado")
    tenant = session.get(Tenant, token.tenant_id)
    if not tenant:
        raise ValueError("Tenant no encontrado")
    return token, employee, tenant


def accept_document_with_pdf(
    session: Session,
    *,
    employee_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
    channel: str = "web",
) -> LegalAcceptance:
    """Acepta un documento legal. El PDF combinado se genera aparte con generate_acceptance_certificate."""
    return accept_document(
        session, employee_id=employee_id, document_id=document_id, tenant_id=tenant_id, channel=channel
    )


def generate_acceptance_certificate(
    session: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
) -> "DocumentDelivery | None":
    """Genera UN PDF con todos los documentos legales aceptados por el empleado.

    Solo genera el PDF si todos los documentos requeridos están aceptados.
    Devuelve el DocumentDelivery creado o None si no procede.
    """
    items, all_ok = employee_legal_status(session, tenant_id, employee_id)
    if not all_ok:
        return None

    employee = session.get(Employee, employee_id)
    tenant = session.get(Tenant, tenant_id)
    if not employee or not tenant:
        return None

    # Recoger los datos de aceptación de cada documento requerido
    acceptances = {
        a.legal_document_id: a
        for a in session.exec(
            select(LegalAcceptance).where(LegalAcceptance.employee_id == employee_id)
        ).all()
    }
    docs_data = []
    for item in items:
        if not item.is_required:
            continue
        acc = acceptances.get(item.document_id)
        if acc is None:
            continue
        from app.services.legal_pdf_service import AcceptedDocData
        docs_data.append(AcceptedDocData(
            title=item.title,
            body=item.body,
            version=item.version,
            accepted_at=acc.accepted_at,
            channel=acc.channel,
        ))

    if not docs_data:
        return None

    try:
        from app.services.legal_pdf_service import store_combined_acceptance_pdf
        delivery = store_combined_acceptance_pdf(
            session,
            tenant_id=tenant_id,
            employee_id=employee_id,
            tenant_name=tenant.name,
            employee_name=employee.full_name,
            docs=docs_data,
        )
        return delivery
    except Exception:
        return None


def accept_document(
    session: Session,
    employee_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
    channel: str = "web",
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
        existing.channel = channel
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = LegalAcceptance(
        employee_id=employee_id,
        legal_document_id=document_id,
        document_version=doc.version,
        channel=channel,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.documents import DocumentDelivery
