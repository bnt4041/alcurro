from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.org_context import OrgContext, get_org_context, resolve_department_chain
from app.core.permissions import Permission, require_permission
from app.core.security import hash_password
from app.database import get_session
from app.models.models import Employee, Role
from app.routers.crud_helpers import get_or_404
from app.routers.search_helpers import ilike_filter
from app.schemas.crud import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services.code_generator import next_employee_code
from app.services.id_document import validate_id_document
from app.services.org_service import employee_ids_in_scope
from app.services.rbac_service import assign_role_default_group
from app.services.work_schedule import normalize_employee_schedule

router = APIRouter(prefix="/employees", tags=["employees"])


def _set_password(row: Employee, password: str | None) -> None:
    if password:
        row.password_hash = hash_password(password)


def _scope_ids(ctx: OrgContext, session: Session) -> list[UUID]:
    return employee_ids_in_scope(
        session,
        ctx.tenant.id,
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    q: str | None = None,
    role: Role | None = None,
    active_only: bool = False,
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> list[Employee]:
    ids = _scope_ids(ctx, session)
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
    _: object = Depends(require_permission(Permission.READ, "employees")),
) -> Employee:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return row


@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(
    data: EmployeeCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "employees")),
) -> Employee:
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

    payload = data.model_dump(exclude={"password", "employee_code"})
    try:
        payload = normalize_employee_schedule(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload["employee_code"] = employee_code
    payload["id_document"] = id_document
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
    _: object = Depends(require_permission(Permission.WRITE, "employees")),
) -> Employee:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    updates = data.model_dump(exclude_unset=True, exclude={"password"})
    if any(
        k in updates
        for k in ("work_schedule_blocks", "work_days", "work_start_time", "work_end_time")
    ):
        try:
            updates = normalize_employee_schedule(updates)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "id_document" in updates and updates["id_document"] is not None:
        try:
            updates["id_document"] = validate_id_document(updates["id_document"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        dup = session.exec(
            select(Employee).where(
                Employee.company_id == row.company_id,
                Employee.id_document == updates["id_document"],
                Employee.id != row.id,
            )
        ).first()
        if dup:
            raise HTTPException(
                status_code=409, detail="DNI/NIE ya registrado en la empresa"
            )
    if "department_id" in updates and updates["department_id"]:
        try:
            _d, _w, company = resolve_department_chain(
                session, updates["department_id"]
            )
            updates["company_id"] = company.id
        except ValueError:
            raise HTTPException(status_code=400, detail="Departamento no válido") from None
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
    _: object = Depends(require_permission(Permission.ADMIN, "employees")),
) -> None:
    row = get_or_404(session, Employee, employee_id)
    if row.id not in _scope_ids(ctx, session):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    session.delete(row)
    session.commit()
