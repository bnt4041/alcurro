import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.database import create_db_and_tables, engine
from app.routers.api import api_router
from app.routers.webhook import router as webhook_router

# Patrón para detectar fechas ISO sin timezone: "2026-06-12T14:00:00" (sin Z ni offset)
_RE_NAIVE_ISO = re.compile(r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"')


class UTCJSONResponse(JSONResponse):
    """JSONResponse que añade sufijo Z a datetimes sin timezone (se asumen UTC)."""

    def render(self, content) -> bytes:
        raw = json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        )
        # Añadir Z a datetimes sin timezone
        raw = _RE_NAIVE_ISO.sub(r'"\1Z"', raw)
        return raw.encode("utf-8")

UPLOAD_DIR = Path("/app/uploads")


def _run_startup_migrations() -> None:
    """Migraciones idempotentes que no cubre SQLModel.create_all."""
    try:
        from scripts.migrate_gowa_device import main as migrate_gowa_device

        migrate_gowa_device()
    except Exception:
        pass
    try:
        from scripts.migrate_system_gowa import main as migrate_system_gowa

        migrate_system_gowa()
    except Exception:
        pass
    try:
        from scripts.migrate_employee_id_document import main as migrate_id_document

        migrate_id_document()
    except Exception:
        pass
    try:
        from scripts.migrate_work_breaks import main as migrate_work_breaks

        migrate_work_breaks()
    except Exception:
        pass
    try:
        from scripts.migrate_legal_and_schedule import main as migrate_legal

        migrate_legal()
    except Exception:
        pass
    try:
        from scripts.migrate_signatures import main as migrate_signatures

        migrate_signatures()
    except Exception:
        pass
    try:
        from scripts.migrate_mail import main as migrate_mail

        migrate_mail()
    except Exception:
        pass
    try:
        from scripts.migrate_work_schedule_blocks import (
            main as migrate_work_schedule_blocks,
        )

        migrate_work_schedule_blocks()
    except Exception:
        pass
    try:
        from scripts.migrate_work_schedule_periods import (
            main as migrate_work_schedule_periods,
        )

        migrate_work_schedule_periods()
    except Exception:
        pass
    try:
        from scripts.migrate_rotating_shift import main as migrate_rotating_shift

        migrate_rotating_shift()
    except Exception:
        pass
    try:
        from scripts.migrate_permissions_v2 import run as migrate_permissions_v2

        migrate_permissions_v2()
    except Exception as exc:
        print(f"migrate_permissions_v2: {exc}")
    try:
        from scripts.migrate_permissions_v3 import run as migrate_permissions_v3

        migrate_permissions_v3()
    except Exception as exc:
        print(f"migrate_permissions_v3: {exc}")
    try:
        from scripts.migrate_employee_weekly_hours import (
            main as migrate_employee_weekly_hours,
        )

        migrate_employee_weekly_hours()
    except Exception as exc:
        print(f"migrate_employee_weekly_hours: {exc}")
    try:
        from scripts.migrate_documents_v2 import main as migrate_documents_v2

        migrate_documents_v2()
    except Exception as exc:
        print(f"migrate_documents_v2: {exc}")
    try:
        from scripts.migrate_documents_v3 import main as migrate_documents_v3

        migrate_documents_v3()
    except Exception as exc:
        print(f"migrate_documents_v3: {exc}")
    try:
        from scripts.migrate_ai_v1 import main as migrate_ai_v1

        migrate_ai_v1()
    except Exception as exc:
        print(f"migrate_ai_v1: {exc}")
    try:
        from scripts.migrate_clock_settings_v1 import main as migrate_clock_settings_v1

        migrate_clock_settings_v1()
    except Exception as exc:
        print(f"migrate_clock_settings_v1: {exc}")
    try:
        from scripts.migrate_clock_settings_v2 import main as migrate_clock_settings_v2

        migrate_clock_settings_v2()
    except Exception as exc:
        print(f"migrate_clock_settings_v2: {exc}")
    try:
        from scripts.migrate_clock_settings_v3 import main as migrate_clock_settings_v3

        migrate_clock_settings_v3()
    except Exception as exc:
        print(f"migrate_clock_settings_v3: {exc}")
    try:
        from scripts.migrate_incidents_v4 import main as migrate_incidents_v4

        migrate_incidents_v4()
    except Exception as exc:
        print(f"migrate_incidents_v4: {exc}")
    try:
        from scripts.migrate_ai_v2 import main as migrate_ai_v2

        migrate_ai_v2()
    except Exception as exc:
        print(f"migrate_ai_v2: {exc}")
    try:
        from scripts.migrate_projects_v4 import main as migrate_projects_v4

        migrate_projects_v4()
    except Exception as exc:
        print(f"migrate_projects_v4: {exc}")
    try:
        from scripts.migrate_wa_dedup import main as migrate_wa_dedup

        migrate_wa_dedup()
    except Exception as exc:
        print(f"migrate_wa_dedup: {exc}")
    try:
        from scripts.migrate_notifications_v1 import main as migrate_notifications_v1

        migrate_notifications_v1()
    except Exception as exc:
        print(f"migrate_notifications_v1: {exc}")

    try:
        from scripts.migrate_leave_types_v1 import main as migrate_leave_types_v1

        migrate_leave_types_v1()
    except Exception as exc:
        print(f"migrate_leave_types_v1: {exc}")

    try:
        from scripts.migrate_geocoding_v1 import main as migrate_geocoding_v1

        migrate_geocoding_v1()
    except Exception as exc:
        print(f"migrate_geocoding_v1: {exc}")

    try:
        from scripts.migrate_leave_balance_v1 import main as migrate_leave_balance_v1

        migrate_leave_balance_v1()
    except Exception as exc:
        print(f"migrate_leave_balance_v1: {exc}")

    try:
        from scripts.migrate_incidents_v5 import main as migrate_incidents_v5

        migrate_incidents_v5()
    except Exception as exc:
        print(f"migrate_incidents_v5: {exc}")

    try:
        from scripts.migrate_lemon_squeezy_v1 import run as migrate_lemon_squeezy_v1

        migrate_lemon_squeezy_v1()
    except Exception as exc:
        print(f"migrate_lemon_squeezy_v1: {exc}")

    try:
        from scripts.migrate_lemon_squeezy_v2 import run as migrate_lemon_squeezy_v2

        migrate_lemon_squeezy_v2()
    except Exception as exc:
        print(f"migrate_lemon_squeezy_v2: {exc}")


async def _reminder_scheduler() -> None:
    """Ejecuta recordatorios de fichaje cada 5 minutos para todos los tenants activos."""
    from sqlmodel import Session, select
    from app.models.tenant import Tenant
    from app.services.clock_reminder_service import run_clock_reminders

    await asyncio.sleep(60)  # espera inicial para que el servidor arranque
    while True:
        try:
            with Session(engine) as session:
                tenants = session.exec(
                    select(Tenant).where(Tenant.is_active == True)  # noqa: E712
                ).all()
                for tenant in tenants:
                    try:
                        await run_clock_reminders(session, tenant.id)
                    except Exception as exc:
                        print(f"[reminders] tenant {tenant.id}: {exc}")
        except Exception as exc:
            print(f"[reminders] loop error: {exc}")
        await asyncio.sleep(300)  # cada 5 minutos


async def _omission_incident_scheduler() -> None:
    """Detecta omisión de fichaje (entrada y salida) y envía avisos cada 15 min."""
    from sqlmodel import Session, select
    from app.models.models import Employee
    from app.models.tenant import Company, Tenant
    from app.services.incident_service import (
        build_whatsapp_incident_message,
        check_missing_clock_in,
        check_missing_clock_out,
        get_or_create_rules,
    )
    from app.services.gowa_service import GoWAService
    from app.services.clock_reminder_service import run_incident_reminders
    from zoneinfo import ZoneInfo

    _SPAIN = ZoneInfo("Europe/Madrid")

    await asyncio.sleep(90)  # espera inicial escalonada
    while True:
        try:
            with Session(engine) as session:
                tenants = session.exec(
                    select(Tenant).where(Tenant.is_active == True)  # noqa: E712
                ).all()
                for tenant in tenants:
                    try:
                        rules = get_or_create_rules(session, tenant.id)
                        has_missing_in = rules.missing_clock_in_enabled
                        has_missing_out = rules.missing_clock_out_enabled
                        if not has_missing_in and not has_missing_out:
                            continue

                        now_local = datetime.now(_SPAIN).replace(tzinfo=None)
                        today = now_local.date()
                        gowa = GoWAService(session)

                        company_ids = [
                            c.id for c in session.exec(
                                select(Company).where(Company.tenant_id == tenant.id)
                            ).all()
                        ]
                        if not company_ids:
                            continue

                        employees = session.exec(
                            select(Employee).where(
                                Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
                                Employee.is_active == True,  # noqa: E712
                            )
                        ).all()

                        for emp in employees:
                            if not emp.phone:
                                continue
                            for inc in [
                                check_missing_clock_in(session, tenant.id, emp, today) if has_missing_in else None,
                                check_missing_clock_out(session, tenant.id, emp) if has_missing_out else None,
                            ]:
                                if inc is None:
                                    continue
                                if not inc.whatsapp_notified_at or not inc.public_token:
                                    continue
                                msg = build_whatsapp_incident_message(session, inc)
                                try:
                                    gowa.send_text_sync(emp.phone, msg)
                                    session.add(inc)
                                except Exception as exc:
                                    print(f"[omission] WA {emp.full_name}: {exc}")

                        session.commit()
                    except Exception as exc:
                        print(f"[omission] tenant {tenant.id}: {exc}")

                # Recordatorio de incidencias pendientes
                for tenant in tenants:
                    try:
                        await run_incident_reminders(session, tenant.id)
                    except Exception as exc:
                        print(f"[incident-reminder] tenant {tenant.id}: {exc}")

        except Exception as exc:
            print(f"[omission] loop error: {exc}")
        await asyncio.sleep(900)  # cada 15 minutos


async def _pending_cleanup_scheduler() -> None:
    """Limpia procesos pendientes de WhatsApp expirados (3 min) cada 60 segundos."""
    from datetime import datetime, timedelta, timezone
    from sqlmodel import Session, select
    from app.models.project import ClockPendingFichaje
    from app.models.clock_settings import InboundPendingUpload
    from app.models.models import Employee
    from app.models.tenant import Tenant as _Tenant
    from app.services.gowa_service import GoWAService
    from app.services.clock_pending_service import clear_pending as _clear_clock_pending
    from app.services.inbound_pending_service import clear_pending_upload

    await asyncio.sleep(30)  # espera inicial
    while True:
        try:
            with Session(engine) as session:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
                # Buscar pendientes de fichaje expirados
                expired = session.exec(
                    select(ClockPendingFichaje).where(
                        ClockPendingFichaje.created_at < cutoff.replace(tzinfo=None)
                    )
                ).all()
                for p in expired:
                    try:
                        # No expirar el pending de justificación de incidencia (timeout más largo: 60 min)
                        if (p.pending_meta or {}).get("awaiting_incident_justification"):
                            justification_cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
                            if p.created_at and p.created_at > justification_cutoff.replace(tzinfo=None):
                                continue
                        employee = session.get(Employee, p.employee_id)
                        if not employee or not employee.is_active:
                            _clear_clock_pending(session, p.employee_id)
                            continue
                        _clear_clock_pending(session, p.employee_id)
                        if not (p.pending_meta or {}).get("awaiting_incident_justification"):
                            try:
                                gowa = GoWAService(session)
                                gowa.send_text_sync(
                                    employee.phone,
                                    "⏰ Tu solicitud pendiente se ha cerrado por inactividad (más de 3 min). ¿Necesitas algo más?",
                                )
                            except Exception:
                                pass
                    except Exception:
                        _clear_clock_pending(session, p.employee_id)
                # Buscar uploads pendientes expirados
                expired_uploads = session.exec(
                    select(InboundPendingUpload).where(
                        InboundPendingUpload.created_at < cutoff.replace(tzinfo=None)
                    )
                ).all()
                for up in expired_uploads:
                    employee = session.get(Employee, up.employee_id)
                    clear_pending_upload(session, up.employee_id)
                    if employee and employee.is_active:
                        try:
                            gowa = GoWAService(session)
                            gowa.send_text_sync(
                                employee.phone,
                                "⏰ La subida de documento pendiente se ha cerrado por inactividad.",
                            )
                        except Exception:
                            pass
                session.commit()
        except Exception as exc:
            print(f"[pending-cleanup] error: {exc}")
        await asyncio.sleep(60)  # cada minuto


@asynccontextmanager
async def lifespan(_app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    _run_startup_migrations()
    task = asyncio.create_task(_reminder_scheduler())
    cleanup_task = asyncio.create_task(_pending_cleanup_scheduler())
    omission_task = asyncio.create_task(_omission_incident_scheduler())
    yield
    task.cancel()
    cleanup_task.cancel()
    omission_task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await omission_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="HRM API",
    description="Gestión de RRHH: panel admin, WhatsApp, vacaciones y turnos",
    version="0.2.0",
    lifespan=lifespan,
    default_response_class=UTCJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://frontend:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(webhook_router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
    msg = str(exc.orig) if exc.orig else str(exc)
    if "uq_employee_phone_company" in msg:
        detail = "Ya existe un empleado con este teléfono en la empresa"
    elif "uq_employee_id_document_company" in msg:
        detail = "DNI/NIE ya registrado en la empresa"
    elif "uq_employee_code_company" in msg:
        detail = "Código de empleado duplicado"
    elif "uq_employee_group" in msg:
        detail = "Conflicto al asignar grupos al empleado"
    elif "document_deliveries" in msg or "document_delivery" in msg:
        detail = "No se puede eliminar: el documento está vinculado a otros registros"
    else:
        detail = "Registro duplicado o conflicto de datos"
    return JSONResponse(status_code=409, content={"detail": detail})


if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
