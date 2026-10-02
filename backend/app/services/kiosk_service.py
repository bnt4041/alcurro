"""Modo kiosko: fichaje desde un enlace público único por centro de trabajo.

El empleado se identifica con su código numérico + PIN. Si tiene jornada abierta
se cierra; si no, se abre. Una jornada abierta hace más de `KIOSK_MAX_OPEN_HOURS`
no se cierra: se deja abierta (con incidencia de omisión de salida para que RRHH
la regularice) y se abre una jornada nueva.
"""

from __future__ import annotations

import re
import secrets
import threading
import time as _time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.core.security import verify_password
from app.models.incident import Incident
from app.models.models import ClockIn, Employee
from app.models.organization import WorkCenter
from app.models.tenant import Company, Tenant
from app.services.clock_service import ClockService
from app.services.incident_service import (
    check_missing_clock_out,
    create_incident,
    get_or_create_rules,
)

KIOSK_MAX_OPEN_HOURS = 12
KIOSK_SOURCE = "kiosk"

# Anti fuerza bruta del PIN (en memoria, por proceso): N fallos en la ventana → bloqueo.
_MAX_FAILED_ATTEMPTS = 5
_LOCK_WINDOW_SECONDS = 15 * 60
_failed: dict[tuple[UUID, str], list[float]] = {}
_failed_lock = threading.Lock()


class KioskError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class KioskContext:
    work_center: WorkCenter
    company: Company
    tenant: Tenant


@dataclass
class KioskResult:
    action: str  # "entrada" | "salida"
    employee_name: str
    at: datetime
    entrada_at: datetime | None = None
    previous_expired: bool = False


def new_kiosk_token() -> str:
    return secrets.token_urlsafe(24)


def resolve_kiosk(session: Session, token: str) -> KioskContext:
    wc = session.exec(select(WorkCenter).where(WorkCenter.kiosk_token == token)).first()
    if not wc or not wc.is_active:
        raise KioskError("Enlace de kiosko no válido o desactivado", 404)
    company = session.get(Company, wc.company_id)
    tenant = session.get(Tenant, company.tenant_id) if company else None
    if not company or not company.is_active or not tenant or not tenant.is_active:
        raise KioskError("Enlace de kiosko no válido o desactivado", 404)
    return KioskContext(work_center=wc, company=company, tenant=tenant)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _find_employees_by_code(session: Session, company_id: UUID, code: str) -> list[Employee]:
    """Empleados activos cuyo código coincide con el número tecleado.

    Acepta el código literal o solo su parte numérica (EMP-007 ↔ "7" / "007").
    """
    wanted = _digits(code)
    if not wanted:
        return []
    rows = session.exec(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.is_active == True,  # noqa: E712
        )
    ).all()
    exact = [e for e in rows if e.employee_code.strip() == code.strip()]
    if exact:
        return exact
    return [e for e in rows if _digits(e.employee_code) and int(_digits(e.employee_code)) == int(wanted)]


def _check_rate_limit(wc_id: UUID, code: str) -> None:
    key = (wc_id, _digits(code))
    now = _time.monotonic()
    with _failed_lock:
        recent = [t for t in _failed.get(key, []) if now - t < _LOCK_WINDOW_SECONDS]
        _failed[key] = recent
        if len(recent) >= _MAX_FAILED_ATTEMPTS:
            raise KioskError(
                "Demasiados intentos fallidos. Espera unos minutos o contacta con RRHH.", 429
            )


def _register_failure(wc_id: UUID, code: str) -> None:
    with _failed_lock:
        _failed.setdefault((wc_id, _digits(code)), []).append(_time.monotonic())


def _clear_failures(wc_id: UUID, code: str) -> None:
    with _failed_lock:
        _failed.pop((wc_id, _digits(code)), None)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _ensure_expired_incident(session: Session, tenant_id: UUID, employee: Employee, clock: ClockIn) -> None:
    """Garantiza una incidencia de omisión de salida sobre la jornada caducada."""
    if check_missing_clock_out(session, tenant_id, employee):
        return
    exists = session.exec(
        select(Incident).where(
            Incident.clock_in_id == clock.id,
            Incident.incident_type == "missing_clock_out",
        )
    ).first()
    if exists:
        return
    rules = get_or_create_rules(session, tenant_id)
    hours_open = int((datetime.now(timezone.utc) - _as_utc(clock.entrada_at)).total_seconds() // 3600)
    create_incident(
        session,
        tenant_id=tenant_id,
        employee_id=employee.id,
        category="fichaje",
        incident_type="missing_clock_out",
        title=f"Fichaje sin cerrar ({hours_open} h)",
        description=(
            "Jornada abierta más de "
            f"{KIOSK_MAX_OPEN_HOURS} h sin registrar salida. "
            "Se abrió una jornada nueva desde el kiosko."
        ),
        source="auto",
        incident_date=clock.entrada_at.date(),
        clock_in_id=clock.id,
        original_data={
            "entrada_at": clock.entrada_at.isoformat(),
            "salida_at": None,
            "notes": clock.notes,
            "latitude": clock.latitude,
            "longitude": clock.longitude,
        },
        require_justification=rules.missing_clock_out_require_justification,
        notify_whatsapp=rules.missing_clock_out_notify_whatsapp,
    )


def kiosk_clock(
    session: Session,
    token: str,
    *,
    employee_code: str,
    pin: str,
    latitude: float,
    longitude: float,
    address: str | None = None,
) -> KioskResult:
    ctx = resolve_kiosk(session, token)
    wc = ctx.work_center
    _check_rate_limit(wc.id, employee_code)

    candidates = _find_employees_by_code(session, ctx.company.id, employee_code)
    employee = next(
        (e for e in candidates if e.kiosk_pin_hash and verify_password(pin, e.kiosk_pin_hash)),
        None,
    )
    if not employee:
        if candidates and not any(e.kiosk_pin_hash for e in candidates):
            raise KioskError("No tienes PIN de kiosko configurado. Pídelo a RRHH.", 403)
        _register_failure(wc.id, employee_code)
        raise KioskError("Código o PIN incorrectos", 401)
    _clear_failures(wc.id, employee_code)

    clock = ClockService(session, tenant_id=ctx.tenant.id)
    open_record = clock.get_open_clock(employee.id)
    previous_expired = False
    if open_record:
        elapsed = datetime.now(timezone.utc) - _as_utc(open_record.entrada_at)
        if elapsed < timedelta(hours=KIOSK_MAX_OPEN_HOURS):
            record = clock.close_clock(
                employee.id,
                latitude=latitude,
                longitude=longitude,
                address=address,
                commit=False,
            )
            session.commit()
            return KioskResult(
                action="salida",
                employee_name=employee.full_name,
                at=record.salida_at,
                entrada_at=record.entrada_at,
            )
        # Jornada caducada: no se cierra; se abre una nueva en el día de hoy.
        _ensure_expired_incident(session, ctx.tenant.id, employee, open_record)
        previous_expired = True

    record = clock.open_clock(
        employee.id,
        latitude=latitude,
        longitude=longitude,
        address=address,
        notes=f"Kiosko: {wc.name}",
        source=KIOSK_SOURCE,
        commit=False,
    )
    session.commit()
    return KioskResult(
        action="entrada",
        employee_name=employee.full_name,
        at=record.entrada_at,
        previous_expired=previous_expired,
    )
