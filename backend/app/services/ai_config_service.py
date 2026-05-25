"""Catálogo de acciones IA, matriz por perfil y reglas conversacionales."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.ai import AiAction, AiConversationRule, AiProfileAction
from app.models.models import Role
from app.schemas.ai import (
    AiActionMatrixRow,
    AiActionRead,
    AiConversationRuleRead,
    AiMatrixCellUpdate,
    AiProfileActionCell,
)

AI_PROFILES: list[tuple[str, str]] = [
    ("employee", "Empleado"),
    ("manager", "Responsable"),
    ("tenant_admin", "Administrador de cuenta"),
    ("labor_inspector", "Inspector de Trabajo"),
]

DEFAULT_ACTIONS: list[tuple[str, str, str, str, int]] = [
    ("fichar_entrada", "Fichar entrada", "Registra entrada por mensaje", "fichajes", 0),
    ("fichar_salida", "Fichar salida", "Registra salida por mensaje", "fichajes", 1),
    ("inicio_parada", "Inicio de parada", "Inicia parada / descanso", "paradas", 2),
    ("fin_parada", "Fin de parada", "Finaliza parada / descanso", "paradas", 3),
    ("solicitar_vacaciones", "Solicitar vacaciones", "Crea solicitud de vacaciones", "vacaciones", 4),
    (
        "consultar_saldo_vacaciones",
        "Consultar saldo vacaciones",
        "Informa días disponibles",
        "vacaciones",
        5,
    ),
    (
        "confirmar_documento",
        "Confirmar documento",
        "Acuse de recibo de documento",
        "documentos",
        6,
    ),
    (
        "resumen_dia",
        "Resumen del día",
        "Muestra fichajes y paradas del día actual",
        "fichajes",
        7,
    ),
]

# Perfil -> códigos habilitados por defecto
DEFAULT_PROFILE_MATRIX: dict[str, set[str]] = {
    "employee": {
        "fichar_entrada",
        "fichar_salida",
        "inicio_parada",
        "fin_parada",
        "solicitar_vacaciones",
        "consultar_saldo_vacaciones",
        "confirmar_documento",
        "resumen_dia",
    },
    "manager": {code for code, *_ in DEFAULT_ACTIONS},
    "tenant_admin": {code for code, *_ in DEFAULT_ACTIONS},
    "labor_inspector": {"consultar_saldo_vacaciones"},
}


def ensure_ai_catalog(session: Session) -> None:
    for code, name, desc, cat, order in DEFAULT_ACTIONS:
        row = session.exec(select(AiAction).where(AiAction.code == code)).first()
        if not row:
            row = AiAction(
                code=code,
                name=name,
                description=desc,
                category=cat,
                sort_order=order,
            )
            session.add(row)
    session.flush()

    actions = {
        a.code: a
        for a in session.exec(select(AiAction)).all()
    }
    for profile_key, allowed in DEFAULT_PROFILE_MATRIX.items():
        for code, action in actions.items():
            exists = session.exec(
                select(AiProfileAction).where(
                    AiProfileAction.action_id == action.id,
                    AiProfileAction.profile_key == profile_key,
                )
            ).first()
            if not exists:
                session.add(
                    AiProfileAction(
                        action_id=action.id,
                        profile_key=profile_key,
                        enabled=code in allowed,
                    )
                )
    session.flush()


def get_action_matrix(session: Session) -> list[AiActionMatrixRow]:
    ensure_ai_catalog(session)
    actions = list(
        session.exec(
            select(AiAction)
            .where(AiAction.is_active == True)  # noqa: E712
            .order_by(AiAction.sort_order, AiAction.name)
        ).all()
    )
    links = {
        (l.action_id, l.profile_key): l.enabled
        for l in session.exec(select(AiProfileAction)).all()
    }
    rows: list[AiActionMatrixRow] = []
    for action in actions:
        profiles = [
            AiProfileActionCell(
                profile_key=key,
                enabled=links.get((action.id, key), False),
            )
            for key, _ in AI_PROFILES
        ]
        rows.append(
            AiActionMatrixRow(
                action=AiActionRead.model_validate(action),
                profiles=profiles,
            )
        )
    return rows


def update_action_matrix(
    session: Session, cells: list[AiMatrixCellUpdate]
) -> list[AiActionMatrixRow]:
    ensure_ai_catalog(session)
    valid_profiles = {k for k, _ in AI_PROFILES}
    for cell in cells:
        if cell.profile_key not in valid_profiles:
            continue
        aid = cell.action_id
        link = session.exec(
            select(AiProfileAction).where(
                AiProfileAction.action_id == aid,
                AiProfileAction.profile_key == cell.profile_key,
            )
        ).first()
        if link:
            link.enabled = cell.enabled
            session.add(link)
        else:
            session.add(
                AiProfileAction(
                    action_id=aid,
                    profile_key=cell.profile_key,
                    enabled=cell.enabled,
                )
            )
    session.flush()
    return get_action_matrix(session)


def is_action_allowed_for_role(session: Session, role: Role | str, action_code: str) -> bool:
    if action_code in ("desconocido", ""):
        return True
    profile = _role_to_profile(role)
    action = session.exec(
        select(AiAction).where(AiAction.code == action_code, AiAction.is_active == True)  # noqa: E712
    ).first()
    if not action:
        return False
    link = session.exec(
        select(AiProfileAction).where(
            AiProfileAction.action_id == action.id,
            AiProfileAction.profile_key == profile,
        )
    ).first()
    return bool(link and link.enabled)


def _role_to_profile(role: Role | str) -> str:
    r = role.value if isinstance(role, Role) else str(role)
    if r in ("admin", "tenant_admin"):
        return "tenant_admin"
    if r == "supervisor":
        return "manager"
    if r in ("employee", "manager", "labor_inspector", "tenant_admin"):
        return r
    return "employee"


def list_rules(session: Session) -> list[AiConversationRuleRead]:
    rows = session.exec(
        select(AiConversationRule).order_by(
            AiConversationRule.priority,
            AiConversationRule.created_at,
        )
    ).all()
    return [AiConversationRuleRead.model_validate(r) for r in rows]


def build_rules_prompt(session: Session) -> str:
    rules = session.exec(
        select(AiConversationRule)
        .where(AiConversationRule.is_active == True)  # noqa: E712
        .order_by(AiConversationRule.priority, AiConversationRule.created_at)
    ).all()
    if not rules:
        return ""
    lines = ["Reglas adicionales (ordenadas por prioridad):"]
    for i, rule in enumerate(rules, start=1):
        lines.append(f"{i}. [{rule.title}] {rule.content}")
    return "\n".join(lines)


def reorder_rules(session: Session, rule_ids: list[UUID]) -> list[AiConversationRuleRead]:
    for priority, rid in enumerate(rule_ids):
        row = session.get(AiConversationRule, rid)
        if row:
            row.priority = priority * 10
            row.updated_at = datetime.utcnow()
            session.add(row)
    session.flush()
    return list_rules(session)
