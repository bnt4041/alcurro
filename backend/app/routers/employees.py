from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context, resolve_department_chain
from app.core.permissions import Permission, require_permission, require_write
from app.core.security import hash_password
from app.database import get_session
from app.models.models import Employee, Role, ShiftConfiguration
from app.routers.crud_helpers import get_or_404
from app.routers.search_helpers import ilike_filter
from app.schemas.crud import (
    EmployeeBulkImportRequest,
    EmployeeBulkImportResponse,
    EmployeeBulkScheduleResult,
    EmployeeBulkScheduleUpdate,
    EmployeeBulkScheduleItemError,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
)
from app.schemas.whatsapp import normalize_mobile_digits
from app.services.code_generator import next_employee_code
from app.services.employee_bulk_import_service import bulk_import_employees
from app.services.ref_resolver import resolve_employee_ref
from app.services.id_document import validate_id_document
from app.services.rbac_service import assign_role_default_group
from app.models.documents import DocumentDelivery
from app.models.signature import SignatureEnvelope, SignatureSigner
from app.schemas.documents import DocumentDeliveryRead
from app.schemas.signature import SignatureEnvelopeRead
from app.services.document_service import delivery_to_read
from app.services.scope_service import assert_employee_target, read_scope_employee_ids
from app.services.signature_service import envelope_to_read
from app.services.work_schedule import normalize_employee_schedule

router = APIRouter(prefix="/employees", tags=["employees"])


def _set_password(row: Employee, password: str | None) -> None:
    if password:
        row.password_hash = hash_password(password)


def _country_iso(ctx: OrgContext) -> str:
    return (ctx.tenant.billing_country if ctx.tenant else None) or "ES"


def _normalize_phone(phone: str, country_iso: str) -> str:
    return normalize_mobile_digits(phone.strip(), country_iso)


def _phone_taken(
    session: Session,
    company_id: UUID,
    phone: str,
    country_iso: str,
    exclude_id: UUID | None = None,
) -> bool:
    normalized = _normalize_phone(phone, country_iso)
    stmt = select(Employee).where(Employee.company_id == company_id)
    if exclude_id:
        stmt = stmt.where(Employee.id != exclude_id)
    for emp in session.exec(stmt).all():
        if _normalize_phone(emp.phone, country_iso) == normalized:
            return True
    return False


def _scope_ids(
    ctx: OrgContext, session: Session, user: Employee
) -> list[UUID]:
    return read_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        "employees",
        company_id=ctx.scope_company_id(),
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("/lookup", response_model=EmployeeRead)
def lookup_employee(
    ref: str,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> Employee:
    """Find a single employee by employee_code, phone, email, or UUID."""
    emp_id = resolve_employee_ref(session, ctx.company.id, employee_ref=ref)
    emp = session.get(Employee, emp_id)
    if not emp or emp.company_id != ctx.company.id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return emp


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    q: str | None = None,
    role: Role | None = None,
    active_only: bool = False,
    phone: str | None = None,
    code: str | None = None,
    email: str | None = None,
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> list[Employee]:
    ids = _scope_ids(ctx, session, user)
    if not ids:
        return []
    stmt = select(Employee).where(Employee.id.in_(ids))  # type: ignore[attr-defined]
    stmt = stmt.order_by(Employee.full_name)
    filt = ilike_filter(
        Employee.full_name,
        Employee.employee_code,
        Employee.id_document,
        Employee.phone,
        Employee.email,
        term=q,
    )
    if filt is not None:
        stmt = stmt.where(filt)
    if role:
        stmt = stmt.where(Employee.role == role)
    if active_only:
        stmt = stmt.where(Employee.is_active == True)  # noqa: E712
    if phone:
        stmt = stmt.where(Employee.phone == phone)
    if code:
        stmt = stmt.where(Employee.employee_code.ilike(code))  # type: ignore[attr-defined]
    if email:
        stmt = stmt.where(Employee.email.ilike(email))  # type: ignore[attr-defined]
    return list(session.exec(stmt).all())


def _schedule_payload(data: EmployeeBulkScheduleUpdate) -> dict:
    return {
        "rotating_shift": data.rotating_shift,
        "shift_configuration_id": data.shift_configuration_id,
        "weekly_hours": data.weekly_hours,
        "work_schedule_periods": data.work_schedule_periods,
    }


def _apply_schedule_to_employee(
    session: Session, row: Employee, schedule: dict
) -> None:
    updates = normalize_employee_schedule(dict(schedule))
    rotating = updates.get("rotating_shift", row.rotating_shift)
    shift_id = updates.get("shift_configuration_id", row.shift_configuration_id)
    if rotating:
        if not shift_id:
            raise ValueError("Selecciona un turno complejo")
        cfg = session.get(ShiftConfiguration, shift_id)
        if not cfg or cfg.company_id != row.company_id:
            raise ValueError("Turno no válido para la empresa del empleado")
        if not updates.get("weekly_hours", row.weekly_hours):
            raise ValueError("Indica las horas semanales")
    for key, value in updates.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)


@router.post("/bulk-schedule", response_model=EmployeeBulkScheduleResult)
def bulk_update_schedule(
    data: EmployeeBulkScheduleUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("employees", "update")),
) -> EmployeeBulkScheduleResult:
    allowed = set(_scope_ids(ctx, session, user))
    schedule = _schedule_payload(data)
    try:
        normalize_employee_schedule(dict(schedule))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated = 0
    skipped = 0
    errors: list[EmployeeBulkScheduleItemError] = []
    seen: set[UUID] = set()

    for emp_id in data.employee_ids:
        if emp_id in seen:
            skipped += 1
            continue
        seen.add(emp_id)
        if emp_id not in allowed:
            errors.append(
                EmployeeBulkScheduleItemError(
                    employee_id=emp_id,
                    message="Sin permiso o empleado no encontrado",
                )
            )
            continue
        row = session.get(Employee, emp_id)
        if not row:
            errors.append(
                EmployeeBulkScheduleItemError(
                    employee_id=emp_id,
                    message="Empleado no encontrado",
                )
            )
            continue
        try:
            assert_employee_target(session, user, ctx, "employees", row.id, "update")
            _apply_schedule_to_employee(session, row, schedule)
            updated += 1
        except HTTPException:
            errors.append(
                EmployeeBulkScheduleItemError(
                    employee_id=emp_id,
                    employee_name=row.full_name,
                    message="Sin permiso para modificar",
                )
            )
        except ValueError as exc:
            errors.append(
                EmployeeBulkScheduleItemError(
                    employee_id=emp_id,
                    employee_name=row.full_name,
                    message=str(exc),
                )
            )

    if updated:
        session.commit()
    else:
        session.rollback()

    return EmployeeBulkScheduleResult(updated=updated, skipped=skipped, errors=errors)


@router.post("/bulk-import", response_model=EmployeeBulkImportResponse)
def bulk_import_employees_route(
    data: EmployeeBulkImportRequest,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("employees", "create")),
) -> EmployeeBulkImportResponse:
    from app.services.scope_service import is_write_own_only

    if is_write_own_only(session, user, ctx.tenant.id, "employees", "create"):
        raise HTTPException(
            status_code=403,
            detail="No puedes importar empleados",
        )
    dept_id = ctx.department.id if ctx.department else None
    if not dept_id:
        raise HTTPException(
            status_code=400,
            detail="Selecciona departamento en el selector de organización",
        )
    try:
        _d, _w, company = resolve_department_chain(session, dept_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Departamento no válido") from None
    if company.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=403, detail="Departamento fuera de la cuenta")
    try:
        return bulk_import_employees(
            session,
            tenant_id=ctx.tenant.id,
            company_id=company.id,
            department_id=dept_id,
            country_iso=_country_iso(ctx),
            rows=data.rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{employee_id}/documents", response_model=list[DocumentDeliveryRead])
def employee_documents(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "documents")),
) -> list[DocumentDeliveryRead]:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    docs = session.exec(
        select(DocumentDelivery)
        .where(
            DocumentDelivery.tenant_id == ctx.tenant.id,
            DocumentDelivery.employee_id == employee_id,
        )
        .order_by(DocumentDelivery.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    return [delivery_to_read(session, d) for d in docs]


@router.get("/{employee_id}/signatures", response_model=list[SignatureEnvelopeRead])
def employee_signatures(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "signatures")),
) -> list[SignatureEnvelopeRead]:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    env_ids = list(
        session.exec(
            select(SignatureSigner.envelope_id).where(
                SignatureSigner.employee_id == employee_id
            )
        ).all()
    )
    if not env_ids:
        return []
    rows = session.exec(
        select(SignatureEnvelope)
        .where(
            SignatureEnvelope.tenant_id == ctx.tenant.id,
            SignatureEnvelope.id.in_(env_ids),  # type: ignore[attr-defined]
        )
        .order_by(SignatureEnvelope.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    return [envelope_to_read(session, e) for e in rows]


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> Employee:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return row


def public_employee_avatar(
    employee_id: UUID,
    session: Session = Depends(get_session),
):
    """Avatar público (sin auth) para usar en etiquetas <img>."""
    from pathlib import Path as _Path
    from fastapi.responses import FileResponse
    from app.models.documents import DocumentDelivery

    row = session.get(Employee, employee_id)
    if not row or not row.avatar_delivery_id:
        raise HTTPException(status_code=404, detail="Sin avatar")

    doc = session.get(DocumentDelivery, row.avatar_delivery_id)
    if not doc or not _Path(doc.file_path).is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(doc.file_path, media_type="image/jpeg")


@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(
    data: EmployeeCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("employees", "create")),
) -> Employee:
    from app.services.scope_service import is_write_own_only

    if is_write_own_only(session, user, ctx.tenant.id, "employees", "create"):
        raise HTTPException(
            status_code=403,
            detail="No puedes dar de alta nuevos empleados",
        )

    from app.services.billing_service import check_employee_limit
    limit = check_employee_limit(session, ctx.tenant.id, adding=1)
    over_limit = not limit.get("ok", True)

    dept_id = data.department_id or (ctx.department.id if ctx.department else None)
    if not dept_id:
        raise HTTPException(
            status_code=400,
            detail="Selecciona departamento (cabecera X-Department-Id o en el formulario)",
        )
    try:
        _dept, _wc, company = resolve_department_chain(session, dept_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Departamento no válido") from None
    if company.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=403, detail="Departamento fuera de la cuenta")

    try:
        id_document = validate_id_document(data.id_document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    employee_code = (data.employee_code or "").strip() or next_employee_code(
        session, company.id
    )

    if session.exec(
        select(Employee).where(
            Employee.company_id == company.id,
            Employee.employee_code == employee_code,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Código de empleado duplicado")

    if session.exec(
        select(Employee).where(
            Employee.company_id == company.id,
            Employee.id_document == id_document,
        )
    ).first():
        raise HTTPException(status_code=409, detail="DNI/NIE ya registrado en la empresa")

    phone = _normalize_phone(data.phone, _country_iso(ctx))
    if _phone_taken(session, company.id, phone, _country_iso(ctx)):
        raise HTTPException(
            status_code=409,
            detail="Ya existe un empleado con este teléfono en la empresa",
        )

    payload = data.model_dump(exclude={"password", "employee_code"})
    try:
        payload = normalize_employee_schedule(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.get("rotating_shift") and not payload.get("shift_configuration_id"):
        raise HTTPException(
            status_code=400,
            detail="Con turno rotativo debes seleccionar un turno complejo",
        )
    if payload.get("rotating_shift") and not payload.get("weekly_hours"):
        raise HTTPException(
            status_code=400,
            detail="Con turno rotativo debes indicar las horas semanales",
        )
    payload["employee_code"] = employee_code
    payload["id_document"] = id_document
    payload["phone"] = phone
    payload["company_id"] = company.id
    payload["department_id"] = dept_id
    row = Employee.model_validate(payload)
    _set_password(row, data.password)
    if over_limit:
        row.is_active = False
    if not row.password_hash and row.role.value in (
        "tenant_admin",
        "admin",
        "manager",
        "supervisor",
        "labor_inspector",
    ):
        row.password_hash = hash_password("changeme")
    session.add(row)
    session.flush()
    assign_role_default_group(session, row, ctx.tenant.id)

    from app.services.clock_settings_service import get_or_create_settings
    from app.services.employee_onboarding_service import (
        build_welcome_message,
        mark_welcome_sent,
        seed_inbound_documents,
    )
    from app.services.gowa_service import GoWAService

    seed_inbound_documents(session, row.id, ctx.tenant.id)
    clock_cfg = get_or_create_settings(session, ctx.tenant.id)
    if clock_cfg.send_welcome_with_documents:
        # Si hay condiciones generales activas pendientes, incluir el enlace de
        # aceptación en el propio mensaje de bienvenida.
        legal_link: str | None = None
        legal_titles: list[str] = []
        try:
            from app.config import get_settings as _get_settings
            from app.services.legal_service import (
                create_whatsapp_token,
                employee_legal_status,
            )

            items, all_ok = employee_legal_status(session, ctx.tenant.id, row.id)
            if not all_ok:
                token = create_whatsapp_token(
                    session, employee_id=row.id, tenant_id=ctx.tenant.id
                )
                base = _get_settings().public_app_url.rstrip("/")
                legal_link = f"{base}/legal/{token.token}"
                legal_titles = [
                    i.title for i in items if i.is_required and not i.accepted
                ]
        except Exception:
            legal_link = None

        try:
            GoWAService(session).send_text_sync(
                row.phone,
                build_welcome_message(
                    session,
                    row,
                    ctx.tenant.name,
                    legal_link=legal_link,
                    legal_titles=legal_titles,
                ),
            )
            mark_welcome_sent(session, row)
        except Exception:
            pass

    session.commit()
    session.refresh(row)
    return row


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_write("employees", "update")),
) -> Employee:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    assert_employee_target(session, user, ctx, "employees", row.id, "update")
    updates = data.model_dump(exclude_unset=True, exclude={"password"})
    country_iso = _country_iso(ctx)
    target_company_id = row.company_id
    if "department_id" in updates and updates["department_id"]:
        try:
            _d, _w, company = resolve_department_chain(
                session, updates["department_id"]
            )
            if company.tenant_id != ctx.tenant.id:
                raise HTTPException(status_code=403, detail="Departamento fuera de la cuenta")
            updates["company_id"] = company.id
            target_company_id = company.id
        except ValueError:
            raise HTTPException(status_code=400, detail="Departamento no válido") from None
    if any(
        k in updates
        for k in (
            "work_schedule_periods",
            "work_schedule_blocks",
            "work_days",
            "work_start_time",
            "work_end_time",
            "rotating_shift",
            "weekly_hours",
            "shift_configuration_id",
        )
    ):
        try:
            updates = normalize_employee_schedule(updates)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    rotating = updates.get("rotating_shift", row.rotating_shift)
    shift_id = updates.get("shift_configuration_id", row.shift_configuration_id)
    if rotating and not shift_id:
        raise HTTPException(
            status_code=400,
            detail="Con turno rotativo debes seleccionar un turno complejo",
        )
    if rotating and not updates.get("weekly_hours", row.weekly_hours):
        raise HTTPException(
            status_code=400,
            detail="Con turno rotativo debes indicar las horas semanales",
        )
    if "phone" in updates and updates["phone"]:
        updates["phone"] = _normalize_phone(updates["phone"], country_iso)
        if _phone_taken(
            session, target_company_id, updates["phone"], country_iso, row.id
        ):
            raise HTTPException(
                status_code=409,
                detail="Ya existe otro empleado con este teléfono en la empresa",
            )
    if "id_document" in updates and updates["id_document"] is not None:
        try:
            updates["id_document"] = validate_id_document(updates["id_document"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        dup = session.exec(
            select(Employee).where(
                Employee.company_id == target_company_id,
                Employee.id_document == updates["id_document"],
                Employee.id != row.id,
            )
        ).first()
        if dup:
            raise HTTPException(
                status_code=409, detail="DNI/NIE ya registrado en la empresa"
            )
    # Si se está activando a un empleado que estaba inactivo, verificar límite
    activating = updates.get("is_active") and not row.is_active
    if activating:
        from app.services.billing_service import check_employee_limit
        limit = check_employee_limit(session, ctx.tenant.id, adding=1)
        if not limit.get("ok", True):
            raise HTTPException(
                status_code=402,
                detail=limit.get("message", "Límite de usuarios alcanzado."),
            )

    for key, value in updates.items():
        setattr(row, key, value)
    _set_password(row, data.password)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    _: object = Depends(require_permission(Permission.ADMIN, "employees")),
) -> None:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session, user):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # Verificar que no tenga registros que impidan el borrado
    from app.models.models import ClockIn, WorkBreak, LeaveRequest
    from app.models.documents import DocumentDelivery
    from app.models.signature import SignatureSigner
    from app.models.incident import Incident

    blockers: list[str] = []

    if session.exec(
        select(ClockIn).where(ClockIn.employee_id == employee_id).limit(1)
    ).first():
        blockers.append("fichajes")
    if session.exec(
        select(WorkBreak).where(WorkBreak.employee_id == employee_id).limit(1)
    ).first():
        blockers.append("paradas")
    if session.exec(
        select(LeaveRequest).where(LeaveRequest.employee_id == employee_id).limit(1)
    ).first():
        blockers.append("permisos/vacaciones")
    if session.exec(
        select(DocumentDelivery).where(DocumentDelivery.employee_id == employee_id).limit(1)
    ).first():
        blockers.append("documentos")
    if session.exec(
        select(SignatureSigner).where(SignatureSigner.employee_id == employee_id).limit(1)
    ).first():
        blockers.append("firmas")
    if session.exec(
        select(Incident).where(Incident.employee_id == employee_id).limit(1)
    ).first():
        blockers.append("incidencias")

    if blockers:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No se puede eliminar: tiene {', '.join(blockers)}. "
                f"Desactívalo como alternativa."
            ),
        )

    # Borrado definitivo: limpiar tablas auxiliares y luego el empleado
    from app.models.rbac import EmployeeGroup
    from app.models.clock_settings import EmployeeInboundDocument, InboundPendingUpload
    from app.models.legal import LegalAcceptance, LegalToken
    from app.models.models import EmployeeLeaveBalance
    from app.models.notification import Notification, NotificationPreference
    from app.models.project import ClockPendingFichaje
    from app.models.ai import AiWhatsappMessage
    from app.models.password_reset import PasswordResetToken
    from app.models.developer import ApiKey

    # Null out supervisor references
    for emp in session.exec(
        select(Employee).where(Employee.supervisor_id == employee_id)
    ).all():
        emp.supervisor_id = None
        session.add(emp)

    # Null out api keys created by this employee
    for key in session.exec(
        select(ApiKey).where(ApiKey.created_by_id == employee_id)
    ).all():
        key.created_by_id = None
        session.add(key)

    ancillary = [
        (EmployeeGroup, EmployeeGroup.employee_id),
        (EmployeeInboundDocument, EmployeeInboundDocument.employee_id),
        (InboundPendingUpload, InboundPendingUpload.employee_id),
        (EmployeeLeaveBalance, EmployeeLeaveBalance.employee_id),
        (LegalAcceptance, LegalAcceptance.employee_id),
        (LegalToken, LegalToken.employee_id),
        (Notification, Notification.employee_id),
        (NotificationPreference, NotificationPreference.employee_id),
        (PasswordResetToken, PasswordResetToken.employee_id),
        (ClockPendingFichaje, ClockPendingFichaje.employee_id),
        (AiWhatsappMessage, AiWhatsappMessage.employee_id),
    ]
    # Importar ShiftAssignment dentro del bloque para evitar errores de tipado
    from app.models.models import ShiftAssignment
    ancillary.append((ShiftAssignment, ShiftAssignment.employee_id))  # type: ignore[arg-type]

    for model, col in ancillary:
        for rec in session.exec(select(model).where(col == employee_id)).all():  # type: ignore[arg-type]
            session.delete(rec)

    session.delete(row)
    session.commit()
