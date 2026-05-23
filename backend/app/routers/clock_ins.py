from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.permissions import Permission, require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.models import ClockIn, ClockInType, Employee
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import ClockInCreate, ClockInRead

router = APIRouter(prefix="/clock-ins", tags=["clock-ins"])


@router.get("", response_model=list[ClockInRead])
def list_clock_ins(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    employee_id: UUID | None = None,
    record_type: ClockInType | None = None,
    q: str | None = None,
    limit: int = 200,
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[ClockIn]:
    emp_ids = [
        e.id
        for e in session.exec(
            select(Employee).where(Employee.company_id == ctx.company.id)
        ).all()
    ]
    stmt = select(ClockIn).order_by(ClockIn.recorded_at.desc())  # type: ignore[attr-defined]
    if emp_ids:
        stmt = stmt.where(ClockIn.employee_id.in_(emp_ids))  # type: ignore[attr-defined]
    else:
        return []
    if employee_id:
        stmt = stmt.where(ClockIn.employee_id == employee_id)
    if record_type:
        stmt = stmt.where(ClockIn.record_type == record_type)
    if q and q.strip():
        emp_ids = [
            e.id
            for e in session.exec(select(Employee)).all()
            if q.lower() in e.full_name.lower()
            or q.lower() in e.employee_code.lower()
        ]
        if emp_ids:
            stmt = stmt.where(ClockIn.employee_id.in_(emp_ids))  # type: ignore[attr-defined]
        else:
            return []
    return list(session.exec(stmt.limit(limit)).all())


@router.get("/{clock_in_id}", response_model=ClockInRead)
def get_clock_in(
    clock_in_id: UUID,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> ClockIn:
    return get_or_404(session, ClockIn, clock_in_id)


@router.post("", response_model=ClockInRead, status_code=201)
def create_clock_in(
    data: ClockInCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "clock_ins")),
) -> ClockIn:
    emp = session.get(Employee, data.employee_id)
    if not emp or emp.company_id != ctx.company.id:
        raise HTTPException(status_code=400, detail="Empleado no existe")
    row = ClockIn.model_validate(data)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
