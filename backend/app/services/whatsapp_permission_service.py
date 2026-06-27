"""Permisos de acciones WhatsApp: matriz IA (perfil) + RBAC del empleado."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.core.permissions import get_employee_permissions, has_perm
from app.models.models import Employee
from app.models.clock_settings import ClockSettings
from app.services.ai_config_service import (
    _role_to_profile,
    is_action_allowed_for_role,
    list_allowed_action_codes_for_role,
)

# Acción WhatsApp -> al menos uno de estos permisos RBAC (sobre datos propios)
ACTION_RBAC_ANY: dict[str, tuple[str, ...]] = {
    "fichar_entrada": ("clock_ins.create_own", "clock_ins.write"),
    "fichar_salida": ("clock_ins.create_own", "clock_ins.write"),
    "inicio_parada": ("breaks.create_own", "breaks.write"),
    "fin_parada": ("breaks.create_own", "breaks.write"),
    "solicitar_vacaciones": ("leave.create_own", "leave.write"),
    "solicitar_permiso": ("leave.create_own", "leave.write"),
    "consultar_saldo_vacaciones": ("leave.read_own", "leave.read"),
    "confirmar_documento": (
        "documents.read_own",
        "documents.write",
        "legal.update_own",
    ),
    "resumen_dia": ("clock_ins.read_own", "clock_ins.read"),
    "reportar_incidencia": ("clock_ins.create_own", "clock_ins.write"),
}

ACTION_LABELS: dict[str, str] = {
    "fichar_entrada": "Fichar entrada",
    "fichar_salida": "Fichar salida",
    "inicio_parada": "Iniciar parada",
    "fin_parada": "Finalizar parada",
    "solicitar_vacaciones": "Solicitar vacaciones",
    "solicitar_permiso": "Solicitar permiso / ausencia",
    "consultar_saldo_vacaciones": "Consultar saldo de vacaciones",
    "confirmar_documento": "Confirmar documento / enviar archivo",
    "resumen_dia": "Resumen del día (fichajes y paradas)",
    "reportar_incidencia": "Reportar incidencia de fichaje",
    "crear_ticket": "Crear ticket de soporte",
    "consultar_tickets": "Consultar tickets de soporte",
    "desconocido": "Sin acción (ayuda)",
}


def _rbac_allows(perms: frozenset[str], action_code: str) -> bool:
    required = ACTION_RBAC_ANY.get(action_code)
    if not required:
        return True
    return any(p in perms for p in required)


def is_whatsapp_action_allowed(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    action_code: str,
) -> bool:
    """
    True si la acción está habilitada en la matriz IA del perfil Y el empleado
    tiene permiso RBAC (si tiene permisos asignados por grupos).
    """
    if action_code in ("desconocido", ""):
        return True
    if not is_action_allowed_for_role(session, employee.role, action_code):
        return False
    perms = get_employee_permissions(session, employee, tenant_id)
    if not perms:
        # Sin grupo: solo matriz IA (empleado WhatsApp sin panel)
        return True
    return _rbac_allows(perms, action_code)


def list_whatsapp_actions_for_employee(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
) -> list[str]:
    """Códigos de acción que el empleado puede ejecutar por WhatsApp."""
    codes = list_allowed_action_codes_for_role(session, employee.role)
    return [c for c in codes if is_whatsapp_action_allowed(session, employee, tenant_id, c)]


def can_whatsapp_location_clock(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    *,
    record_type: str,
) -> bool:
    code = "fichar_entrada" if record_type == "entrada" else "fichar_salida"
    return is_whatsapp_action_allowed(session, employee, tenant_id, code)


def can_whatsapp_inbound_media(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    settings: ClockSettings,
) -> bool:
    if not settings.inbound_documents_enabled:
        return False
    perms = get_employee_permissions(session, employee, tenant_id)
    if not perms:
        return True
    return has_perm(session, employee, tenant_id, "documents.read_own") or has_perm(
        session, employee, tenant_id, "documents.write"
    )


def denial_message(session: Session, employee: Employee, tenant_id: UUID) -> str:
    from app.services.whatsapp_format import format_denial_list

    allowed = list_whatsapp_actions_for_employee(session, employee, tenant_id)
    if not allowed:
        return format_denial_list(
            "Sin acciones por WhatsApp",
            ["Contacta con RRHH o tu responsable."],
        )
    labels = [ACTION_LABELS.get(c, c) for c in allowed[:8]]
    return format_denial_list(
        "Acción no permitida",
        labels,
    )


def profile_key_for_employee_role(employee: Employee) -> str:
    return _role_to_profile(employee.role)
