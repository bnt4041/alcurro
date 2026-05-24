from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.database import create_db_and_tables
from app.routers.api import api_router
from app.routers.webhook import router as webhook_router

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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    _run_startup_migrations()
    yield


app = FastAPI(
    title="HRM API",
    description="Gestión de RRHH: panel admin, WhatsApp, vacaciones y turnos",
    version="0.2.0",
    lifespan=lifespan,
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
    else:
        detail = "Registro duplicado o conflicto de datos"
    return JSONResponse(status_code=409, content={"detail": detail})


if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
