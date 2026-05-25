import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.models import Employee
from app.models.signature import SignatureEnvelope, SignatureSigner
from app.schemas.signature import (
    SignatureEnvelopeCancel,
    SignatureEnvelopeCreate,
    SignatureEnvelopeRead,
)
from app.services.scope_service import is_read_own_only
from app.services.signature_service import (
    cancel_envelope,
    create_envelope,
    create_envelope_from_upload,
    envelope_to_read,
    resend_signer,
)

router = APIRouter(prefix="/signatures", tags=["signatures"])


@router.get("", response_model=list[SignatureEnvelopeRead])
def list_envelopes(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    status: str | None = None,
    employee_id: UUID | None = None,
    _: object = Depends(require_permission(Permission.READ, "signatures")),
) -> list[SignatureEnvelopeRead]:
    stmt = (
        select(SignatureEnvelope)
        .where(SignatureEnvelope.tenant_id == ctx.tenant.id)
        .order_by(SignatureEnvelope.created_at.desc())  # type: ignore[attr-defined]
    )
    if is_read_own_only(session, user, ctx.tenant.id, "signatures"):
        own_env_ids = session.exec(
            select(SignatureSigner.envelope_id).where(
                SignatureSigner.employee_id == user.id
            )
        ).all()
        if not own_env_ids:
            return []
        stmt = stmt.where(SignatureEnvelope.id.in_(own_env_ids))  # type: ignore[attr-defined]
    if status:
        stmt = stmt.where(SignatureEnvelope.status == status)
    if employee_id:
        env_ids = list(
            session.exec(
                select(SignatureSigner.envelope_id).where(
                    SignatureSigner.employee_id == employee_id
                )
            ).all()
        )
        if not env_ids:
            return []
        stmt = stmt.where(SignatureEnvelope.id.in_(env_ids))  # type: ignore[attr-defined]
    rows = list(session.exec(stmt).all())
    return [envelope_to_read(session, e) for e in rows]


@router.get("/{envelope_id}", response_model=SignatureEnvelopeRead)
def get_envelope(
    envelope_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "signatures")),
) -> SignatureEnvelopeRead:
    row = session.get(SignatureEnvelope, envelope_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return envelope_to_read(session, row)


@router.post("", response_model=SignatureEnvelopeRead, status_code=201)
def create_signature_envelope(
    data: SignatureEnvelopeCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("signatures", "create")),
) -> SignatureEnvelopeRead:
    try:
        row = create_envelope(
            session,
            ctx.tenant.id,
            ctx.company.id,
            data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope_to_read(session, row)


@router.post("/from-upload", response_model=SignatureEnvelopeRead, status_code=201)
async def create_signature_from_upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    signers_json: str = Form(...),
    owner_employee_id: UUID | None = Form(None),
    send_notifications: bool = Form(True),
    expires_in_days: int = Form(14),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("signatures", "create")),
) -> SignatureEnvelopeRead:
    try:
        signers_data = json.loads(signers_json)
        if not isinstance(signers_data, list) or not signers_data:
            raise ValueError("Indica al menos un firmante")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Formato de firmantes inválido") from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    try:
        row = create_envelope_from_upload(
            session,
            ctx.tenant.id,
            ctx.company.id,
            file_name=file.filename or "documento.pdf",
            content=content,
            title=title.strip() or None,
            signers_data=signers_data,
            owner_employee_id=owner_employee_id,
            send_notifications=send_notifications,
            expires_in_days=expires_in_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope_to_read(session, row)


@router.post("/{envelope_id}/cancel", response_model=SignatureEnvelopeRead)
def cancel_signature_envelope(
    envelope_id: UUID,
    data: SignatureEnvelopeCancel,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("signatures", "update")),
) -> SignatureEnvelopeRead:
    row = session.get(SignatureEnvelope, envelope_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    cancel_envelope(session, row, data.reason)
    session.refresh(row)
    return envelope_to_read(session, row)


@router.post("/{envelope_id}/signers/{signer_id}/resend")
def resend_signer_link(
    envelope_id: UUID,
    signer_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("signatures", "update")),
) -> dict[str, str]:
    row = session.get(SignatureEnvelope, envelope_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    signer = session.get(SignatureSigner, signer_id)
    if not signer or signer.envelope_id != row.id:
        raise HTTPException(status_code=404, detail="Firmante no encontrado")
    result = resend_signer(session, row, signer)
    return result


@router.get("/{envelope_id}/signed")
def download_signed(
    envelope_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "signatures")),
) -> FileResponse:
    row = session.get(SignatureEnvelope, envelope_id)
    if not row or row.tenant_id != ctx.tenant.id or not row.signed_path:
        raise HTTPException(status_code=404, detail="PDF firmado no disponible")
    path = Path(row.signed_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{row.reference}_signed.pdf",
    )


@router.get("/{envelope_id}/certificate")
def download_certificate(
    envelope_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "signatures")),
) -> FileResponse:
    row = session.get(SignatureEnvelope, envelope_id)
    if not row or row.tenant_id != ctx.tenant.id or not row.certificate_path:
        raise HTTPException(status_code=404, detail="Certificado no disponible")
    path = Path(row.certificate_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{row.reference}_cert.pdf",
    )
