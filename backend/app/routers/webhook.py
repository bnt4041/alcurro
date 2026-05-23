from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.models import Employee
from app.models.tenant import Company, Tenant
from app.schemas.whatsapp import GoWAWebhookPayload
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["webhook"])


def _resolve_employee_and_tenant(
    session: Session, phone: str
) -> tuple[Employee, Tenant] | None:
    """Un único WhatsApp: el tenant se deduce por el teléfono del empleado."""
    normalized = "".join(c for c in phone if c.isdigit())
    if len(normalized) < 9:
        return None

    employees = session.exec(
        select(Employee).where(Employee.is_active == True)  # noqa: E712
    ).all()
    for emp in employees:
        emp_digits = "".join(c for c in emp.phone if c.isdigit())
        if emp_digits.endswith(normalized[-9:]) or normalized.endswith(
            emp_digits[-9:]
        ):
            company = session.get(Company, emp.company_id)
            if not company:
                continue
            tenant = session.get(Tenant, company.tenant_id)
            if tenant and tenant.is_active:
                return emp, tenant
    return None


async def _process_global(
    session: Session, payload: GoWAWebhookPayload
) -> dict[str, Any]:
    phone = payload.resolve_phone()
    if not phone:
        return {"ok": False, "error": "Teléfono no identificado en el webhook"}

    resolved = _resolve_employee_and_tenant(session, phone)
    if not resolved:
        return {"ok": True, "action": "unknown_employee"}

    _employee, tenant = resolved
    service = WebhookService(session, tenant_id=tenant.id)
    return await service.process(payload)


@router.post("/webhook/whatsapp/{tenant_slug}")
async def whatsapp_webhook_tenant(
    tenant_slug: str,
    payload: GoWAWebhookPayload,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Compatibilidad: redirige al webhook global (un solo WhatsApp)."""
    del tenant_slug
    try:
        return await _process_global(session, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook: {exc}",
        ) from exc


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    payload: GoWAWebhookPayload,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return await _process_global(session, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook: {exc}",
        ) from exc
