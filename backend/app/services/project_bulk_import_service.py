"""Importación masiva de proyectos por empresa."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.models.project import Project
from app.models.tenant import Company
from app.schemas.project import ProjectBulkImportResponse, ProjectBulkImportRow
from app.services.code_generator import next_project_code


def _parse_float(value: str | None) -> float | None:
    if not value or not str(value).strip():
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        raise ValueError("horas previstas no válidas")


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if not value or not str(value).strip():
        return default
    v = str(value).strip().lower()
    return v in ("1", "true", "si", "sí", "yes", "y", "activo")


def bulk_import_projects(
    session: Session,
    *,
    tenant_id: UUID,
    company_id: UUID,
    rows: list[ProjectBulkImportRow],
) -> ProjectBulkImportResponse:
    company = session.get(Company, company_id)
    if not company or company.tenant_id != tenant_id:
        raise ValueError("Empresa no válida")

    created = 0
    errors: list[str] = []

    for idx, raw in enumerate(rows, start=2):
        name = (raw.name or "").strip()
        if not name:
            if not (raw.address or raw.planned_hours):
                continue
            errors.append(f"Fila {idx}: nombre obligatorio")
            continue
        try:
            hours = _parse_float(raw.planned_hours)
        except ValueError as exc:
            errors.append(f"Fila {idx}: {exc}")
            continue

        existing = session.exec(
            select(Project).where(
                Project.company_id == company_id,
                Project.name == name,
            )
        ).first()
        if existing:
            errors.append(f"Fila {idx}: ya existe el proyecto «{name}»")
            continue

        row = Project(
            company_id=company_id,
            name=name,
            code=next_project_code(session, company_id),
            address=(raw.address or "").strip() or None,
            planned_hours=hours,
            is_active=_parse_bool(raw.is_active),
        )
        session.add(row)
        created += 1

    if created:
        session.commit()
    else:
        session.rollback()

    return ProjectBulkImportResponse(created=created, errors=errors)
