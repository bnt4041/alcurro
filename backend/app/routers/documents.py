import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.models import DocumentDelivery, Employee
from app.routers.crud_helpers import get_or_404
from app.routers.search_helpers import ilike_filter
from app.schemas.crud import DocumentDeliveryRead, DocumentDeliveryUpdate
from app.core.tenant_context import TenantContext, get_tenant_context
from app.models.tenant import Tenant
from app.services.gowa_service import GoWAService
from app.services.scope_service import (
    assert_employee_target,
    is_read_own_only,
    read_scope_employee_ids,
    resolve_write_employee_id,
    tenant_company_ids,
)

router = APIRouter(prefix="/documents", tags=["documents"])
UPLOAD_DIR = Path("/app/uploads")


def _document_in_scope(
    session: Session,
    user: Employee,
    ctx: OrgContext,
    row: DocumentDelivery,
) -> bool:
    if is_read_own_only(session, user, ctx.tenant.id, "documents"):
        return row.employee_id == user.id
    emp_ids = read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "documents",
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )
    if row.employee_id:
        return row.employee_id in emp_ids
    company_ids = tenant_company_ids(session, ctx.tenant.id)
    return row.company_id in company_ids if row.company_id else False


@router.get("", response_model=list[DocumentDeliveryRead])
def list_documents(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    q: str | None = None,
    document_type: str | None = None,
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> list[DocumentDelivery]:
    stmt = select(DocumentDelivery).order_by(DocumentDelivery.created_at.desc())  # type: ignore[attr-defined]
    if is_read_own_only(session, user, ctx.tenant.id, "documents"):
        stmt = stmt.where(DocumentDelivery.employee_id == user.id)
    else:
        emp_ids = read_scope_employee_ids(
            session,
            user,
            ctx.tenant.id,
            "documents",
            company_id=ctx.company.id,
            work_center_id=ctx.work_center.id if ctx.work_center else None,
            department_id=ctx.department.id if ctx.department else None,
        )
        company_ids = tenant_company_ids(session, ctx.tenant.id)
        if emp_ids:
            stmt = stmt.where(
                (DocumentDelivery.employee_id.in_(emp_ids))  # type: ignore[attr-defined]
                | (
                    DocumentDelivery.employee_id.is_(None)  # type: ignore[union-attr]
                    & DocumentDelivery.company_id.in_(company_ids)  # type: ignore[attr-defined]
                )
            )
        else:
            return []
    filt = ilike_filter(DocumentDelivery.file_name, DocumentDelivery.document_type, term=q)
    if filt is not None:
        stmt = stmt.where(filt)
    if document_type:
        stmt = stmt.where(DocumentDelivery.document_type == document_type)
    return list(session.exec(stmt).all())


@router.get("/{doc_id}", response_model=DocumentDeliveryRead)
def get_document(
    doc_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> DocumentDelivery:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return row


@router.post("/upload", response_model=DocumentDeliveryRead, status_code=201)
async def upload_document(
    employee_id: UUID = Form(...),
    document_type: str = Form(...),
    requires_acknowledgment: bool = Form(True),
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "create")),
) -> DocumentDelivery:
    target_id = resolve_write_employee_id(
        session, user, ctx, "documents", employee_id, "create"
    )
    employee = session.get(Employee, target_id)
    if not employee:
        raise HTTPException(status_code=400, detail="Empleado no existe")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = file.filename or "documento.pdf"
    stored = UPLOAD_DIR / f"{uuid4()}_{safe_name}"
    with stored.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)
    row = DocumentDelivery(
        employee_id=target_id,
        file_path=str(stored),
        file_name=safe_name,
        document_type=document_type,
        requires_acknowledgment=requires_acknowledgment,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.post("/{doc_id}/send-whatsapp", response_model=DocumentDeliveryRead)
async def send_via_whatsapp(
    doc_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "update")),
) -> DocumentDelivery:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if row.employee_id:
        assert_employee_target(session, user, ctx, "documents", row.employee_id, "update")
    if not row.employee_id:
        raise HTTPException(status_code=400, detail="Documento sin empleado asignado")
    employee = session.get(Employee, row.employee_id)
    if not employee:
        raise HTTPException(status_code=400, detail="Empleado no encontrado")
    tenant = session.get(Tenant, ctx.tenant.id)
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant no encontrado")
    msg = (
        f"📄 Documento: {row.file_name} ({row.document_type}). "
        f"Responde *Recibido* o *Acepto* para confirmar recepción."
    )
    try:
        await GoWAService(session).send_text(employee.phone, msg)
        row.sent_at = datetime.utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"goWA: {exc}") from exc
    return row


@router.patch("/{doc_id}", response_model=DocumentDeliveryRead)
def update_document(
    doc_id: UUID,
    data: DocumentDeliveryUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "update")),
) -> DocumentDelivery:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if row.employee_id:
        assert_employee_target(session, user, ctx, "documents", row.employee_id, "update")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: UUID,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "documents")),
) -> None:
    row = get_or_404(session, DocumentDelivery, doc_id)
    path = Path(row.file_path)
    if path.exists():
        path.unlink()
    session.delete(row)
    session.commit()
