from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import cast
from sqlalchemy.types import Date as SADate
from sqlmodel import Session, func, select

from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.documents import DocumentDelivery
from app.models.incident import Incident
from app.models.models import ClockIn, Employee, LeaveRequest, LeaveStatus
from app.models.signature import SignatureSigner, SignerStatus
from app.models.tenant import Company

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DailyCount(BaseModel):
    date: str
    count: int


class RecentClockIn(BaseModel):
    id: str
    employee_name: str
    entrada_at: str
    salida_at: str | None


class RecentLeave(BaseModel):
    id: str
    employee_name: str
    start_date: str
    end_date: str
    days: float


class RecentIncident(BaseModel):
    id: str
    title: str
    employee_name: str
    created_at: str
    managed: bool


class DashboardStats(BaseModel):
    employees: int
    clockins_today: int
    pending_leaves: int
    open_incidents: int
    pending_signatures: int
    documents: int
    clockins_by_day: list[DailyCount]
    recent_clockins: list[RecentClockIn]
    pending_leaves_list: list[RecentLeave]
    recent_incidents: list[RecentIncident]


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> DashboardStats:
    scoped_company_id = ctx.scope_company_id()
    tenant_id = ctx.tenant.id
    today = date.today()
    week_ago = today - timedelta(days=6)
    today_dt = datetime.combine(today, datetime.min.time())

    # Build company filter: single company or all companies in tenant
    if scoped_company_id:
        emp_company_filter = Employee.company_id == scoped_company_id
    else:
        company_ids = [
            c.id for c in session.exec(
                select(Company).where(Company.tenant_id == tenant_id, Company.is_active == True)  # noqa: E712
            ).all()
        ]
        emp_company_filter = Employee.company_id.in_(company_ids)  # type: ignore[attr-defined]

    employees_count = session.scalar(
        select(func.count(Employee.id)).where(
            emp_company_filter,
            Employee.is_active == True,  # noqa: E712
        )
    ) or 0

    clockins_today = session.scalar(
        select(func.count(ClockIn.id))
        .join(Employee, ClockIn.employee_id == Employee.id)
        .where(
            emp_company_filter,
            ClockIn.entrada_at >= today_dt,
        )
    ) or 0

    pending_leaves = session.scalar(
        select(func.count(LeaveRequest.id))
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .where(
            emp_company_filter,
            LeaveRequest.status == LeaveStatus.PENDING,
        )
    ) or 0

    open_incidents = session.scalar(
        select(func.count(Incident.id))
        .join(Employee, Incident.employee_id == Employee.id)
        .where(
            emp_company_filter,
            Incident.managed == False,  # noqa: E712
        )
    ) or 0

    pending_signatures = session.scalar(
        select(func.count(SignatureSigner.id))
        .join(Employee, SignatureSigner.employee_id == Employee.id)
        .where(
            emp_company_filter,
            SignatureSigner.status == SignerStatus.PENDING,
        )
    ) or 0

    documents_count = session.scalar(
        select(func.count(DocumentDelivery.id))
        .join(Employee, DocumentDelivery.employee_id == Employee.id)
        .where(emp_company_filter)
    ) or 0

    # Clock-ins per day last 7 days
    ci_rows = session.execute(
        select(
            cast(ClockIn.entrada_at, SADate).label("day"),
            func.count(ClockIn.id).label("cnt"),
        )
        .join(Employee, ClockIn.employee_id == Employee.id)
        .where(
            emp_company_filter,
            cast(ClockIn.entrada_at, SADate) >= week_ago,
        )
        .group_by(cast(ClockIn.entrada_at, SADate))
        .order_by(cast(ClockIn.entrada_at, SADate))
    ).all()
    day_map = {str(r.day): r.cnt for r in ci_rows}
    clockins_by_day = [
        DailyCount(date=str(week_ago + timedelta(days=i)), count=day_map.get(str(week_ago + timedelta(days=i)), 0))
        for i in range(7)
    ]

    # Recent clock-ins
    recent_ci = session.execute(
        select(ClockIn, Employee)
        .join(Employee, ClockIn.employee_id == Employee.id)
        .where(emp_company_filter)
        .order_by(ClockIn.entrada_at.desc())
        .limit(6)
    ).all()
    recent_clockins = [
        RecentClockIn(
            id=str(ci.id),
            employee_name=emp.full_name,
            entrada_at=ci.entrada_at.isoformat(),
            salida_at=ci.salida_at.isoformat() if ci.salida_at else None,
        )
        for ci, emp in recent_ci
    ]

    # Pending leaves
    pending_lv = session.execute(
        select(LeaveRequest, Employee)
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .where(
            emp_company_filter,
            LeaveRequest.status == LeaveStatus.PENDING,
        )
        .order_by(LeaveRequest.created_at.desc())
        .limit(6)
    ).all()
    pending_leaves_list = [
        RecentLeave(
            id=str(lr.id),
            employee_name=emp.full_name,
            start_date=str(lr.start_date),
            end_date=str(lr.end_date),
            days=lr.days_requested,
        )
        for lr, emp in pending_lv
    ]

    # Recent incidents
    recent_inc = session.execute(
        select(Incident, Employee)
        .join(Employee, Incident.employee_id == Employee.id)
        .where(emp_company_filter)
        .order_by(Incident.created_at.desc())
        .limit(6)
    ).all()
    recent_incidents = [
        RecentIncident(
            id=str(inc.id),
            title=inc.title,
            employee_name=emp.full_name,
            created_at=inc.created_at.isoformat(),
            managed=inc.managed,
        )
        for inc, emp in recent_inc
    ]

    return DashboardStats(
        employees=employees_count,
        clockins_today=clockins_today,
        pending_leaves=pending_leaves,
        open_incidents=open_incidents,
        pending_signatures=pending_signatures,
        documents=documents_count,
        clockins_by_day=clockins_by_day,
        recent_clockins=recent_clockins,
        pending_leaves_list=pending_leaves_list,
        recent_incidents=recent_incidents,
    )
