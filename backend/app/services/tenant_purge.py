"""Purga selectiva de datos por tenant desde el panel de administración.

Categorías:
- clock_ins      → fichajes
- work_breaks    → paradas / descansos
- leave_requests → vacaciones y permisos
- incidents      → incidencias
- employees      → usuarios (empleados + datos asociados)
- accounts       → cuentas (tenant completo)
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, col, delete, select

from app.models.ai import AiWhatsappMessage, AiUsageRecord
from app.models.billing import BillingMethod, LemonSqueezyPayment, StripePayment, Subscription
from app.models.invoice import Invoice
from app.models.clock_settings import (
    ClockSettings,
    EmployeeInboundDocument,
    InboundPendingUpload,
)
from app.models.developer import ApiKey, WebhookDelivery, WebhookEndpoint
from app.models.documents import (
    DocumentDelivery,
    DocumentDeliveryTag,
    DocumentExpiryNotificationLog,
    DocumentNotificationSettings,
    DocumentTag,
    DocumentType,
)
from app.models.incident import Incident, IncidentAutoRule
from app.models.legal import LegalAcceptance, LegalDocument, LegalToken
from app.models.mail import MailLog
from app.models.models import (
    ClockIn,
    Employee,
    EmployeeLeaveBalance,
    LeaveRequest,
    LeaveType,
    ShiftAssignment,
    ShiftConfiguration,
    WorkBreak,
)
from app.models.notification import Notification
from app.models.organization import Department, WorkCenter
from app.models.project import ClockPendingFichaje, Project
from app.models.rbac import EmployeeGroup, UserGroup
from app.models.signature import (
    SignatureEnvelope,
    SignatureEvent,
    SignatureOtp,
    SignatureSigner,
)
from app.models.tenant import Company, Tenant


def _company_ids(session: Session, tenant_id: UUID) -> list[UUID]:
    return list(
        session.exec(
            select(Company.id).where(Company.tenant_id == tenant_id)
        ).all()
    )


def purge_clock_ins(session: Session, tenant_id: UUID) -> int:
    """Elimina todos los fichajes de un tenant."""
    company_ids = _company_ids(session, tenant_id)
    if not company_ids:
        return 0
    emp_subquery = select(Employee.id).where(col(Employee.company_id).in_(company_ids))
    result = session.exec(
        delete(ClockIn).where(col(ClockIn.employee_id).in_(emp_subquery))
    )
    session.flush()
    return result.rowcount


def purge_work_breaks(session: Session, tenant_id: UUID) -> int:
    """Elimina todas las paradas / descansos de un tenant."""
    company_ids = _company_ids(session, tenant_id)
    if not company_ids:
        return 0
    emp_subquery = select(Employee.id).where(col(Employee.company_id).in_(company_ids))
    result = session.exec(
        delete(WorkBreak).where(col(WorkBreak.employee_id).in_(emp_subquery))
    )
    session.flush()
    return result.rowcount


def purge_leave_requests(session: Session, tenant_id: UUID) -> int:
    """Elimina todas las solicitudes de vacaciones / permisos de un tenant."""
    company_ids = _company_ids(session, tenant_id)
    if not company_ids:
        return 0
    emp_subquery = select(Employee.id).where(col(Employee.company_id).in_(company_ids))
    result = session.exec(
        delete(LeaveRequest).where(col(LeaveRequest.employee_id).in_(emp_subquery))
    )
    session.flush()
    return result.rowcount


def purge_incidents(session: Session, tenant_id: UUID) -> int:
    """Elimina todas las incidencias de un tenant."""
    result = session.exec(
        delete(Incident).where(Incident.tenant_id == tenant_id)
    )
    session.exec(
        delete(IncidentAutoRule).where(IncidentAutoRule.tenant_id == tenant_id)
    )
    session.flush()
    return result.rowcount


def purge_employees(session: Session, tenant_id: UUID) -> int:
    """Elimina todos los empleados y datos asociados de un tenant."""
    company_ids = _company_ids(session, tenant_id)
    if not company_ids:
        return 0
    emp_subquery = select(Employee.id).where(col(Employee.company_id).in_(company_ids))

    # Datos dependientes de empleados
    session.exec(delete(ClockPendingFichaje).where(
        col(ClockPendingFichaje.employee_id).in_(emp_subquery)
    ))
    session.exec(delete(AiWhatsappMessage).where(
        col(AiWhatsappMessage.employee_id).in_(emp_subquery)
    ))
    session.exec(delete(EmployeeInboundDocument).where(
        col(EmployeeInboundDocument.employee_id).in_(emp_subquery)
    ))
    session.exec(delete(InboundPendingUpload).where(
        col(InboundPendingUpload.employee_id).in_(emp_subquery)
    ))
    session.exec(delete(EmployeeGroup).where(
        col(EmployeeGroup.employee_id).in_(emp_subquery)
    ))
    session.exec(delete(LegalAcceptance).where(
        col(LegalAcceptance.employee_id).in_(emp_subquery)
    ))

    # Empleados
    result = session.exec(
        delete(Employee).where(col(Employee.company_id).in_(company_ids))
    )
    session.flush()
    return result.rowcount


def purge_accounts(session: Session, tenant_id: UUID) -> None:
    """Elimina por completo un tenant y todos sus datos asociados.

    ATENCIÓN: Operación irreversible. Elimina cuenta, empresas, centros,
    departamentos, facturación, grupos, documentos, firmas, etc.
    """
    company_ids = _company_ids(session, tenant_id)

    if company_ids:
        # 1. Datos de empleados (primero hijos, luego empleados)
        emp_subquery = select(Employee.id).where(
            col(Employee.company_id).in_(company_ids)
        )

        session.exec(delete(ClockPendingFichaje).where(
            col(ClockPendingFichaje.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(WorkBreak).where(
            col(WorkBreak.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(ClockIn).where(
            col(ClockIn.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(LeaveRequest).where(
            col(LeaveRequest.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(Incident).where(Incident.tenant_id == tenant_id))
        session.exec(delete(IncidentAutoRule).where(IncidentAutoRule.tenant_id == tenant_id))

        session.exec(delete(EmployeeGroup).where(
            col(EmployeeGroup.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(LegalAcceptance).where(
            col(LegalAcceptance.employee_id).in_(emp_subquery)
        ))

        # Documentos
        doc_ids = session.exec(
            select(DocumentDelivery.id).where(
                col(DocumentDelivery.tenant_id) == tenant_id
            )
        ).all()
        if doc_ids:
            session.exec(
                delete(DocumentDeliveryTag).where(
                    col(DocumentDeliveryTag.document_delivery_id).in_(doc_ids)
                )
            )
        session.exec(delete(DocumentDelivery).where(
            col(DocumentDelivery.tenant_id) == tenant_id
        ))
        session.exec(delete(DocumentTag).where(
            col(DocumentTag.tenant_id) == tenant_id
        ))
        session.exec(delete(DocumentType).where(
            col(DocumentType.tenant_id) == tenant_id
        ))
        session.exec(delete(DocumentNotificationSettings).where(
            DocumentNotificationSettings.tenant_id == tenant_id
        ))

        # Firmas
        envelope_ids = session.exec(
            select(SignatureEnvelope.id).where(
                SignatureEnvelope.tenant_id == tenant_id
            )
        ).all()
        if envelope_ids:
            signer_ids = session.exec(
                select(SignatureSigner.id).where(
                    col(SignatureSigner.envelope_id).in_(envelope_ids)
                )
            ).all()
            if signer_ids:
                session.exec(
                    delete(SignatureOtp).where(
                        col(SignatureOtp.signer_id).in_(signer_ids)
                    )
                )
            session.exec(
                delete(SignatureEvent).where(
                    col(SignatureEvent.envelope_id).in_(envelope_ids)
                )
            )
            session.exec(
                delete(SignatureSigner).where(
                    col(SignatureSigner.envelope_id).in_(envelope_ids)
                )
            )
        session.exec(delete(SignatureEnvelope).where(
            SignatureEnvelope.tenant_id == tenant_id
        ))

        session.exec(delete(ShiftAssignment).where(
            col(ShiftAssignment.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(AiWhatsappMessage).where(
            col(AiWhatsappMessage.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(AiWhatsappMessage).where(
            AiWhatsappMessage.tenant_id == tenant_id
        ))
        session.exec(delete(AiUsageRecord).where(
            AiUsageRecord.tenant_id == tenant_id
        ))

        session.exec(delete(EmployeeInboundDocument).where(
            col(EmployeeInboundDocument.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(InboundPendingUpload).where(
            col(InboundPendingUpload.employee_id).in_(emp_subquery)
        ))
        session.exec(delete(EmployeeLeaveBalance).where(
            col(EmployeeLeaveBalance.employee_id).in_(emp_subquery)
        ))

        session.exec(delete(Employee).where(
            col(Employee.company_id).in_(company_ids)
        ))

        session.exec(delete(LeaveType).where(LeaveType.tenant_id == tenant_id))

        # 2. Jerarquía organizativa
        for cid in company_ids:
            wc_ids = session.exec(
                select(WorkCenter.id).where(WorkCenter.company_id == cid)
            ).all()
            if wc_ids:
                session.exec(
                    delete(Department).where(
                        col(Department.work_center_id).in_(wc_ids)
                    )
                )
            session.exec(delete(WorkCenter).where(WorkCenter.company_id == cid))

            session.exec(delete(ShiftConfiguration).where(
                ShiftConfiguration.company_id == cid
            ))
            session.exec(delete(Project).where(Project.company_id == cid))

    # 3. Facturación y pagos (antes de companies por FK subscriptions.company_id)
    session.exec(delete(Invoice).where(Invoice.tenant_id == tenant_id))
    session.exec(delete(LemonSqueezyPayment).where(LemonSqueezyPayment.tenant_id == tenant_id))
    session.exec(delete(StripePayment).where(StripePayment.tenant_id == tenant_id))
    session.exec(delete(Subscription).where(Subscription.tenant_id == tenant_id))
    session.exec(delete(BillingMethod).where(BillingMethod.tenant_id == tenant_id))

    if company_ids:
        # 4. Empresas (después de borrar suscripciones)
        # Primero anular billing_company_id del tenant para evitar FK tenants→companies
        tenant_row = session.get(Tenant, tenant_id)
        if tenant_row and tenant_row.billing_company_id:
            tenant_row.billing_company_id = None
            session.add(tenant_row)
            session.flush()
        for cid in company_ids:
            company = session.get(Company, cid)
            if company:
                session.delete(company)
        session.flush()

    # 5. Grupos y RBAC del tenant
    session.exec(delete(UserGroup).where(UserGroup.tenant_id == tenant_id))

    # 6. Configuraciones de clock del tenant
    session.exec(delete(ClockSettings).where(ClockSettings.tenant_id == tenant_id))

    # 7. Documentos legales y tokens
    session.exec(delete(LegalDocument).where(LegalDocument.tenant_id == tenant_id))
    session.exec(delete(LegalToken).where(LegalToken.tenant_id == tenant_id))

    # 8. Correo y notificaciones
    session.exec(delete(MailLog).where(MailLog.tenant_id == tenant_id))
    session.exec(delete(Notification).where(Notification.tenant_id == tenant_id))
    session.exec(delete(DocumentExpiryNotificationLog).where(
        DocumentExpiryNotificationLog.tenant_id == tenant_id
    ))

    # 9. API keys y webhooks
    webhook_ids = list(session.exec(
        select(WebhookEndpoint.id).where(WebhookEndpoint.tenant_id == tenant_id)
    ).all())
    if webhook_ids:
        session.exec(delete(WebhookDelivery).where(
            col(WebhookDelivery.webhook_id).in_(webhook_ids)
        ))
    session.exec(delete(WebhookEndpoint).where(WebhookEndpoint.tenant_id == tenant_id))
    session.exec(delete(ApiKey).where(ApiKey.tenant_id == tenant_id))

    # 10. Tenant
    tenant = session.get(Tenant, tenant_id)
    if tenant:
        session.delete(tenant)

    session.flush()


PURGE_CATEGORIES = {
    "clock_ins": "Fichajes",
    "work_breaks": "Paradas / descansos",
    "leave_requests": "Vacaciones y permisos",
    "incidents": "Incidencias",
    "employees": "Usuarios (empleados)",
    "accounts": "Cuentas (eliminación total)",
}

PURGE_ORDER = [
    "work_breaks",
    "clock_ins",
    "leave_requests",
    "incidents",
    "employees",
    "accounts",
]


def purge_tenant_data(
    session: Session,
    tenant_id: UUID,
    categories: list[str],
) -> dict[str, int]:
    """Purga las categorías indicadas para un tenant.

    Si se incluye 'accounts', ignora el resto y ejecuta borrado total.
    Si se incluye 'employees', primero purga clock_ins, work_breaks,
    leave_requests e incidents para evitar errores de FK.
    """
    unknown = [c for c in categories if c not in PURGE_CATEGORIES]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Categorías no reconocidas: {', '.join(unknown)}",
        )

    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    results: dict[str, int] = {}

    # Si se pide borrar cuentas, se hace borrado total ignorando el resto
    if "accounts" in categories:
        purge_accounts(session, tenant_id)
        results["accounts"] = 1
        return results

    # Si se pide borrar empleados, se borran automáticamente
    # los datos dependientes (fichajes, paradas, etc.)
    if "employees" in categories:
        # Asegurar que los datos dependientes se borran primero
        for dep in ["clock_ins", "work_breaks", "leave_requests", "incidents"]:
            if dep not in categories:
                categories = [dep] + categories

    # Ordenar según PURGE_ORDER para respetar dependencias FK
    ordered = [c for c in PURGE_ORDER if c in categories]

    for cat in ordered:
        if cat == "clock_ins":
            results[cat] = purge_clock_ins(session, tenant_id)
        elif cat == "work_breaks":
            results[cat] = purge_work_breaks(session, tenant_id)
        elif cat == "leave_requests":
            results[cat] = purge_leave_requests(session, tenant_id)
        elif cat == "incidents":
            results[cat] = purge_incidents(session, tenant_id)
        elif cat == "employees":
            results[cat] = purge_employees(session, tenant_id)
        elif cat == "accounts":
            purge_accounts(session, tenant_id)
            results[cat] = 1

    return results
