"""Login unificado: un solo campo de usuario + contraseña."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.permissions import get_employee_permissions, normalize_role
from app.core.security import (
    PANEL_ROLES,
    create_access_token,
    create_platform_token,
    verify_password,
)
from app.models.models import Employee
from app.models.rbac import PlatformUser
from app.models.tenant import Company, Tenant


@dataclass
class UnifiedLoginResult:
    scope: str
    access_token: str
    tenant_slug: str | None = None


def _role_key(role) -> str:
    return normalize_role(role).value if hasattr(role, "value") else str(role)


def _parse_login(raw: str) -> tuple[str | None, str]:
    """
    Devuelve (tenant_slug | None, username_or_email).
    - cuenta/usuario → (cuenta, usuario)
    - usuario@cuenta (sin punto en cuenta) → (cuenta, usuario)
    - email@dominio.com → (None, email completo)
    - ADM001 → (None, código) búsqueda global
    """
    s = raw.strip()
    if not s:
        raise HTTPException(status_code=400, detail="Indica usuario y contraseña")

    if "/" in s:
        slug, user = s.split("/", 1)
        return slug.strip().lower(), user.strip().lower()

    if "@" in s:
        local, domain = s.rsplit("@", 1)
        local = local.strip().lower()
        domain = domain.strip().lower()
        if "." not in domain:
            return domain, local
        return None, s.lower()

    return None, s.lower()


def _find_employee_in_tenant(
    session: Session, tenant: Tenant, username: str
) -> Employee | None:
    companies = list(
        session.exec(select(Company).where(Company.tenant_id == tenant.id)).all()
    )
    company_ids = [c.id for c in companies]
    if not company_ids:
        return None
    for emp in session.exec(
        select(Employee).where(Employee.company_id.in_(company_ids))  # type: ignore[attr-defined]
    ).all():
        if emp.employee_code.lower() == username:
            return emp
        if emp.email and emp.email.lower() == username:
            return emp
    return None


def _find_employee_global(session: Session, username: str) -> tuple[Tenant, Employee] | None:
    matches: list[tuple[Tenant, Employee]] = []
    for emp in session.exec(select(Employee)).all():
        code_match = emp.employee_code.lower() == username
        email_match = emp.email and emp.email.lower() == username
        if not code_match and not email_match:
            continue
        company = session.get(Company, emp.company_id)
        if not company:
            continue
        tenant = session.get(Tenant, company.tenant_id)
        if not tenant or not tenant.is_active:
            continue
        matches.append((tenant, emp))

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        slugs = sorted({t.slug for t, _ in matches})
        raise HTTPException(
            status_code=400,
            detail=f"Usuario ambiguo. Indica la cuenta: {' o '.join(slugs[:3])} (formato cuenta/usuario)",
        )
    return None


def _tenant_login(
    session: Session, tenant_slug: str, username: str, password: str
) -> UnifiedLoginResult:
    tenant = session.exec(select(Tenant).where(Tenant.slug == tenant_slug)).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    row = _find_employee_in_tenant(session, tenant, username)
    if not row or _role_key(row.role) not in PANEL_ROLES:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not verify_password(password, row.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    perms = get_employee_permissions(session, row, tenant.id)
    if not perms:
        raise HTTPException(
            status_code=403,
            detail="Sin permisos de panel. Asigna un grupo al usuario.",
        )

    return UnifiedLoginResult(
        scope="tenant",
        access_token=create_access_token(
            row.id, _role_key(row.role), tenant.id, row.company_id
        ),
        tenant_slug=tenant.slug,
    )


def _platform_login(session: Session, email: str, password: str) -> UnifiedLoginResult:
    user = session.exec(
        select(PlatformUser).where(PlatformUser.email == email)
    ).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return UnifiedLoginResult(
        scope="platform",
        access_token=create_platform_token(user.id),
    )


def unified_login(session: Session, login: str, password: str) -> UnifiedLoginResult:
    tenant_slug, identity = _parse_login(login)

    if tenant_slug:
        return _tenant_login(session, tenant_slug, identity, password)

    if "@" in identity and "." in identity.split("@", 1)[1]:
        try:
            return _platform_login(session, identity, password)
        except HTTPException as platform_err:
            if platform_err.status_code != 401:
                raise
            found = _find_employee_global(session, identity)
            if found:
                tenant, row = found
                return _tenant_login(session, tenant.slug, identity, password)
            raise platform_err from None

    found = _find_employee_global(session, identity)
    if found:
        tenant, _ = found
        return _tenant_login(session, tenant.slug, identity, password)

    raise HTTPException(status_code=401, detail="Credenciales inválidas")
