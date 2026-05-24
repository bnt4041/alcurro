from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context, resolve_department_chain
from app.core.permissions import Permission, require_permission, require_write
from app.core.security import hash_password
from app.database import get_session
from app.models.models import Employee, Role
from app.routers.crud_helpers import get_or_404
from app.routers.search_helpers import ilike_filter
from app.schemas.crud import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.schemas.whatsapp import normalize_mobile_digits
from app.services.code_generator import next_employee_code
from app.services.id_document import validate_id_document
from app.services.rbac_service import assign_role_default_group
from app.services.scope_service import assert_employee_target, read_scope_employee_ids
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
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(get_current_user),
    q: str | None = None,
    role: Role | None = None,
    active_only: bool = False,
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
    return list(session.exec(stmt).all())


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
    session.delete(row)
    session.commit()
