"""Añade create_own / update_own y ajusta grupo Empleados con panel."""

from sqlmodel import Session, select

from app.core.permissions import ALL_PERMS, OWN_SCOPE_MODULES, create_own_perm, update_own_perm
from app.database import engine
from app.models.rbac import UserGroup
from app.services.rbac_service import EMPLOYEE_PANEL_PERMS, ensure_system_groups

# Si tenían solo .write en módulos de empleado (sin lectura global), pasan a create+update own
WRITE_TO_OWN_MODULES = OWN_SCOPE_MODULES


def _upgrade_group_perms(perms: list[str]) -> list[str]:
    s = set(perms)
    for module in WRITE_TO_OWN_MODULES:
        write_key = f"{module}.write"
        c_own = create_own_perm(module)
        u_own = update_own_perm(module)
        if write_key in s and module != "legal":
            # leave.write / employees.write = gestión completa; no sustituir
            if module in ("leave", "employees", "shifts", "documents", "signatures"):
                continue
            if c_own not in s and u_own not in s:
                s.discard(write_key)
                s.add(c_own)
                s.add(u_own)
        if module == "leave" and write_key in s:
            if c_own not in s:
                s.add(c_own)
            if u_own not in s:
                s.add(u_own)
            s.discard(write_key)
    if "clock_ins.create_own" in s and "breaks.create_own" not in s:
        s.add("breaks.create_own")
    if "documents.read_own" in s and "signatures.create_own" not in s:
        s.add("signatures.read_own")
    return sorted(p for p in s if p in ALL_PERMS)


def run() -> None:
    with Session(engine) as session:
        tenant_ids = {g.tenant_id for g in session.exec(select(UserGroup)).all()}
        for tenant_id in tenant_ids:
            ensure_system_groups(session, tenant_id)
        session.commit()

        for g in session.exec(select(UserGroup)).all():
            if g.name == "Empleados con panel":
                g.permissions = sorted(EMPLOYEE_PANEL_PERMS)
            else:
                g.permissions = _upgrade_group_perms(list(g.permissions))
            session.add(g)
        session.commit()
    print("Permisos v3 OK — create_own / update_own")


if __name__ == "__main__":
    run()
