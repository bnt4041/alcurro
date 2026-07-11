from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.communication import (
    Communication,
    RecipientStatus,
)
from app.models.models import Employee
from app.schemas.communication import (
    AttachmentRead,
    CommunicationAddRecipients,
    CommunicationCancel,
    CommunicationCreate,
    CommunicationDetail,
    CommunicationRead,
    RecipientRead,
)
from app.services.communication_service import (
    add_attachment,
    add_recipients,
    cancel_communication,
    create_communication,
    list_recipients,
    send_communication,
    sync_recipient_statuses,
)
from app.services.communication_service import _attachments as _get_attachments

router = APIRouter(prefix="/communications", tags=["communications"])


def _get_comm(session: Session, tenant_id: UUID, comm_id: UUID) -> Communication:
    comm = session.get(Communication, comm_id)
    if not comm or comm.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")
    return comm


def _read(session: Session, comm: Communication) -> CommunicationRead:
    recipients = list_recipients(session, comm.id)
    sent = sum(
        1
        for r in recipients
        if r.status in (RecipientStatus.SENT, RecipientStatus.READ, RecipientStatus.SIGNED)
    )
    signed = sum(1 for r in recipients if r.status == RecipientStatus.SIGNED)
    data = CommunicationRead.model_validate(comm)
    data.recipient_count = len(recipients)
    data.sent_count = sent
    data.signed_count = signed
    return data


def _detail(session: Session, comm: Communication) -> CommunicationDetail:
    base = _read(session, comm)
    detail = CommunicationDetail(**base.model_dump())
    detail.recipients = [
        RecipientRead.model_validate(r) for r in list_recipients(session, comm.id)
    ]
    detail.attachments = [
        AttachmentRead.model_validate(a) for a in _get_attachments(session, comm.id)
    ]
    return detail


@router.get("", response_model=list[CommunicationRead])
def list_communications(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "communications")),
) -> list[CommunicationRead]:
    from sqlmodel import select

    rows = list(
        session.exec(
            select(Communication)
            .where(Communication.tenant_id == ctx.tenant.id)
            .order_by(Communication.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )
    return [_read(session, c) for c in rows]


@router.post("", response_model=CommunicationDetail, status_code=201)
def create_communication_route(
    data: CommunicationCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.WRITE, "communications")),
) -> CommunicationDetail:
    comm = create_communication(
        session,
        ctx.tenant.id,
        ctx.company.id,
        title=data.title,
        body=data.body,
        mode=data.mode,
        audience=data.audience.model_dump(mode="json"),
        externals=[e.model_dump() for e in data.externals],
        created_by_id=user.id,
        expires_in_days=data.expires_in_days,
    )
    return _detail(session, comm)


@router.get("/{comm_id}", response_model=CommunicationDetail)
def get_communication(
    comm_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "communications")),
) -> CommunicationDetail:
    comm = _get_comm(session, ctx.tenant.id, comm_id)
    sync_recipient_statuses(session, comm)
    return _detail(session, comm)


@router.post("/{comm_id}/attachments", response_model=AttachmentRead, status_code=201)
async def upload_attachment(
    comm_id: UUID,
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "communications")),
) -> AttachmentRead:
    comm = _get_comm(session, ctx.tenant.id, comm_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    row = add_attachment(session, comm, file.filename or "adjunto", content)
    return AttachmentRead.model_validate(row)


@router.post("/{comm_id}/send", response_model=CommunicationDetail)
def send_communication_route(
    comm_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "communications")),
) -> CommunicationDetail:
    comm = _get_comm(session, ctx.tenant.id, comm_id)
    comm = send_communication(session, comm)
    return _detail(session, comm)


@router.post("/{comm_id}/cancel", response_model=CommunicationDetail)
def cancel_communication_route(
    comm_id: UUID,
    data: CommunicationCancel,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "communications")),
) -> CommunicationDetail:
    comm = _get_comm(session, ctx.tenant.id, comm_id)
    comm = cancel_communication(session, comm, data.reason)
    return _detail(session, comm)


@router.post("/{comm_id}/recipients", response_model=CommunicationDetail)
def add_recipients_route(
    comm_id: UUID,
    data: CommunicationAddRecipients,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "communications")),
) -> CommunicationDetail:
    comm = _get_comm(session, ctx.tenant.id, comm_id)
    add_recipients(
        session,
        comm,
        audience=data.audience.model_dump(mode="json"),
        externals=[e.model_dump() for e in data.externals],
    )
    session.refresh(comm)
    return _detail(session, comm)
