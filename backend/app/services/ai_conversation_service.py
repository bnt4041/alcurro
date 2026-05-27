"""Historial de conversación WhatsApp para contexto de la IA."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models.ai import AiWhatsappMessage
from app.models.models import BreakType, ClockInType, Employee
from app.models.tenant import Tenant
from app.models.clock_settings import ClockSettings
from app.services.break_service import BreakService
from app.services.clock_pending_service import get_pending
from app.services.clock_service import ClockService
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


def build_employee_clock_context(
    session: Session,
    tenant_id: UUID,
    employee_id: UUID,
) -> str:
    """Estado de fichaje para que el modelo interprete mensajes coloquiales."""
    clock = ClockService(session, tenant_id)
    last = clock.get_last_clock(employee_id)
    pending = get_pending(session, employee_id)
    lines: list[str] = []

    if last:
        tipo = "ENTRADA" if last.record_type == ClockInType.ENTRADA else "SALIDA"
        lines.append(
            f"- Último fichaje registrado: {tipo} "
            f"({last.recorded_at.strftime('%Y-%m-%d %H:%M')} UTC)."
        )
        if last.record_type == ClockInType.ENTRADA:
            lines.append(
                "- Si el empleado dice «ficho», «fichar ahora», «me voy» sin más detalle, "
                "lo más probable es que quiera fichar SALIDA."
            )
        else:
            lines.append(
                "- Tras una SALIDA (o sin jornada abierta), «ficho» / «empiezo» "
                "suele significar fichar ENTRADA."
            )
    else:
        lines.append("- No hay fichajes previos registrados para este empleado.")
        lines.append(
            "- Mensajes como «ficho ahora», «llego», «empiezo» suelen ser fichar ENTRADA."
        )

    if pending:
        rt = pending.record_type or "entrada"
        lines.append(
            f"- Hay una selección de proyecto pendiente para fichaje de {rt.upper()}. "
            "Si responde con un número o nombre de proyecto, no es un fichaje nuevo."
        )

    return "\n".join(lines)


def build_employee_break_context(
    session: Session,
    employee_id: UUID,
) -> str:
    """Estado de paradas para interpretar «vuelvo al trabajo», «pausa», etc."""
    last = BreakService(session).get_last_break(employee_id)
    if not last:
        return (
            "- Sin paradas registradas hoy recientemente.\n"
            "- «Voy a descansar», «pausa», «a comer» → inicio_parada.\n"
            "- «Vuelvo al trabajo» sin parada abierta puede ser fichar_entrada "
            "(según fichaje).\n"
            "- Las paradas se asocian automáticamente al fichaje de entrada abierto."
        )
    tipo = "INICIO (parada abierta)" if last.record_type == BreakType.INICIO else "FIN"
    lines = [
        f"- Última parada: {tipo} ({last.recorded_at.strftime('%Y-%m-%d %H:%M')} UTC).",
    ]
    if last.record_type == BreakType.INICIO:
        lines.append(
            "- «Vuelvo al trabajo», «vuelvo», «regreso», «sigo trabajando», "
            "«termino el descanso» → fin_parada."
        )
        lines.append(
            "- La parada está vinculada al fichaje de entrada activo (jornada abierta)."
        )
    else:
        lines.append(
            "- Tras cerrar parada, «voy a descansar» / «pausa» → inicio_parada."
        )
    return "\n".join(lines)


def get_history_for_ollama(
    session: Session,
    tenant_id: UUID,
    employee_id: UUID,
    *,
    exclude_last_user_content: str | None = None,
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
    out = [
        {
            "role": r.role if r.role in ("user", "assistant") else "user",
            "content": r.content,
        }
        for r in tail
    ]
    if (
        exclude_last_user_content
        and out
        and out[-1]["role"] == "user"
        and out[-1]["content"].strip() == exclude_last_user_content.strip()
    ):
        out = out[:-1]
    return out


def build_system_prompt(
    session: Session,
    *,
    employee: Employee,
    tenant: Tenant,
    settings: ClockSettings,
    tenant_id: UUID,
    nlu_hint: str | None = None,
) -> str:
    profile = _role_to_profile(employee.role)
    allowed_matrix = list_allowed_action_codes_for_role(session, employee.role)
    allowed_effective = list_whatsapp_actions_for_employee(
        session, employee, tenant_id
    )
    intents_for_model = allowed_effective + ["desconocido"]
    intent_list = ", ".join(intents_for_model)

    clock_ctx = build_employee_clock_context(session, tenant_id, employee.id)
    break_ctx = build_employee_break_context(session, employee.id)

    lines = [
        "Eres el asistente de RRHH de la empresa por WhatsApp. Actúas como ORQUESTADOR "
        "conversacional: tu trabajo es guiar al empleado paso a paso hasta ejecutar la "
        "acción correcta, usando el historial de la conversación como contexto.",
        "",
        "Responde ÚNICAMENTE con un JSON válido (sin markdown ni texto extra):",
        "{",
        '  "stage": "ask" | "confirm" | "execute",',
        '  "intent": "<intención detectada o desconocido>",',
        '  "entities": { "fecha_inicio": "YYYY-MM-DD", "fecha_fin": "YYYY-MM-DD", "motivo": "..." },',
        '  "confidence": 0.0-1.0,',
        '  "message": "<texto que se enviará al empleado en WhatsApp>"',
        "}",
        "",
        "=== Los 3 stages y cuándo usar cada uno ===",
        "",
        '1. "ask" — necesitas más información del empleado:',
        "   • El mensaje es ambiguo o incompleto (ej. «necesito algo» sin especificar).",
        "   • Faltan datos para ejecutar la acción (ej. faltan fechas para vacaciones).",
        '   • El empleado pregunta algo y necesitas aclarar (ej. «¿para qué fecha?»).',
        "   • message DEBE ser una pregunta clara y breve en español.",
        "",
        '2. "confirm" — has entendido la intención y necesitas confirmación:',
        "   • La intención es clara (fichaje, parada, vacaciones) y es una acción que modifica estado.",
        '   • message DEBE ser: "Hola [nombre], entiendo que quieres [acción], ¿es correcto? Responde sí o no."',
        "   • NO confirmes acciones de solo lectura (consultar saldo, resumen del día).",
        "",
        '3. "execute" — la acción ya está confirmada o es de solo lectura:',
        "   • El empleado acaba de responder «sí»/«vale»/«ok» a una confirmación previa.",
        "   • Es una consulta (saldo vacaciones, resumen día) que no necesita confirmación.",
        "   • intent DEBE ser la acción a ejecutar (nunca desconocido).",
        "   • message puede ser un mensaje de éxito breve o vacío (el sistema añadirá el resultado).",
        "",
        "=== Reglas de oro ===",
        "- Usa SIEMPRE el historial: si el asistente acaba de preguntar «¿quieres fichar entrada?»",
        "  y el empleado dice «sí», el stage es «execute» con intent=fichar_entrada.",
        "- Si el empleado dice «no»/«cancelar» tras una confirmación, stage=ask con intent=desconocido",
        "  y message amable ofreciendo ayuda de nuevo.",
        "- Saludos solos («hola», «buenos días») → stage=ask, intent=desconocido,",
        "  message ofreciendo ayuda breve.",
        "- Ante duda real, stage=ask pidiendo aclaración, confidence < 0.5.",
        "- NO uses stage=execute para fichajes/paradas/vacaciones a menos que el historial "
        "muestre claramente que el empleado ya confirmó (dijo «sí»/«vale»/«ok»).",
        "",
        "=== Contexto del empleado ===",
        f"- Nombre: {employee.full_name}",
        f"- Perfil IA: {profile}",
        f"- Empresa: {tenant.name}",
        f"- Fichaje con proyecto obligatorio: {'sí' if settings.require_project_on_clock_in else 'no'}",
        f"- Resumen del día disponible: {'sí' if settings.daily_summary_enabled else 'no'}",
        f"- Documentación por WhatsApp: {'sí' if settings.inbound_documents_enabled else 'no'}",
        "",
        "=== Estado de fichaje (ahora) ===",
        clock_ctx,
        "",
        "=== Estado de paradas (ahora) ===",
        break_ctx,
        "",
        "=== Intenciones PERMITIDAS para este empleado ===",
        f"Solo puedes devolver una de: {intent_list}.",
        "Si pide algo no permitido para su perfil, usa stage=ask con intent=desconocido.",
        "",
        "Descripción de intenciones:",
    ]
    for code in intents_for_model:
        if code == "desconocido":
            lines.append(
                "- desconocido: saludo, charla, o mensaje ambiguo. "
                "Usar con stage=ask para preguntar qué necesita."
            )
        else:
            lines.append(f"- {code}: {ACTION_LABELS.get(code, code)}")

    lines.extend(
        [
            "",
            "=== Ejemplos de conversación completa ===",
            "",
            "# Ejemplo 1 — Fichaje con confirmación:",
            "Historial: [user: «ficho ya»] →",
            '  {"stage":"confirm","intent":"fichar_entrada","confidence":0.9,'
            '"message":"Hola Juan, entiendo que quieres fichar la entrada, ¿es correcto? Responde sí o no."}',
            "",
            "Historial: [..., assistant: «¿es correcto?»] [user: «si»] →",
            '  {"stage":"execute","intent":"fichar_entrada","confidence":1.0,'
            '"message":"¡Perfecto! Te registro la entrada."}',
            "",
            "# Ejemplo 2 — Consulta directa:",
            "Historial: [user: «¿cuántos días de vacaciones me quedan?»] →",
            '  {"stage":"execute","intent":"consultar_saldo_vacaciones","confidence":0.95,"message":""}',
            "",
            "# Ejemplo 3 — Ambigüedad:",
            "Historial: [user: «necesito algo»] →",
            '  {"stage":"ask","intent":"desconocido","confidence":0.2,'
            '"message":"Cuéntame qué necesitas: ¿fichar, una parada, consultar vacaciones...?"}',
            "",
            "# Ejemplo 4 — Vacaciones con fechas incompletas:",
            "Historial: [user: «quiero pedir vacaciones»] →",
            '  {"stage":"ask","intent":"solicitar_vacaciones","confidence":0.7,'
            '"message":"Claro, ¿para qué fechas quieres solicitar las vacaciones? (ej. del 10 al 15 de junio)"}',
            "",
            "# Ejemplo 5 — Cancelación tras confirmación:",
            "Historial: [..., assistant: «¿quieres fichar salida?»] [user: «no, cancelar»] →",
            '  {"stage":"ask","intent":"desconocido","confidence":0.9,'
            '"message":"Entendido, no pasa nada. ¿Necesitas algo más?"}',
            "",
            "Matriz IA (perfil): " + ", ".join(allowed_matrix) or "ninguna",
            "Efectivas (con permisos panel): " + ", ".join(allowed_effective) or "ninguna",
        ]
    )

    if nlu_hint:
        lines.extend(["", "=== Pista del analizador rápido ===", nlu_hint])

    rules = build_rules_prompt(session)
    if rules:
        lines.append("")
        lines.append(rules)

    return "\n".join(lines)
