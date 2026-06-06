"""Servicio de notificaciones: in-app, WhatsApp y email."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session, select

from app.models.models import Employee
from app.models.notification import Notification, NotificationPreference

if TYPE_CHECKING:
    from app.services.gowa_service import GoWAService

logger = logging.getLogger(__name__)

NOTIFICATION_EVENTS = [
    "clock_in",
    "clock_out",
    "leave_request",
    "incident",
    "document",
]
NOTIFICATION_CHANNELS = ["inapp", "whatsapp", "email"]


def _pref_enabled(session: Session, employee_id: UUID, event_type: str, channel: str) -> bool:
    pref = session.exec(
        select(NotificationPreference).where(
            NotificationPreference.employee_id == employee_id,
            NotificationPreference.event_type == event_type,
            NotificationPreference.channel == channel,
        )
    ).first()
    return pref.enabled if pref is not None else True  # default: habilitado


def seed_preferences(session: Session, employee_id: UUID) -> None:
    """Crea las preferencias por defecto (todas habilitadas) si no existen."""
    existing = session.exec(
        select(NotificationPreference).where(
            NotificationPreference.employee_id == employee_id
        )
    ).all()
    existing_keys = {(p.event_type, p.channel) for p in existing}
    for event in NOTIFICATION_EVENTS:
        for channel in NOTIFICATION_CHANNELS:
            if (event, channel) not in existing_keys:
                session.add(
                    NotificationPreference(
                        employee_id=employee_id,
                        event_type=event,
                        channel=channel,
                        enabled=True,
                    )
                )


def get_preferences(session: Session, employee_id: UUID) -> list[NotificationPreference]:
    seed_preferences(session, employee_id)
    return list(
        session.exec(
            select(NotificationPreference).where(
                NotificationPreference.employee_id == employee_id
            )
        ).all()
    )


def update_preferences(
    session: Session,
    employee_id: UUID,
    updates: list[dict],  # [{event_type, channel, enabled}]
) -> list[NotificationPreference]:
    seed_preferences(session, employee_id)
    for upd in updates:
        pref = session.exec(
            select(NotificationPreference).where(
                NotificationPreference.employee_id == employee_id,
                NotificationPreference.event_type == upd["event_type"],
                NotificationPreference.channel == upd["channel"],
            )
        ).first()
        if pref:
            pref.enabled = upd["enabled"]
            session.add(pref)
    session.flush()
    return get_preferences(session, employee_id)


def create_notification(
    session: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    event_type: str,
    title: str,
    body: str,
    link: str | None = None,
    actor_name: str | None = None,
) -> Notification:
    notif = Notification(
        tenant_id=tenant_id,
        employee_id=employee_id,
        event_type=event_type,
        title=title,
        body=body,
        link=link,
        actor_name=actor_name,
    )
    session.add(notif)
    return notif


def get_notifications(
    session: Session,
    employee_id: UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.employee_id == employee_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return list(session.exec(stmt).all())


def count_unread(session: Session, employee_id: UUID) -> int:
    return len(get_notifications(session, employee_id, unread_only=True, limit=200))


def mark_read(session: Session, notification_id: UUID, employee_id: UUID) -> bool:
    notif = session.exec(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.employee_id == employee_id,
        )
    ).first()
    if not notif or notif.read_at:
        return False
    notif.read_at = datetime.now(timezone.utc)
    session.add(notif)
    return True


def mark_all_read(session: Session, employee_id: UUID) -> int:
    notifs = get_notifications(session, employee_id, unread_only=True, limit=200)
    now = datetime.now(timezone.utc)
    for n in notifs:
        n.read_at = now
        session.add(n)
    return len(notifs)


def notify_supervisor_sync(
    session: Session,
    *,
    tenant_id: UUID,
    actor: Employee,
    event_type: str,
    title: str,
    body: str,
    link: str | None = None,
) -> None:
    """Notificación in-app síncrona al supervisor (sin WhatsApp/email)."""
    supervisor_id = actor.supervisor_id
    if not supervisor_id:
        return
    supervisor = session.get(Employee, supervisor_id)
    if not supervisor or not supervisor.is_active:
        return
    if _pref_enabled(session, supervisor_id, event_type, "inapp"):
        create_notification(
            session,
            tenant_id=tenant_id,
            employee_id=supervisor_id,
            event_type=event_type,
            title=title,
            body=body,
            link=link,
            actor_name=actor.full_name,
        )


async def notify_supervisor(
    session: Session,
    *,
    tenant_id: UUID,
    actor: Employee,
    event_type: str,
    title: str,
    body: str,
    link: str | None = None,
    gowa: "GoWAService | None" = None,
) -> None:
    """Notifica al supervisor directo del actor por todos los canales habilitados."""
    supervisor_id = actor.supervisor_id
    if not supervisor_id:
        return
    supervisor = session.get(Employee, supervisor_id)
    if not supervisor or not supervisor.is_active:
        return

    # In-app
    if _pref_enabled(session, supervisor_id, event_type, "inapp"):
        create_notification(
            session,
            tenant_id=tenant_id,
            employee_id=supervisor_id,
            event_type=event_type,
            title=title,
            body=body,
            link=link,
            actor_name=actor.full_name,
        )

    # WhatsApp
    if gowa and supervisor.phone and _pref_enabled(session, supervisor_id, event_type, "whatsapp"):
        msg = f"*{title}*\n{body}"
        try:
            await gowa.send_text(supervisor.phone, msg)
        except Exception as exc:
            logger.warning("notify_supervisor WhatsApp failed: %s", exc)

    # Email — no SMTP directo aquí, se deja para una extensión futura


def build_org_chart(session: Session, tenant_id: UUID) -> list[dict]:
    """Devuelve el árbol jerárquico de empleados para el organigrama."""
    from app.models.tenant import Company

    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tenant_id)
        ).all()
    ]
    employees = session.exec(
        select(Employee).where(
            Employee.company_id.in_(company_ids),
            Employee.is_active == True,  # noqa: E712
        )
    ).all()

    # Construir mapa id → nodo
    nodes: dict[UUID, dict] = {}
    for emp in employees:
        nodes[emp.id] = {
            "id": str(emp.id),
            "full_name": emp.full_name,
            "job_title": emp.job_title,
            "role": emp.role.value,
            "supervisor_id": str(emp.supervisor_id) if emp.supervisor_id else None,
            "avatar_url": f"/api/employees/{emp.id}/avatar" if emp.avatar_delivery_id else None,
            "children": [],
        }

    roots: list[dict] = []
    for node in nodes.values():
        parent_id = node["supervisor_id"]
        if parent_id and parent_id in {str(k) for k in nodes}:
            nodes[UUID(parent_id)]["children"].append(node)
        else:
            roots.append(node)

    return roots
