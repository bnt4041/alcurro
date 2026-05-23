from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.schemas.crud import (
    ConnectionTestResult,
    SystemSettingsRead,
    SystemSettingsUpdate,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SystemSettingsRead)
def get_settings(
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "settings")),
) -> SystemSettingsRead:
    return SettingsService(session).read()


@router.put("", response_model=SystemSettingsRead)
def update_settings(
    data: SystemSettingsUpdate,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "settings")),
) -> SystemSettingsRead:
    return SettingsService(session).update(data)


@router.post("/test/gowa", response_model=ConnectionTestResult)
async def test_gowa(
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "settings")),
) -> ConnectionTestResult:
    ok, msg, detail = await SettingsService(session).test_gowa()
    return ConnectionTestResult(ok=ok, message=msg, detail=detail)


@router.post("/test/ollama", response_model=ConnectionTestResult)
async def test_ollama(
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "settings")),
) -> ConnectionTestResult:
    ok, msg, detail = await SettingsService(session).test_ollama()
    return ConnectionTestResult(ok=ok, message=msg, detail=detail)
