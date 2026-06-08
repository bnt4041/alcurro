"""Gestión de políticas globales de la plataforma (admin)."""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.platform_policy import PlatformPolicy
from app.core.platform_deps import get_platform_user as get_current_platform_user

router = APIRouter(prefix="/platform/policies", tags=["platform-policies"])

_SINGLETON_ID = UUID("00000000-0000-0000-0000-000000000001")


def _get_or_create(session: Session) -> PlatformPolicy:
    row = session.get(PlatformPolicy, _SINGLETON_ID)
    if not row:
        row = PlatformPolicy(id=_SINGLETON_ID)
        session.add(row)
        session.flush()
    return row


class PolicyRead(BaseModel):
    ai_monthly_limit: int
    ai_limit_action: str
    whatsapp_monthly_limit: int
    whatsapp_limit_action: str
    support_channel: str
    support_email: str | None
    support_notice: str | None
    tos_notice: str | None
    updated_at: datetime


class PolicyUpdate(BaseModel):
    ai_monthly_limit: int | None = None
    ai_limit_action: str | None = None
    whatsapp_monthly_limit: int | None = None
    whatsapp_limit_action: str | None = None
    support_channel: str | None = None
    support_email: str | None = None
    support_notice: str | None = None
    tos_notice: str | None = None


@router.get("", response_model=PolicyRead)
def get_policies(
    session: Session = Depends(get_session),
    _: object = Depends(get_current_platform_user),
) -> PolicyRead:
    row = _get_or_create(session)
    session.commit()
    return PolicyRead.model_validate(row, from_attributes=True)


@router.patch("", response_model=PolicyRead)
def update_policies(
    data: PolicyUpdate,
    session: Session = Depends(get_session),
    _: object = Depends(get_current_platform_user),
) -> PolicyRead:
    row = _get_or_create(session)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return PolicyRead.model_validate(row, from_attributes=True)


# Public endpoint — readable by authenticated tenant users (for support notice)
@router.get("/public", response_model=PolicyRead, include_in_schema=False)
def get_policies_public(
    session: Session = Depends(get_session),
) -> PolicyRead:
    row = _get_or_create(session)
    session.commit()
    return PolicyRead.model_validate(row, from_attributes=True)
