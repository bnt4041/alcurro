"""Importación masiva de empleados desde plantilla Excel."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.models.models import Employee, Role
from app.models.tenant import Company
from app.schemas.crud import EmployeeBulkImportResponse, EmployeeBulkImportRow
from app.services.code_generator import next_employee_code
from app.services.id_document import validate_id_document
from app.core.org_context import resolve_department_chain
from app.services.rbac_service import assign_role_default_group
from app.schemas.whatsapp import normalize_mobile_digits

ROLE_MAP = {
    "employee": Role.EMPLOYEE,
    "empleado": Role.EMPLOYEE,
    "manager": Role.MANAGER,
    "responsable": Role.MANAGER,
    "supervisor": Role.SUPERVISOR,
    "admin": Role.ADMIN,
    "tenant_admin": Role.TENANT_ADMIN,
    "labor_inspector": Role.LABOR_INSPECTOR,
    "inspector": Role.LABOR_INSPECTOR,
}


def _parse_bool(value: str | None) -> bool:
    if not value:
        return True
    v = value.strip().lower()
    return v in ("1", "true", "si", "sí", "yes", "y", "activo")


def bulk_import_employees(
    session: Session,
    *,
    tenant_id: UUID,
    company_id: UUID,
    department_id: UUID,
    country_iso: str,
    rows: list[EmployeeBulkImportRow],
) -> EmployeeBulkImportResponse:
    company = session.get(Company, company_id)
    if not company or company.tenant_id != tenant_id:
        raise ValueError("Empresa no válida")
    try:
        _d, _w, chain_company = resolve_department_chain(session, department_id)
        if chain_company.id != company_id:
            raise ValueError("Departamento no pertenece a la empresa")
    except ValueError as exc:
        raise ValueError("Departamento no válido") from exc

    created = 0
    errors: list[str] = []

    # Verificar límite de usuarios antes de procesar
    non_empty_rows = sum(
        1 for r in rows
        if (r.full_name or "").strip() or (r.id_document or "").strip() or (r.phone or "").strip()
    )
    over_limit = False
    if non_empty_rows > 0:
        from app.services.billing_service import check_employee_limit
        limit = check_employee_limit(session, tenant_id, adding=non_empty_rows)
        over_limit = not limit.get("ok", True)

    for idx, raw in enumerate(rows, start=2):
        name = (raw.full_name or "").strip()
        doc = (raw.id_document or "").strip()
        phone = (raw.phone or "").strip()
        if not name and not doc and not phone:
            continue
        if not name or not doc or not phone:
            errors.append(f"Fila {idx}: nombre, DNI y teléfono son obligatorios")
            continue
        try:
            id_document = validate_id_document(doc)
        except ValueError as exc:
            errors.append(f"Fila {idx}: {exc}")
            continue
        phone_norm = normalize_mobile_digits(phone, country_iso)
        role_key = (raw.role or "employee").strip().lower()
        role = ROLE_MAP.get(role_key, Role.EMPLOYEE)
        vac = 22.0
        if raw.vacation_days_balance:
            try:
                vac = float(str(raw.vacation_days_balance).replace(",", "."))
            except ValueError:
                errors.append(f"Fila {idx}: días vacaciones no válidos")
                continue

        if session.exec(
            select(Employee).where(
                Employee.company_id == company_id,
                Employee.id_document == id_document,
            )
        ).first():
            errors.append(f"Fila {idx}: DNI/NIE {id_document} ya existe")
            continue
        if session.exec(
            select(Employee).where(
                Employee.company_id == company_id,
                Employee.phone == phone_norm,
            )
        ).first():
            errors.append(f"Fila {idx}: teléfono ya registrado")
            continue

        code = (raw.employee_code or "").strip() or next_employee_code(
            session, company_id
        )
        row = Employee(
            company_id=company_id,
            department_id=department_id,
            full_name=name,
            id_document=id_document,
            phone=phone_norm,
            email=(raw.email or "").strip() or None,
            employee_code=code,
            role=role,
            vacation_days_balance=vac,
            is_active=_parse_bool(raw.is_active) and not over_limit,
        )
        session.add(row)
        session.flush()
        assign_role_default_group(session, row, tenant_id)
        created += 1

    if created:
        session.commit()
    else:
        session.rollback()

    return EmployeeBulkImportResponse(created=created, errors=errors)
