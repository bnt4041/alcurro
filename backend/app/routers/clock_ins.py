from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.models import ClockIn, ClockInType, Employee
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import ClockInCreate, ClockInRead
from app.services.scope_service import read_scope_employee_ids, resolve_write_employee_id

router = APIRouter(prefix="/clock-ins", tags=["clock-ins"])


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


@router.get("", response_model=list[ClockInRead])
def list_clock_ins(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    employee_id: UUID | None = None,
    record_type: ClockInType | None = None,
    q: str | None = None,
    limit: int = 200,
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[ClockIn]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = (
        select(ClockIn)
        .where(ClockIn.employee_id.in_(ids))  # type: ignore[attr-defined]
        .order_by(ClockIn.recorded_at.desc())  # type: ignore[attr-defined]
    )
    if employee_id:
        if employee_id not in ids:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        stmt = stmt.where(ClockIn.employee_id == employee_id)
    if record_type:
        stmt = stmt.where(ClockIn.record_type == record_type)
    if q and q.strip():
        employees = {
            e.id: e
            for e in session.exec(
                select(Employee).where(Employee.id.in_(ids))  # type: ignore[attr-defined]
            ).all()
        }
        emp_ids = [
            eid
            for eid, e in employees.items()
            if q.lower() in e.full_name.lower()
            or q.lower() in e.employee_code.lower()
        ]
        if not emp_ids:
            return []
        stmt = stmt.where(ClockIn.employee_id.in_(emp_ids))  # type: ignore[attr-defined]
    return list(session.exec(stmt.limit(limit)).all())


@router.get("/{clock_in_id}", response_model=ClockInRead)
def get_clock_in(
    clock_in_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> ClockIn:
    row = get_or_404(session, ClockIn, clock_in_id)
    if row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Fichaje no encontrado")
    return row


@router.post("", response_model=ClockInRead, status_code=201)
def create_clock_in(
    data: ClockInCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "create")),
) -> ClockIn:
    target = resolve_write_employee_id(
        session, user, ctx, "clock_ins", data.employee_id, "create"
    )
    row = ClockIn.model_validate(
        {**data.model_dump(), "employee_id": target, "source": data.source or "panel"}
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
