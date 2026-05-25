"""Subida masiva de nóminas: ZIP o PDFs → reparto por DNI/NIE."""

from __future__ import annotations

import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader, PdfWriter
from sqlmodel import Session, select

from app.models.documents import DocumentType
from app.models.models import Employee
from app.models.tenant import Company
from app.schemas.documents import BulkPayrollItemResult, BulkPayrollResponse
from app.services.document_service import create_delivery, store_upload_file
from app.services.id_document import find_id_documents_in_text, normalize_id_document


def _employees_by_id_document(
    session: Session, company_id: UUID
) -> dict[str, Employee]:
    mapping: dict[str, Employee] = {}
    for emp in session.exec(
        select(Employee).where(Employee.company_id == company_id)
    ).all():
        if emp.id_document:
            mapping[normalize_id_document(emp.id_document)] = emp
    return mapping


def _split_pdf(content: bytes) -> list[tuple[int, bytes]]:
    reader = PdfReader(BytesIO(content))
    pages: list[tuple[int, bytes]] = []
    for idx, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        buf = BytesIO()
        writer.write(buf)
        pages.append((idx, buf.getvalue()))
    return pages


def _extract_id_from_pdf_page(page_bytes: bytes) -> str | None:
    try:
        reader = PdfReader(BytesIO(page_bytes))
        if not reader.pages:
            return None
        text = reader.pages[0].extract_text() or ""
    except Exception:
        return None
    ids = find_id_documents_in_text(text)
    return ids[0] if ids else None


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    name = file.filename or "documento.pdf"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"Archivo vacío: {name}")
    return name, content


def _iter_pdf_sources(
    filename: str, content: bytes
) -> list[tuple[str, int | None, bytes]]:
    """Devuelve (nombre_origen, página, bytes_pdf)."""
    lower = filename.lower()
    if lower.endswith(".zip"):
        items: list[tuple[str, int | None, bytes]] = []
        with zipfile.ZipFile(BytesIO(content)) as zf:
            for info in zf.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                    continue
                pdf_bytes = zf.read(info)
                base = Path(info.filename).name
                for page_num, page_pdf in _split_pdf(pdf_bytes):
                    label = f"{base} (pág. {page_num})" if page_num > 1 else base
                    items.append((label, page_num, page_pdf))
        return items
    if lower.endswith(".pdf"):
        pages = _split_pdf(content)
        if len(pages) <= 1:
            return [(filename, None, content)]
        return [(f"{filename} (pág. {p})", p, pb) for p, pb in pages]
    raise HTTPException(
        status_code=400,
        detail=f"Formato no soportado: {filename} (usa PDF o ZIP)",
    )


async def process_bulk_payrolls(
    session: Session,
    *,
    tenant_id: UUID,
    company_id: UUID,
    upload_dir: Path,
    files: list[UploadFile],
    document_type_id: UUID | None,
    document_type_code: str,
    expires_at: date | None,
    tag_ids: list[UUID],
) -> BulkPayrollResponse:
    company = session.get(Company, company_id)
    if not company or company.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="Empresa no válida")

    doc_type: DocumentType | None = None
    if document_type_id:
        doc_type = session.get(DocumentType, document_type_id)
        if not doc_type or doc_type.tenant_id != tenant_id:
            raise HTTPException(status_code=400, detail="Tipología no válida")
        document_type_code = doc_type.code
    else:
        doc_type = session.exec(
            select(DocumentType).where(
                DocumentType.tenant_id == tenant_id,
                DocumentType.code == document_type_code,
            )
        ).first()

    emp_map = _employees_by_id_document(session, company_id)
    items: list[BulkPayrollItemResult] = []
    assigned = skipped = errors = 0
    total_pages = 0

    for upload in files:
        filename, content = await _read_upload(upload)
        try:
            sources = _iter_pdf_sources(filename, content)
        except HTTPException as exc:
            items.append(
                BulkPayrollItemResult(
                    source_file=filename,
                    status="error",
                    message=str(exc.detail),
                )
            )
            errors += 1
            continue

        for source_name, page, page_pdf in sources:
            total_pages += 1
            id_doc = _extract_id_from_pdf_page(page_pdf)
            if not id_doc:
                items.append(
                    BulkPayrollItemResult(
                        source_file=source_name,
                        page=page,
                        status="no_id",
                        message="No se detectó DNI/NIE en la página",
                    )
                )
                skipped += 1
                continue

            emp = emp_map.get(id_doc)
            if not emp:
                items.append(
                    BulkPayrollItemResult(
                        source_file=source_name,
                        page=page,
                        id_document=id_doc,
                        status="no_employee",
                        message="Ningún empleado de la empresa con ese DNI/NIE",
                    )
                )
                skipped += 1
                continue

            try:
                stored_path, safe_name = store_upload_file(
                    upload_dir, f"nomina_{id_doc}.pdf", page_pdf
                )
                row = create_delivery(
                    session,
                    tenant_id=tenant_id,
                    company_id=None,
                    employee_id=emp.id,
                    document_type_id=doc_type.id if doc_type else None,
                    document_type_code=document_type_code,
                    file_path=stored_path,
                    file_name=safe_name,
                    title=f"Nómina {expires_at.strftime('%m/%Y') if expires_at else ''}".strip(),
                    expires_at=expires_at,
                    requires_acknowledgment=True,
                    tag_ids=tag_ids,
                )
                session.commit()
                session.refresh(row)
                items.append(
                    BulkPayrollItemResult(
                        source_file=source_name,
                        page=page,
                        id_document=id_doc,
                        employee_id=emp.id,
                        employee_name=emp.full_name,
                        status="ok",
                        document_id=row.id,
                    )
                )
                assigned += 1
            except Exception as exc:
                session.rollback()
                items.append(
                    BulkPayrollItemResult(
                        source_file=source_name,
                        page=page,
                        id_document=id_doc,
                        employee_id=emp.id,
                        employee_name=emp.full_name,
                        status="error",
                        message=str(exc),
                    )
                )
                errors += 1

    return BulkPayrollResponse(
        total_files=len(files),
        total_pages=total_pages,
        assigned=assigned,
        skipped=skipped,
        errors=errors,
        items=items,
    )
