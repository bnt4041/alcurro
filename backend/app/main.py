from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
