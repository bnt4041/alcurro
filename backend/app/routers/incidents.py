from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.incident import Incident
from app.models.models import Employee
from app.routers.crud_helpers import get_or_404
from app.schemas.incident import (
    IncidentApplyClock,
    IncidentApplyLeave,
    IncidentAutoRuleRead,
    IncidentAutoRuleUpdate,
    IncidentCreate,
    IncidentRead,
    IncidentUpdate,
)
from app.services.incident_service import (
    apply_clock_correction,
    apply_leave_correction,
    create_incident,
    get_or_create_rules,
    incident_to_read,
    original_data_for_links,
    rules_to_read,
    update_rules,
)
from app.services.scope_service import read_scope_employee_ids

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _scope_ids(ctx: OrgContext, session: Session, user: Employee) -> list[UUID]:
    return read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "clock_ins",
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    status: str | None = None,
    employee_id: UUID | None = None,
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[IncidentRead]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = select(Incident).where(
        Incident.tenant_id == ctx.tenant.id,
        Incident.employee_id.in_(ids),  # type: ignore[attr-defined]
    )
    if status:
        stmt = stmt.where(Incident.status == status)
    if employee_id:
        if employee_id not in ids:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        stmt = stmt.where(Incident.employee_id == employee_id)
    rows = list(
        session.exec(stmt.order_by(Incident.created_at.desc())).all()  # type: ignore[attr-defined]
    )
    return [incident_to_read(session, r, include_url=True) for r in rows]


@router.get("/rules", response_model=IncidentAutoRuleRead)
def get_incident_rules(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentAutoRuleRead:
    return rules_to_read(get_or_create_rules(session, ctx.tenant.id))


@router.put("/rules", response_model=IncidentAutoRuleRead)
def put_incident_rules(
    data: IncidentAutoRuleUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentAutoRuleRead:
    row = update_rules(session, ctx.tenant.id, data)
    session.commit()
    return row


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id or row.employee_id not in _scope_ids(
        ctx, session, user
    ):
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incident_to_read(session, row, include_url=True)


@router.post("", response_model=IncidentRead, status_code=201)
def create_incident_route(
    data: IncidentCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    ids = _scope_ids(ctx, session, user)
    if data.employee_id not in ids:
        raise HTTPException(status_code=400, detail="Empleado no válido")
    try:
        original = original_data_for_links(
            session,
            employee_id=data.employee_id,
            clock_in_id=data.clock_in_id,
            leave_request_id=data.leave_request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = create_incident(
        session,
        tenant_id=ctx.tenant.id,
        employee_id=data.employee_id,
        category=data.category,
        incident_type=data.incident_type,
        title=data.title.strip(),
        description=data.description,
        source="manual",
        clock_in_id=data.clock_in_id,
        leave_request_id=data.leave_request_id,
        original_data=original,
        require_justification=data.require_justification,
        notify_whatsapp=data.notify_whatsapp and data.require_justification,
    )
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident_route(
    incident_id: UUID,
    data: IncidentUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.post("/{incident_id}/apply-clock", response_model=IncidentRead)
def apply_clock(
    incident_id: UUID,
    data: IncidentApplyClock,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    try:
        apply_clock_correction(session, row, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.post("/{incident_id}/apply-leave", response_model=IncidentRead)
def apply_leave(
    incident_id: UUID,
    data: IncidentApplyLeave,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    try:
        apply_leave_correction(session, row, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)
