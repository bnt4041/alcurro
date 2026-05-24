"""Envío SMTP y registro de correos."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from uuid import UUID

from sqlmodel import Session, select

from app.models.mail import MailLog
from app.models.settings import SystemSettings
from app.schemas.mail import MailSettingsRead, MailSettingsUpdate
from app.services.settings_service import SettingsService


def smtp_configured(settings: SystemSettings) -> bool:
    return bool(settings.smtp_host and settings.mail_from_address)


class MailService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._settings = SettingsService(session).get_or_create()

    def read_settings(self) -> MailSettingsRead:
        s = self._settings
        return MailSettingsRead(
            smtp_host=s.smtp_host,
            smtp_port=s.smtp_port or 587,
            smtp_user=s.smtp_user,
            smtp_use_tls=s.smtp_use_tls,
            mail_from_address=s.mail_from_address,
            mail_from_name=s.mail_from_name,
            smtp_password_configured=bool(s.smtp_password),
            updated_at=s.updated_at,
        )

    def update_settings(self, data: MailSettingsUpdate) -> MailSettingsRead:
        payload = data.model_dump(exclude_unset=True)
        password = payload.pop("smtp_password", None)
        for key, value in payload.items():
            setattr(self._settings, key, value)
        if password:
            self._settings.smtp_password = password
        self._session.add(self._settings)
        self._session.commit()
        self._session.refresh(self._settings)
        return self.read_settings()

    def list_logs(
        self,
        *,
        limit: int = 100,
        success_only: bool | None = None,
    ) -> list[MailLog]:
        stmt = select(MailLog).order_by(MailLog.created_at.desc())  # type: ignore[attr-defined]
        if success_only is True:
            stmt = stmt.where(MailLog.success == True)  # noqa: E712
        elif success_only is False:
            stmt = stmt.where(MailLog.success == False)  # noqa: E712
        return list(self._session.exec(stmt.limit(min(limit, 500))).all())

    def log(
        self,
        *,
        to_address: str,
        subject: str,
        event_type: str,
        success: bool,
        detail: str | None = None,
        tenant_id: UUID | None = None,
        envelope_id: UUID | None = None,
    ) -> MailLog:
        row = MailLog(
            to_address=to_address[:255],
            subject=subject[:500],
            event_type=event_type,
            success=success,
            detail=(detail or "")[:1000] or None,
            tenant_id=tenant_id,
            envelope_id=envelope_id,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def send(
        self,
        to_address: str,
        subject: str,
        body: str,
        *,
        event_type: str = "generic",
        tenant_id: UUID | None = None,
        envelope_id: UUID | None = None,
    ) -> tuple[bool, str | None]:
        settings = self._settings
        if not smtp_configured(settings):
            detail = "SMTP no configurado (host o remitente)"
            self.log(
                to_address=to_address,
                subject=subject,
                event_type=event_type,
                success=False,
                detail=detail,
                tenant_id=tenant_id,
                envelope_id=envelope_id,
            )
            self._session.commit()
            return False, detail

        from_name = settings.mail_from_name or "alcurro"
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{settings.mail_from_address}>"
        msg["To"] = to_address
        msg.set_content(body)

        try:
            self._deliver(msg, settings)
            self.log(
                to_address=to_address,
                subject=subject,
                event_type=event_type,
                success=True,
                tenant_id=tenant_id,
                envelope_id=envelope_id,
            )
            self._session.commit()
            return True, None
        except Exception as exc:
            detail = str(exc)
            self.log(
                to_address=to_address,
                subject=subject,
                event_type=event_type,
                success=False,
                detail=detail,
                tenant_id=tenant_id,
                envelope_id=envelope_id,
            )
            self._session.commit()
            return False, detail

    def _deliver(self, msg: EmailMessage, settings: SystemSettings) -> None:
        host = settings.smtp_host or ""
        port = settings.smtp_port or 587
        user = settings.smtp_user or ""
        password = settings.smtp_password or ""

        if settings.smtp_use_tls and port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                context = ssl.create_default_context()
                smtp.starttls(context=context)
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)

    def send_test(self, to_email: str) -> tuple[bool, str, str | None]:
        ok, detail = self.send(
            to_email.strip(),
            "Prueba SMTP — alcurro",
            (
                "Este es un correo de prueba enviado desde el panel de administración de alcurro.\n\n"
                "Si lo recibes, la configuración SMTP es correcta."
            ),
            event_type="test",
        )
        if ok:
            return True, f"Correo de prueba enviado a {to_email}", None
        return False, "No se pudo enviar el correo de prueba", detail
