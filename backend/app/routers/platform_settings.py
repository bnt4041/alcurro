"""Configuración global de la plataforma (datos fiscales, facturación)."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.rbac import PlatformUser
from app.schemas.platform_settings import PlatformSettingsRead, PlatformSettingsUpdate
from app.services.invoice_service import get_platform_settings

router = APIRouter(prefix="/platform/settings", tags=["platform-settings"])


@router.get("", response_model=PlatformSettingsRead)
def get_settings(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PlatformSettingsRead:
    row = get_platform_settings(session)
    session.commit()
    session.refresh(row)
    return PlatformSettingsRead.model_validate(row)


@router.patch("", response_model=PlatformSettingsRead)
def update_settings(
    data: PlatformSettingsUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PlatformSettingsRead:
    row = get_platform_settings(session)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return PlatformSettingsRead.model_validate(row)
