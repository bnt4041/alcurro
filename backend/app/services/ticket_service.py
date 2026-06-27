"""Lógica de negocio de tickets de soporte (cliente ↔ plataforma)."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.config import get_settings
from app.models.models import Employee
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.models.ticket import (
    Ticket,
    TicketAuthorType,
    TicketMessage,
    TicketSource,
    TicketStatus,
)
from app.schemas.ticket import (
    KbSearchResult,
    TicketDetailRead,
    TicketMessageRead,
    TicketRead,
)
from app.services import kb_service
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


# ── Pre-check de documentación ────────────────────────────────────────────────
def precheck_docs(query: str, limit: int = 3) -> list[KbSearchResult]:
    return [
        KbSearchResult(title=r.title, source=r.source, snippet=r.snippet)
        for r in kb_service.search(query, limit=limit)
    ]


# ── Lectura / serialización ───────────────────────────────────────────────────
def _platform_name(session: Session, pid: UUID | None) -> str | None:
    if not pid:
        return None
    pu = session.get(PlatformUser, pid)
    return pu.full_name if pu else None


def _author_name(session: Session, msg: TicketMessage) -> str | None:
    if msg.author_type == TicketAuthorType.PLATFORM and msg.author_platform_user_id:
        pu = session.get(PlatformUser, msg.author_platform_user_id)
        return pu.full_name if pu else "Soporte Alcurro"
    if msg.author_employee_id:
        emp = session.get(Employee, msg.author_employee_id)
        return emp.full_name if emp else None
    return None


def _to_read(session: Session, t: Ticket) -> TicketRead:
    tenant = session.get(Tenant, t.tenant_id)
    creator = session.get(Employee, t.created_by_employee_id)
    count = session.exec(
        select(func.count()).select_from(TicketMessage).where(
            TicketMessage.ticket_id == t.id
        )
    ).one()
    return TicketRead(
        id=t.id,
        tenant_id=t.tenant_id,
        tenant_name=tenant.name if tenant else None,
        created_by_employee_id=t.created_by_employee_id,
        created_by_name=creator.full_name if creator else None,
        subject=t.subject,
        body=t.body,
        status=t.status,
        priority=t.priority,
        category=t.category,
        source=t.source,
        assigned_platform_user_id=t.assigned_platform_user_id,
        assigned_to_name=_platform_name(session, t.assigned_platform_user_id),
        message_count=int(count),
        created_at=t.created_at,
        updated_at=t.updated_at,
        closed_at=t.closed_at,
    )


def _to_detail(session: Session, t: Ticket, *, include_internal: bool) -> TicketDetailRead:
    base = _to_read(session, t)
    stmt = select(TicketMessage).where(TicketMessage.ticket_id == t.id)
    if not include_internal:
        stmt = stmt.where(TicketMessage.is_internal == False)  # noqa: E712
    stmt = stmt.order_by(TicketMessage.created_at.asc())  # type: ignore[attr-defined]
    msgs = session.exec(stmt).all()
    messages = [
        TicketMessageRead(
            id=m.id,
            author_type=m.author_type,
            author_name=_author_name(session, m),
            body=m.body,
            is_internal=m.is_internal,
            created_at=m.created_at,
        )
        for m in msgs
    ]
    return TicketDetailRead(**base.model_dump(), messages=messages)


def list_tickets(
    session: Session,
    *,
    tenant_id: UUID | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[TicketRead]:
    stmt = select(Ticket)
    if tenant_id:
        stmt = stmt.where(Ticket.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Ticket.status == status)
    stmt = stmt.order_by(Ticket.updated_at.desc()).limit(limit)  # type: ignore[attr-defined]
    return [_to_read(session, t) for t in session.exec(stmt).all()]


def get_ticket(
    session: Session,
    ticket_id: UUID,
    *,
    tenant_id: UUID | None = None,
    include_internal: bool = False,
) -> Ticket | None:
    t = session.get(Ticket, ticket_id)
    if not t:
        return None
    if tenant_id and t.tenant_id != tenant_id:
        return None
    return t


# ── Creación ──────────────────────────────────────────────────────────────────
def create_ticket(
    session: Session,
    *,
    tenant_id: UUID,
    employee: Employee,
    subject: str,
    body: str,
    priority: str = "normal",
    category: str | None = None,
    source: str = TicketSource.WEB,
) -> Ticket:
    ticket = Ticket(
        tenant_id=tenant_id,
        created_by_employee_id=employee.id,
        subject=subject.strip()[:200],
        body=body.strip()[:4000],
        priority=priority,
        category=category,
        source=source,
    )
    session.add(ticket)
    session.flush()
    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            author_type=TicketAuthorType.CLIENT,
            author_employee_id=employee.id,
            body=body.strip()[:4000],
        )
    )
    session.commit()
    session.refresh(ticket)
    _notify_platform_new_ticket(session, ticket, employee)
    return ticket


# ── Mensajes / cambios de estado ──────────────────────────────────────────────
def add_client_message(
    session: Session, ticket: Ticket, employee: Employee, body: str
) -> TicketMessage:
    msg = TicketMessage(
        ticket_id=ticket.id,
        author_type=TicketAuthorType.CLIENT,
        author_employee_id=employee.id,
        body=body.strip()[:4000],
    )
    session.add(msg)
    if ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.PENDING):
        ticket.status = TicketStatus.OPEN
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(msg)
    return msg


def add_platform_message(
    session: Session,
    ticket: Ticket,
    platform_user: PlatformUser,
    body: str,
    *,
    is_internal: bool = False,
) -> TicketMessage:
    msg = TicketMessage(
        ticket_id=ticket.id,
        author_type=TicketAuthorType.PLATFORM,
        author_platform_user_id=platform_user.id,
        body=body.strip()[:4000],
        is_internal=is_internal,
    )
    session.add(msg)
    if not is_internal and ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.PENDING  # esperando al cliente
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(msg)
    if not is_internal:
        _notify_client_reply(session, ticket, body)
    return msg


def update_ticket(
    session: Session,
    ticket: Ticket,
    *,
    status: str | None = None,
    priority: str | None = None,
    assigned_platform_user_id: UUID | None = ...,  # type: ignore[assignment]
) -> Ticket:
    if status is not None:
        ticket.status = status
        ticket.closed_at = datetime.utcnow() if status == TicketStatus.CLOSED else None
    if priority is not None:
        ticket.priority = priority
    if assigned_platform_user_id is not ...:
        ticket.assigned_platform_user_id = assigned_platform_user_id
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


# ── Notificaciones ────────────────────────────────────────────────────────────
def _ticket_link(ticket_id: UUID) -> str:
    base = get_settings().public_app_url.rstrip("/")
    return f"{base}/admin/tickets/{ticket_id}"


def _notify_platform_new_ticket(session: Session, ticket: Ticket, employee: Employee) -> None:
    tenant = session.get(Tenant, ticket.tenant_id)
    tenant_name = tenant.name if tenant else "—"
    link = _ticket_link(ticket.id)
    subject = f"[Ticket] {ticket.subject} — {tenant_name}"
    body = (
        f"Nuevo ticket de soporte:\n\n"
        f"Cuenta: {tenant_name}\n"
        f"Creado por: {employee.full_name}\n"
        f"Prioridad: {ticket.priority}\n"
        f"Origen: {ticket.source}\n\n"
        f"Asunto: {ticket.subject}\n"
        f"{ticket.body}\n\n"
        f"Gestiónalo aquí: {link}"
    )

    # Email a todos los admins de plataforma con email
    try:
        from app.services.mail_service import MailService

        mail = MailService(session)
        admins = session.exec(
            select(PlatformUser).where(PlatformUser.is_active == True)  # noqa: E712
        ).all()
        for pu in admins:
            if pu.email:
                mail.send(pu.email, subject, body, event_type="ticket")
    except Exception as exc:
        logger.warning("Email aviso nuevo ticket falló: %s", exc)

    # WhatsApp al número de alertas de plataforma
    try:
        settings = SettingsService(session).get_or_create()
        alert_phone = getattr(settings, "platform_alert_phone", None)
        if alert_phone:
            from app.services.gowa_service import GoWAService

            caption = (
                f"🎫 *Nuevo ticket* — {tenant_name}\n"
                f"{ticket.subject}\n"
                f"Por {employee.full_name} · prioridad {ticket.priority}"
            )
            try:
                GoWAService(session).send_text_sync(alert_phone, f"{caption}\n\n{link}")
            except Exception as exc:
                logger.warning("WhatsApp aviso nuevo ticket falló: %s", exc)
    except Exception as exc:
        logger.warning("Config WhatsApp aviso ticket falló: %s", exc)


def _notify_client_reply(session: Session, ticket: Ticket, body: str) -> None:
    employee = session.get(Employee, ticket.created_by_employee_id)
    if not employee:
        return
    base = get_settings().public_app_url.rstrip("/")
    link = f"{base}/app/soporte"
    preview = body.strip()
    if len(preview) > 300:
        preview = preview[:300] + "…"

    # In-app
    try:
        from app.services.notification_service import create_notification

        create_notification(
            session,
            tenant_id=ticket.tenant_id,
            employee_id=employee.id,
            event_type="ticket",
            title=f"Respuesta a tu ticket: {ticket.subject}",
            body=preview,
            link="/app/soporte",
        )
        session.commit()
    except Exception as exc:
        logger.warning("Notif in-app respuesta ticket falló: %s", exc)

    # WhatsApp
    if employee.phone:
        try:
            from app.services.gowa_service import GoWAService

            GoWAService(session).send_text_sync(
                employee.phone,
                f"💬 *Soporte Alcurro* respondió a tu ticket «{ticket.subject}»:\n\n"
                f"{preview}\n\nResponde desde {link}",
            )
        except Exception as exc:
            logger.warning("WhatsApp respuesta ticket falló: %s", exc)

    # Email
    if employee.email:
        try:
            from app.services.mail_service import MailService

            MailService(session).send(
                employee.email,
                f"Respuesta a tu ticket: {ticket.subject}",
                f"Hola {employee.full_name.split()[0]},\n\n"
                f"El equipo de soporte ha respondido a tu ticket «{ticket.subject}»:\n\n"
                f"{preview}\n\nAccede a {link} para continuar.\n\n— Alcurro",
                event_type="ticket",
                tenant_id=ticket.tenant_id,
            )
        except Exception as exc:
            logger.warning("Email respuesta ticket falló: %s", exc)


# ── Serializadores expuestos ──────────────────────────────────────────────────
def to_read(session: Session, ticket: Ticket) -> TicketRead:
    return _to_read(session, ticket)


def to_detail(session: Session, ticket: Ticket, *, include_internal: bool) -> TicketDetailRead:
    return _to_detail(session, ticket, include_internal=include_internal)
