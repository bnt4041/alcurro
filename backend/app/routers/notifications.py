from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.deps import get_current_user
from app.database import get_session
from app.models.models import Employee
from app.models.tenant import Company
from app.services.notification_service import (
    build_org_chart,
    count_unread,
    get_notifications,
    get_preferences,
    mark_all_read,
    mark_read,
    update_preferences,
)

router = APIRouter(tags=["notifications"])


def _tenant_id(session: Session, user: Employee) -> UUID:
    company = session.get(Company, user.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Empresa no encontrada")
    return company.tenant_id


class NotificationOut(BaseModel):
    id: str
    event_type: str
    title: str
    body: str
    link: str | None
    actor_name: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationPreferenceOut(BaseModel):
    event_type: str
    channel: str
    enabled: bool


class PreferenceUpdateItem(BaseModel):
    event_type: str
    channel: str
    enabled: bool


class PreferenceUpdateRequest(BaseModel):
    preferences: list[PreferenceUpdateItem]


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> Any:
    notifs = get_notifications(session, user.id, unread_only=unread_only, limit=limit)
    return [
        NotificationOut(
            id=str(n.id),
            event_type=n.event_type,
            title=n.title,
            body=n.body,
            link=n.link,
            actor_name=n.actor_name,
            read_at=n.read_at,
            created_at=n.created_at,
        )
        for n in notifs
    ]


@router.get("/notifications/unread-count")
def unread_count(
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> dict[str, int]:
    return {"count": count_unread(session, user.id)}


@router.post("/notifications/{notification_id}/read")
def read_notification(
    notification_id: UUID,
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> dict[str, bool]:
    ok = mark_read(session, notification_id, user.id)
    session.commit()
    return {"ok": ok}


@router.post("/notifications/read-all")
def read_all(
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> dict[str, int]:
    count = mark_all_read(session, user.id)
    session.commit()
    return {"marked": count}


@router.get("/employees/me/notification-preferences", response_model=list[NotificationPreferenceOut])
def get_my_preferences(
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> Any:
    prefs = get_preferences(session, user.id)
    session.commit()
    return [NotificationPreferenceOut(event_type=p.event_type, channel=p.channel, enabled=p.enabled) for p in prefs]


@router.put("/employees/me/notification-preferences", response_model=list[NotificationPreferenceOut])
def update_my_preferences(
    body: PreferenceUpdateRequest,
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> Any:
    prefs = update_preferences(
        session,
        user.id,
        [p.model_dump() for p in body.preferences],
    )
    session.commit()
    return [NotificationPreferenceOut(event_type=p.event_type, channel=p.channel, enabled=p.enabled) for p in prefs]


@router.get("/employees/{employee_id}/notification-preferences", response_model=list[NotificationPreferenceOut])
def get_employee_preferences(
    employee_id: UUID,
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> Any:
    prefs = get_preferences(session, employee_id)
    session.commit()
    return [NotificationPreferenceOut(event_type=p.event_type, channel=p.channel, enabled=p.enabled) for p in prefs]


@router.put("/employees/{employee_id}/notification-preferences", response_model=list[NotificationPreferenceOut])
def update_employee_preferences(
    employee_id: UUID,
    body: PreferenceUpdateRequest,
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> Any:
    prefs = update_preferences(
        session,
        employee_id,
        [p.model_dump() for p in body.preferences],
    )
    session.commit()
    return [NotificationPreferenceOut(event_type=p.event_type, channel=p.channel, enabled=p.enabled) for p in prefs]


@router.get("/employees/org-chart")
def org_chart(
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> Any:
    tid = _tenant_id(session, user)
    return build_org_chart(session, tid)
