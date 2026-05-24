"""Actualiza permisos de grupos: apartados nuevos y read_own para empleados."""

from sqlmodel import Session, select

from app.core.permissions import ALL_PERMS
from app.database import engine
from app.models.rbac import UserGroup
from app.services.rbac_service import EMPLOYEE_PANEL_PERMS, ensure_system_groups

READ_OWN_MAP = {
    "employees.read": "employees.read_own",
    "clock_ins.read": "clock_ins.read_own",
    "leave.read": "leave.read_own",
    "documents.read": "documents.read_own",
    "shifts.read": "shifts.read_own",
    "legal.read": "legal.read_own",
}


def _normalize_group_perms(perms: list[str]) -> list[str]:
    s = set(perms)
    for full, own in READ_OWN_MAP.items():
        if full in s and own not in s:
            s.discard(full)
            s.add(own)
    # Paradas: antes compartían clock_ins
    if "clock_ins.read_own" in s and "breaks.read_own" not in s:
        s.add("breaks.read_own")
    if "clock_ins.read" in s and "breaks.read" not in s:
        s.add("breaks.read")
    if "documents.read_own" in s and "signatures.read_own" not in s:
        s.add("signatures.read_own")
    if "documents.read" in s and "signatures.read" not in s:
        s.add("signatures.read")
    return sorted(p for p in s if p in ALL_PERMS)


def run() -> None:
    with Session(engine) as session:
        tenant_ids = {g.tenant_id for g in session.exec(select(UserGroup)).all()}
        for tenant_id in tenant_ids:
            ensure_system_groups(session, tenant_id)
        session.commit()

        groups = session.exec(select(UserGroup)).all()
        for g in groups:
            if g.name == "Empleados con panel":
                g.permissions = sorted(EMPLOYEE_PANEL_PERMS)
            else:
                g.permissions = _normalize_group_perms(list(g.permissions))
            session.add(g)
        session.commit()
    print("Permisos v2 OK — grupos actualizados")


if __name__ == "__main__":
    run()
