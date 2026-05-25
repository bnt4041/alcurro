from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models.tenant import Tenant
from app.schemas.incident import PublicIncidentJustify, PublicIncidentMeta
from app.services.incident_service import (
    get_incident_by_token,
    submit_employee_justification,
)

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/incidencia/{token}", response_model=PublicIncidentMeta)
def public_incident_meta(
    token: str,
    session: Session = Depends(get_session),
) -> PublicIncidentMeta:
    row = get_incident_by_token(session, token)
    if not row:
        raise HTTPException(status_code=404, detail="Enlace no válido o caducado")
    emp = row.employee_id
    from app.models.models import Employee

    employee = session.get(Employee, emp)
    tenant = session.get(Tenant, row.tenant_id)
    return PublicIncidentMeta(
        title=row.title,
        description=row.description,
        category=row.category,
        status=row.status,
        employee_name=employee.full_name if employee else "—",
        tenant_name=tenant.name if tenant else "—",
        original_data=row.original_data or {},
        modified_data=row.modified_data,
        can_justify=row.status in ("pending_justification", "open")
        and not row.justified_at,
    )


@router.post("/incidencia/{token}/justify", response_model=dict)
def public_incident_justify(
    token: str,
    data: PublicIncidentJustify,
    session: Session = Depends(get_session),
) -> dict:
    row = submit_employee_justification(session, token, data.justification)
    if not row:
        raise HTTPException(status_code=404, detail="Enlace no válido o caducado")
    session.commit()
    return {"ok": True, "status": row.status}
