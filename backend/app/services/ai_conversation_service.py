"""Historial de conversación WhatsApp para contexto de la IA."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models.ai import AiWhatsappMessage
from app.models.models import Employee
from app.models.tenant import Tenant
from app.models.clock_settings import ClockSettings
from app.services.ai_config_service import build_rules_prompt, list_allowed_action_codes_for_role
from app.services.ai_config_service import _role_to_profile
from app.services.whatsapp_permission_service import (
    ACTION_LABELS,
    list_whatsapp_actions_for_employee,
)

MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_AGE_DAYS = 7
MAX_CONTENT_LEN = 2000


def append_message(
    session: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    role: str,
    content: str,
    intent_code: str | None = None,
) -> None:
    text = (content or "").strip()[:MAX_CONTENT_LEN]
    if not text:
        return
    session.add(
        AiWhatsappMessage(
            tenant_id=tenant_id,
            employee_id=employee_id,
            role=role,
            content=text,
            intent_code=intent_code,
        )
    )
    session.flush()
    _trim_old_messages(session, tenant_id, employee_id)


def _trim_old_messages(
    session: Session, tenant_id: UUID, employee_id: UUID
) -> None:
    cutoff = datetime.utcnow() - timedelta(days=MAX_MESSAGE_AGE_DAYS)
    rows = list(
        session.exec(
            select(AiWhatsappMessage)
            .where(
                AiWhatsappMessage.tenant_id == tenant_id,
                AiWhatsappMessage.employee_id == employee_id,
                AiWhatsappMessage.created_at >= cutoff,
            )
            .order_by(AiWhatsappMessage.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )
    if len(rows) <= MAX_HISTORY_MESSAGES:
        return
    for row in rows[MAX_HISTORY_MESSAGES:]:
        session.delete(row)
    session.flush()


def get_history_for_ollama(
    session: Session,
    tenant_id: UUID,
    employee_id: UUID,
) -> list[dict[str, str]]:
    cutoff = datetime.utcnow() - timedelta(days=MAX_MESSAGE_AGE_DAYS)
    rows = list(
        session.exec(
            select(AiWhatsappMessage)
            .where(
                AiWhatsappMessage.tenant_id == tenant_id,
                AiWhatsappMessage.employee_id == employee_id,
                AiWhatsappMessage.created_at >= cutoff,
            )
            .order_by(AiWhatsappMessage.created_at.asc())  # type: ignore[attr-defined]
        ).all()
    )
    tail = rows[-MAX_HISTORY_MESSAGES:]
    return [
        {"role": r.role if r.role in ("user", "assistant") else "user", "content": r.content}
        for r in tail
    ]


def build_system_prompt(
    session: Session,
    *,
    employee: Employee,
    tenant: Tenant,
    settings: ClockSettings,
    tenant_id: UUID,
) -> str:
    profile = _role_to_profile(employee.role)
    allowed_matrix = list_allowed_action_codes_for_role(session, employee.role)
    allowed_effective = list_whatsapp_actions_for_employee(
        session, employee, tenant_id
    )
    intents_for_model = allowed_effective + ["desconocido"]
    intent_list = ", ".join(intents_for_model)

    lines = [
        "Eres un clasificador de intenciones para un sistema HRM español por WhatsApp.",
        "Analiza el mensaje del empleado (y el historial reciente si existe) y responde ÚNICAMENTE con un JSON válido (sin markdown):",
        "{",
        '  "intent": "<una de las intenciones permitidas>",',
        '  "entities": { "fecha_inicio": "YYYY-MM-DD", "fecha_fin": "YYYY-MM-DD", "motivo": "..." },',
        '  "confidence": 0.0-1.0',
        "}",
        "",
        "=== Contexto del empleado ===",
        f"- Nombre: {employee.full_name}",
        f"- Perfil IA: {profile}",
        f"- Empresa (tenant): {tenant.name}",
        f"- Fichaje con proyecto obligatorio: {'sí' if settings.require_project_on_clock_in else 'no'}",
        f"- Resumen del día disponible: {'sí' if settings.daily_summary_enabled else 'no'}",
        f"- Documentación por WhatsApp: {'sí' if settings.inbound_documents_enabled else 'no'}",
        "",
        "=== Intenciones PERMITIDAS para este empleado ===",
        f"Solo puedes devolver una de: {intent_list}.",
        "Si pide algo no permitido, usa desconocido.",
        "",
        "Descripción de intenciones:",
    ]
    for code in intents_for_model:
        if code == "desconocido":
            lines.append("- desconocido: no encaja o acción no permitida")
        else:
            lines.append(f"- {code}: {ACTION_LABELS.get(code, code)}")

    lines.extend(
        [
            "",
            "=== Reglas de clasificación base ===",
            '- "entrada", "fiché", "empiezo", "llego" -> fichar_entrada (si permitido)',
            '- "salida", "termino", "me voy" -> fichar_salida (si permitido)',
            '- "parada", "descanso", "pausa" -> inicio_parada o fin_parada según contexto',
            "- vacaciones, días libres -> solicitar_vacaciones",
            "- saldo vacaciones, cuántos días -> consultar_saldo_vacaciones",
            '- "recibido", "acepto" documento -> confirmar_documento',
            "- resumen del día, qué he fichado hoy -> resumen_dia (solo si está disponible)",
            "",
            "Matriz IA (perfil): " + ", ".join(allowed_matrix) or "ninguna",
            "Efectivas (con permisos panel): " + ", ".join(allowed_effective) or "ninguna",
        ]
    )

    rules = build_rules_prompt(session)
    if rules:
        lines.append("")
        lines.append(rules)

    return "\n".join(lines)
