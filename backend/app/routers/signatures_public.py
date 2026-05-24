from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.database import get_session
from app.models.signature import EnvelopeStatus, SignatureEnvelope
from app.models.tenant import Tenant
from app.schemas.signature import (
    PublicSignRequest,
    PublicSignerMeta,
    PublicStartRequest,
    PublicVerifyOtpRequest,
)
from app.services.signature_service import (
    get_signer_by_token,
    public_sign,
    public_start,
    public_verify_otp,
)

router = APIRouter(prefix="/public/firma", tags=["signatures-public"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/{token}", response_model=PublicSignerMeta)
def public_meta(
    token: str,
    session: Session = Depends(get_session),
) -> PublicSignerMeta:
    signer = get_signer_by_token(session, token)
    if not signer:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    envelope = session.get(SignatureEnvelope, signer.envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    tenant = session.get(Tenant, envelope.tenant_id)
    email_hint = None
    if signer.email:
        parts = signer.email.split("@")
        email_hint = f"{parts[0][:2]}***@{parts[1]}" if len(parts) == 2 else "***"
    phone_hint = None
    if signer.phone and len(signer.phone) >= 4:
        phone_hint = f"***{signer.phone[-4:]}"
    return PublicSignerMeta(
        full_name=signer.full_name,
        document_title=envelope.title,
        company_name=tenant.name if tenant else "Empresa",
        email_hint=email_hint,
        phone_hint=phone_hint,
        status=signer.status,
        envelope_status=envelope.status,
        requires_otp=True,
    )


@router.post("/{token}/start")
def public_start_signing(
    token: str,
    data: PublicStartRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    signer = get_signer_by_token(session, token)
    if not signer:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    public_start(session, signer, data.id_document, data.email, data.phone)
    return {"message": "Código enviado por WhatsApp"}


@router.post("/{token}/verify-otp")
def public_verify(
    token: str,
    data: PublicVerifyOtpRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    signer = get_signer_by_token(session, token)
    if not signer:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    public_verify_otp(session, signer, data.code)
    return {"message": "Código verificado"}


@router.post("/{token}/sign")
def public_sign_document(
    token: str,
    data: PublicSignRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not data.accept_terms:
        raise HTTPException(status_code=400, detail="Debes aceptar los términos")
    signer = get_signer_by_token(session, token)
    if not signer:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    public_sign(
        session,
        signer,
        data.signature_base64,
        data.signer_name,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    envelope = session.get(SignatureEnvelope, signer.envelope_id)
    done = envelope and envelope.status == EnvelopeStatus.COMPLETED
    return {
        "message": "Firma registrada correctamente",
        "envelope_completed": str(done).lower(),
    }


@router.get("/{token}/download-signed")
def public_download_signed(
    token: str,
    session: Session = Depends(get_session),
) -> FileResponse:
    signer = get_signer_by_token(session, token)
    if not signer:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    envelope = session.get(SignatureEnvelope, signer.envelope_id)
    if not envelope or envelope.status != EnvelopeStatus.COMPLETED or not envelope.signed_path:
        raise HTTPException(status_code=404, detail="Documento aún no disponible")
    path = Path(envelope.signed_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{envelope.reference}_signed.pdf",
    )
