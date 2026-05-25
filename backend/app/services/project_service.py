"""Proyectos por empresa y validación en fichajes."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.models.project import Project
from app.models.tenant import Company


def list_active_projects(session: Session, company_id: UUID) -> list[Project]:
    return list(
        session.exec(
            select(Project)
            .where(
                Project.company_id == company_id,
                Project.is_active == True,  # noqa: E712
            )
            .order_by(Project.name)
        ).all()
    )


def get_project_for_company(
    session: Session, project_id: UUID, company_id: UUID
) -> Project | None:
    row = session.get(Project, project_id)
    if not row or row.company_id != company_id or not row.is_active:
        return None
    return row


def ensure_project_belongs_to_tenant(
    session: Session, project_id: UUID, tenant_id: UUID
) -> Project:
    row = session.get(Project, project_id)
    if not row:
        raise ValueError("Proyecto no encontrado")
    company = session.get(Company, row.company_id)
    if not company or company.tenant_id != tenant_id:
        raise ValueError("Proyecto no válido")
    if not row.is_active:
        raise ValueError("Proyecto inactivo")
    return row


def resolve_project_from_reply(
    session: Session, company_id: UUID, text: str
) -> Project | None:
    raw = (text or "").strip()
    if not raw:
        return None
    projects = list_active_projects(session, company_id)
    if not projects:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(projects):
            return projects[idx]
    lower = raw.lower()
    for p in projects:
        if lower == p.code.lower() or lower == p.name.lower():
            return p
    for p in projects:
        if lower in p.name.lower():
            return p
    return None


def format_project_picker_message(projects: list[Project], record_label: str) -> str:
    if not projects:
        return (
            f"Para registrar {record_label} debes indicar un proyecto, "
            "pero no hay proyectos activos en tu empresa. Contacta con RRHH."
        )
    lines = [
        f"Indica el proyecto para {record_label}. Responde con el número o el nombre:",
    ]
    for i, p in enumerate(projects, start=1):
        extra = ""
        if p.address:
            extra = f" — {p.address}"
        hours = (
            f" ({p.planned_hours:g} h prev.)" if p.planned_hours is not None else ""
        )
        lines.append(f"{i}. {p.name} [{p.code}]{hours}{extra}")
    return "\n".join(lines)
