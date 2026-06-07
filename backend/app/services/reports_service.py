"""Servicio de informes: cronológico y resumen por rango de fechas."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

_SPAIN_TZ = ZoneInfo("Europe/Madrid")


def _to_spain(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_SPAIN_TZ)


def _minutes_between(a: datetime, b: datetime) -> int:
    return max(0, int((b - a).total_seconds() // 60))


def fmt_duration(minutes: int) -> str:
    if minutes == 0:
        return "—"
    h, m = divmod(minutes, 60)
    return f"{h:02d}h {m:02d}m"


from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.models import (
    BreakType,
    ClockIn,
    Employee,
    WorkBreak,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from app.models.incident import Incident
from app.models.project import Project


class BreakPairReport(BaseModel):
    inicio_at: str | None = None
    fin_at: str | None = None
    duration_minutes: int = 0


class ClockEntryReport(BaseModel):
    id: str
    entrada_at: str
    salida_at: str | None = None
    worked_minutes: int = 0
    project_name: str | None = None
    address: str | None = None
    address_out: str | None = None
    source: str = ""
    breaks: list[BreakPairReport] = Field(default_factory=list)
    is_open: bool = False


class LeaveReportRow(BaseModel):
    id: str
    leave_type_name: str | None = None
    status: str
    days_requested: float
    reason: str | None = None


class IncidentReportRow(BaseModel):
    id: str
    incident_type: str
    title: str
    status: str
    minutes_late: int | None = None


class DayReportRow(BaseModel):
    employee_id: str
    employee_name: str
    report_date: str  # YYYY-MM-DD
    weekday: str = ""  # "Lunes"
    clock_entries: list[ClockEntryReport] = Field(default_factory=list)
    leaves: list[LeaveReportRow] = Field(default_factory=list)
    incidents: list[IncidentReportRow] = Field(default_factory=list)
    worked_minutes: int = 0
    break_minutes: int = 0
    net_minutes: int = 0
    has_open_clock: bool = False


class EmployeeSummaryRow(BaseModel):
    employee_id: str
    employee_name: str
    days_worked: int = 0
    total_worked_minutes: int = 0
    total_break_minutes: int = 0
    total_net_minutes: int = 0
    total_leave_days: float = 0.0
    leave_by_type: dict[str, float] = Field(default_factory=dict)
    total_incidents: int = 0
    open_clocks: int = 0


_WEEKDAY_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def build_chronological_report(
    session: Session,
    employee_ids: list[UUID],
    date_from: date,
    date_to: date,
) -> list[DayReportRow]:
    if not employee_ids or date_from > date_to:
        return []

    employees = {
        e.id: e
        for e in session.exec(
            select(Employee).where(Employee.id.in_(employee_ids))  # type: ignore[attr-defined]
        ).all()
    }

    start_dt = datetime.combine(date_from, time.min)
    end_dt = datetime.combine(date_to, time.max)

    # Clock-ins in range
    clocks = session.exec(
        select(ClockIn).where(
            ClockIn.employee_id.in_(employee_ids),  # type: ignore[attr-defined]
            ClockIn.entrada_at >= start_dt,
            ClockIn.entrada_at <= end_dt,
        ).order_by(ClockIn.entrada_at)  # type: ignore[attr-defined]
    ).all()

    clock_ids = [c.id for c in clocks]

    # Breaks grouped by clock_in_id
    breaks_by_clock: dict[UUID, list[WorkBreak]] = {}
    if clock_ids:
        for b in session.exec(
            select(WorkBreak)
            .where(WorkBreak.clock_in_id.in_(clock_ids))  # type: ignore[attr-defined]
            .order_by(WorkBreak.recorded_at)  # type: ignore[attr-defined]
        ).all():
            if b.clock_in_id:
                breaks_by_clock.setdefault(b.clock_in_id, []).append(b)

    # Project names
    project_names: dict[UUID, str] = {}
    project_ids = list({c.project_id for c in clocks if c.project_id})
    if project_ids:
        for p in session.exec(
            select(Project).where(Project.id.in_(project_ids))  # type: ignore[attr-defined]
        ).all():
            project_names[p.id] = p.name

    # Leave requests overlapping range
    leaves = session.exec(
        select(LeaveRequest).where(
            LeaveRequest.employee_id.in_(employee_ids),  # type: ignore[attr-defined]
            LeaveRequest.end_date >= date_from,
            LeaveRequest.start_date <= date_to,
        )
    ).all()
    leave_type_names: dict[UUID, str] = {}
    for lr in leaves:
        if lr.leave_type_id and lr.leave_type_id not in leave_type_names:
            lt = session.get(LeaveType, lr.leave_type_id)
            if lt:
                leave_type_names[lr.leave_type_id] = lt.name

    # Incidents in range
    incidents = session.exec(
        select(Incident).where(
            Incident.employee_id.in_(employee_ids),  # type: ignore[attr-defined]
            Incident.created_at >= start_dt,
            Incident.created_at <= end_dt,
        )
    ).all()

    rows: dict[tuple[UUID, date], DayReportRow] = {}
    today = date.today()

    # Pre-populate every (employee, day) in the range so all days always appear
    cur = date_from
    while cur <= date_to:
        for emp_id in employee_ids:
            emp = employees.get(emp_id)
            rows[(emp_id, cur)] = DayReportRow(
                employee_id=str(emp_id),
                employee_name=emp.full_name if emp else str(emp_id),
                report_date=cur.isoformat(),
                weekday=_WEEKDAY_ES[cur.weekday()],
            )
        cur += timedelta(days=1)

    def get_or_create(emp_id: UUID, d: date) -> DayReportRow:
        key = (emp_id, d)
        if key not in rows:
            emp = employees.get(emp_id)
            rows[key] = DayReportRow(
                employee_id=str(emp_id),
                employee_name=emp.full_name if emp else str(emp_id),
                report_date=d.isoformat(),
                weekday=_WEEKDAY_ES[d.weekday()],
            )
        return rows[key]

    for c in clocks:
        entry_date = _to_spain(c.entrada_at).date()
        row = get_or_create(c.employee_id, entry_date)

        if c.salida_at:
            worked = _minutes_between(c.entrada_at, c.salida_at)
            is_open = False
        else:
            is_open = True
            worked = _minutes_between(c.entrada_at, datetime.utcnow()) if entry_date == today else 0

        # Break pairs for this clock
        clk_breaks = breaks_by_clock.get(c.id, [])
        break_pairs: list[BreakPairReport] = []
        break_total = 0
        pending_start: datetime | None = None
        for b in clk_breaks:
            if b.record_type == BreakType.INICIO:
                pending_start = b.recorded_at
            elif b.record_type == BreakType.FIN and pending_start:
                dur = _minutes_between(pending_start, b.recorded_at)
                break_pairs.append(BreakPairReport(
                    inicio_at=_to_spain(pending_start).strftime("%H:%M"),
                    fin_at=_to_spain(b.recorded_at).strftime("%H:%M"),
                    duration_minutes=dur,
                ))
                break_total += dur
                pending_start = None
        if pending_start:
            dur = _minutes_between(pending_start, datetime.utcnow()) if entry_date == today else 0
            break_pairs.append(BreakPairReport(
                inicio_at=_to_spain(pending_start).strftime("%H:%M"),
                fin_at=None,
                duration_minutes=dur,
            ))
            break_total += dur

        entry = ClockEntryReport(
            id=str(c.id),
            entrada_at=_to_spain(c.entrada_at).strftime("%H:%M"),
            salida_at=_to_spain(c.salida_at).strftime("%H:%M") if c.salida_at else None,
            worked_minutes=worked,
            project_name=project_names.get(c.project_id) if c.project_id else None,
            address=c.address,
            address_out=getattr(c, "address_out", None),
            source=c.source or "",
            breaks=break_pairs,
            is_open=is_open,
        )
        row.clock_entries.append(entry)
        row.worked_minutes += worked
        row.break_minutes += break_total
        row.net_minutes = row.worked_minutes - row.break_minutes
        if is_open:
            row.has_open_clock = True

    # Leave requests — one entry per day in the range
    seen_leave_day: set[tuple[str, date]] = set()
    for lr in leaves:
        lr_from = max(lr.start_date, date_from)
        lr_to = min(lr.end_date, date_to)
        cur = lr_from
        while cur <= lr_to:
            key = (str(lr.id), cur)
            if key not in seen_leave_day:
                seen_leave_day.add(key)
                row = get_or_create(lr.employee_id, cur)
                row.leaves.append(LeaveReportRow(
                    id=str(lr.id),
                    leave_type_name=leave_type_names.get(lr.leave_type_id) if lr.leave_type_id else None,
                    status=lr.status.value,
                    days_requested=lr.days_requested,
                    reason=lr.reason,
                ))
            cur += timedelta(days=1)

    # Incidents
    for inc in incidents:
        inc_date = _to_spain(inc.created_at).date()
        row = get_or_create(inc.employee_id, inc_date)
        row.incidents.append(IncidentReportRow(
            id=str(inc.id),
            incident_type=inc.incident_type or "",
            title=inc.title or "",
            status=inc.status or "",
            minutes_late=inc.minutes_late,
        ))

    return sorted(rows.values(), key=lambda r: (r.report_date, r.employee_name))


def build_summary_report(
    session: Session,
    employee_ids: list[UUID],
    date_from: date,
    date_to: date,
) -> list[EmployeeSummaryRow]:
    if not employee_ids or date_from > date_to:
        return []

    chrono = build_chronological_report(session, employee_ids, date_from, date_to)

    summaries: dict[str, EmployeeSummaryRow] = {}

    for day in chrono:
        emp_id = day.employee_id
        if emp_id not in summaries:
            summaries[emp_id] = EmployeeSummaryRow(
                employee_id=emp_id,
                employee_name=day.employee_name,
            )
        s = summaries[emp_id]
        if day.clock_entries:
            s.days_worked += 1
        s.total_worked_minutes += day.worked_minutes
        s.total_break_minutes += day.break_minutes
        s.total_net_minutes += day.net_minutes
        s.total_incidents += len(day.incidents)
        if day.has_open_clock:
            s.open_clocks += 1

    # Leave days: query directly for accuracy (sum over employees)
    leaves = session.exec(
        select(LeaveRequest).where(
            LeaveRequest.employee_id.in_(employee_ids),  # type: ignore[attr-defined]
            LeaveRequest.end_date >= date_from,
            LeaveRequest.start_date <= date_to,
            LeaveRequest.status.in_([LeaveStatus.APPROVED, LeaveStatus.PENDING]),  # type: ignore[attr-defined]
        )
    ).all()
    leave_type_names: dict[UUID, str] = {}
    for lr in leaves:
        if lr.leave_type_id and lr.leave_type_id not in leave_type_names:
            lt = session.get(LeaveType, lr.leave_type_id)
            if lt:
                leave_type_names[lr.leave_type_id] = lt.name

    for lr in leaves:
        emp_id = str(lr.employee_id)
        if emp_id not in summaries:
            emp = session.get(Employee, lr.employee_id)
            summaries[emp_id] = EmployeeSummaryRow(
                employee_id=emp_id,
                employee_name=emp.full_name if emp else emp_id,
            )
        s = summaries[emp_id]
        # Count business days in the range for this leave
        eff_from = max(lr.start_date, date_from)
        eff_to = min(lr.end_date, date_to)
        eff_days = _count_business_days(eff_from, eff_to)
        s.total_leave_days += eff_days
        type_key = leave_type_names.get(lr.leave_type_id) if lr.leave_type_id else None
        label = type_key or "Sin tipo"
        s.leave_by_type[label] = round(s.leave_by_type.get(label, 0.0) + eff_days, 2)

    return sorted(summaries.values(), key=lambda s: s.employee_name)


def _count_business_days(start: date, end: date) -> float:
    days = 0.0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days
