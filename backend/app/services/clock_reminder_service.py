"""Recordatorios de fichaje por WhatsApp (solo dentro del horario laboral)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from app.models.models import ClockIn, Employee
from app.models.tenant import Company
from app.schemas.clock_settings import ClockReminderRunResult
from app.services.clock_settings_service import get_or_create_settings
from app.services.gowa_service import GoWAService
from app.services.work_schedule import (
    earliest_work_start,
    is_within_working_hours,
    is_work_day,
)


async def run_clock_reminders(session: Session, tenant_id) -> ClockReminderRunResult:
    from uuid import UUID

    tid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
    settings = get_or_create_settings(session, tid)
    result = ClockReminderRunResult(sent=0, skipped=0)
    if not settings.clock_reminder_minutes:
        return result

    minutes = settings.clock_reminder_minutes
    now = datetime.utcnow()
    today = date.today()
    gowa = GoWAService(session)

    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tid)
        ).all()
    ]
    if not company_ids:
        return result

    for emp in session.exec(
        select(Employee).where(
            Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
            Employee.is_active == True,  # noqa: E712
        )
    ).all():
        if not is_work_day(emp, today):
            result.skipped += 1
            continue
        if not is_within_working_hours(emp, now):
            result.skipped += 1
            continue

        start_t = earliest_work_start(emp, today)
        if not start_t:
            result.skipped += 1
            continue
        due = datetime.combine(today, start_t) + timedelta(minutes=minutes)
        if now < due:
            result.skipped += 1
            continue
        if emp.last_clock_reminder_at and emp.last_clock_reminder_at.date() == today:
            result.skipped += 1
            continue
        has_entrada = session.exec(
            select(ClockIn).where(
                ClockIn.employee_id == emp.id,
                ClockIn.entrada_at >= datetime.combine(today, time.min),  # type: ignore[operator]
            )
        ).first()
        if has_entrada:
            result.skipped += 1
            continue
        msg = (
            f"Hola {emp.full_name}, recuerda fichar tu ENTRADA cuando comiences la jornada. "
            "Envía «entrada» o comparte tu ubicación."
        )
        try:
            await gowa.send_text(emp.phone, msg)
            emp.last_clock_reminder_at = now
            session.add(emp)
            result.sent += 1
        except Exception as exc:
            result.errors.append(f"{emp.full_name}: {exc}")
    session.commit()
    return result
