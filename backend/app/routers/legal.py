from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, has_coarse, require_permission
from app.core.tenant_context import TenantContext
from app.database import get_session
from app.models.legal import LegalDocument
from app.models.models import Employee
from app.routers.crud_helpers import get_or_404
from app.schemas.legal import (
    EmployeeLegalStatusRead,
    LegalAcceptRequest,
    LegalAcceptanceRead,
    LegalDocumentCreate,
    LegalDocumentRead,
    LegalDocumentUpdate,
    LegalTokenAcceptResponse,
    LegalTokenPageRead,
)
from app.services.legal_service import (
    accept_document,
    accept_document_with_pdf,
    create_whatsapp_token,
    employee_legal_status,
    generate_acceptance_certificate,
    validate_token,
)
from app.services.org_service import employee_ids_in_scope

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documents", response_model=list[LegalDocumentRead])
def list_documents(
    ctx: TenantContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    active_only: bool = False,
    _: object = Depends(require_permission(Permission.READ, "legal")),
) -> list[LegalDocument]:
    stmt = select(LegalDocument).where(LegalDocument.tenant_id == ctx.tenant.id)
    if active_only:
        stmt = stmt.where(LegalDocument.is_active == True)  # noqa: E712
    stmt = stmt.order_by(LegalDocument.sort_order, LegalDocument.title)
    return list(session.exec(stmt).all())


@router.post("/documents", response_model=LegalDocumentRead, status_code=201)
def create_document(
    data: LegalDocumentCreate,
    ctx: TenantContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "legal")),
) -> LegalDocument:
    if session.exec(
        select(LegalDocument).where(
            LegalDocument.tenant_id == ctx.tenant.id,
            LegalDocument.code == data.code,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Código de documento duplicado")
    row = LegalDocument(tenant_id=ctx.tenant.id, **data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/documents/{document_id}", response_model=LegalDocumentRead)
def update_document(
    document_id: UUID,
    data: LegalDocumentUpdate,
    ctx: TenantContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "legal")),
) -> LegalDocument:
    row = get_or_404(session, LegalDocument, document_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    payload = data.model_dump(exclude_unset=True, exclude={"bump_version"})
    if data.bump_version and "body" in payload:
        row.version += 1
    for key, value in payload.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: UUID,
    ctx: TenantContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "legal")),
) -> None:
    row = get_or_404(session, LegalDocument, document_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    session.delete(row)
    session.commit()


@router.get("/employees/{employee_id}/status", response_model=EmployeeLegalStatusRead)
def employee_status(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "legal")),
) -> EmployeeLegalStatusRead:
    from app.services.scope_service import is_read_own_only

    if is_read_own_only(session, user, ctx.tenant.id, "legal") and employee_id != user.id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not is_read_own_only(session, user, ctx.tenant.id, "legal"):
        if employee_id not in employee_ids_in_scope(
            session,
            ctx.tenant.id,
            company_id=ctx.company.id,
            work_center_id=ctx.work_center.id if ctx.work_center else None,
            department_id=ctx.department.id if ctx.department else None,
        ):
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
    items, all_ok = employee_legal_status(session, ctx.tenant.id, employee_id)
    return EmployeeLegalStatusRead(
        employee_id=employee_id, all_required_accepted=all_ok, items=items
    )


@router.get("/my/pending", response_model=EmployeeLegalStatusRead)
def my_pending(
    ctx: TenantContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> EmployeeLegalStatusRead:
    items, all_ok = employee_legal_status(session, ctx.tenant.id, user.id)
    return EmployeeLegalStatusRead(
        employee_id=user.id, all_required_accepted=all_ok, items=items
    )


@router.post("/documents/{document_id}/accept", response_model=LegalAcceptanceRead)
def accept_legal_document(
    document_id: UUID,
    data: LegalAcceptRequest,
    ctx: TenantContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
) -> LegalAcceptanceRead:
    target_id = data.employee_id or user.id
    if target_id != user.id and not has_coarse(
        session, user, ctx.tenant.id, Permission.WRITE, "legal"
    ):
        raise HTTPException(
            status_code=403,
            detail="No puedes registrar aceptaciones de otros empleados",
        )
    try:
        row = accept_document_with_pdf(
            session, employee_id=target_id, document_id=document_id, tenant_id=ctx.tenant.id, channel="web"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Generate combined certificate if all required docs are now accepted
    generate_acceptance_certificate(session, tenant_id=ctx.tenant.id, employee_id=target_id)
    return LegalAcceptanceRead.model_validate(row)


# ─── Public token endpoints (no auth required) ────────────────────────────────

public_router = APIRouter(prefix="/legal/public", tags=["legal-public"])


@public_router.get("/token/{token}", response_model=LegalTokenPageRead)
def token_page(
    token: str,
    session: Session = Depends(get_session),
) -> LegalTokenPageRead:
    """Devuelve los datos del empleado y los documentos pendientes de aceptar."""
    try:
        token_row, employee, tenant = validate_token(session, token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items, all_ok = employee_legal_status(session, tenant.id, employee.id)
    pending = [i for i in items if i.is_required and not i.accepted]
    return LegalTokenPageRead(
        employee_name=employee.full_name,
        tenant_name=tenant.name,
        pending_items=pending,
        all_accepted=all_ok,
    )


@public_router.post("/token/{token}/accept/{document_id}", response_model=LegalTokenAcceptResponse)
def token_accept(
    token: str,
    document_id: UUID,
    session: Session = Depends(get_session),
) -> LegalTokenAcceptResponse:
    """Acepta un documento legal usando el token de WhatsApp."""
    try:
        token_row, employee, tenant = validate_token(session, token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        accept_document_with_pdf(
            session,
            employee_id=employee.id,
            document_id=document_id,
            tenant_id=tenant.id,
            channel="whatsapp",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items, all_ok = employee_legal_status(session, tenant.id, employee.id)
    remaining = sum(1 for i in items if i.is_required and not i.accepted)

    if all_ok:
        # Mark token as used
        if token_row.used_at is None:
            from datetime import datetime, timezone
            token_row.used_at = datetime.now(tz=timezone.utc)
            session.add(token_row)
            session.commit()

        # Generate combined PDF certificate
        generate_acceptance_certificate(session, tenant_id=tenant.id, employee_id=employee.id)

        # Send WhatsApp confirmation
        try:
            from app.services.gowa_service import GoWAService
            gowa = GoWAService(session)
            msg = (
                f"Gracias, {employee.full_name}. Has aceptado todos los textos legales requeridos.\n\n"
                "Se ha generado un certificado PDF que encontrarás en el apartado de documentos de la aplicación."
            )
            gowa.send_text_sync(employee.phone, msg)
        except Exception:
            pass

    return LegalTokenAcceptResponse(
        document_id=document_id,
        accepted=True,
        remaining=remaining,
    )
