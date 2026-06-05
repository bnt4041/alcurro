"""Gestión de incidencias y reglas automáticas."""

from __future__ import annotations

import secrets
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

_SPAIN_TZ = ZoneInfo("Europe/Madrid")


def _to_spain(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_SPAIN_TZ)

from sqlmodel import Session, select

from app.config import get_settings
from app.models.incident import Incident, IncidentAutoRule
from app.models.models import ClockIn, Employee, LeaveRequest, LeaveStatus
from app.models.tenant import Tenant
from app.schemas.incident import (
    IncidentApplyClock,
    IncidentApplyLeave,
    IncidentAutoRuleRead,
    IncidentAutoRuleUpdate,
    IncidentRead,
)
from app.services.work_schedule import earliest_work_start, is_work_day


def get_or_create_rules(session: Session, tenant_id: UUID) -> IncidentAutoRule:
    row = session.get(IncidentAutoRule, tenant_id)
    if row:
        return row
    row = IncidentAutoRule(tenant_id=tenant_id)
    session.add(row)
    session.flush()
    return row


def rules_to_read(row: IncidentAutoRule) -> IncidentAutoRuleRead:
    return IncidentAutoRuleRead.model_validate(row)


def update_rules(
    session: Session, tenant_id: UUID, data: IncidentAutoRuleUpdate
) -> IncidentAutoRuleRead:
    row = get_or_create_rules(session, tenant_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.flush()
    return rules_to_read(row)


def _clock_snapshot(clock: ClockIn) -> dict:
    return {
        "entrada_at": clock.entrada_at.isoformat(),
        "salida_at": clock.salida_at.isoformat() if clock.salida_at else None,
        "notes": clock.notes,
        "work_summary": clock.work_summary,
        "project_id": str(clock.project_id) if clock.project_id else None,
        "latitude": clock.latitude,
        "longitude": clock.longitude,
    }


def _leave_snapshot(leave: LeaveRequest) -> dict:
    return {
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
        "days_requested": leave.days_requested,
        "status": leave.status.value if hasattr(leave.status, "value") else str(leave.status),
        "reason": leave.reason,
    }


def _justify_url(token: str | None) -> str | None:
    if not token:
        return None
    base = get_settings().public_app_url.rstrip("/")
    return f"{base}/justificar-incidencia/{token}"


def incident_to_read(
    session: Session, row: Incident, *, include_url: bool = False
) -> IncidentRead:
    emp = session.get(Employee, row.employee_id)
    data = IncidentRead.model_validate(row)
    data.employee_name = emp.full_name if emp else None
    if include_url:
        data.justify_url = _justify_url(row.public_token)
    return data


def original_data_for_links(
    session: Session,
    *,
    employee_id: UUID,
    clock_in_id: UUID | None = None,
    leave_request_id: UUID | None = None,
) -> dict:
    """Snapshot al crear incidencia manual vinculada a fichaje o solicitud."""
    data: dict = {}
    if clock_in_id:
        clock = session.get(ClockIn, clock_in_id)
        if not clock or clock.employee_id != employee_id:
            raise ValueError("Fichaje no válido para este empleado")
        data = _clock_snapshot(clock)
    elif leave_request_id:
        leave = session.get(LeaveRequest, leave_request_id)
        if not leave or leave.employee_id != employee_id:
            raise ValueError("Solicitud no válida para este empleado")
        data = _leave_snapshot(leave)
    return data


def create_incident(
    session: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    category: str,
    incident_type: str,
    title: str,
    description: str | None = None,
    source: str = "manual",
    clock_in_id: UUID | None = None,
    leave_request_id: UUID | None = None,
    minutes_late: int | None = None,
    original_data: dict | None = None,
    require_justification: bool = False,
    notify_whatsapp: bool = False,
) -> Incident:
    token = secrets.token_urlsafe(32) if require_justification else None
    status = "pending_justification" if require_justification else "open"
    row = Incident(
        tenant_id=tenant_id,
        employee_id=employee_id,
        category=category,
        incident_type=incident_type,
        status=status,
        source=source,
        title=title,
        description=description,
        clock_in_id=clock_in_id,
        leave_request_id=leave_request_id,
        minutes_late=minutes_late,
        original_data=original_data or {},
        public_token=token,
    )
    session.add(row)
    session.flush()
    if notify_whatsapp and token:
        _schedule_whatsapp_notify(session, row)
    return row


def _schedule_whatsapp_notify(session: Session, incident: Incident) -> None:
    incident.whatsapp_notified_at = datetime.utcnow()
    session.add(incident)


def build_whatsapp_incident_message(session: Session, incident: Incident) -> str:
    url = _justify_url(incident.public_token)
    lines = [
        f"⚠️ Incidencia: {incident.title}",
        incident.description or "",
    ]
    if url:
        lines.append("")
        lines.append(f"Puedes justificarla aquí: {url}")
    else:
        lines.append("")
        lines.append("Contacta con RRHH para más información.")
    return "\n".join(lines).strip()


def check_late_clock_in(
    session: Session,
    tenant_id: UUID,
    employee: Employee,
    clock: ClockIn,
) -> Incident | None:
    rules = get_or_create_rules(session, tenant_id)
    if not rules.late_entrada_enabled:
        return None
    on_date = clock.entrada_at.date()
    if not is_work_day(employee, on_date):
        return None
    expected = earliest_work_start(employee, on_date)
    if not expected:
        return None
    scheduled = datetime.combine(on_date, expected)
    late_minutes = int((clock.entrada_at - scheduled).total_seconds() // 60)
    if late_minutes <= rules.late_entrada_grace_minutes:
        return None
    existing = session.exec(
        select(Incident).where(Incident.clock_in_id == clock.id)
    ).first()
    if existing:
        return existing
    return create_incident(
        session,
        tenant_id=tenant_id,
        employee_id=employee.id,
        category="fichaje",
        incident_type="late_clock_in",
        title=f"Entrada {late_minutes} min tarde",
        description=(
            f"Entrada registrada a las {_to_spain(clock.entrada_at).strftime('%H:%M')} "
            f"(horario previsto desde las {expected.strftime('%H:%M')})."
        ),
        source="auto",
        clock_in_id=clock.id,
        minutes_late=late_minutes,
        original_data=_clock_snapshot(clock),
        require_justification=rules.late_entrada_require_justification,
        notify_whatsapp=rules.late_entrada_notify_whatsapp,
    )


def apply_clock_correction(
    session: Session,
    incident: Incident,
    data: IncidentApplyClock,
    resolver_id: UUID | None,
) -> Incident:
    if not incident.clock_in_id:
        raise ValueError("La incidencia no está vinculada a un fichaje")
    clock = session.get(ClockIn, incident.clock_in_id)
    if not clock:
        raise ValueError("Fichaje no encontrado")
    if not incident.original_data:
        incident.original_data = _clock_snapshot(clock)
    modified = _clock_snapshot(clock)
    modified["entrada_at"] = data.recorded_at.isoformat()
    if data.notes is not None:
        modified["notes"] = data.notes
    if data.project_id is not None:
        modified["project_id"] = str(data.project_id)
    incident.modified_data = modified
    clock.entrada_at = data.recorded_at
    if data.notes is not None:
        clock.notes = data.notes
    if data.project_id is not None:
        clock.project_id = data.project_id
    session.add(clock)
    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    incident.resolved_by_id = resolver_id
    incident.updated_at = datetime.utcnow()
    session.add(incident)
    session.flush()
    return incident


def apply_leave_correction(
    session: Session,
    incident: Incident,
    data: IncidentApplyLeave,
    resolver_id: UUID | None,
) -> Incident:
    if not incident.leave_request_id:
        raise ValueError("La incidencia no está vinculada a una solicitud")
    leave = session.get(LeaveRequest, incident.leave_request_id)
    if not leave:
        raise ValueError("Solicitud no encontrada")
    if not incident.original_data:
        incident.original_data = _leave_snapshot(leave)
    modified = _leave_snapshot(leave)
    if data.start_date:
        modified["start_date"] = data.start_date.isoformat()
        leave.start_date = data.start_date
    if data.end_date:
        modified["end_date"] = data.end_date.isoformat()
        leave.end_date = data.end_date
    if data.days_requested is not None:
        modified["days_requested"] = data.days_requested
        leave.days_requested = data.days_requested
    if data.reason is not None:
        modified["reason"] = data.reason
        leave.reason = data.reason
    if data.status:
        modified["status"] = data.status
        leave.status = LeaveStatus(data.status)
    incident.modified_data = modified
    session.add(leave)
    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    incident.resolved_by_id = resolver_id
    incident.updated_at = datetime.utcnow()
    session.add(incident)
    session.flush()
    return incident


def submit_employee_justification(
    session: Session, token: str, text: str
) -> Incident | None:
    row = session.exec(
        select(Incident).where(Incident.public_token == token)
    ).first()
    if not row:
        return None
    row.employee_justification = text.strip()
    row.justified_at = datetime.utcnow()
    if row.status == "pending_justification":
        row.status = "open"
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.flush()
    return row


def get_incident_by_token(session: Session, token: str) -> Incident | None:
    return session.exec(
        select(Incident).where(Incident.public_token == token)
    ).first()
