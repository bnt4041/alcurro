from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.rbac import PlatformUser
from app.schemas.crud import ConnectionTestResult, SystemSettingsRead, SystemSettingsUpdate
from app.schemas.tenant import WhatsAppSessionRead
from app.services.gowa_client import get_shared_whatsapp_session
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/platform/whatsapp", tags=["platform-whatsapp"])


@router.get("/settings", response_model=SystemSettingsRead)
def get_whatsapp_settings(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> SystemSettingsRead:
    return SettingsService(session).read()


@router.put("/settings", response_model=SystemSettingsRead)
def update_whatsapp_settings(
    data: SystemSettingsUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> SystemSettingsRead:
    return SettingsService(session).update(data)


@router.get("/session", response_model=WhatsAppSessionRead)
async def whatsapp_session(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> WhatsAppSessionRead:
    data = await get_shared_whatsapp_session(session)
    return WhatsAppSessionRead(
        gowa_status="running" if data.get("configured") else "pending",
        gowa_error=None,
        gowa_port=3000 if data.get("configured") else None,
        connected=data.get("connected", False),
        qr_image=data.get("qr_image"),
        qr_expires_in=data.get("qr_expires_in"),
        message=data.get("message"),
    )


@router.post("/test", response_model=ConnectionTestResult)
async def test_whatsapp(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> ConnectionTestResult:
    ok, msg, detail = await SettingsService(session).test_gowa()
    return ConnectionTestResult(ok=ok, message=msg, detail=detail)
