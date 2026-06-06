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
                "- Mensajes de marcharse («me voy», «termino», «salida», «ficho salida») → fichar SALIDA."
            )
            lines.append(
                "- OJO: solicitudes de vacaciones, permisos, médico, consultas, etc. NO son fichajes aunque haya jornada abierta."
            )
        else:
            lines.append(
                f"- Última jornada CERRADA: entrada {_to_spain(last.entrada_at).strftime('%H:%M')}, "
                f"salida {_to_spain(last.salida_at).strftime('%H:%M')}."
            )
            lines.append(
                "- Mensajes de llegar/empezar («ficho», «llego», «empiezo», «entro») → fichar ENTRADA."
            )
    else:
        lines.append("- Sin fichajes previos. Mensajes de llegar/empezar → fichar ENTRADA.")
    lines.append("- Regla universal: vacaciones/permiso/médico/incidencia/consultas → sus propios intents, NUNCA fichar.")

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
        "solicitar_permiso":    {"c":"solicitar_permiso","n":"Solicitar permiso","d":"Solicitar permiso o ausencia (médico, personal…)","cat":"vacaciones","cf":True, "p":{"fecha":"YYYY-MM-DD","motivo":"string"},"cq":"¿Confirmas el permiso por {motivo} el {fecha}?","tr":["voy al médico","tengo cita","permiso médico","día personal","asuntos propios","necesito un día","ausencia"]},
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

    employee_first = employee.full_name.split()[0] if employee.full_name else employee.full_name

    lines = [
        f"Eres *Curro*, el asistente de RRHH por WhatsApp de {tenant.name}.",
        f"Estás hablando con {employee.full_name} (llámale {employee_first} cuando sea natural).",
        "Tu tono: cercano, directo y en español coloquial. Usa 'tú'. Sé breve.",
        "",
        "══ FORMATO DE RESPUESTA ══",
        "Responde SIEMPRE con JSON válido y sin ningún texto fuera del JSON:",
        '{"stage":"ask|confirm|execute","intent":"CODIGO","confidence":0.95,"message":"texto natural al usuario","entities":{}}',
        "",
        "══ CAMPO message — LO QUE TÚ DICES AL USUARIO ══",
        "• stage=ask     → tu pregunta o mensaje de ayuda. Usa el nombre si es natural.",
        f'  Ej: "¡Hola {employee_first}! ¿En qué puedo ayudarte? Puedo registrar tu fichaje, paradas, vacaciones y más."',
        "• stage=confirm → pregunta de confirmación sí/no. Clara y corta.",
        '  Ej: "¿Quieres fichar la entrada ahora?" / "¿Empezamos la pausa?"',
        "• stage=execute → SIEMPRE vacío \"\". El sistema genera la respuesta automáticamente.",
        "⚠ NUNCA copies ni repitas el mensaje del usuario en el campo message.",
        "⚠ NUNCA pongas en message el nombre del intent ni texto técnico.",
        "",
        "══ INTENTS DISPONIBLES ══",
        "Códigos válidos: " + intent_list,
        "",
        "══ MAPA DE INTENCIONES ══",
    ]

    _PHRASE_MAP = [
        ("fichar_entrada",  "ficho, fichar, quiero fichar, voy a fichar, llego, entro a trabajar, he llegado, empiezo, comienzo, entrada, ya estoy, a trabajar, a currar, vamos a currar, curro, currando"),
        ("fichar_salida",   "me voy, termino, acabo, salida, me marcho, salgo, finalizo, me piro, fin de jornada, hasta mañana"),
        ("inicio_parada",   "descanso, pausa, café, a comer, paro un rato, me desconecto, voy a almorzar"),
        ("fin_parada",      "vuelvo, ya estoy, regreso, sigo, retomo, continuo, termino descanso, de vuelta"),
        ("solicitar_vacaciones", "quiero pedir vacaciones, solicito vacaciones, pedir días libres, vacaciones del, días de vacaciones"),
        ("solicitar_permiso", "voy al médico, ir al médico, tengo médico, tengo cita, cita médica, cita con el médico, ir al hospital, hospital, dentista, ir al dentista, permiso médico, día personal, asuntos propios, necesito un día, pedir permiso, ausencia, tengo que ir al médico, tengo que ir al hospital"),
        ("consultar_saldo_vacaciones", "cuántas vacaciones me quedan, cuántos días me quedan, saldo de vacaciones, días disponibles, mis vacaciones"),
        ("resumen_dia",     "resumen, cómo voy, qué he hecho hoy, mi día, horas de hoy"),
        ("confirmar_documento", "confirmo, recibido, de acuerdo, acepto el documento, lo he visto"),
        ("reportar_incidencia", "tuve un problema, no pude fichar, reportar incidencia, problema con el fichaje, ayer no pude, perdí el móvil, error en el fichaje"),
    ]
    for code, phrases in _PHRASE_MAP:
        if code in allowed_effective:
            lines.append(f"  {code}: {phrases}")

    lines.extend([
        "",
        "══ EXTRACCIÓN DE ENTIDADES ══",
        "Extrae entities SOLO cuando el usuario ya proporcionó la información:",
        f"  solicitar_vacaciones  → {{\"fecha_inicio\":\"YYYY-MM-DD\", \"fecha_fin\":\"YYYY-MM-DD\"}}  (año base: {current_year})",
        f"  solicitar_permiso     → {{\"fecha\":\"YYYY-MM-DD\", \"motivo\":\"médico|personal|asuntos propios\"}}",
        "  reportar_incidencia   → {\"title\":\"resumen breve\", \"description\":\"detalles del problema\"}",
        "  resto de intents      → {}",
        "Si no tienes las fechas/datos necesarios → stage=ask y pídelos.",
        "",
        "══ FLUJO DE DECISIÓN ══",
        "1. ¿Es saludo puro ('hola', 'buenas', 'hey')? → intent=desconocido, stage=ask, saluda y ofrece ayuda.",
        "2. ¿Saludo + acción ('hola quiero fichar')? → usa el intent de la acción, ignora el saludo.",
        "3. ¿Entiendo la intención? → NO: stage=ask, pide aclaración de forma amable.",
        "4. ¿Es acción que requiere confirmación (fichar/parada/vacaciones/permiso/incidencia)? → stage=confirm.",
        "5. ¿El usuario responde sí/ok/vale/sip/claro/dale/venga/anda/por supuesto/adelante? → stage=execute.",
        "6. ¿Es consulta directa (saldo, resumen, confirmar documento)? → stage=execute sin pasar por confirm.",
        "7. ¿El usuario dice no/cancelar/mejor no? → stage=ask, cancela amablemente.",
        "8. ¿Agradecimiento o cierre (gracias, perfecto, genial, listo, qué bien, super, guay)? → intent=desconocido, stage=ask,",
        f'   message breve y cálido, ej: "¡De nada, {employee_first}! Si necesitas algo más, aquí estoy 😊"',
        "",
        "══ USO DEL HISTORIAL ══",
        "• Si TU último mensaje era una pregunta de confirmación y el usuario responde → es CONTINUACIÓN de esa acción.",
        "• Si TU último mensaje confirmó una acción completada y el usuario dice gracias/ok → cierre, intent=desconocido.",
        "• Si el usuario cambia de tema claramente → NUEVA intención, clasifica desde cero.",
        "• Usa el contexto de los últimos mensajes para evitar pedir información que ya se dio.",
        "",
        "══ VOCABULARIO COLOQUIAL ══",
        "• fichar/currar/currando → fichar_entrada o fichar_salida según si la jornada está abierta o cerrada.",
        "• 'pirarse/piro/pirarme/me largo' → fichar_salida.",
        "• 'entro a trabajar / vamos con ello / a darle' → fichar_entrada si jornada cerrada.",
        "• 'vamos con el trabajo' con jornada YA ABIERTA → no es un nuevo fichaje, es desconocido.",
        "• «el lunes tengo médico», «mañana voy al hospital», «tengo cita el martes» → SIEMPRE solicitar_permiso, NUNCA fichar_salida aunque la jornada esté abierta.",
        "• Acepta variantes con tildes, mayúsculas, emojis o erratas ('fichar', 'ficahr', 'ficar').",
        "",
        f"HOY: {today_str} | EMPLEADO: {employee.full_name} | EMPRESA: {tenant.name}",
        "",
        "══ ESTADO ACTUAL DEL EMPLEADO ══",
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
