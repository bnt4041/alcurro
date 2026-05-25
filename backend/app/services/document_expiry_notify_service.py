"""Avisos configurables por caducidad de documentos."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core.permissions import get_employee_permissions
from app.models.documents import (
    DocumentDelivery,
    DocumentExpiryNotificationLog,
    DocumentNotificationSettings,
)
from app.models.models import Employee
from app.schemas.documents import (
    DocumentNotificationSettingsRead,
    DocumentNotificationSettingsUpdate,
    ExpiryNotificationRunResult,
)
from app.services.gowa_service import GoWAService
from app.services.mail_service import MailService


def parse_days_before(raw: str) -> list[int]:
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
            if n >= 0:
                out.append(n)
        except ValueError:
            continue
    return sorted(set(out), reverse=True) or [30, 7, 1]


def format_days_before(days: list[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)))


def parse_extra_emails(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [e.strip().lower() for e in raw.split(",") if e.strip() and "@" in e]


def format_extra_emails(emails: list[str]) -> str | None:
    cleaned = [e.strip().lower() for e in emails if e.strip()]
    return ",".join(cleaned) if cleaned else None


def get_or_create_settings(
    session: Session, tenant_id: UUID
) -> DocumentNotificationSettings:
    row = session.get(DocumentNotificationSettings, tenant_id)
    if row:
        return row
    row = DocumentNotificationSettings(tenant_id=tenant_id)
    session.add(row)
    session.flush()
    return row


def settings_to_read(row: DocumentNotificationSettings) -> DocumentNotificationSettingsRead:
    return DocumentNotificationSettingsRead(
        tenant_id=row.tenant_id,
        enabled=row.enabled,
        days_before=parse_days_before(row.days_before),
        channel_whatsapp=row.channel_whatsapp,
        channel_email=row.channel_email,
        notify_employee=row.notify_employee,
        notify_managers=row.notify_managers,
        extra_emails=parse_extra_emails(row.extra_emails),
        updated_at=row.updated_at,
    )


def update_settings(
    session: Session, tenant_id: UUID, data: DocumentNotificationSettingsUpdate
) -> DocumentNotificationSettingsRead:
    row = get_or_create_settings(session, tenant_id)
    payload = data.model_dump(exclude_unset=True)
    if "days_before" in payload and payload["days_before"] is not None:
        row.days_before = format_days_before(payload["days_before"])
    if "extra_emails" in payload and payload["extra_emails"] is not None:
        row.extra_emails = format_extra_emails(payload["extra_emails"])
    for key, value in payload.items():
        if key in ("days_before", "extra_emails"):
            continue
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.flush()
    return settings_to_read(row)


def _already_sent(
    session: Session,
    document_id: UUID,
    days_before: int,
    channel: str,
    recipient: str,
) -> bool:
    return (
        session.exec(
            select(DocumentExpiryNotificationLog).where(
                DocumentExpiryNotificationLog.document_delivery_id == document_id,
                DocumentExpiryNotificationLog.days_before == days_before,
                DocumentExpiryNotificationLog.channel == channel,
                DocumentExpiryNotificationLog.recipient == recipient,
            )
        ).first()
        is not None
    )


def _log_send(
    session: Session,
    *,
    tenant_id: UUID,
    document_id: UUID,
    days_before: int,
    channel: str,
    recipient: str,
    success: bool,
    detail: str | None,
) -> None:
    session.add(
        DocumentExpiryNotificationLog(
            tenant_id=tenant_id,
            document_delivery_id=document_id,
            days_before=days_before,
            channel=channel,
            recipient=recipient[:255],
            success=success,
            detail=(detail or "")[:500] or None,
        )
    )


def _managers_for_document(
    session: Session, tenant_id: UUID, doc: DocumentDelivery
) -> list[Employee]:
    company_id = doc.company_id
    if not company_id and doc.employee_id:
        emp = session.get(Employee, doc.employee_id)
        company_id = emp.company_id if emp else None
    if not company_id:
        return []
    managers: list[Employee] = []
    for emp in session.exec(
        select(Employee).where(Employee.company_id == company_id, Employee.is_active == True)  # noqa: E712
    ).all():
        perms = get_employee_permissions(session, emp, tenant_id)
        if "documents.read" in perms or "documents.write" in perms:
            if doc.employee_id and emp.id == doc.employee_id:
                continue
            managers.append(emp)
    return managers


def _doc_label(doc: DocumentDelivery) -> str:
    parts = [doc.file_name]
    if doc.title:
        parts.append(f"({doc.title})")
    return " ".join(parts)


async def run_expiry_notifications(
    session: Session, tenant_id: UUID, *, dry_run: bool = False
) -> ExpiryNotificationRunResult:
    settings = get_or_create_settings(session, tenant_id)
    result = ExpiryNotificationRunResult(checked=0, sent=0, skipped=0, errors=0)
    if not settings.enabled:
        result.details.append("Avisos desactivados en configuración")
        return result

    thresholds = parse_days_before(settings.days_before)
    today = date.today()
    docs = list(
        session.exec(
            select(DocumentDelivery).where(
                DocumentDelivery.tenant_id == tenant_id,
                DocumentDelivery.expires_at.is_not(None),  # type: ignore[union-attr]
            )
        ).all()
    )

    gowa = GoWAService(session) if settings.channel_whatsapp else None
    mail = MailService(session) if settings.channel_email else None

    for doc in docs:
        if not doc.expires_at:
            continue
        days_left = (doc.expires_at - today).days
        if days_left not in thresholds:
            continue
        result.checked += 1
        label = _doc_label(doc)
        when = (
            "hoy"
            if days_left == 0
            else f"en {days_left} día(s)" if days_left > 0 else "ya caducó"
        )
        body = (
            f"El documento «{label}» caduca el {doc.expires_at.strftime('%d/%m/%Y')} ({when})."
        )

        recipients_whatsapp: list[tuple[str, str]] = []
        recipients_email: list[tuple[str, str]] = []

        if settings.notify_employee and doc.employee_id:
            emp = session.get(Employee, doc.employee_id)
            if emp:
                if emp.phone:
                    recipients_whatsapp.append((emp.phone, emp.full_name))
                if emp.email:
                    recipients_email.append((emp.email, emp.full_name))

        if settings.notify_managers:
            for mgr in _managers_for_document(session, tenant_id, doc):
                if mgr.phone:
                    recipients_whatsapp.append((mgr.phone, mgr.full_name))
                if mgr.email:
                    recipients_email.append((mgr.email, mgr.full_name))

        for email in parse_extra_emails(settings.extra_emails):
            recipients_email.append((email, email))

        # dedupe
        seen_wa: set[str] = set()
        seen_em: set[str] = set()
        unique_wa = []
        for phone, name in recipients_whatsapp:
            key = phone.strip()
            if key in seen_wa:
                continue
            seen_wa.add(key)
            unique_wa.append((phone, name))
        unique_em = []
        for email, name in recipients_email:
            key = email.strip().lower()
            if key in seen_em:
                continue
            seen_em.add(key)
            unique_em.append((email, name))

        if settings.channel_whatsapp and gowa:
            for phone, name in unique_wa:
                recipient = phone.strip()
                if _already_sent(session, doc.id, days_left, "whatsapp", recipient):
                    result.skipped += 1
                    continue
                if dry_run:
                    result.sent += 1
                    continue
                try:
                    await gowa.send_text(
                        recipient,
                        f"⚠️ Aviso documento\n{body}\n— {name}",
                    )
                    _log_send(
                        session,
                        tenant_id=tenant_id,
                        document_id=doc.id,
                        days_before=days_left,
                        channel="whatsapp",
                        recipient=recipient,
                        success=True,
                        detail=None,
                    )
                    result.sent += 1
                except Exception as exc:
                    _log_send(
                        session,
                        tenant_id=tenant_id,
                        document_id=doc.id,
                        days_before=days_left,
                        channel="whatsapp",
                        recipient=recipient,
                        success=False,
                        detail=str(exc),
                    )
                    result.errors += 1
                    result.details.append(f"WA {recipient}: {exc}")

        if settings.channel_email and mail:
            subject = f"Documento próximo a caducar: {doc.file_name}"
            for email, name in unique_em:
                recipient = email.strip().lower()
                if _already_sent(session, doc.id, days_left, "email", recipient):
                    result.skipped += 1
                    continue
                if dry_run:
                    result.sent += 1
                    continue
                ok, detail = mail.send(
                    recipient,
                    subject,
                    f"Hola {name},\n\n{body}\n",
                    event_type="document_expiry",
                    tenant_id=tenant_id,
                )
                _log_send(
                    session,
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    days_before=days_left,
                    channel="email",
                    recipient=recipient,
                    success=ok,
                    detail=detail,
                )
                if ok:
                    result.sent += 1
                else:
                    result.errors += 1
                    result.details.append(f"Email {recipient}: {detail}")

    if not dry_run:
        session.commit()
    return result
