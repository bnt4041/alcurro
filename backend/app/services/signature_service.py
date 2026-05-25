"""Orquestación de envelopes y flujo de firma."""

from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.models.documents import DocumentDelivery
from app.models.models import Employee
from app.models.signature import (
    EnvelopeStatus,
    SignatureEnvelope,
    SignatureNotification,
    SignatureOtp,
    SignatureSigner,
    SignerStatus,
)
from app.models.tenant import Company, Tenant
from app.schemas.signature import (
    SignatureEnvelopeCreate,
    SignatureEnvelopeRead,
    SignatureSignerRead,
    SignerInput,
)
from app.schemas.whatsapp import normalize_mobile_digits
from app.services.id_document import normalize_id_document
from app.services.signature_audit import append_event
from app.services.signature_pdf import file_sha256, finalize_signed_pdf
from app.services.signature_tokens import (
    generate_otp,
    generate_signer_token,
    hash_otp,
    hash_token,
    otp_expires_at,
)

UPLOAD_DIR = Path("/app/uploads")
MAX_OTP_ATTEMPTS = 5


def _envelope_ref() -> str:
    return f"FRM-{datetime.utcnow():%Y%m%d}-{datetime.utcnow().strftime('%H%M%S')}"


def _signing_url(token: str) -> str:
    base = get_settings().public_app_url.rstrip("/")
    return f"{base}/firmar/{token}"


def _normalize_phone(phone: str | None, country_iso: str) -> str | None:
    if not phone or not str(phone).strip():
        return None
    return normalize_mobile_digits(str(phone).strip(), country_iso)


def _resolve_signer(
    session: Session, data: SignerInput, company_id: UUID, country_iso: str = "ES"
) -> dict:
    if data.employee_id:
        emp = session.get(Employee, data.employee_id)
        if not emp or emp.company_id != company_id:
            raise ValueError("Empleado no válido para esta empresa")
        return {
            "employee_id": emp.id,
            "full_name": emp.full_name,
            "email": emp.email,
            "phone": _normalize_phone(emp.phone, country_iso),
            "id_document": normalize_id_document(emp.id_document or data.id_document or ""),
            "sign_order": data.sign_order,
        }
    if not data.full_name or not data.id_document or not data.phone:
        raise ValueError("Firmante externo requiere nombre, DNI/NIE y teléfono")
    return {
        "employee_id": None,
        "full_name": data.full_name.strip(),
        "email": (data.email or "").strip() or None,
        "phone": _normalize_phone(data.phone, country_iso),
        "id_document": normalize_id_document(data.id_document),
        "sign_order": data.sign_order,
    }


def envelope_to_read(
    session: Session, envelope: SignatureEnvelope
) -> SignatureEnvelopeRead:
    signers = list(
        session.exec(
            select(SignatureSigner)
            .where(SignatureSigner.envelope_id == envelope.id)
            .order_by(SignatureSigner.sign_order)  # type: ignore[attr-defined]
        ).all()
    )
    base = SignatureEnvelopeRead.model_validate(envelope)
    base.signers = [SignatureSignerRead.model_validate(s) for s in signers]
    return base


def _document_belongs_to_company(
    session: Session, doc: DocumentDelivery, company_id: UUID
) -> bool:
    if doc.company_id:
        return doc.company_id == company_id
    if doc.employee_id:
        emp = session.get(Employee, doc.employee_id)
        return bool(emp and emp.company_id == company_id)
    return False


def create_envelope(
    session: Session,
    tenant_id: UUID,
    company_id: UUID,
    data: SignatureEnvelopeCreate,
) -> SignatureEnvelope:
    original_path: Path
    title = data.title

    if data.document_delivery_id:
        doc = session.get(DocumentDelivery, data.document_delivery_id)
        if not doc:
            raise ValueError("Documento no encontrado")
        if not _document_belongs_to_company(session, doc, company_id):
            raise ValueError("Documento fuera de la empresa activa")
        original_path = Path(doc.file_path)
        if not original_path.exists() or original_path.stat().st_size == 0:
            raise ValueError("El archivo del documento está vacío o no existe")
        title = title or doc.file_name
    else:
        raise ValueError("Indica document_delivery_id")

    original_hash = file_sha256(original_path)
    env_dir = UPLOAD_DIR / "firma" / "staging"
    env_dir.mkdir(parents=True, exist_ok=True)

    envelope = SignatureEnvelope(
        tenant_id=tenant_id,
        document_delivery_id=data.document_delivery_id,
        reference=_envelope_ref(),
        title=title,
        status=EnvelopeStatus.DRAFT,
        original_path=str(original_path),
        original_hash=original_hash,
        expires_at=datetime.utcnow() + timedelta(days=data.expires_in_days),
    )
    session.add(envelope)
    session.flush()

    append_event(
        session,
        envelope.id,
        "envelope_created",
        {"reference": envelope.reference, "original_hash": original_hash},
    )

    tenant = session.get(Tenant, tenant_id)
    country_iso = (tenant.billing_country if tenant else None) or "ES"

    orders = sorted(data.signers, key=lambda s: s.sign_order)
    for idx, signer_in in enumerate(orders, start=1):
        resolved = _resolve_signer(session, signer_in, company_id, country_iso)
        plain, token_hash = generate_signer_token()
        signer = SignatureSigner(
            envelope_id=envelope.id,
            employee_id=resolved["employee_id"],
            full_name=resolved["full_name"],
            email=resolved["email"],
            phone=resolved["phone"],
            id_document=resolved["id_document"],
            sign_order=signer_in.sign_order or idx,
            token_hash=token_hash,
            token_plain=plain,
        )
        session.add(signer)
        session.flush()
        append_event(
            session,
            envelope.id,
            "signer_added",
            {"signer_id": str(signer.id), "name": signer.full_name},
        )

    if data.send_notifications:
        _send_envelope(session, envelope)
    else:
        envelope.status = EnvelopeStatus.SENT
        session.add(envelope)

    session.commit()
    session.refresh(envelope)
    return envelope


def _store_document_delivery(
    session: Session,
    company_id: UUID,
    file_name: str,
    content: bytes,
    employee_id: UUID | None = None,
) -> DocumentDelivery:
    if employee_id:
        emp = session.get(Employee, employee_id)
        if not emp or emp.company_id != company_id:
            raise ValueError("Empleado no válido para asociar el documento")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file_name).name or "documento.pdf"
    stored = UPLOAD_DIR / f"{uuid4()}_{safe_name}"
    stored.write_bytes(content)
    company = session.get(Company, company_id)
    if not company:
        raise ValueError("Empresa no válida")
    row = DocumentDelivery(
        tenant_id=company.tenant_id,
        company_id=company_id if not employee_id else None,
        employee_id=employee_id,
        file_path=str(stored),
        file_name=safe_name,
        document_type="firma",
        requires_acknowledgment=False,
    )
    session.add(row)
    session.flush()
    return row


def _parse_signers_payload(signers_data: list[dict]) -> list[SignerInput]:
    return [SignerInput.model_validate(item) for item in signers_data]


def _resolve_owner_employee_id(
    signers: list[SignerInput], owner_employee_id: UUID | None
) -> UUID | None:
    if owner_employee_id:
        return owner_employee_id
    for s in signers:
        if s.employee_id:
            return s.employee_id
    return None


def create_envelope_from_upload(
    session: Session,
    tenant_id: UUID,
    company_id: UUID,
    *,
    file_name: str,
    content: bytes,
    title: str | None,
    signers_data: list[dict],
    owner_employee_id: UUID | None,
    send_notifications: bool,
    expires_in_days: int,
) -> SignatureEnvelope:
    signers = _parse_signers_payload(signers_data)
    owner_id = _resolve_owner_employee_id(signers, owner_employee_id)
    doc = _store_document_delivery(
        session, company_id, file_name, content, employee_id=owner_id
    )
    data = SignatureEnvelopeCreate(
        document_delivery_id=doc.id,
        title=title or doc.file_name,
        signers=signers,
        send_notifications=send_notifications,
        expires_in_days=expires_in_days,
    )
    return create_envelope(session, tenant_id, company_id, data)


def _send_envelope(session: Session, envelope: SignatureEnvelope) -> None:
    from app.services.signature_notify import notify_signer

    signers = list(
        session.exec(
            select(SignatureSigner).where(SignatureSigner.envelope_id == envelope.id)
        ).all()
    )
    tenant = session.get(Tenant, envelope.tenant_id)
    company_name = tenant.name if tenant else "Empresa"

    for signer in signers:
        if not signer.token_plain:
            continue
        link = _signing_url(signer.token_plain)
        notify_signer(
            session,
            envelope,
            signer,
            event_type="solicitud",
            company_name=company_name,
            link=link,
        )
        signer.token_plain = None
        session.add(signer)

    envelope.status = EnvelopeStatus.SENT
    envelope.updated_at = datetime.utcnow()
    session.add(envelope)
    append_event(session, envelope.id, "envelope_sent", {})


def get_signer_by_token(session: Session, token: str) -> SignatureSigner | None:
    th = hash_token(token)
    return session.exec(
        select(SignatureSigner).where(SignatureSigner.token_hash == th)
    ).first()


def public_start(
    session: Session,
    signer: SignatureSigner,
    id_document: str,
    email: str | None,
    phone: str | None,
) -> str:
    envelope = session.get(SignatureEnvelope, signer.envelope_id)
    if not envelope or envelope.status in (
        EnvelopeStatus.CANCELLED,
        EnvelopeStatus.COMPLETED,
        EnvelopeStatus.EXPIRED,
    ):
        raise HTTPException(status_code=410, detail="Solicitud de firma no disponible")

    if envelope.expires_at and envelope.expires_at < datetime.utcnow():
        envelope.status = EnvelopeStatus.EXPIRED
        session.add(envelope)
        session.commit()
        raise HTTPException(status_code=410, detail="La solicitud de firma ha expirado")

    doc_norm = normalize_id_document(id_document)
    if doc_norm != signer.id_document:
        raise HTTPException(status_code=403, detail="DNI/NIE no coincide")

    if email and signer.email and email.strip().lower() != signer.email.lower():
        raise HTTPException(status_code=403, detail="Email no coincide")
    if phone and signer.phone:
        p1 = re.sub(r"\D", "", phone)
        p2 = re.sub(r"\D", "", signer.phone)
        if p1 and p2 and not (p1.endswith(p2[-9:]) or p2.endswith(p1[-9:])):
            raise HTTPException(status_code=403, detail="Teléfono no coincide")

    code, code_hash = generate_otp()
    session.add(
        SignatureOtp(
            signer_id=signer.id,
            code_hash=code_hash,
            expires_at=otp_expires_at(10),
        )
    )
    append_event(
        session,
        signer.envelope_id,
        "otp_issued",
        {"signer_id": str(signer.id)},
    )
    session.commit()

    from app.services.signature_notify import send_otp

    send_otp(session, signer, code, envelope)
    return "OTP enviado"


def public_verify_otp(session: Session, signer: SignatureSigner, code: str) -> None:
    row = session.exec(
        select(SignatureOtp)
        .where(
            SignatureOtp.signer_id == signer.id,
            SignatureOtp.used_at == None,  # noqa: E711
        )
        .order_by(SignatureOtp.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    if not row:
        raise HTTPException(status_code=400, detail="No hay código activo")
    if row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Código expirado")
    if row.attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Demasiados intentos")

    row.attempts += 1
    if hash_otp(code.strip()) != row.code_hash:
        session.add(row)
        session.commit()
        raise HTTPException(status_code=403, detail="Código incorrecto")

    row.used_at = datetime.utcnow()
    signer.status = SignerStatus.AUTHENTICATED
    signer.otp_verified_at = datetime.utcnow()
    session.add(row)
    session.add(signer)
    append_event(
        session,
        signer.envelope_id,
        "otp_verified",
        {"signer_id": str(signer.id)},
    )
    session.commit()


def public_sign(
    session: Session,
    signer: SignatureSigner,
    signature_base64: str,
    signer_name: str,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    if signer.status == SignerStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Ya has firmado este documento")
    envelope = session.get(SignatureEnvelope, signer.envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="Envelope no encontrado")

    if not signer.otp_verified_at:
        raise HTTPException(status_code=403, detail="Debes verificar el código OTP primero")

    match = re.match(r"^data:image/(png|jpeg);base64,(.+)$", signature_base64, re.I)
    raw_b64 = match.group(2) if match else signature_base64
    try:
        img_bytes = base64.b64decode(raw_b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Imagen de firma inválida") from exc

    sig_dir = UPLOAD_DIR / "firma" / f"envelope-{envelope.id}" / "signatures"
    sig_dir.mkdir(parents=True, exist_ok=True)
    sig_path = sig_dir / f"signer-{signer.id}.png"
    sig_path.write_bytes(img_bytes)

    signer.status = SignerStatus.SIGNED
    signer.signed_at = datetime.utcnow()
    signer.signature_path = str(sig_path)
    signer.signer_name = signer_name.strip()
    signer.ip_address = ip_address
    signer.user_agent = (user_agent or "")[:500] or None
    session.add(signer)

    append_event(
        session,
        envelope.id,
        "document_signed",
        {
            "signer_id": str(signer.id),
            "name": signer.signer_name,
            "ip": ip_address,
        },
    )

    all_signers = list(
        session.exec(
            select(SignatureSigner).where(SignatureSigner.envelope_id == envelope.id)
        ).all()
    )
    signed_count = sum(1 for s in all_signers if s.status == SignerStatus.SIGNED)
    total = len(all_signers)

    if signed_count < total:
        envelope.status = EnvelopeStatus.PARTIAL
    else:
        _finalize_envelope(session, envelope)

    envelope.updated_at = datetime.utcnow()
    session.add(envelope)
    session.commit()


def _finalize_envelope(session: Session, envelope: SignatureEnvelope) -> None:
    paths = finalize_signed_pdf(session, envelope, UPLOAD_DIR)
    envelope.status = EnvelopeStatus.COMPLETED
    envelope.completed_at = datetime.utcnow()
    envelope.signed_path = paths["signed_path"]
    envelope.signed_hash = paths["signed_hash"]
    envelope.certificate_path = paths["certificate_path"]
    envelope.certificate_json_path = paths["certificate_json_path"]
    session.add(envelope)
    append_event(
        session,
        envelope.id,
        "envelope_completed",
        {"signed_hash": envelope.signed_hash},
    )

    from app.services.signature_notify import notify_completed

    notify_completed(session, envelope)


def cancel_envelope(
    session: Session, envelope: SignatureEnvelope, reason: str
) -> None:
    envelope.status = EnvelopeStatus.CANCELLED
    envelope.cancelled_at = datetime.utcnow()
    envelope.cancel_reason = reason
    envelope.updated_at = datetime.utcnow()
    session.add(envelope)

    signers = list(
        session.exec(
            select(SignatureSigner).where(SignatureSigner.envelope_id == envelope.id)
        ).all()
    )
    for s in signers:
        if s.status != SignerStatus.SIGNED:
            s.status = SignerStatus.EXPIRED
            session.add(s)

    append_event(session, envelope.id, "envelope_cancelled", {"reason": reason})
    session.commit()

    from app.services.signature_notify import notify_cancelled

    notify_cancelled(session, envelope, reason)


def resend_signer(session: Session, envelope: SignatureEnvelope, signer: SignatureSigner) -> dict:
    plain, token_hash = generate_signer_token()
    signer.token_hash = token_hash
    signer.token_plain = plain
    signer.status = SignerStatus.PENDING
    signer.otp_verified_at = None
    tenant = session.get(Tenant, envelope.tenant_id)
    country_iso = (tenant.billing_country if tenant else None) or "ES"
    if signer.phone:
        signer.phone = _normalize_phone(signer.phone, country_iso)
    session.add(signer)
    append_event(
        session,
        envelope.id,
        "signer_resent",
        {"signer_id": str(signer.id)},
    )
    session.commit()

    from app.services.signature_notify import notify_signer

    link = _signing_url(plain)
    notify_signer(
        session,
        envelope,
        signer,
        event_type="solicitud",
        company_name=tenant.name if tenant else "Empresa",
        link=link,
    )
    session.commit()
    notif = session.exec(
        select(SignatureNotification)
        .where(
            SignatureNotification.signer_id == signer.id,
            SignatureNotification.channel == "whatsapp",
        )
        .order_by(SignatureNotification.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    signer.token_plain = None
    session.add(signer)
    session.commit()
    wa_ok = bool(notif and notif.success)
    return {
        "link": link,
        "whatsapp_sent": wa_ok,
        "message": "Enlace reenviado por WhatsApp"
        if wa_ok
        else "No se pudo enviar WhatsApp; revisa el teléfono y la configuración goWA",
        "detail": notif.detail if notif and not notif.success else None,
    }
