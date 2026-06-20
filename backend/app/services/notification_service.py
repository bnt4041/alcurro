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


def notify_leave_request_created(
    session: Session,
    *,
    tenant_id: UUID,
    employee: Employee,
    start_date: str,
    end_date: str,
    days: float,
    leave_type_name: str | None = None,
    reason: str | None = None,
) -> None:
    """Notifica al supervisor directo y admins del tenant cuando se crea un permiso."""
    from app.models.models import Role
    from app.models.tenant import Company

    supervisor_id = employee.supervisor_id
    supervisor: Employee | None = session.get(Employee, supervisor_id) if supervisor_id else None
    if supervisor and not supervisor.is_active:
        supervisor = None

    type_label = f" [{leave_type_name}]" if leave_type_name else ""
    reason_label = f"\nMotivo: {reason}" if reason else ""
    subject = f"Nueva solicitud de permiso{type_label} — {employee.full_name}"
    body = (
        f"{employee.full_name} ha solicitado un permiso{type_label}:\n\n"
        f"• Desde: {start_date}\n"
        f"• Hasta:  {end_date}\n"
        f"• Días:   {days:.1f}{reason_label}\n\n"
        "Accede al panel de Alcurro para aprobar o rechazar la solicitud."
    )
    body_inapp = f"{employee.full_name} solicita permiso del {start_date} al {end_date} ({days:.1f} días)."

    # In-app al supervisor
    if supervisor and _pref_enabled(session, supervisor.id, "leave_request", "inapp"):
        create_notification(
            session,
            tenant_id=tenant_id,
            employee_id=supervisor.id,
            event_type="leave_request",
            title=subject,
            body=body_inapp,
            link="/app/permisos",
            actor_name=employee.full_name,
        )

    # WhatsApp al supervisor
    if (
        supervisor
        and supervisor.phone
        and _pref_enabled(session, supervisor.id, "leave_request", "whatsapp")
    ):
        wa_msg = (
            f"📋 *Nueva solicitud de permiso*{type_label}\n\n"
            f"{employee.full_name} ha solicitado un permiso:\n"
            f"• Desde: {start_date}\n"
            f"• Hasta: {end_date}\n"
            f"• Días: {days:.1f}{reason_label}\n\n"
            "Accede al panel de Alcurro para aprobar o rechazar la solicitud."
        )
        try:
            from app.services.gowa_service import GoWAService
            GoWAService(session).send_text_sync(supervisor.phone, wa_msg)
        except Exception as exc:
            logger.warning(
                "notify_leave_request_created WhatsApp al supervisor falló (%s): %s",
                supervisor.id, exc,
            )

    # Recoger destinatarios email: supervisor + admins del mismo tenant con email
    from app.services.mail_service import MailService
    mail = MailService(session)

    # Empleados del mismo tenant con rol admin/tenant_admin que tengan email
    company_ids = [
        c.id
        for c in session.exec(
            select(Company).where(Company.tenant_id == tenant_id)
        ).all()
    ]
    admin_roles = {Role.TENANT_ADMIN, Role.ADMIN}
    tenant_admins = session.exec(
        select(Employee).where(
            Employee.company_id.in_(company_ids),  # type: ignore[attr-defined]
            Employee.is_active == True,  # noqa: E712
            Employee.role.in_(admin_roles),  # type: ignore[attr-defined]
            Employee.email != None,  # noqa: E711
        )
    ).all()

    recipients: dict[str, Employee] = {}  # email → employee (para pref check)
    if supervisor and supervisor.email:
        recipients[supervisor.email] = supervisor
    for admin in tenant_admins:
        if admin.id != employee.id and admin.email:
            recipients[admin.email] = admin

    for to_addr, recipient in recipients.items():
        if _pref_enabled(session, recipient.id, "leave_request", "email"):
            mail.send(
                to_addr,
                subject,
                body,
                event_type="leave_request",
                tenant_id=tenant_id,
            )

    # In-app a admins del tenant (excepto el propio empleado)
    for admin in tenant_admins:
        if admin.id != employee.id and _pref_enabled(session, admin.id, "leave_request", "inapp"):
            if not supervisor or admin.id != supervisor.id:  # no duplicar con el supervisor
                create_notification(
                    session,
                    tenant_id=tenant_id,
                    employee_id=admin.id,
                    event_type="leave_request",
                    title=subject,
                    body=body_inapp,
                    link="/app/permisos",
                    actor_name=employee.full_name,
                )


def notify_leave_request_reviewed(
    session: Session,
    *,
    tenant_id: UUID,
    employee: Employee,
    new_status: str,
    start_date: str,
    end_date: str,
    days: float,
    leave_type_name: str | None = None,
    review_notes: str | None = None,
) -> None:
    """WhatsApp + email al empleado cuando su solicitud es aprobada o rechazada."""
    if new_status == "approved":
        verdict = "✅ *APROBADA*"
        verdict_plain = "aprobada"
    elif new_status == "rejected":
        verdict = "❌ *RECHAZADA*"
        verdict_plain = "rechazada"
    else:
        return

    type_label = f" [{leave_type_name}]" if leave_type_name else ""
    notes_label = f"\n📝 Nota: {review_notes}" if review_notes else ""
    wa_msg = (
        f"Tu solicitud de permiso{type_label} ha sido {verdict}.\n\n"
        f"📅 Del {start_date} al {end_date} ({days:.1f} días){notes_label}"
    )

    # WhatsApp al empleado
    if _pref_enabled(session, employee.id, "leave_request", "whatsapp"):
        try:
            from app.services.gowa_service import GoWAService
            GoWAService(session).send_text_sync(employee.phone, wa_msg)
        except Exception as exc:
            logger.warning("notify_leave_reviewed WhatsApp failed for %s: %s", employee.id, exc)

    # In-app al empleado
    if _pref_enabled(session, employee.id, "leave_request", "inapp"):
        create_notification(
            session,
            tenant_id=tenant_id,
            employee_id=employee.id,
            event_type="leave_request",
            title=f"Solicitud de permiso{type_label} {verdict_plain}",
            body=f"Tu permiso del {start_date} al {end_date} ha sido {verdict_plain}.",
            link="/app/permisos",
        )

    # Email al empleado (si tiene email)
    if employee.email and _pref_enabled(session, employee.id, "leave_request", "email"):
        from app.services.mail_service import MailService
        subject = f"Solicitud de permiso{type_label} {verdict_plain} — {start_date} al {end_date}"
        body = (
            f"Hola {employee.full_name.split()[0]},\n\n"
            f"Tu solicitud de permiso{type_label} del {start_date} al {end_date} "
            f"({days:.1f} días) ha sido {verdict_plain}."
            + (f"\n\nNota del responsable: {review_notes}" if review_notes else "")
            + "\n\n— Alcurro RRHH"
        )
        MailService(session).send(
            employee.email,
            subject,
            body,
            event_type="leave_request",
            tenant_id=tenant_id,
        )


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
