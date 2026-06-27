from datetime import date
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.models import Employee
from app.models.organization import Department, WorkCenter
from app.models.tenant import Company
from app.services.clock_journal_pdf_service import (
    JournalEmployeeMeta,
    generate_journal_pdf,
)
from app.services.reports_service import (
    DayReportRow,
    EmployeeSummaryRow,
    build_chronological_report,
    build_summary_report,
)
from app.services.scope_service import read_scope_employee_ids

router = APIRouter(prefix="/reports", tags=["reports"])


def _scope_ids(ctx: OrgContext, session: Session, user: Employee) -> list[UUID]:
    return read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "clock_ins",
        company_id=ctx.scope_company_id(),
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


def _apply_filters(
    session: Session,
    ids: list[UUID],
    *,
    employee_ids: list[UUID],
    supervisor_ids: list[UUID],
    company_ids: list[UUID],
    work_center_ids: list[UUID],
    department_ids: list[UUID],
) -> list[UUID]:
    if employee_ids:
        emp_set = set(employee_ids)
        return [i for i in ids if i in emp_set]

    if not any([supervisor_ids, company_ids, work_center_ids, department_ids]):
        return ids

    employees = session.exec(
        select(Employee).where(Employee.id.in_(ids))  # type: ignore[attr-defined]
    ).all()

    if supervisor_ids:
        sup_set = set(supervisor_ids)
        employees = [e for e in employees if e.supervisor_id in sup_set]
    if company_ids:
        co_set = set(company_ids)
        employees = [e for e in employees if e.company_id in co_set]
    if department_ids:
        dept_set = set(department_ids)
        employees = [e for e in employees if e.department_id in dept_set]
    if work_center_ids:
        wc_dept_ids = {
            r.id
            for r in session.exec(
                select(Department).where(Department.work_center_id.in_(work_center_ids))  # type: ignore[attr-defined]
            ).all()
        }
        employees = [e for e in employees if e.department_id in wc_dept_ids]

    return [e.id for e in employees]


# ── Filter options ─────────────────────────────────────────────────────────────

class FilterOption(BaseModel):
    id: str
    name: str


class ReportFilterOptions(BaseModel):
    companies: list[FilterOption]
    work_centers: list[FilterOption]
    departments: list[FilterOption]
    supervisors: list[FilterOption]
    employees: list[FilterOption]


@router.get("/filter-options", response_model=ReportFilterOptions)
def report_filter_options(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> ReportFilterOptions:
    ids = _scope_ids(ctx, session, user)
    emp_list = session.exec(
        select(Employee).where(
            Employee.id.in_(ids),  # type: ignore[attr-defined]
            Employee.is_active == True,  # noqa: E712
        )
    ).all()

    company_ids = {e.company_id for e in emp_list}
    companies = [
        FilterOption(id=str(c.id), name=c.name)
        for c in session.exec(
            select(Company).where(Company.id.in_(company_ids))  # type: ignore[attr-defined]
        ).all()
    ]

    dept_ids = {e.department_id for e in emp_list if e.department_id}
    departments = [
        FilterOption(id=str(d.id), name=d.name)
        for d in session.exec(
            select(Department).where(Department.id.in_(dept_ids))  # type: ignore[attr-defined]
        ).all()
    ]

    wc_ids = {
        d.work_center_id
        for d in session.exec(
            select(Department).where(Department.id.in_(dept_ids))  # type: ignore[attr-defined]
        ).all()
        if d.work_center_id
    }
    work_centers = [
        FilterOption(id=str(wc.id), name=wc.name)
        for wc in session.exec(
            select(WorkCenter).where(WorkCenter.id.in_(wc_ids))  # type: ignore[attr-defined]
        ).all()
    ]

    supervisor_ids = {e.supervisor_id for e in emp_list if e.supervisor_id}
    supervisors = [
        FilterOption(id=str(sup.id), name=sup.full_name)
        for sup in session.exec(
            select(Employee).where(Employee.id.in_(supervisor_ids))  # type: ignore[attr-defined]
        ).all()
    ]

    employees = [
        FilterOption(id=str(e.id), name=e.full_name)
        for e in sorted(emp_list, key=lambda x: x.full_name)
    ]

    return ReportFilterOptions(
        companies=sorted(companies, key=lambda x: x.name),
        work_centers=sorted(work_centers, key=lambda x: x.name),
        departments=sorted(departments, key=lambda x: x.name),
        supervisors=sorted(supervisors, key=lambda x: x.name),
        employees=employees,
    )


# ── Report endpoints ───────────────────────────────────────────────────────────

@router.get("/chronological", response_model=list[DayReportRow])
def chronological_report(
    date_from: date,
    date_to: date,
    employee_ids: list[UUID] = Query(default=[]),
    supervisor_ids: list[UUID] = Query(default=[]),
    company_ids: list[UUID] = Query(default=[]),
    work_center_ids: list[UUID] = Query(default=[]),
    department_ids: list[UUID] = Query(default=[]),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[DayReportRow]:
    ids = _scope_ids(ctx, session, user)
    ids = _apply_filters(
        session, ids,
        employee_ids=employee_ids,
        supervisor_ids=supervisor_ids,
        company_ids=company_ids,
        work_center_ids=work_center_ids,
        department_ids=department_ids,
    )
    return build_chronological_report(session, ids, date_from, date_to)


@router.get("/summary", response_model=list[EmployeeSummaryRow])
def summary_report(
    date_from: date,
    date_to: date,
    employee_ids: list[UUID] = Query(default=[]),
    supervisor_ids: list[UUID] = Query(default=[]),
    company_ids: list[UUID] = Query(default=[]),
    work_center_ids: list[UUID] = Query(default=[]),
    department_ids: list[UUID] = Query(default=[]),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[EmployeeSummaryRow]:
    ids = _scope_ids(ctx, session, user)
    ids = _apply_filters(
        session, ids,
        employee_ids=employee_ids,
        supervisor_ids=supervisor_ids,
        company_ids=company_ids,
        work_center_ids=work_center_ids,
        department_ids=department_ids,
    )
    return build_summary_report(session, ids, date_from, date_to)


def _build_employee_meta(
    session: Session, employee_ids: list[UUID]
) -> dict[str, JournalEmployeeMeta]:
    """Resuelve nombre, DNI, empresa y centro/departamento por empleado."""
    if not employee_ids:
        return {}

    employees = session.exec(
        select(Employee).where(Employee.id.in_(employee_ids))  # type: ignore[attr-defined]
    ).all()

    company_ids = {e.company_id for e in employees}
    companies = {
        c.id: c
        for c in session.exec(
            select(Company).where(Company.id.in_(company_ids))  # type: ignore[attr-defined]
        ).all()
    }

    dept_ids = {e.department_id for e in employees if e.department_id}
    departments = {
        d.id: d
        for d in session.exec(
            select(Department).where(Department.id.in_(dept_ids))  # type: ignore[attr-defined]
        ).all()
    }
    wc_ids = {d.work_center_id for d in departments.values() if d.work_center_id}
    wc_names = {
        wc.id: wc.name
        for wc in session.exec(
            select(WorkCenter).where(WorkCenter.id.in_(wc_ids))  # type: ignore[attr-defined]
        ).all()
    }

    meta: dict[str, JournalEmployeeMeta] = {}
    for e in employees:
        dept = departments.get(e.department_id) if e.department_id else None
        parts = []
        if dept and dept.work_center_id:
            wc = wc_names.get(dept.work_center_id)
            if wc:
                parts.append(wc)
        if dept:
            parts.append(dept.name)
        company = companies.get(e.company_id)
        meta[str(e.id)] = JournalEmployeeMeta(
            full_name=e.full_name,
            id_document=e.id_document,
            company_name=company.name if company else "—",
            company_cif=company.tax_id if company else None,
            center_dept=" · ".join(parts) if parts else "—",
        )
    return meta


@router.get("/journal-pdf")
def journal_pdf_report(
    date_from: date,
    date_to: date,
    employee_ids: list[UUID] = Query(default=[]),
    supervisor_ids: list[UUID] = Query(default=[]),
    company_ids: list[UUID] = Query(default=[]),
    work_center_ids: list[UUID] = Query(default=[]),
    department_ids: list[UUID] = Query(default=[]),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> StreamingResponse:
    """Registro Diario de Jornada (RD-ley 8/2019) en PDF, un bloque por trabajador y mes."""
    ids = _scope_ids(ctx, session, user)
    ids = _apply_filters(
        session, ids,
        employee_ids=employee_ids,
        supervisor_ids=supervisor_ids,
        company_ids=company_ids,
        work_center_ids=work_center_ids,
        department_ids=department_ids,
    )
    rows = build_chronological_report(session, ids, date_from, date_to)
    emp_meta = _build_employee_meta(session, ids)
    branding_color = getattr(ctx.tenant, "primary_color", None)

    pdf_bytes = generate_journal_pdf(
        rows=rows,
        emp_meta=emp_meta,
        date_from=date_from,
        date_to=date_to,
        branding_color=branding_color,
    )
    filename = f"registro-jornada_{date_from.isoformat()}_{date_to.isoformat()}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
