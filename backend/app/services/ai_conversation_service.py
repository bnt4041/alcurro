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

MAX_HISTORY_MESSAGES = 10
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
            f"({_to_spain(last.recorded_at).strftime('%Y-%m-%d %H:%M')})."
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
        "consultar_saldo_vacaciones": {"c":"consultar_saldo_vacaciones","n":"Consultar saldo","d":"Días disponibles","cat":"vacaciones","cf":False,"p":{},"cq":None,"tr":["saldo","cuantos dias me quedan","dias disponibles","cuantas vacaciones tengo","balance de vacaciones"]},
        "confirmar_documento":  {"c":"confirmar_documento","n":"Confirmar documento","d":"Acuse de recibo","cat":"documentos","cf":False,"p":{},"cq":None,"tr":["confirmo","recibido","de acuerdo","acepto el documento"]},
        "resumen_dia":          {"c":"resumen_dia","n":"Resumen del día","d":"Fichajes y paradas de hoy","cat":"fichajes","cf":False,"p":{},"cq":None,"tr":["resumen","como voy","que he hecho hoy","mi dia","resumen del dia"]},
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

    actions_catalog = _build_actions_catalog(session, allowed_effective)

    # Prompt conciso y estructurado: prioridad 0 = nuevo vs continuación, 1 = saludos, 2 = interpretar, 3 = catálogo, 4 = confirmar
    lines = [
        "Eres un orquestador conversacional de RRHH por WhatsApp, te llamas Curro. Interpretas mensajes coloquiales",
        "y decides si hay que preguntar, confirmar o ejecutar una acción. Responde SOLO en JSON.",
        "",
        "=== PRIORIDAD 0: ¿CONVERSACIÓN NUEVA O CONTINUACIÓN? ===",
        "ANTES de clasificar la intención, revisa el HISTORIAL y decide el contexto:",
        "",
        "CONTINUACIÓN (el usuario responde a algo que TÚ preguntaste antes):",
        "- Tu último mensaje era una pregunta de confirmación sí/no y el usuario responde",
        "  «sí»/«vale»/«ok»/«dale»/«confirmo»/«adelante» → stage=execute, ejecuta la acción pendiente.",
        "- Tu último mensaje era una pregunta de confirmación y el usuario responde",
        "  «no»/«cancelar»/«mejor no» → stage=ask, pregunta qué quiere hacer en su lugar.",
        "- Tu último mensaje pedía fechas («¿Qué período de vacaciones?») y el usuario",
        "  responde con fechas → stage=confirm, extrae las fechas y confirma el período.",
        "- Tu último mensaje pedía que eligiera un proyecto y el usuario responde con",
        "  un número o nombre → NO es un fichaje nuevo, es la selección del proyecto.",
        "",
        "CONVERSACIÓN NUEVA (el usuario empieza de cero o cambia de tema):",
        "- El historial está vacío o el último mensaje tuyo es de una acción ya ejecutada.",
        "- El usuario manda un saludo («hola», «buenas», «hey») → intent=desconocido, stage=ask.",
        "- El usuario introduce un verbo de acción nuevo («ficho», «me voy», «descanso»)",
        "  que NO tiene relación con lo que se estaba hablando → ignora el contexto previo.",
        "- El usuario dice una palabra suelta («vacaciones?») sin verbo claro",
        "  → intent=desconocido, stage=ask, pregúntale qué quiere hacer exactamente.",
        "",
        "REGLA CLAVE: si el historial muestra que TÚ hiciste una pregunta y el usuario",
        "responde a ella, estás en CONTINUACIÓN. Si el usuario introduce un tema totalmente",
        "nuevo sin relación con tu última pregunta, estás en CONVERSACIÓN NUEVA.",
        "",
        "=== PRIORIDAD 1: CATÁLOGO DE ACCIONES (JSON) ===",
        "Leyenda: c=código, n=nombre, d=descripción, cat=categoría, cf=requiereConfirmación,",
        "p=parámetros, cq=preguntaConfirmación, tr=frasesDisparadoras.",
        actions_catalog,
        "",
        "=== PRIORIDAD 2: FLUJO DE CONFIRMACIÓN ===",
        "- Acciones con cf=true (fichar, paradas, solicitar_vacaciones): stage=confirm, usa cq.",
        "- Acciones con cf=false (consultar_saldo, resumen_dia, confirmar_documento): stage=execute.",
        "- Si el usuario dice «sí»/«vale»/«ok»/«dale»/«confirmo» tras tu confirmación → stage=execute.",
        "- Si el usuario dice «no»/«cancelar» → stage=ask, pregunta qué desea.",
        "- Si el mensaje no encaja en ninguna acción → intent=desconocido, stage=ask.",
        "",
        "=== PRIORIDAD 3: EXTRACCIÓN DE FECHAS (solo para solicitar_vacaciones) ===",
        f"Año actual: {current_year}. Formato: YYYY-MM-DD.",
        f'«del 1 al 8 de agosto» → entities={{"fecha_inicio":"{current_year}-08-01","fecha_fin":"{current_year}-08-08"}}.',
        "Sin fechas claras → stage=ask pidiendo las fechas.",
        "",
        "=== FORMATO DE RESPUESTA ===",
        'SIEMPRE responde SOLO este JSON (nada más):',
        '{"stage":"ask","intent":"fichar_entrada","confidence":0.9,"message":"...","entities":{}}',
        f"stage: ask | confirm | execute. intent: {intent_list}.",
        "",
        f"EMPLEADO: {employee.full_name} | EMPRESA: {tenant.name} | HOY: {today_str}.",
        f"Proyecto obligatorio al fichar: {'SI' if settings.require_project_on_clock_in else 'NO'}.",
        "",
        "ESTADO FICHAJE:",
        clock_ctx,
        "",
        "ESTADO PARADAS:",
        break_ctx,
    ]

    if nlu_hint:
        lines.extend(["", "PISTA NLU (referencia): " + nlu_hint])

    rules = build_rules_prompt(session)
    if rules:
        lines.append("")
        lines.append(rules)

    return "\n".join(lines)
