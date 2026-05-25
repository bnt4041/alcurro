import json
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_perm, require_permission, require_write
from app.database import get_session
from app.models.documents import (
    DocumentDelivery,
    DocumentTag,
    DocumentType,
)
from app.models.models import Employee
from app.models.tenant import Tenant
from app.routers.crud_helpers import get_or_404
from app.routers.search_helpers import ilike_filter
from app.schemas.documents import (
    BulkPayrollResponse,
    DocumentDeliveryRead,
    DocumentDeliveryUpdate,
    DocumentNotificationSettingsRead,
    DocumentNotificationSettingsUpdate,
    DocumentTagCreate,
    DocumentTagRead,
    DocumentTagUpdate,
    DocumentTypeCreate,
    DocumentTypeRead,
    DocumentTypeUpdate,
    DownloadZipRequest,
    ExpiryNotificationRunResult,
)
from app.services.document_service import (
    create_delivery,
    delete_delivery,
    delivery_to_read,
    ensure_default_types,
    get_type_or_404,
    set_document_tags,
    store_upload_file,
)
from app.services.gowa_service import GoWAService
from app.services.document_expiry_notify_service import (
    run_expiry_notifications,
    settings_to_read,
    update_settings,
)
from app.services.document_zip_service import build_documents_zip
from app.services.payroll_bulk_service import process_bulk_payrolls
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
    if row.tenant_id != ctx.tenant.id:
        return False
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


def _list_stmt(
    session: Session,
    user: Employee,
    ctx: OrgContext,
    *,
    company_id: UUID | None = None,
    employee_id: UUID | None = None,
    document_type_id: UUID | None = None,
    tag_id: UUID | None = None,
    expired_only: bool = False,
    q: str | None = None,
):
    stmt = (
        select(DocumentDelivery)
        .where(DocumentDelivery.tenant_id == ctx.tenant.id)
        .order_by(DocumentDelivery.created_at.desc())  # type: ignore[attr-defined]
    )
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
            return None
    if company_id:
        stmt = stmt.where(DocumentDelivery.company_id == company_id)
    if employee_id:
        stmt = stmt.where(DocumentDelivery.employee_id == employee_id)
    if document_type_id:
        stmt = stmt.where(DocumentDelivery.document_type_id == document_type_id)
    if tag_id:
        from app.models.documents import DocumentDeliveryTag

        stmt = stmt.join(
            DocumentDeliveryTag,
            DocumentDeliveryTag.document_delivery_id == DocumentDelivery.id,
        ).where(DocumentDeliveryTag.tag_id == tag_id)
    if expired_only:
        stmt = stmt.where(
            DocumentDelivery.expires_at.is_not(None),  # type: ignore[union-attr]
            DocumentDelivery.expires_at < date.today(),  # type: ignore[operator]
        )
    filt = ilike_filter(
        DocumentDelivery.file_name,
        DocumentDelivery.document_type,
        DocumentDelivery.title,
        term=q,
    )
    if filt is not None:
        stmt = stmt.where(filt)
    return stmt


def _resolve_document_rows(
    session: Session,
    user: Employee,
    ctx: OrgContext,
    *,
    ids: list[UUID] | None = None,
    company_id: UUID | None = None,
    employee_id: UUID | None = None,
    document_type_id: UUID | None = None,
    tag_id: UUID | None = None,
    expired_only: bool = False,
    q: str | None = None,
    document_type: str | None = None,
) -> list[DocumentDelivery]:
    if ids:
        rows: list[DocumentDelivery] = []
        for doc_id in ids:
            row = session.get(DocumentDelivery, doc_id)
            if row and _document_in_scope(session, user, ctx, row):
                rows.append(row)
        return rows
    stmt = _list_stmt(
        session,
        user,
        ctx,
        company_id=company_id,
        employee_id=employee_id,
        document_type_id=document_type_id,
        tag_id=tag_id,
        expired_only=expired_only,
        q=q,
    )
    if stmt is None:
        return []
    rows = list(session.exec(stmt).all())
    if document_type and not document_type_id:
        rows = [r for r in rows if r.document_type == document_type]
    return rows


# --- Tipologías ---


@router.get("/types", response_model=list[DocumentTypeRead])
def list_document_types(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> list[DocumentType]:
    ensure_default_types(session, ctx.tenant.id)
    session.commit()
    rows = session.exec(
        select(DocumentType)
        .where(DocumentType.tenant_id == ctx.tenant.id)
        .order_by(DocumentType.sort_order, DocumentType.name)
    ).all()
    return [DocumentTypeRead.model_validate(r) for r in rows]


@router.post("/types", response_model=DocumentTypeRead, status_code=201)
def create_document_type(
    data: DocumentTypeCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "documents")),
) -> DocumentType:
    code = data.code.strip().lower()
    if session.exec(
        select(DocumentType).where(
            DocumentType.tenant_id == ctx.tenant.id,
            DocumentType.code == code,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Código de tipología duplicado")
    row = DocumentType(tenant_id=ctx.tenant.id, code=code, **data.model_dump(exclude={"code"}))
    session.add(row)
    session.commit()
    session.refresh(row)
    return DocumentTypeRead.model_validate(row)


@router.patch("/types/{type_id}", response_model=DocumentTypeRead)
def update_document_type(
    type_id: UUID,
    data: DocumentTypeUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "documents")),
) -> DocumentType:
    row = get_type_or_404(session, ctx.tenant.id, type_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return DocumentTypeRead.model_validate(row)


# --- Etiquetas ---


@router.get("/tags", response_model=list[DocumentTagRead])
def list_document_tags(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> list[DocumentTag]:
    rows = session.exec(
        select(DocumentTag)
        .where(DocumentTag.tenant_id == ctx.tenant.id, DocumentTag.is_active == True)  # noqa: E712
        .order_by(DocumentTag.name)
    ).all()
    return [DocumentTagRead.model_validate(r) for r in rows]


@router.post("/tags", response_model=DocumentTagRead, status_code=201)
def create_document_tag(
    data: DocumentTagCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "documents")),
) -> DocumentTag:
    name = data.name.strip()
    if session.exec(
        select(DocumentTag).where(
            DocumentTag.tenant_id == ctx.tenant.id,
            DocumentTag.name == name,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Etiqueta duplicada")
    row = DocumentTag(tenant_id=ctx.tenant.id, name=name, color=data.color)
    session.add(row)
    session.commit()
    session.refresh(row)
    return DocumentTagRead.model_validate(row)


@router.patch("/tags/{tag_id}", response_model=DocumentTagRead)
def update_document_tag(
    tag_id: UUID,
    data: DocumentTagUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "documents")),
) -> DocumentTag:
    row = session.get(DocumentTag, tag_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return DocumentTagRead.model_validate(row)


# --- Nóminas masivas ---


@router.post("/bulk-payrolls", response_model=BulkPayrollResponse)
async def bulk_upload_payrolls(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    company_id: UUID = Form(...),
    document_type_id: UUID | None = Form(None),
    document_type: str = Form("nomina"),
    expires_at: date | None = Form(None),
    tag_ids: str = Form(""),
    files: list[UploadFile] = File(...),
    _: object = Depends(require_perm("documents.bulk")),
) -> BulkPayrollResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Sube al menos un archivo PDF o ZIP")
    parsed_tags: list[UUID] = []
    if tag_ids.strip():
        try:
            parsed_tags = [UUID(x) for x in json.loads(tag_ids)]
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="tag_ids inválido") from exc
    return await process_bulk_payrolls(
        session,
        tenant_id=ctx.tenant.id,
        company_id=company_id,
        upload_dir=UPLOAD_DIR,
        files=files,
        document_type_id=document_type_id,
        document_type_code=document_type.strip().lower() or "nomina",
        expires_at=expires_at,
        tag_ids=parsed_tags,
    )


# --- Avisos de caducidad ---


@router.get("/notification-settings", response_model=DocumentNotificationSettingsRead)
def get_notification_settings(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> DocumentNotificationSettingsRead:
    from app.services.document_expiry_notify_service import get_or_create_settings

    row = get_or_create_settings(session, ctx.tenant.id)
    session.commit()
    return settings_to_read(row)


@router.put("/notification-settings", response_model=DocumentNotificationSettingsRead)
def put_notification_settings(
    data: DocumentNotificationSettingsUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "documents")),
) -> DocumentNotificationSettingsRead:
    result = update_settings(session, ctx.tenant.id, data)
    session.commit()
    return result


@router.post("/run-expiry-notifications", response_model=ExpiryNotificationRunResult)
async def trigger_expiry_notifications(
    dry_run: bool = Query(False),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "documents")),
) -> ExpiryNotificationRunResult:
    return await run_expiry_notifications(session, ctx.tenant.id, dry_run=dry_run)


@router.get("/download-zip")
def download_documents_zip_get(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    ids: str | None = Query(None, description="UUIDs separados por coma"),
    q: str | None = None,
    document_type: str | None = None,
    document_type_id: UUID | None = None,
    company_id: UUID | None = None,
    employee_id: UUID | None = None,
    tag_id: UUID | None = None,
    expired_only: bool = False,
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> StreamingResponse:
    parsed_ids: list[UUID] | None = None
    if ids:
        try:
            parsed_ids = [UUID(x.strip()) for x in ids.split(",") if x.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="ids inválidos") from exc
    rows = _resolve_document_rows(
        session,
        user,
        ctx,
        ids=parsed_ids,
        company_id=company_id,
        employee_id=employee_id,
        document_type_id=document_type_id,
        tag_id=tag_id,
        expired_only=expired_only,
        q=q,
        document_type=document_type,
    )
    buf, added = build_documents_zip(rows)
    if added == 0:
        raise HTTPException(status_code=404, detail="No hay archivos para descargar")
    filename = f"documentos_{date.today().isoformat()}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/download-zip")
def download_documents_zip_post(
    body: DownloadZipRequest = Body(...),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    q: str | None = None,
    document_type: str | None = None,
    document_type_id: UUID | None = None,
    company_id: UUID | None = None,
    employee_id: UUID | None = None,
    tag_id: UUID | None = None,
    expired_only: bool = False,
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> StreamingResponse:
    rows = _resolve_document_rows(
        session,
        user,
        ctx,
        ids=body.ids,
        company_id=company_id,
        employee_id=employee_id,
        document_type_id=document_type_id,
        tag_id=tag_id,
        expired_only=expired_only,
        q=q,
        document_type=document_type,
    )
    buf, added = build_documents_zip(rows)
    if added == 0:
        raise HTTPException(status_code=404, detail="No hay archivos para descargar")
    filename = f"documentos_{date.today().isoformat()}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Documentos ---


@router.get("", response_model=list[DocumentDeliveryRead])
def list_documents(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    q: str | None = None,
    document_type: str | None = None,
    document_type_id: UUID | None = None,
    company_id: UUID | None = None,
    employee_id: UUID | None = None,
    tag_id: UUID | None = None,
    expired_only: bool = False,
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> list[DocumentDeliveryRead]:
    stmt = _list_stmt(
        session,
        user,
        ctx,
        company_id=company_id,
        employee_id=employee_id,
        document_type_id=document_type_id,
        tag_id=tag_id,
        expired_only=expired_only,
        q=q,
    )
    if stmt is None:
        return []
    rows = list(session.exec(stmt).all())
    if document_type and not document_type_id:
        rows = [r for r in rows if r.document_type == document_type]
    return [delivery_to_read(session, r) for r in rows]


@router.get("/{doc_id}/download")
def download_document(
    doc_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> FileResponse:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    path = Path(row.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
    return FileResponse(path, filename=row.file_name, media_type="application/octet-stream")


@router.get("/{doc_id}", response_model=DocumentDeliveryRead)
def get_document(
    doc_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> DocumentDeliveryRead:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return delivery_to_read(session, row)


@router.post("/upload", response_model=DocumentDeliveryRead, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    company_id: UUID | None = Form(None),
    employee_id: UUID | None = Form(None),
    document_type_id: UUID | None = Form(None),
    document_type: str = Form("otro"),
    title: str | None = Form(None),
    expires_at: date | None = Form(None),
    requires_acknowledgment: bool = Form(True),
    tag_ids: str = Form(""),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "create")),
) -> DocumentDeliveryRead:
    parsed_company = company_id
    parsed_employee = employee_id
    if parsed_employee:
        parsed_employee = resolve_write_employee_id(
            session, user, ctx, "documents", parsed_employee, "create"
        )
    elif not parsed_company:
        parsed_company = ctx.company.id

    type_code = document_type.strip().lower() or "otro"
    type_row: DocumentType | None = None
    if document_type_id:
        type_row = get_type_or_404(session, ctx.tenant.id, document_type_id)
        type_code = type_row.code
    else:
        type_row = session.exec(
            select(DocumentType).where(
                DocumentType.tenant_id == ctx.tenant.id,
                DocumentType.code == type_code,
            )
        ).first()

    parsed_tags: list[UUID] = []
    if tag_ids.strip():
        try:
            parsed_tags = [UUID(x) for x in json.loads(tag_ids)]
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="tag_ids inválido") from exc

    content = await file.read()
    path, safe_name = store_upload_file(
        UPLOAD_DIR, file.filename or "documento.pdf", content
    )
    row = create_delivery(
        session,
        tenant_id=ctx.tenant.id,
        company_id=parsed_company,
        employee_id=parsed_employee,
        document_type_id=type_row.id if type_row else None,
        document_type_code=type_code,
        file_path=path,
        file_name=safe_name,
        title=title,
        expires_at=expires_at,
        requires_acknowledgment=requires_acknowledgment,
        tag_ids=parsed_tags,
    )
    session.commit()
    session.refresh(row)
    return delivery_to_read(session, row)


@router.post("/{doc_id}/send-whatsapp", response_model=DocumentDeliveryRead)
async def send_via_whatsapp(
    doc_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "update")),
) -> DocumentDeliveryRead:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not row.employee_id:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede enviar por WhatsApp a documentos de empleado",
        )
    assert_employee_target(session, user, ctx, "documents", row.employee_id, "update")
    employee = session.get(Employee, row.employee_id)
    if not employee:
        raise HTTPException(status_code=400, detail="Empleado no encontrado")
    tenant = session.get(Tenant, ctx.tenant.id)
    if not tenant:
        raise HTTPException(status_code=400, detail="Cuenta no encontrada")
    msg = (
        f"📄 Documento: {row.file_name}"
        f"{f' ({row.title})' if row.title else ''}. "
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
    return delivery_to_read(session, row)


@router.patch("/{doc_id}", response_model=DocumentDeliveryRead)
def update_document(
    doc_id: UUID,
    data: DocumentDeliveryUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "update")),
) -> DocumentDeliveryRead:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if row.employee_id:
        assert_employee_target(session, user, ctx, "documents", row.employee_id, "update")
    payload = data.model_dump(exclude_unset=True, exclude={"tag_ids"})
    if "document_type_id" in payload and payload["document_type_id"]:
        dt = get_type_or_404(session, ctx.tenant.id, payload["document_type_id"])
        row.document_type = dt.code
    for key, value in payload.items():
        setattr(row, key, value)
    if data.tag_ids is not None:
        set_document_tags(session, row.id, ctx.tenant.id, data.tag_ids)
    session.add(row)
    session.commit()
    session.refresh(row)
    return delivery_to_read(session, row)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("documents", "update")),
) -> None:
    row = get_or_404(session, DocumentDelivery, doc_id)
    if not _document_in_scope(session, user, ctx, row):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if row.employee_id:
        assert_employee_target(session, user, ctx, "documents", row.employee_id, "update")
    delete_delivery(session, row)
    session.commit()
