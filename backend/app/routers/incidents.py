from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.incident import Incident, IncidentNote
from app.models.models import ClockIn, Employee, WorkBreak
from app.routers.crud_helpers import get_or_404
from app.schemas.incident import (
    IncidentActionBreak,
    IncidentActionClock,
    IncidentActionLeave,
    IncidentApplyClock,
    IncidentApplyLeave,
    IncidentAutoRuleRead,
    IncidentAutoRuleUpdate,
    IncidentCreate,
    IncidentNoteCreate,
    IncidentNoteRead,
    IncidentRead,
    IncidentSendMessage,
    IncidentUpdate,
)
from app.services.incident_service import (
    add_note,
    apply_clock_correction,
    apply_leave_correction,
    create_incident,
    get_or_create_rules,
    incident_to_read,
    list_notes,
    original_data_for_links,
    rules_to_read,
    send_email_from_incident,
    send_whatsapp_from_incident,
    update_rules,
)
from app.services.scope_service import read_scope_employee_ids

_UPLOAD_DIR = Path("/app/uploads")

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _scope_ids(ctx: OrgContext, session: Session, user: Employee) -> list[UUID]:
    return read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "clock_ins",
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    status: str | None = None,
    employee_id: UUID | None = None,
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[IncidentRead]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = select(Incident).where(
        Incident.tenant_id == ctx.tenant.id,
        Incident.employee_id.in_(ids),  # type: ignore[attr-defined]
    )
    if status:
        stmt = stmt.where(Incident.status == status)
    if employee_id:
        if employee_id not in ids:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        stmt = stmt.where(Incident.employee_id == employee_id)
    rows = list(
        session.exec(stmt.order_by(Incident.created_at.desc())).all()  # type: ignore[attr-defined]
    )
    return [incident_to_read(session, r, include_url=True) for r in rows]


@router.get("/rules", response_model=IncidentAutoRuleRead)
def get_incident_rules(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentAutoRuleRead:
    return rules_to_read(get_or_create_rules(session, ctx.tenant.id))


@router.put("/rules", response_model=IncidentAutoRuleRead)
def put_incident_rules(
    data: IncidentAutoRuleUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentAutoRuleRead:
    row = update_rules(session, ctx.tenant.id, data)
    session.commit()
    return row


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id or row.employee_id not in _scope_ids(
        ctx, session, user
    ):
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incident_to_read(session, row, include_url=True)


@router.post("", response_model=IncidentRead, status_code=201)
def create_incident_route(
    data: IncidentCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    ids = _scope_ids(ctx, session, user)
    if data.employee_id not in ids:
        raise HTTPException(status_code=400, detail="Empleado no válido")
    try:
        original = original_data_for_links(
            session,
            employee_id=data.employee_id,
            clock_in_id=data.clock_in_id,
            leave_request_id=data.leave_request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = create_incident(
        session,
        tenant_id=ctx.tenant.id,
        employee_id=data.employee_id,
        category=data.category,
        incident_type=data.incident_type,
        title=data.title.strip(),
        description=data.description,
        source="manual",
        incident_date=data.incident_date,
        clock_in_id=data.clock_in_id,
        leave_request_id=data.leave_request_id,
        original_data=original,
        require_justification=data.require_justification,
        notify_whatsapp=data.notify_whatsapp and data.require_justification,
        created_by_id=user.id,
    )
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident_route(
    incident_id: UUID,
    data: IncidentUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.post("/{incident_id}/apply-clock", response_model=IncidentRead)
def apply_clock(
    incident_id: UUID,
    data: IncidentApplyClock,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    try:
        apply_clock_correction(session, row, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


# ── Notas ──────────────────────────────────────────────────────────────────────

@router.get("/{incident_id}/notes", response_model=list[IncidentNoteRead])
def get_incident_notes(
    incident_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "clock_ins")),
) -> list[IncidentNoteRead]:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    notes = list_notes(session, incident_id)
    return [IncidentNoteRead.model_validate(n) for n in notes]


@router.post("/{incident_id}/notes", response_model=IncidentNoteRead, status_code=201)
def add_incident_note(
    incident_id: UUID,
    data: IncidentNoteCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentNoteRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    note = add_note(
        session,
        incident_id=incident_id,
        content=data.content,
        author_id=user.id,
        author_name=user.full_name,
    )
    session.commit()
    session.refresh(note)
    return IncidentNoteRead.model_validate(note)


# ── Envío de WhatsApp / Email desde incidencia (con adjuntos opcionales) ──────

@router.post("/{incident_id}/send-message", response_model=dict)
async def send_incident_message(
    incident_id: UUID,
    channel: str = Form(..., pattern="^(whatsapp|email)$"),
    message: str = Form(..., min_length=1, max_length=2000),
    recipient_email: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> dict:
    from app.services.document_service import store_upload_file

    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    # Guardar adjuntos y construir nota de archivos
    file_notes: list[str] = []
    file_paths: list[str] = []
    for upload in files:
        if not upload.filename:
            continue
        data = await upload.read()
        if not data:
            continue
        stored_path, safe_name = store_upload_file(_UPLOAD_DIR, upload.filename, data)
        rel = stored_path.replace("/app/uploads/", "/uploads/")
        file_notes.append(f"📎 [{safe_name}]({rel})")
        file_paths.append(stored_path)

    try:
        if channel == "whatsapp":
            result = send_whatsapp_from_incident(
                session,
                incident=row,
                message=message,
                tenant_id=ctx.tenant.id,
                file_notes=file_notes,
                file_paths=file_paths,
            )
        else:
            if not recipient_email:
                raise HTTPException(status_code=400, detail="Email del destinatario requerido")
            result = send_email_from_incident(
                session,
                incident=row,
                message=message,
                recipient_email=recipient_email,
                tenant_id=ctx.tenant.id,
                file_notes=file_notes,
            )
        session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Acciones sobre incidencias ─────────────────────────────────────────────────

@router.post("/{incident_id}/actions/clock", response_model=IncidentRead)
def action_clock(
    incident_id: UUID,
    data: IncidentActionClock,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    target_clock_id = data.clock_in_id or row.clock_in_id
    if data.action == "modify" and target_clock_id:
        clock = session.get(ClockIn, target_clock_id)
        if not clock:
            raise HTTPException(status_code=404, detail="Fichaje no encontrado")
        if not row.original_data:
            row.original_data = {"entrada_at": clock.entrada_at.isoformat(), "salida_at": clock.salida_at.isoformat() if clock.salida_at else None}
        clock.entrada_at = data.entrada_at
        if data.salida_at is not None:
            clock.salida_at = data.salida_at
        if data.notes is not None:
            clock.notes = data.notes
        if data.project_id is not None:
            clock.project_id = data.project_id
        row.clock_in_id = clock.id
        row.modified_data = {"entrada_at": clock.entrada_at.isoformat(), "salida_at": clock.salida_at.isoformat() if clock.salida_at else None}
        session.add(clock)
    else:
        # Crear nuevo fichaje y vincularlo
        clock = ClockIn(
            employee_id=row.employee_id,
            entrada_at=data.entrada_at,
            salida_at=data.salida_at,
            notes=data.notes,
            project_id=data.project_id,
            source="incident_action",
        )
        session.add(clock)
        session.flush()
        row.clock_in_id = clock.id
        row.original_data = row.original_data or {}

    add_note(session, incident_id=row.id, content=f"✏️ Fichaje {'modificado' if data.action == 'modify' else 'creado'} desde incidencia ({data.entrada_at.strftime('%d/%m/%Y %H:%M')})", author_id=user.id, author_name=user.full_name)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.post("/{incident_id}/actions/break", response_model=IncidentRead)
def action_break(
    incident_id: UUID,
    data: IncidentActionBreak,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    target_break_id = data.break_id or row.break_id
    if data.action == "modify" and target_break_id:
        brk = session.get(WorkBreak, target_break_id)
        if not brk:
            raise HTTPException(status_code=404, detail="Parada no encontrada")
        if not row.original_data:
            row.original_data = {"recorded_at": brk.recorded_at.isoformat(), "record_type": brk.record_type}
        brk.recorded_at = data.recorded_at
        brk.record_type = data.record_type
        if data.notes is not None:
            brk.notes = data.notes
        row.break_id = brk.id
        row.modified_data = {"recorded_at": brk.recorded_at.isoformat(), "record_type": str(brk.record_type)}
        session.add(brk)
    else:
        clock_in_id = data.clock_in_id or row.clock_in_id
        if not clock_in_id:
            raise HTTPException(status_code=400, detail="Se requiere clock_in_id para crear una parada")
        brk = WorkBreak(
            employee_id=row.employee_id,
            clock_in_id=clock_in_id,
            record_type=data.record_type,
            recorded_at=data.recorded_at,
            notes=data.notes,
            source="incident_action",
        )
        session.add(brk)
        session.flush()
        row.break_id = brk.id
        row.original_data = row.original_data or {}

    add_note(session, incident_id=row.id, content=f"✏️ Parada {'modificada' if data.action == 'modify' else 'creada'} desde incidencia ({data.record_type}, {data.recorded_at.strftime('%d/%m/%Y %H:%M')})", author_id=user.id, author_name=user.full_name)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)


@router.post("/{incident_id}/actions/leave", response_model=IncidentRead)
def action_leave(
    incident_id: UUID,
    data: IncidentActionLeave,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("clock_ins", "write")),
) -> IncidentRead:
    from app.models.models import LeaveRequest, LeaveStatus

    row = get_or_404(session, Incident, incident_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    target_leave_id = data.leave_id or row.leave_request_id
    if data.action == "modify" and target_leave_id:
        leave = session.get(LeaveRequest, target_leave_id)
        if not leave:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")
        if not row.original_data:
            row.original_data = {"start_date": leave.start_date.isoformat(), "end_date": leave.end_date.isoformat()}
        leave.start_date = data.start_date
        leave.end_date = data.end_date
        leave.days_requested = data.days_requested
        if data.reason is not None:
            leave.reason = data.reason
        if data.leave_type_id is not None:
            leave.leave_type_id = data.leave_type_id
        row.leave_request_id = leave.id
        row.modified_data = {"start_date": leave.start_date.isoformat(), "end_date": leave.end_date.isoformat(), "days_requested": leave.days_requested}
        session.add(leave)
    else:
        leave = LeaveRequest(
            employee_id=row.employee_id,
            start_date=data.start_date,
            end_date=data.end_date,
            days_requested=data.days_requested,
            reason=data.reason,
            leave_type_id=data.leave_type_id,
            status=LeaveStatus.PENDING,
        )
        session.add(leave)
        session.flush()
        row.leave_request_id = leave.id
        row.original_data = row.original_data or {}

    add_note(session, incident_id=row.id, content=f"✏️ Permiso {'modificado' if data.action == 'modify' else 'creado'} desde incidencia ({data.start_date} → {data.end_date}, {data.days_requested}d)", author_id=user.id, author_name=user.full_name)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return incident_to_read(session, row, include_url=True)
