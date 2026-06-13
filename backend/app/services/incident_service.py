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
from app.models.incident import Incident, IncidentAutoRule, IncidentNote
from app.models.models import ClockIn, Employee, LeaveRequest, LeaveStatus
from app.models.tenant import Tenant
from app.schemas.incident import (
    IncidentApplyClock,
    IncidentApplyLeave,
    IncidentAutoRuleRead,
    IncidentAutoRuleUpdate,
    IncidentRead,
)
from app.services.work_schedule import earliest_work_start, is_work_day, is_within_working_hours


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
    incident_date=None,
    clock_in_id: UUID | None = None,
    leave_request_id: UUID | None = None,
    minutes_late: int | None = None,
    original_data: dict | None = None,
    require_justification: bool = False,
    notify_whatsapp: bool = False,
    created_by_id: UUID | None = None,
) -> Incident:
    token = secrets.token_urlsafe(32) if require_justification else None
    # Incidencias creadas por el usuario (WhatsApp) → auto-cerradas (resolved)
    # Incidencias automáticas (cron/sistema) o manuales (panel web) → open/pending_justification
    if source == "whatsapp":
        status = "resolved"
        now = datetime.utcnow()
    elif require_justification:
        status = "pending_justification"
        now = None
    else:
        status = "open"
        now = None

    row = Incident(
        tenant_id=tenant_id,
        employee_id=employee_id,
        category=category,
        incident_type=incident_type,
        status=status,
        source=source,
        title=title,
        description=description,
        incident_date=incident_date,
        clock_in_id=clock_in_id,
        leave_request_id=leave_request_id,
        minutes_late=minutes_late,
        original_data=original_data or {},
        public_token=token,
        created_by_id=created_by_id,
        resolved_at=now,
        resolved_by_id=created_by_id if now else None,
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
    lines = [
        f"⚠️ *Incidencia: {incident.title}*",
    ]
    if incident.description:
        lines.append(incident.description)
    lines.append("")
    if incident.public_token:
        lines.append("Responde *justificar* seguido de tu explicación para resolverla. Ejemplo:")
        lines.append("_justificar Llegué tarde por un retraso del metro_")
    else:
        lines.append("Contacta con RRHH para más información.")
    return "\n".join(lines).strip()


def get_pending_justification_incidents(
    session: Session, employee_id: UUID
) -> list[Incident]:
    """Devuelve incidencias con estado pending_justification del empleado, ordenadas por fecha."""
    return list(
        session.exec(
            select(Incident).where(
                Incident.employee_id == employee_id,
                Incident.status == "pending_justification",
            ).order_by(Incident.created_at)  # type: ignore[attr-defined]
        ).all()
    )


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


def _has_approved_leave(session: Session, employee_id: UUID, on_date: date) -> bool:
    """True si el empleado tiene permiso aprobado que cubre on_date."""
    from app.models.models import LeaveRequest, LeaveStatus

    leave = session.exec(
        select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= on_date,
            LeaveRequest.end_date >= on_date,
        )
    ).first()
    return leave is not None


def check_missing_clock_in(
    session: Session,
    tenant_id: UUID,
    employee: Employee,
    today: date,
) -> Incident | None:
    """Crea incidencia si el empleado no ha fichado entrada X horas tras inicio de jornada."""
    rules = get_or_create_rules(session, tenant_id)
    if not rules.missing_clock_in_enabled:
        return None
    if not is_work_day(employee, today):
        return None
    if _has_approved_leave(session, employee.id, today):
        return None
    expected = earliest_work_start(employee, today)
    if not expected:
        return None
    now_local = _to_spain(datetime.now(timezone.utc)).replace(tzinfo=None)
    threshold = datetime.combine(today, expected) + timedelta(hours=rules.missing_clock_in_hours)
    if now_local < threshold:
        return None
    has_clock = session.exec(
        select(ClockIn).where(
            ClockIn.employee_id == employee.id,
            ClockIn.entrada_at >= datetime.combine(today, time.min),
        )
    ).first()
    if has_clock:
        return None
    existing = session.exec(
        select(Incident).where(
            Incident.employee_id == employee.id,
            Incident.incident_date == today,
            Incident.incident_type == "missing_clock_in",
        )
    ).first()
    if existing:
        return None
    return create_incident(
        session,
        tenant_id=tenant_id,
        employee_id=employee.id,
        category="fichaje",
        incident_type="missing_clock_in",
        title=f"Sin entrada registrada ({expected.strftime('%H:%M')})",
        description=(
            f"No se ha registrado entrada. "
            f"Horario previsto desde las {expected.strftime('%H:%M')}."
        ),
        source="auto",
        incident_date=today,
        original_data={"expected_start_time": expected.isoformat()},
        require_justification=rules.missing_clock_in_require_justification,
        notify_whatsapp=rules.missing_clock_in_notify_whatsapp,
    )


def check_missing_clock_out(
    session: Session,
    tenant_id: UUID,
    employee: Employee,
) -> Incident | None:
    """Crea incidencia si hay fichaje abierto (sin salida) más de X horas."""
    rules = get_or_create_rules(session, tenant_id)
    if not rules.missing_clock_out_enabled:
        return None
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now_utc - timedelta(hours=rules.missing_clock_out_hours)
    open_clock = session.exec(
        select(ClockIn).where(
            ClockIn.employee_id == employee.id,
            ClockIn.salida_at == None,  # noqa: E711
            ClockIn.entrada_at <= cutoff,
        )
    ).first()
    if not open_clock:
        return None
    clock_date = open_clock.entrada_at.date()
    if _has_approved_leave(session, employee.id, clock_date):
        return None
    existing = session.exec(
        select(Incident).where(
            Incident.clock_in_id == open_clock.id,
            Incident.incident_type == "missing_clock_out",
        )
    ).first()
    if existing:
        return None
    hours_open = int((now_utc - open_clock.entrada_at).total_seconds() // 3600)
    entrada_local = _to_spain(open_clock.entrada_at.replace(tzinfo=timezone.utc))
    return create_incident(
        session,
        tenant_id=tenant_id,
        employee_id=employee.id,
        category="fichaje",
        incident_type="missing_clock_out",
        title=f"Fichaje sin cerrar ({hours_open} h)",
        description=(
            f"Fichaje de entrada abierto desde las {entrada_local.strftime('%H:%M')} "
            f"del {clock_date.strftime('%d/%m/%Y')} sin registrar salida."
        ),
        source="auto",
        incident_date=clock_date,
        clock_in_id=open_clock.id,
        original_data=_clock_snapshot(open_clock),
        require_justification=rules.missing_clock_out_require_justification,
        notify_whatsapp=rules.missing_clock_out_notify_whatsapp,
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
    incident.managed = True
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
    incident.managed = True
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


# ── Notas ──────────────────────────────────────────────────────────────────────

def add_note(
    session: Session,
    *,
    incident_id: UUID,
    content: str,
    author_id: UUID | None = None,
    author_name: str | None = None,
) -> IncidentNote:
    note = IncidentNote(
        incident_id=incident_id,
        author_id=author_id,
        author_name=author_name,
        content=content.strip(),
    )
    session.add(note)
    session.flush()
    # Actualizar updated_at de la incidencia
    incident = session.get(Incident, incident_id)
    if incident:
        incident.updated_at = datetime.utcnow()
        session.add(incident)
    return note


def list_notes(session: Session, incident_id: UUID) -> list[IncidentNote]:
    return list(
        session.exec(
            select(IncidentNote)
            .where(IncidentNote.incident_id == incident_id)
            .order_by(IncidentNote.created_at)  # type: ignore[attr-defined]
        ).all()
    )


# ── Envío de mensajes desde incidencia ─────────────────────────────────────────

def send_whatsapp_from_incident(
    session: Session,
    *,
    incident: Incident,
    message: str,
    tenant_id: UUID,
    file_notes: list[str] | None = None,
    file_paths: list[str] | None = None,
) -> dict:
    """Envía WhatsApp al empleado de la incidencia con un mensaje y adjuntos opcionales."""
    from pathlib import Path as _Path
    employee = session.get(Employee, incident.employee_id)
    if not employee or not employee.phone:
        raise ValueError("El empleado no tiene teléfono configurado")
    from app.services.gowa_service import GoWAService

    gowa = GoWAService(session)
    IMAGE_EXT = {".jpg", ".jpeg", ".png"}
    try:
        result = gowa.send_text_sync(employee.phone, message)
        note_parts = [f"📱 WhatsApp enviado: {message[:500]}{'…' if len(message) > 500 else ''}"]

        # Enviar archivos adjuntos uno a uno
        for fpath in (file_paths or []):
            p = _Path(fpath)
            if not p.is_file():
                continue
            try:
                data = p.read_bytes()
                ext = p.suffix.lower()
                if ext in IMAGE_EXT:
                    gowa.send_image_sync(employee.phone, data, p.name, caption=p.name)
                else:
                    gowa.send_file_sync(employee.phone, data, p.name, caption=p.name)
                note_parts.append(f"📎 Adjunto enviado por WA: {p.name}")
            except Exception as fe:
                note_parts.append(f"⚠️ Adjunto no enviado ({p.name}): {fe}")

        if file_notes:
            note_parts.extend(file_notes)
        add_note(
            session,
            incident_id=incident.id,
            content="\n".join(note_parts),
            author_name="Sistema",
        )
        return {"ok": True, "detail": str(result)}
    except Exception as exc:
        raise RuntimeError(f"Error al enviar WhatsApp: {exc}") from exc


def send_email_from_incident(
    session: Session,
    *,
    incident: Incident,
    message: str,
    recipient_email: str,
    tenant_id: UUID,
    file_notes: list[str] | None = None,
) -> dict:
    """Envía email relacionado con la incidencia."""
    from app.services.mail_service import MailService

    mail = MailService(session)
    subject = f"Incidencia: {incident.title}"
    body = (
        f"Incidencia #{incident.id}\n"
        f"Empleado: (ID {incident.employee_id})\n"
        f"Título: {incident.title}\n"
        f"Estado: {incident.status}\n"
        f"\n---\n\n"
        f"{message}\n"
        f"\n---\n"
        f"Gestiona la incidencia en el panel de RRHH."
    )
    ok, err = mail.send(
        to_address=recipient_email,
        subject=subject,
        body=body,
        event_type="incident_message",
        tenant_id=tenant_id,
    )
    if not ok:
        raise RuntimeError(err or "Error al enviar email")
    note_parts = [f"📧 Email enviado a {recipient_email}: {message[:500]}{'…' if len(message) > 500 else ''}"]
    if file_notes:
        note_parts.extend(file_notes)
    add_note(
        session,
        incident_id=incident.id,
        content="\n".join(note_parts),
        author_name="Sistema",
    )
    return {"ok": True, "detail": f"Email enviado a {recipient_email}"}
