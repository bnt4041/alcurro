from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.models import Employee, LeaveRequest, LeaveStatus, LeaveType
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import LeaveRequestCreate, LeaveRequestRead, LeaveRequestUpdate
from app.services.scope_service import (
    assert_employee_target,
    read_scope_employee_ids,
    resolve_write_employee_id,
)

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])


def _enrich(row: LeaveRequest, session: Session) -> dict:
    data = row.model_dump()
    if row.leave_type_id:
        lt = session.get(LeaveType, row.leave_type_id)
        data["leave_type_name"] = lt.name if lt else None
    else:
        data["leave_type_name"] = None
    return data


def _scope_ids(ctx: OrgContext, session: Session, user: Employee) -> list[UUID]:
    return read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "leave",
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("", response_model=list[LeaveRequestRead])
def list_leave_requests(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    employee_id: UUID | None = None,
    status: LeaveStatus | None = None,
    q: str | None = None,
    _: object = Depends(require_permission(Permission.READ, "leave")),
) -> list[LeaveRequestRead]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = (
        select(LeaveRequest)
        .where(LeaveRequest.employee_id.in_(ids))  # type: ignore[attr-defined]
        .order_by(LeaveRequest.created_at.desc())  # type: ignore[attr-defined]
    )
    if employee_id:
        if employee_id not in ids:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    rows = list(session.exec(stmt).all())
    if q and q.strip():
        term = q.lower()
        emp_map = {
            e.id: e
            for e in session.exec(
                select(Employee).where(Employee.id.in_(ids))  # type: ignore[attr-defined]
            ).all()
        }
        rows = [
            r
            for r in rows
            if (emp := emp_map.get(r.employee_id))
            and (term in emp.full_name.lower() or term in emp.employee_code.lower())
        ]
    return [LeaveRequestRead(**_enrich(r, session)) for r in rows]


@router.get("/{request_id}", response_model=LeaveRequestRead)
def get_leave_request(
    request_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "leave")),
) -> LeaveRequestRead:
    row = get_or_404(session, LeaveRequest, request_id)
    if row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return LeaveRequestRead(**_enrich(row, session))


@router.post("", response_model=LeaveRequestRead, status_code=201)
def create_leave_request(
    data: LeaveRequestCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("leave", "create")),
) -> LeaveRequestRead:
    emp_id = resolve_write_employee_id(
        session, user, ctx, "leave", data.employee_id, "create"
    )
    row = LeaveRequest.model_validate({**data.model_dump(), "employee_id": emp_id})
    session.add(row)
    session.commit()
    session.refresh(row)

    employee = session.get(Employee, emp_id)
    if employee:
        lt = session.get(LeaveType, row.leave_type_id) if row.leave_type_id else None
        from app.services.notification_service import notify_leave_request_created
        try:
            notify_leave_request_created(
                session,
                tenant_id=ctx.tenant.id,
                employee=employee,
                start_date=str(row.start_date),
                end_date=str(row.end_date),
                days=row.days_requested,
                leave_type_name=lt.name if lt else None,
                reason=row.reason,
            )
        except Exception:
            pass

    return LeaveRequestRead(**_enrich(row, session))


@router.patch("/{request_id}", response_model=LeaveRequestRead)
def update_leave_request(
    request_id: UUID,
    data: LeaveRequestUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("leave", "update")),
) -> LeaveRequestRead:
    row = get_or_404(session, LeaveRequest, request_id)
    if row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    assert_employee_target(session, user, ctx, "leave", row.employee_id, "update")
    prev_status = row.status
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)

    # Notificar al empleado si cambia el estado a aprobado/rechazado
    new_status = row.status
    if prev_status != new_status and new_status in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
        employee = session.get(Employee, row.employee_id)
        if employee:
            lt = session.get(LeaveType, row.leave_type_id) if row.leave_type_id else None
            from app.services.notification_service import notify_leave_request_reviewed
            try:
                notify_leave_request_reviewed(
                    session,
                    tenant_id=ctx.tenant.id,
                    employee=employee,
                    new_status=new_status.value,
                    start_date=str(row.start_date),
                    end_date=str(row.end_date),
                    days=row.days_requested,
                    leave_type_name=lt.name if lt else None,
                    review_notes=row.review_notes,
                )
            except Exception:
                pass  # Notificación best-effort: no bloquear la respuesta

    return LeaveRequestRead(**_enrich(row, session))


@router.delete("/{request_id}", status_code=204)
def delete_leave_request(
    request_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> None:
    row = get_or_404(session, LeaveRequest, request_id)
    if row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    session.delete(row)
    session.commit()
