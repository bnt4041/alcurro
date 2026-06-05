from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.models import ClockIn, Employee
from app.models.project import Project
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import ClockInCreate, ClockInRead
from app.services.clock_incident_hook import process_clock_in_incidents
from app.services.clock_report_service import EmployeeDayReport, build_employee_day_report
from app.services.clock_settings_service import get_or_create_settings
from app.services.project_service import get_project_for_company
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


def _enrich_reads(session: Session, rows: list[ClockIn]) -> list[ClockInRead]:
    project_names: dict[UUID, str] = {}
    result: list[ClockInRead] = []
    for row in rows:
        data = ClockInRead.model_validate(row)
        if row.project_id:
            if row.project_id not in project_names:
                p = session.get(Project, row.project_id)
                project_names[row.project_id] = p.name if p else "—"
            data.project_name = project_names[row.project_id]
        result.append(data)
    return result


@router.get("", response_model=list[ClockInRead])
def list_clock_ins(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    employee_id: UUID | None = None,
    q: str | None = None,
    limit: int = 200,
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[ClockInRead]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = (
        select(ClockIn)
        .where(ClockIn.employee_id.in_(ids))  # type: ignore[attr-defined]
        .order_by(ClockIn.entrada_at.desc())  # type: ignore[attr-defined]
    )
    if employee_id:
        if employee_id not in ids:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        stmt = stmt.where(ClockIn.employee_id == employee_id)
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
    rows = list(session.exec(stmt.limit(limit)).all())
    return _enrich_reads(session, rows)


@router.get("/reports/day", response_model=EmployeeDayReport)
def employee_day_report(
    employee_id: UUID,
    report_date: date | None = None,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> EmployeeDayReport:
    ids = _scope_ids(ctx, session, user)
    if employee_id not in ids:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return build_employee_day_report(session, employee_id, report_date)


@router.get("/{clock_in_id}", response_model=ClockInRead)
def get_clock_in(
    clock_in_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> ClockInRead:
    row = get_or_404(session, ClockIn, clock_in_id)
    if row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Fichaje no encontrado")
    return _enrich_reads(session, [row])[0]


@router.post("", response_model=ClockInRead, status_code=201)
def create_clock_in(
    data: ClockInCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "create")),
) -> ClockInRead:
    target = resolve_write_employee_id(
        session, user, ctx, "clock_ins", data.employee_id, "create"
    )
    emp = session.get(Employee, target)
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    settings = get_or_create_settings(session, ctx.tenant.id)
    project_id = data.project_id
    if settings.require_project_on_clock_in:
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="Debes seleccionar un proyecto para fichar",
            )
        if not get_project_for_company(session, project_id, emp.company_id):
            raise HTTPException(status_code=400, detail="Proyecto no válido")
    elif project_id and not get_project_for_company(
        session, project_id, emp.company_id
    ):
        raise HTTPException(status_code=400, detail="Proyecto no válido")

    row = ClockIn(
        employee_id=target,
        entrada_at=data.entrada_at,
        salida_at=data.salida_at,
        latitude=data.latitude,
        longitude=data.longitude,
        source=data.source or "panel",
        notes=data.notes,
        work_summary=data.work_summary,
        project_id=project_id,
    )
    session.add(row)
    session.flush()
    process_clock_in_incidents(
        session,
        tenant_id=ctx.tenant.id,
        employee=emp,
        clock=row,
    )
    session.commit()
    session.refresh(row)
    return _enrich_reads(session, [row])[0]
