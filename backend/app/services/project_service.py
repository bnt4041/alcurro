"""Proyectos por empresa y validación en fichajes."""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher
from uuid import UUID

from sqlmodel import Session, select

from app.models.project import Project
from app.models.tenant import Company


def _normalize(text: str) -> str:
    """Minúsculas sin acentos para comparación tolerante."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def list_active_projects(session: Session, company_id: UUID) -> list[Project]:
    """Proyectos disponibles para fichar (activos y habilitados en fichaje)."""
    return list(
        session.exec(
            select(Project)
            .where(
                Project.company_id == company_id,
                Project.is_active == True,  # noqa: E712
                Project.active_for_clock == True,  # noqa: E712
            )
            .order_by(Project.name)
        ).all()
    )


def get_project_for_company(
    session: Session, project_id: UUID, company_id: UUID
) -> Project | None:
    row = session.get(Project, project_id)
    if (
        not row
        or row.company_id != company_id
        or not row.is_active
        or not row.active_for_clock
    ):
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
    if not row.active_for_clock:
        raise ValueError("Proyecto no disponible para fichar")
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
    # Por número
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(projects):
            return projects[idx]
    lower = raw.lower()
    # Exacto por código o nombre
    for p in projects:
        if lower == p.code.lower() or lower == p.name.lower():
            return p
    # Substring exacto
    for p in projects:
        if lower in p.name.lower():
            return p
    # Fuzzy con normalización de acentos (umbral 0.72)
    norm_query = _normalize(raw)
    best: Project | None = None
    best_score = 0.0
    for p in projects:
        score = max(
            SequenceMatcher(None, norm_query, _normalize(p.name)).ratio(),
            SequenceMatcher(None, norm_query, _normalize(p.code)).ratio(),
        )
        if score > best_score:
            best_score = score
            best = p
    if best_score >= 0.72:
        return best
    return None


def format_project_picker_message(projects: list[Project], record_label: str) -> str:
    from app.services.whatsapp_format import format_project_picker

    return format_project_picker(record_label, projects)
