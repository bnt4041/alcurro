"""Recordatorios de fichaje e incidencias por WhatsApp (entrada, salida, incidencias)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.models.incident import Incident
from app.models.models import ClockIn, Employee
from app.models.tenant import Company
from app.schemas.clock_settings import ClockReminderRunResult
from app.services.clock_settings_service import get_or_create_settings
from app.services.gowa_service import GoWAService
from app.services.work_schedule import (
    earliest_work_start,
    is_work_day,
    slots_for_day,
)

_SPAIN_TZ = ZoneInfo("Europe/Madrid")


def _now_local() -> datetime:
    """Hora actual en Spain timezone, naive (para comparar con horarios almacenados)."""
    return datetime.now(_SPAIN_TZ).replace(tzinfo=None)


def _latest_work_end(employee: Employee, on_date: date) -> time | None:
    slots = slots_for_day(employee, on_date)
    if not slots:
        return None
    return max(s[1] for s in slots)


async def run_clock_reminders(session: Session, tenant_id) -> ClockReminderRunResult:
    from uuid import UUID

    tid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
    settings = get_or_create_settings(session, tid)
    result = ClockReminderRunResult()

    has_entry_reminder = bool(settings.clock_reminder_minutes)
    has_exit_reminder = bool(settings.clock_exit_reminder_minutes)
    if not has_entry_reminder and not has_exit_reminder:
        return result

    now = _now_local()
    today = now.date()
    gowa = GoWAService(session)

    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tid)
        ).all()
    ]
    if not company_ids:
        return result

    employees = session.exec(
        select(Employee).where(
            Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
            Employee.is_active == True,  # noqa: E712
        )
    ).all()

    for emp in employees:
        if not emp.phone:
            result.skipped += 1
            continue
        if not is_work_day(emp, today):
            result.skipped += 1
            continue

        # ── Recordatorio de entrada ────────────────────────────────────────
        if has_entry_reminder:
            await _check_entry_reminder(
                session, gowa, emp, now, today,
                settings.clock_reminder_minutes,  # type: ignore[arg-type]
                result,
            )

        # ── Recordatorio de salida ─────────────────────────────────────────
        if has_exit_reminder:
            await _check_exit_reminder(
                session, gowa, emp, now, today,
                settings.clock_exit_reminder_minutes,  # type: ignore[arg-type]
                result,
            )

    session.commit()
    return result


async def run_incident_reminders(session: Session, tenant_id) -> int:
    """Envía recordatorio por WA a empleados con incidencias pendientes de justificación.

    Usa ClockSettings.incident_reminder_enabled y incident_reminder_minutes.
    Solo envía una vez por empleado por día. Solo durante horas laborales.
    """
    from uuid import UUID

    tid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
    settings = get_or_create_settings(session, tid)
    if not settings.incident_reminder_enabled or not settings.incident_reminder_minutes:
        return 0

    now = _now_local()
    today = now.date()
    gowa = GoWAService(session)
    sent = 0

    company_ids = [
        c.id
        for c in session.exec(select(Company).where(Company.tenant_id == tid)).all()
    ]
    if not company_ids:
        return 0

    employees = session.exec(
        select(Employee).where(
            Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
            Employee.is_active == True,  # noqa: E712
        )
    ).all()

    for emp in employees:
        if not emp.phone:
            continue
        if emp.last_incident_reminder_at and emp.last_incident_reminder_at.date() == today:
            continue

        pending = session.exec(
            select(Incident).where(
                Incident.employee_id == emp.id,
                Incident.status == "pending_justification",
            )
        ).all()
        if not pending:
            continue

        # Solo enviar durante jornada laboral del empleado
        if not is_work_day(emp, today):
            continue
        slots = slots_for_day(emp, today)
        if slots:
            work_start = datetime.combine(today, min(s[0] for s in slots))
            work_end = datetime.combine(today, max(s[1] for s in slots))
            if now < work_start or now > work_end:
                continue

        count = len(pending)
        noun = "incidencia" if count == 1 else "incidencias"
        msg = (
            f"Hola {emp.full_name.split()[0]}, tienes {count} {noun} pendiente{'s' if count > 1 else ''} "
            f"de justificación. Por favor, accede al enlace que te enviamos para gestionarla{'s' if count > 1 else ''}."
        )
        try:
            await gowa.send_text(emp.phone, msg)
            emp.last_incident_reminder_at = datetime.utcnow()
            session.add(emp)
            sent += 1
        except Exception:
            pass

    session.commit()
    return sent


async def _check_entry_reminder(
    session: Session,
    gowa: GoWAService,
    emp: Employee,
    now: datetime,
    today: date,
    minutes: int,
    result: ClockReminderRunResult,
) -> None:
    start_t = earliest_work_start(emp, today)
    if not start_t:
        result.skipped += 1
        return

    due = datetime.combine(today, start_t) + timedelta(minutes=minutes)
    if now < due:
        result.skipped += 1
        return

    # Ya se envió hoy
    if emp.last_clock_reminder_at and emp.last_clock_reminder_at.date() == today:
        result.skipped += 1
        return

    # Ya fichó entrada hoy
    has_entrada = session.exec(
        select(ClockIn).where(
            ClockIn.employee_id == emp.id,
            ClockIn.entrada_at >= datetime.combine(today, time.min),  # type: ignore[operator]
        )
    ).first()
    if has_entrada:
        result.skipped += 1
        return

    msg = (
        f"Hola {emp.full_name.split()[0]}, recuerda fichar tu *ENTRADA* "
        "cuando comiences la jornada. Envía «entrada» o comparte tu ubicación. 📍"
    )
    try:
        await gowa.send_text(emp.phone, msg)
        emp.last_clock_reminder_at = datetime.utcnow()
        session.add(emp)
        result.sent += 1
    except Exception as exc:
        result.errors.append(f"entrada {emp.full_name}: {exc}")


async def _check_exit_reminder(
    session: Session,
    gowa: GoWAService,
    emp: Employee,
    now: datetime,
    today: date,
    minutes: int,
    result: ClockReminderRunResult,
) -> None:
    end_t = _latest_work_end(emp, today)
    if not end_t:
        return

    due = datetime.combine(today, end_t) + timedelta(minutes=minutes)
    if now < due:
        return

    # Ya se envió aviso de salida hoy
    if emp.last_exit_reminder_at and emp.last_exit_reminder_at.date() == today:
        return

    # Buscar fichaje abierto hoy (entrada sin salida)
    open_clockin = session.exec(
        select(ClockIn).where(
            ClockIn.employee_id == emp.id,
            ClockIn.entrada_at >= datetime.combine(today, time.min),  # type: ignore[operator]
            ClockIn.salida_at == None,  # noqa: E711
        )
    ).first()
    if not open_clockin:
        return

    msg = (
        f"Hola {emp.full_name.split()[0]}, recuerda fichar tu *SALIDA* "
        "antes de terminar la jornada. Envía «salida». 👋"
    )
    try:
        await gowa.send_text(emp.phone, msg)
        emp.last_exit_reminder_at = datetime.utcnow()
        session.add(emp)
        result.sent_exit += 1
    except Exception as exc:
        result.errors.append(f"salida {emp.full_name}: {exc}")
