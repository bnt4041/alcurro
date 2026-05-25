"""Configuración de fichajes del tenant."""

from uuid import UUID

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.models import Employee
from app.routers.crud_helpers import get_or_404
from app.schemas.clock_settings import (
    ClockReminderRunResult,
    ClockSettingsRead,
    ClockSettingsUpdate,
    EmployeeInboundDocumentRead,
    InboundDocumentTypeRead,
)
from app.services.clock_reminder_service import run_clock_reminders
from app.services.clock_settings_service import (
    catalog_reads,
    get_or_create_settings,
    settings_to_read,
    update_settings,
)
from app.services.employee_onboarding_service import (
    build_welcome_message,
    list_inbound_documents,
    mark_welcome_sent,
    receive_inbound_file,
    seed_inbound_documents,
)
from app.services.gowa_service import GoWAService
from app.services.scope_service import assert_employee_target

router = APIRouter(prefix="/clock-settings", tags=["clock-settings"])


@router.get("/inbound-catalog", response_model=list[InboundDocumentTypeRead])
def inbound_catalog(
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[InboundDocumentTypeRead]:
    return catalog_reads()


@router.get("", response_model=ClockSettingsRead)
def get_clock_settings(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> ClockSettingsRead:
    row = get_or_create_settings(session, ctx.tenant.id)
    session.commit()
    return settings_to_read(session, row)


@router.put("", response_model=ClockSettingsRead)
def put_clock_settings(
    data: ClockSettingsUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "clock_ins")),
) -> ClockSettingsRead:
    result = update_settings(session, ctx.tenant.id, data)
    session.commit()
    return result


@router.post("/run-reminders", response_model=ClockReminderRunResult)
async def trigger_clock_reminders(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "clock_ins")),
) -> ClockReminderRunResult:
    return await run_clock_reminders(session, ctx.tenant.id)


@router.get(
    "/employees/{employee_id}/inbound-documents",
    response_model=list[EmployeeInboundDocumentRead],
)
def employee_inbound_documents(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> list[EmployeeInboundDocumentRead]:
    row = get_or_404(session, Employee, employee_id)
    assert_employee_target(session, user, ctx, "employees", row.id, "update")
    return list_inbound_documents(session, employee_id)


@router.post("/employees/{employee_id}/inbound-documents/upload")
async def upload_employee_inbound_document(
    employee_id: UUID,
    document_code: str = Form(...),
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("employees", "update")),
) -> dict:
    row = get_or_404(session, Employee, employee_id)
    assert_employee_target(session, user, ctx, "employees", row.id, "update")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    ok, message = receive_inbound_file(
        session,
        row,
        tenant_id=ctx.tenant.id,
        file_bytes=data,
        filename=file.filename or "documento.pdf",
        document_code=document_code.strip(),
    )
    session.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


@router.post("/employees/{employee_id}/resend-welcome")
async def resend_welcome(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("employees", "update")),
) -> dict:
    row = get_or_404(session, Employee, employee_id)
    assert_employee_target(session, user, ctx, "employees", row.id, "update")
    from app.services.employee_onboarding_service import provision_inbound_signatures

    seed_inbound_documents(session, row.id, ctx.tenant.id)
    provision_inbound_signatures(session, row, ctx.tenant.id)
    msg = build_welcome_message(session, row, ctx.tenant.name)
    await GoWAService(session).send_text(row.phone, msg)
    mark_welcome_sent(session, row)
    session.commit()
    return {"ok": True, "message": "Mensaje de bienvenida enviado"}
