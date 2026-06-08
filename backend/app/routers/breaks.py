from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.incident import Incident
from app.models.models import BreakType, Employee, WorkBreak
from app.models.tenant import Company
from app.schemas.crud import (
    BreakCompanySummary,
    BreakCreate,
    BreakRead,
    BreakSummaryResponse,
    BreakSummaryRow,
)
from app.services.break_service import BreakService
from app.services.scope_service import read_scope_employee_ids, resolve_write_employee_id


class BreakUpdate(BaseModel):
    recorded_at: datetime | None = None
    record_type: BreakType | None = None
    notes: str | None = None

router = APIRouter(prefix="/breaks", tags=["breaks"])


def _scope_ids(ctx: OrgContext, session: Session, user: Employee) -> list[UUID]:
    return read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "breaks",
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("", response_model=list[BreakRead])
def list_breaks(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    employee_id: UUID | None = None,
    record_type: BreakType | None = None,
    q: str | None = None,
    limit: int = 200,
    _: object = Depends(require_permission(Permission.READ, "breaks")),
) -> list[WorkBreak]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = (
        select(WorkBreak)
        .where(WorkBreak.employee_id.in_(ids))  # type: ignore[attr-defined]
        .order_by(WorkBreak.recorded_at.desc())  # type: ignore[attr-defined]
    )
    if employee_id:
        if employee_id not in ids:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        stmt = stmt.where(WorkBreak.employee_id == employee_id)
    if record_type:
        stmt = stmt.where(WorkBreak.record_type == record_type)
    if q and q.strip():
        emp_ids = [
            eid
            for eid in ids
            if session.get(Employee, eid)
            and (
                q.lower() in (session.get(Employee, eid).full_name or "").lower()
                or q.lower()
                in (session.get(Employee, eid).employee_code or "").lower()
            )
        ]
        if not emp_ids:
            return []
        stmt = stmt.where(WorkBreak.employee_id.in_(emp_ids))  # type: ignore[attr-defined]
    return list(session.exec(stmt.limit(limit)).all())


@router.get("/summary", response_model=BreakSummaryResponse)
def breaks_summary(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    _: object = Depends(require_permission(Permission.READ, "breaks")),
) -> BreakSummaryResponse:
    ids = _scope_ids(ctx, session, user)
    svc = BreakService(session)
    rows_data = svc.summary_for_employees(ids, day_from=from_date, day_to=to_date)
    rows = [BreakSummaryRow.model_validate(r) for r in rows_data]

    companies = {
        c.id: c
        for c in session.exec(
            select(Company).where(Company.tenant_id == ctx.tenant.id)
        ).all()
    }
    by_company_map: dict[UUID, dict] = {}
    for row in rows:
        bucket = by_company_map.setdefault(
            row.company_id,
            {
                "company_id": row.company_id,
                "company_name": (
                    companies[row.company_id].name
                    if row.company_id in companies
                    else "—"
                ),
                "total_minutes": 0,
                "employee_count": 0,
            },
        )
        bucket["total_minutes"] += row.total_minutes
        bucket["employee_count"] += 1

    by_company = [
        BreakCompanySummary(
            company_id=b["company_id"],
            company_name=b["company_name"],
            total_minutes=b["total_minutes"],
            total_hours=round(b["total_minutes"] / 60, 2),
            employee_count=b["employee_count"],
        )
        for b in sorted(by_company_map.values(), key=lambda x: x["company_name"])
    ]

    return BreakSummaryResponse(
        rows=rows,
        by_company=by_company,
        period_from=from_date,
        period_to=to_date,
    )


@router.get("/{break_id}", response_model=BreakRead)
def get_break(
    break_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "breaks")),
) -> WorkBreak:
    row = get_or_404(session, WorkBreak, break_id)
    if row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    return row


@router.post("", response_model=BreakRead, status_code=201)
def create_break(
    data: BreakCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("breaks", "create")),
) -> WorkBreak:
    emp_id = resolve_write_employee_id(
        session, user, ctx, "breaks", data.employee_id, "create"
    )
    row = WorkBreak(
        employee_id=emp_id,
        record_type=data.record_type,
        notes=data.notes,
        source="panel",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{break_id}", response_model=BreakRead)
def update_break(
    break_id: UUID,
    data: BreakUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("breaks", "write")),
) -> WorkBreak:
    row = session.get(WorkBreak, break_id)
    if not row or row.employee_id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    # Auto-cerrar incidencia vinculada si existe
    linked = session.exec(
        select(Incident).where(Incident.break_id == break_id)
    ).first()
    if linked and linked.status != "resolved":
        linked.status = "resolved"
        linked.managed = True
        linked.resolved_at = datetime.utcnow()
        linked.resolved_by_id = user.id
        linked.updated_at = datetime.utcnow()
        session.add(linked)
    session.commit()
    session.refresh(row)
    return row
