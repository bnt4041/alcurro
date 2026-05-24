"""Notificaciones de firma por WhatsApp (goWA)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlmodel import Session

from app.models.signature import SignatureEnvelope, SignatureNotification, SignatureSigner
from app.models.tenant import Tenant
from app.services.gowa_service import GoWAService


def _tenant_country(session: Session, envelope: SignatureEnvelope) -> str:
    tenant = session.get(Tenant, envelope.tenant_id)
    return (tenant.billing_country if tenant else None) or "ES"


def _gowa(session: Session, envelope: SignatureEnvelope) -> GoWAService:
    return GoWAService(session, country_iso=_tenant_country(session, envelope))


def _log_notification(
    session: Session,
    envelope_id,
    signer_id,
    channel: str,
    event_type: str,
    success: bool,
    detail: str | None = None,
) -> None:
    session.add(
        SignatureNotification(
            envelope_id=envelope_id,
            signer_id=signer_id,
            channel=channel,
            event_type=event_type,
            success=success,
            detail=(detail or "")[:500] or None,
        )
    )


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def notify_signer(
    session: Session,
    envelope: SignatureEnvelope,
    signer: SignatureSigner,
    *,
    event_type: str,
    company_name: str,
    link: str,
) -> None:
    caption = (
        f"📝 *{company_name}* — Firma de documento\n"
        f"Documento: {envelope.title}\n"
        f"Referencia: {envelope.reference}\n\n"
        f"Enlace para firmar (pulsa para abrir):\n{link}\n\n"
        f"Necesitarás tu DNI/NIE y un código que te enviaremos por este canal."
    )
    if signer.phone:
        try:
            gowa = _gowa(session, envelope)
            try:
                _run_async(gowa.send_link(signer.phone, link, caption))
            except Exception:
                _run_async(gowa.send_text(signer.phone, caption))
            _log_notification(
                session, envelope.id, signer.id, "whatsapp", event_type, True
            )
        except Exception as exc:
            _log_notification(
                session,
                envelope.id,
                signer.id,
                "whatsapp",
                event_type,
                False,
                str(exc)[:500],
            )
    if signer.email:
        subject = f"Firma de documento — {envelope.reference}"
        body = (
            f"Hola {signer.full_name},\n\n"
            f"{company_name} te solicita firmar: {envelope.title}\n"
            f"Referencia: {envelope.reference}\n\n"
            f"Accede para firmar:\n{link}\n\n"
            f"Necesitarás tu DNI/NIE y un código que también recibirás por WhatsApp si aplica."
        )
        from app.services.mail_service import MailService

        ok, err = MailService(session).send(
            signer.email,
            subject,
            body,
            event_type=f"firma_{event_type}",
            tenant_id=envelope.tenant_id,
            envelope_id=envelope.id,
        )
        _log_notification(
            session,
            envelope.id,
            signer.id,
            "email",
            event_type,
            ok,
            err,
        )


def send_otp(
    session: Session,
    signer: SignatureSigner,
    code: str,
    envelope: SignatureEnvelope,
) -> None:
    msg = (
        f"🔐 Código de firma — {envelope.reference}\n"
        f"Tu código es: *{code}*\n"
        f"Válido 10 minutos. No lo compartas con nadie."
    )
    if signer.phone:
        try:
            _run_async(_gowa(session, envelope).send_text(signer.phone, msg))
            _log_notification(session, envelope.id, signer.id, "whatsapp", "otp", True)
        except Exception as exc:
            _log_notification(
                session, envelope.id, signer.id, "whatsapp", "otp", False, str(exc)[:500]
            )
    if signer.email:
        from app.services.mail_service import MailService

        subject = f"Código de firma — {envelope.reference}"
        body = (
            f"Tu código de verificación es: {code}\n\n"
            f"Válido 10 minutos. No lo compartas con nadie.\n"
            f"Referencia: {envelope.reference}"
        )
        ok, err = MailService(session).send(
            signer.email,
            subject,
            body,
            event_type="firma_otp",
            tenant_id=envelope.tenant_id,
            envelope_id=envelope.id,
        )
        _log_notification(session, envelope.id, signer.id, "email", "otp", ok, err)


def notify_completed(session: Session, envelope: SignatureEnvelope) -> None:
    from sqlmodel import select

    signers = list(
        session.exec(
            select(SignatureSigner).where(SignatureSigner.envelope_id == envelope.id)
        ).all()
    )
    msg = (
        f"✅ Documento firmado — {envelope.reference}\n"
        f"{envelope.title}\n"
        f"Todas las firmas están completadas."
    )
    for signer in signers:
        if signer.phone:
            try:
                _run_async(_gowa(session, envelope).send_text(signer.phone, msg))
                _log_notification(
                    session, envelope.id, signer.id, "whatsapp", "completada", True
                )
            except Exception as exc:
                _log_notification(
                    session,
                    envelope.id,
                    signer.id,
                    "whatsapp",
                    "completada",
                    False,
                    str(exc)[:500],
                )


def notify_cancelled(
    session: Session, envelope: SignatureEnvelope, reason: str
) -> None:
    from sqlmodel import select

    signers = list(
        session.exec(
            select(SignatureSigner).where(SignatureSigner.envelope_id == envelope.id)
        ).all()
    )
    msg = (
        f"❌ Firma cancelada — {envelope.reference}\n"
        f"Motivo: {reason}"
    )
    for signer in signers:
        if signer.phone:
            try:
                _run_async(_gowa(session, envelope).send_text(signer.phone, msg))
                _log_notification(
                    session, envelope.id, signer.id, "whatsapp", "cancelada", True
                )
            except Exception as exc:
                _log_notification(
                    session,
                    envelope.id,
                    signer.id,
                    "whatsapp",
                    "cancelada",
                    False,
                    str(exc)[:500],
                )
