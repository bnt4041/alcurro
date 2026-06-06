"""Historial de conversación WhatsApp para contexto de la IA."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

_SPAIN_TZ = ZoneInfo("Europe/Madrid")


def _now_spain() -> datetime:
    return datetime.now(tz=_SPAIN_TZ)


def _to_spain(dt: datetime) -> datetime:
    """Convierte un datetime UTC naive a hora española."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_SPAIN_TZ)

from sqlmodel import Session, select

from app.models.ai import AiWhatsappMessage
from app.models.models import BreakType, Employee
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

MAX_HISTORY_MESSAGES = 5
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
        if last.salida_at is None:
            lines.append(
                f"- Jornada ABIERTA desde {_to_spain(last.entrada_at).strftime('%Y-%m-%d %H:%M')} (sin salida)."
            )
            lines.append(
                "- «me voy», «ficho», «termino», «me piro», «a currar» sin más contexto → fichar SALIDA."
            )
        else:
            lines.append(
                f"- Última jornada CERRADA: entrada {_to_spain(last.entrada_at).strftime('%H:%M')}, "
                f"salida {_to_spain(last.salida_at).strftime('%H:%M')}."
            )
            lines.append(
                "- Sin jornada abierta: «ficho», «llego», «empiezo», «a currar» → fichar ENTRADA."
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
        f"- Última parada: {tipo} ({_to_spain(last.recorded_at).strftime('%Y-%m-%d %H:%M')}).",
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


def _build_actions_catalog(
    session: Session,
    allowed_codes: list[str],
) -> str:
    """Catálogo compacto de acciones como JSON para incluir en el prompt del modelo."""
    from app.models.ai import AiAction

    actions = session.exec(
        select(AiAction).where(
            AiAction.code.in_(allowed_codes),
            AiAction.is_active == True,  # noqa: E712
        )
    ).all()
    action_map = {a.code: a for a in actions}

    _TPL: dict[str, dict] = {
        "fichar_entrada":       {"c":"fichar_entrada","n":"Fichar entrada","d":"Inicio de jornada","cat":"fichajes","cf":True, "p":{},"cq":"¿Quieres fichar la entrada ahora?","tr":["ficho","llego","empiezo","comienzo","entrada","empezar a trabajar","ya estoy"]},
        "fichar_salida":        {"c":"fichar_salida","n":"Fichar salida","d":"Fin de jornada","cat":"fichajes","cf":True, "p":{},"cq":"¿Quieres fichar la salida ahora?","tr":["me voy","termino","acabo","salida","me marcho","salgo","finalizo","me piro"]},
        "inicio_parada":        {"c":"inicio_parada","n":"Iniciar parada","d":"Pausa/descanso","cat":"paradas","cf":True, "p":{},"cq":"¿Quieres iniciar una pausa ahora?","tr":["descanso","pausa","cafe","a comer","paro un rato","desconecto"]},
        "fin_parada":           {"c":"fin_parada","n":"Finalizar parada","d":"Reanudar jornada","cat":"paradas","cf":True, "p":{},"cq":"¿Quieres finalizar la pausa y reanudar?","tr":["vuelvo","regreso","sigo","retomo","termino descanso","continuo"]},
        "solicitar_vacaciones": {"c":"solicitar_vacaciones","n":"Solicitar vacaciones","d":"Crear solicitud de vacaciones","cat":"vacaciones","cf":True, "p":{"fecha_inicio":"YYYY-MM-DD","fecha_fin":"YYYY-MM-DD"},"cq":"¿Confirmas las vacaciones del {fecha_inicio} al {fecha_fin}?","tr":["quiero pedir vacaciones","solicito vacaciones","pedir dias libres","vacaciones del","dias libres del"]},
        "consultar_saldo_vacaciones": {"c":"consultar_saldo_vacaciones","n":"Consultar saldo","d":"Días disponibles","cat":"vacaciones","cf":False,"p":{},"cq":None,"tr":["cuantas vacaciones me quedan","cuantos dias me quedan","dias de vacaciones","saldo de vacaciones","cuantas vacaciones tengo","dias disponibles","balance de vacaciones","saldo"]},
        "confirmar_documento":  {"c":"confirmar_documento","n":"Confirmar documento","d":"Acuse de recibo","cat":"documentos","cf":False,"p":{},"cq":None,"tr":["confirmo","recibido","de acuerdo","acepto el documento"]},
        "resumen_dia":          {"c":"resumen_dia","n":"Resumen del día","d":"Fichajes y paradas de hoy","cat":"fichajes","cf":False,"p":{},"cq":None,"tr":["resumen","como voy","que he hecho hoy","mi dia","resumen del dia"]},
        "reportar_incidencia":  {"c":"reportar_incidencia","n":"Reportar incidencia","d":"Registrar un problema o incidencia de fichaje","cat":"fichajes","cf":True,"p":{"title":"string","description":"string"},"cq":"¿Quieres que registre esta incidencia?","tr":["tuve un problema","no pude fichar","reportar incidencia","registrar incidencia","perdí el móvil","tuve un inconveniente"]},
    }

    catalog: list[dict] = []
    for code in allowed_codes:
        if code == "desconocido":
            continue
        tmpl = _TPL.get(code)
        if tmpl:
            entry = dict(tmpl)
            if code in action_map:
                entry["n"] = action_map[code].name or entry["n"]
                entry["d"] = action_map[code].description or entry["d"]
            catalog.append(entry)
        elif code in action_map:
            catalog.append({"c":code,"n":action_map[code].name,"d":action_map[code].description or "","cat":action_map[code].category,"cf":True,"p":{},"cq":f"¿Quieres {action_map[code].name.lower()}?","tr":[]})

    import json
    return json.dumps(catalog, ensure_ascii=False, indent=2)


def build_system_prompt(
    session: Session,
    *,
    employee: Employee,
    tenant: Tenant,
    settings: ClockSettings,
    tenant_id: UUID,
    nlu_hint: str | None = None,
) -> str:
    allowed_effective = list_whatsapp_actions_for_employee(
        session, employee, tenant_id
    )
    intents_for_model = allowed_effective + ["desconocido"]
    intent_list = ", ".join(intents_for_model)

    clock_ctx = build_employee_clock_context(session, tenant_id, employee.id)
    break_ctx = build_employee_break_context(session, employee.id)

    today_str = _now_spain().strftime("%Y-%m-%d")
    current_year = _now_spain().year

    # Prompt ultra-compacto para modelos pequeños (1.5B-7B)
    lines = [
        "Eres Curro, asistente de RRHH por WhatsApp. Clasifica mensajes en JSON.",
        "",
        "RESPONDE SOLO con JSON válido, sin texto extra:",
        '{"stage":"ask|confirm|execute","intent":"CODIGO","confidence":0.9,"message":"TEXTO_PARA_USUARIO","entities":{}}',
        "",
        "STAGE y MESSAGE:",
        "ask    → no entiendes o necesitas más info | message = pregunta o ayuda al usuario",
        "confirm → entendiste, pides confirmación sí/no | message = pregunta de confirmación (ej: '¿Quieres fichar la entrada ahora?')",
        "execute → acción confirmada o consulta directa | message = '' (vacío, el sistema genera la respuesta)",
        "",
        "IMPORTANTE: 'message' es LO QUE TÚ DICES al usuario, NUNCA repitas el mensaje del usuario.",
        "",
        "INTENTS: " + intent_list,
        "",
        "MAPA FRASE -> INTENT:",
    ]

    # Mapa compacto de frases clave
    _PHRASE_MAP = [
        ("fichar_entrada", "ficho, fichar, quiero fichar, voy a fichar, llego, empiezo, comienzo, entrada, ya estoy, a trabajar, a currar, voy a currar, quiero currar, curro, empezar a currar"),
        ("fichar_salida", "me voy, termino, acabo, salida, me marcho, salgo, finalizo, me piro"),
        ("inicio_parada", "descanso, pausa, cafe, a comer, paro un rato, desconecto"),
        ("fin_parada", "vuelvo, regreso, sigo, retomo, continuo, termino descanso"),
        ("solicitar_vacaciones", "quiero pedir vacaciones, solicito vacaciones, pedir dias, vacaciones del"),
        ("consultar_saldo_vacaciones", "cuantas vacaciones me quedan, cuantos dias me quedan, saldo, dias disponibles, cuantas vacaciones tengo"),
        ("resumen_dia", "resumen, como voy, que he hecho hoy, mi dia"),
        ("confirmar_documento", "confirmo, recibido, de acuerdo, acepto"),
        ("reportar_incidencia", "tuve un problema, no pude fichar, reportar incidencia, registrar incidencia, perdí el móvil, tuve un inconveniente, ayer no pude, problema con el fichaje"),
    ]
    for code, phrases in _PHRASE_MAP:
        if code in allowed_effective:
            lines.append(f"- {code}: {phrases}")

    lines.extend([
        "",
        "CONFIRMACIÓN:",
        "- fichar/paradas/vacaciones/reportar_incidencia NUEVAS: stage=confirm (pregunta sí/no)",
        "- consultar_saldo/resumen_dia/confirmar_documento: stage=execute (directo)",
        "- usuario dice sí/ok/vale/dale/confirmo/adelante/anda/venga: stage=execute",
        "- usuario dice no/cancelar: stage=ask",
        "",
        "CIERRE CONVERSACIONAL (MUY IMPORTANTE):",
        "- 'gracias', 'de nada', 'genial', 'perfecto', 'ok', 'qué bien', 'listo', 'super', 'guay', 'mola' → intent=desconocido, stage=ask",
        "- Cualquier expresión de agradecimiento o cierre TRAS una acción completada → intent=desconocido, stage=ask",
        "- NO interpretes un 'gracias' como confirmación ni como nueva acción",
        "",
        "HISTORIAL:",
        "- Si TU último mensaje preguntaba algo y el usuario responde a eso -> CONTINUACIÓN",
        "- Si TU último mensaje confirmó una acción (Fichaje ENTRADA/SALIDA, parada, etc.) y el usuario dice gracias/ok/perfecto -> intent=desconocido, stage=ask",
        "- Si el usuario cambia de tema o saluda -> CONVERSACIÓN NUEVA -> intent=desconocido",
        "- Saludo SOLO (solo 'hola', 'buenas', 'hey'): intent=desconocido, stage=ask",
        "- Saludo + acción ('hola quiero fichar', 'hola voy a currar'): usa el intent de la acción, ignora el saludo",
        "",
        "VOCABULARIO COLOQUIAL:",
        "- fichar / quiero fichar / voy a fichar → fichar_entrada o fichar_salida según contexto (jornada abierta=salida, cerrada=entrada)",
        "- 'vamos con el trabajo' / 'a trabajar' / 'a currar' → si jornada ABIERTA: desconocido (ya está fichado); si jornada CERRADA: fichar_entrada",
        "- currar/curro/currando = trabajar → fichar_entrada o fichar_salida según contexto",
        "- pirarse/piro/pirarme = marcharse → fichar_salida",
        "- chupar el dedo/no hacer nada = no aplica → desconocido",
        "- si el mensaje no encaja perfectamente en el mapa, usa tu comprensión del español para decidir",
        "",
        f"AÑO: {current_year} | HOY: {today_str}",
        f"EMPLEADO: {employee.full_name} | EMPRESA: {tenant.name}",
        "",
        "FICHAJE:",
        clock_ctx,
        "PARADAS:",
        break_ctx,
    ])

    if nlu_hint:
        lines.extend(["", "PISTA NLU (referencia): " + nlu_hint])

    rules = build_rules_prompt(session)
    if rules:
        lines.append("")
        lines.append(rules)

    return "\n".join(lines)
