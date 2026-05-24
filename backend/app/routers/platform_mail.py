from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.rbac import PlatformUser
from app.schemas.crud import ConnectionTestResult
from app.schemas.mail import MailLogRead, MailSettingsRead, MailSettingsUpdate, MailTestRequest
from app.services.mail_service import MailService

router = APIRouter(prefix="/platform/mail", tags=["platform-mail"])


@router.get("/settings", response_model=MailSettingsRead)
def get_mail_settings(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> MailSettingsRead:
    return MailService(session).read_settings()


@router.put("/settings", response_model=MailSettingsRead)
def update_mail_settings(
    data: MailSettingsUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> MailSettingsRead:
    return MailService(session).update_settings(data)


@router.get("/logs", response_model=list[MailLogRead])
def list_mail_logs(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    limit: int = 100,
    success_only: bool | None = None,
) -> list[MailLogRead]:
    return MailService(session).list_logs(limit=limit, success_only=success_only)


@router.post("/test", response_model=ConnectionTestResult)
def test_mail(
    data: MailTestRequest,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> ConnectionTestResult:
    ok, msg, detail = MailService(session).send_test(data.to_email)
    return ConnectionTestResult(ok=ok, message=msg, detail=detail)
