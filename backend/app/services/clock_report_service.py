"""Informe de jornada: fichajes y paradas en línea temporal."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

_SPAIN_TZ = ZoneInfo("Europe/Madrid")


def _to_spain(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_SPAIN_TZ)

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.models import BreakType, ClockIn, ClockInType, Employee, WorkBreak
from app.models.project import Project


def _minutes_between(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    if m:
        return f"{h} h {m} min"
    return f"{h} h"


class ReportTimelineItem(BaseModel):
    time_label: str
    kind: str
    label: str
    detail: str | None = None


class EmployeeDayReport(BaseModel):
    employee_id: UUID
    employee_name: str
    report_date: date
    timeline: list[ReportTimelineItem] = Field(default_factory=list)
    worked_minutes: int = 0
    break_minutes: int = 0
    open_clock: bool = False
    open_break: bool = False
    text_summary: str = ""


def build_employee_day_report(
    session: Session,
    employee_id: UUID,
    on_date: date | None = None,
) -> EmployeeDayReport:
    employee = session.get(Employee, employee_id)
    if not employee:
        return EmployeeDayReport(
            employee_id=employee_id,
            employee_name="—",
            report_date=on_date or date.today(),
            text_summary="Empleado no encontrado.",
        )

    report_date = on_date or date.today()
    start = datetime.combine(report_date, time.min)
    end = start + timedelta(days=1)

    clocks = list(
        session.exec(
            select(ClockIn)
            .where(
                ClockIn.employee_id == employee_id,
                ClockIn.recorded_at >= start,
                ClockIn.recorded_at < end,
            )
            .order_by(ClockIn.recorded_at)
        ).all()
    )

    breaks = list(
        session.exec(
            select(WorkBreak)
            .where(
                WorkBreak.employee_id == employee_id,
                WorkBreak.recorded_at >= start,
                WorkBreak.recorded_at < end,
            )
            .order_by(WorkBreak.recorded_at)
        ).all()
    )

    timeline: list[tuple[datetime, ReportTimelineItem]] = []

    for c in clocks:
        tipo = "Entrada" if c.record_type == ClockInType.ENTRADA else "Salida"
        detail_parts: list[str] = []
        if c.project_id:
            p = session.get(Project, c.project_id)
            if p:
                detail_parts.append(p.name)
        if c.latitude is not None:
            detail_parts.append("con ubicación")
        if c.notes:
            detail_parts.append(c.notes)
        timeline.append(
            (
                c.recorded_at,
                ReportTimelineItem(
                    time_label=_to_spain(c.recorded_at).strftime("%H:%M"),
                    kind="fichaje",
                    label=tipo,
                    detail=" · ".join(detail_parts) if detail_parts else None,
                ),
            )
        )

    for b in breaks:
        label = "Inicio parada" if b.record_type == BreakType.INICIO else "Fin parada"
        timeline.append(
            (
                b.recorded_at,
                ReportTimelineItem(
                    time_label=_to_spain(b.recorded_at).strftime("%H:%M"),
                    kind="parada",
                    label=label,
                    detail=b.notes,
                ),
            )
        )

    timeline.sort(key=lambda x: x[0])
    items = [t[1] for t in timeline]

    worked = 0
    open_start: datetime | None = None
    for c in clocks:
        if c.record_type == ClockInType.ENTRADA:
            open_start = c.recorded_at
        elif c.record_type == ClockInType.SALIDA and open_start:
            worked += _minutes_between(open_start, c.recorded_at)
            open_start = None
    open_clock = open_start is not None
    if open_start and report_date == date.today():
        worked += _minutes_between(open_start, datetime.utcnow())

    break_minutes = 0
    break_start: datetime | None = None
    open_break = False
    for b in breaks:
        if b.record_type == BreakType.INICIO:
            break_start = b.recorded_at
        elif b.record_type == BreakType.FIN and break_start:
            break_minutes += _minutes_between(break_start, b.recorded_at)
            break_start = None
    if break_start:
        open_break = True
        if report_date == date.today():
            break_minutes += _minutes_between(break_start, datetime.utcnow())

    lines = [
        f"📋 Informe de fichajes {report_date.strftime('%d/%m/%Y')}",
        f"Empleado: {employee.full_name}",
        "",
    ]
    if not items:
        lines.append("Sin fichajes ni paradas registrados.")
    else:
        lines.append("Línea temporal (fichajes y paradas):")
        for it in items:
            prefix = "⏱" if it.kind == "fichaje" else "☕"
            extra = f" — {it.detail}" if it.detail else ""
            lines.append(f"  {prefix} {it.time_label} · {it.label}{extra}")
    lines.append("")
    lines.append(f"Tiempo trabajado (fichajes): {_format_duration(worked)}")
    if break_minutes:
        lines.append(f"Tiempo en paradas: {_format_duration(break_minutes)}")
    if open_clock:
        lines.append("⚠️ Entrada abierta (jornada en curso).")
    if open_break:
        lines.append("⚠️ Parada iniciada sin cerrar.")

    return EmployeeDayReport(
        employee_id=employee_id,
        employee_name=employee.full_name,
        report_date=report_date,
        timeline=items,
        worked_minutes=worked,
        break_minutes=break_minutes,
        open_clock=open_clock,
        open_break=open_break,
        text_summary="\n".join(lines),
    )


def build_daily_summary(session: Session, employee_id: UUID) -> str:
    """Resumen WhatsApp del día (usa informe unificado)."""
    return build_employee_day_report(session, employee_id).text_summary
