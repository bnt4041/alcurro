"""Generación y normalización del código de cuenta (slug)."""

import re

from sqlmodel import Session, select

from app.models.tenant import Tenant


def normalize_slug_text(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def resolve_tenant_slug(
    session: Session, name: str, preferred: str | None = None
) -> str:
    """Devuelve un slug único a partir del nombre o del valor preferido del admin."""
    base = normalize_slug_text(preferred or "")
    if len(base) < 2:
        base = normalize_slug_text(name)
    if len(base) < 2:
        base = "cuenta"

    candidate = base
    if not session.exec(select(Tenant).where(Tenant.slug == candidate)).first():
        return candidate

    n = 2
    while n < 1000:
        suffix = f"-{n}"
        trimmed = base[: 80 - len(suffix)]
        candidate = f"{trimmed}{suffix}"
        if not session.exec(select(Tenant).where(Tenant.slug == candidate)).first():
            return candidate
        n += 1

    raise ValueError("No se pudo generar un código de cuenta único")
