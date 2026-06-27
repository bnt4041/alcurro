"""Utilidades de texto para WhatsApp: normalización, intents por keywords, confirmación sí/no."""

from __future__ import annotations

import re
import unicodedata
from typing import Callable

from app.schemas.ollama import OllamaIntentResponse

# ---------------------------------------------------------------------------
# Patrones de intención por keyword (alta precisión, ordenados por prioridad)
# ---------------------------------------------------------------------------
# Cada entrada: (regex, intent, stage, confidence, message)
# Se evalúan en orden; el primer match gana.

_INTENT_PATTERNS: list[tuple[re.Pattern, str, str, float, str | None]] = [
    # --- Consultas (execute directo, sin confirmación) ---
    (
        re.compile(
            r"\b("
            r"cuantas\s+vacaciones\s+(me\s+)?quedan|"
            r"cuantos\s+dias\s+(me\s+)?quedan|"
            r"cuantas\s+vacaciones\s+tengo|"
            r"saldo\s+(de\s+)?vacaciones|"
            r"dias\s+( disponibles|de\s+vacaciones)|"
            r"balance\s+de\s+vacaciones|"
            r"que\s+saldo\s+(me\s+)?queda"
            r")\b", re.IGNORECASE
        ),
        "consultar_saldo_vacaciones", "execute", 0.9, None,
    ),
    (
        re.compile(
            r"\b("
            r"resumen\s+(del\s+)?dia|"
            r"como\s+(voy|va\s+(mi|el)\s+dia)|"
            r"que\s+he\s+hecho\s+hoy|"
            r"mi\s+dia|mi\s+jornada|"
            r"cuantas\s+horas\s+(llevo|he\s+hecho)"
            r")\b", re.IGNORECASE
        ),
        "resumen_dia", "execute", 0.9, None,
    ),
    (
        re.compile(
            r"\b("
            r"confirmo|confirmar\s+documento|recibido|"
            r"de\s+acuerdo|acepto\s+(el\s+)?documento"
            r")\b", re.IGNORECASE
        ),
        "confirmar_documento", "execute", 0.7, None,
    ),

    # --- Gestión de equipo (responsables) — execute directo ---
    (
        re.compile(
            r"\b("
            r"(vacaciones|solicitudes)\s+(pendientes|por\s+aprobar|sin\s+aprobar|para\s+aprobar|a\s+aprobar)|"
            r"pendientes\s+de\s+aprobar|"
            r"(que|cuantas)\s+(vacaciones|solicitudes)\s+.*\baprobar\b"
            r")\b", re.IGNORECASE
        ),
        "vacaciones_pendientes", "execute", 0.9, None,
    ),
    (
        re.compile(
            r"\b("
            r"(aprobar|aprueba|apruebo|rechazar|rechaza|rechazo|denegar|deniega|gestionar|revisar)\s+"
            r"(las\s+|unas\s+|esas\s+|estas\s+|la\s+|esa\s+)?(vacaciones|solicitud(es)?)"
            r")\b", re.IGNORECASE
        ),
        "aprobar_vacaciones", "execute", 0.9, None,
    ),
    (
        re.compile(
            r"\b("
            r"incidencias?\s+(sin\s+gestionar|no\s+gestionadas?|por\s+gestionar|sin\s+revisar|pendientes\s+de\s+gestion)"
            r")\b", re.IGNORECASE
        ),
        "incidencias_sin_gestionar", "execute", 0.9, None,
    ),
    (
        re.compile(
            r"\b("
            r"incidencias?\s+(abiertas?|activas?|en\s+curso|sin\s+resolver|del?\s+equipo|del?\s+personal)|"
            r"(ver|muestra|mostrar|listar?|dame|consultar?|ensename|ens[eé]name)\s+(las\s+)?incidencias"
            r")\b", re.IGNORECASE
        ),
        "incidencias_abiertas", "execute", 0.85, None,
    ),

    # --- Fichajes (requieren confirmación) ---
    (
        re.compile(
            r"\b("
            r"ficho\s*(ahora|ya)?|"
            r"fichar\s+entrada|fichar\s+ahora|"
            r"llego|(estoy\s+)?llegando|"
            r"empiezo|comienzo|comenzar\s+(a\s+)?trabajar|"
            r"entrada|ya\s+estoy|en\s+el\s+trabajo|"
            r"voy\s+a\s+(fichar|trabajar|empezar)|"
            r"a\s+trabajar"
            r")\b", re.IGNORECASE
        ),
        "fichar_entrada", "confirm", 0.85, "¿Quieres fichar la entrada ahora?",
    ),
    (
        re.compile(
            r"\b("
            r"me\s+voy|me\s+marcho|me\s+piro|"
            r"termino|acabo|finalizo|"
            r"salida|fin\s+de\s+jornada|"
            r"salgo|terminar\s+(de\s+)?trabajar|"
            r"he\s+terminado|he\s+acabado|"
            r"voy\s+a\s+salir"
            r")\b", re.IGNORECASE
        ),
        "fichar_salida", "confirm", 0.85, "¿Quieres fichar la salida ahora?",
    ),

    # --- Paradas (requieren confirmación) ---
    (
        re.compile(
            r"\b("
            r"descanso|voy\s+a\s+descansar|me\s+tomo\s+un\s+descanso|"
            r"pausa|voy\s+a\s+hacer\s+una\s+pausa|"
            r"a\s+comer|voy\s+a\s+comer|me\s+voy\s+a\s+comer|"
            r"cafe|caf[eé]|voy\s+a\s+por\s+un\s+caf[eé]|"
            r"paro\s+un\s+rato|paro\s+ya|voy\s+a\s+parar|"
            r"desconecto|me\s+desconecto|"
            r"almuerzo|voy\s+a\s+almorzar"
            r")\b", re.IGNORECASE
        ),
        "inicio_parada", "confirm", 0.85, "¿Quieres iniciar una pausa ahora?",
    ),
    (
        re.compile(
            r"\b("
            r"vuelvo|ya\s+he\s+vuelto|he\s+vuelto|"
            r"regreso|estoy\s+de\s+vuelta|"
            r"sigo|sigo\s+trabajando|continuo|contin[uú]o|"
            r"retomo|retomo\s+(el\s+)?trabajo|"
            r"termino\s+(el\s+)?descanso|fin\s+del?\s+descanso|"
            r"reanudo|reanudo\s+(la\s+)?jornada"
            r")\b", re.IGNORECASE
        ),
        "fin_parada", "confirm", 0.85, "¿Quieres finalizar la pausa y reanudar?",
    ),

    # --- Vacaciones (requiere confirmación / fechas) ---
    (
        re.compile(
            r"\b("
            r"quiero\s+pedir\s+vacaciones|solicito\s+vacaciones|"
            r"pedir\s+(d[ií]as|vacaciones)|"
            r"vacaciones\s+del?\s+\d|d[ií]as\s+libres?\s+del?\s+\d|"
            r"solicitar\s+vacaciones"
            r")\b", re.IGNORECASE
        ),
        "solicitar_vacaciones", "confirm", 0.8, None,
    ),
    (
        re.compile(
            r"\b("
            r"vacaciones|d[ií]as\s+libres?|"
            r"pedir\s+d[ií]as|solicitar\s+d[ií]as"
            r")\b", re.IGNORECASE
        ),
        "solicitar_vacaciones", "ask", 0.5, "¿Qué período de vacaciones deseas solicitar? Indícame las fechas.",
    ),
]


def normalize_whatsapp_text(message_text: str) -> str:
    t = (message_text or "").lower().strip()
    return "".join(
        c
        for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )


def match_whatsapp_intent(
    message_text: str,
    allowed: list[str] | None = None,
    *,
    infer_fichar: Callable[[], str | None] | None = None,
    infer_break: Callable[[], str | None] | None = None,
) -> OllamaIntentResponse:
    """Keyword matching primario: detecta la intención por frases clave.

    Devuelve OllamaIntentResponse con stage, intent, confidence y message.
    Si no hay match, devuelve intent=desconocido con confidence baja para
    que Ollama pueda intentar interpretarlo.
    """
    t = normalize_whatsapp_text(message_text)
    allowed_set = set(allowed) if allowed else None

    for pattern, intent, stage, confidence, msg in _INTENT_PATTERNS:
        if allowed_set and intent not in allowed_set and intent != "desconocido":
            continue
        if pattern.search(t):
            # Desambiguar fichajes según contexto real
            if intent == "fichar_entrada" and infer_fichar:
                hint = infer_fichar()
                if hint == "fichar_salida":
                    return OllamaIntentResponse(
                        stage="confirm", intent="fichar_salida",
                        confidence=0.85,
                        message="¿Quieres fichar la salida ahora?",
                    )
            elif intent == "fichar_salida" and infer_fichar:
                hint = infer_fichar()
                if hint == "fichar_entrada":
                    return OllamaIntentResponse(
                        stage="confirm", intent="fichar_entrada",
                        confidence=0.85,
                        message="¿Quieres fichar la entrada ahora?",
                    )
            # Desambiguar paradas según contexto real
            if intent == "inicio_parada" and infer_break:
                hint = infer_break()
                if hint == "fin_parada":
                    return OllamaIntentResponse(
                        stage="confirm", intent="fin_parada",
                        confidence=0.85,
                        message="¿Quieres finalizar la pausa y reanudar?",
                    )
            elif intent == "fin_parada" and infer_break:
                hint = infer_break()
                if hint == "inicio_parada":
                    return OllamaIntentResponse(
                        stage="confirm", intent="inicio_parada",
                        confidence=0.85,
                        message="¿Quieres iniciar una pausa ahora?",
                    )

            return OllamaIntentResponse(
                stage=stage, intent=intent,
                confidence=confidence,
                message=msg or "",
            )

    # Saludo genérico (último recurso antes de desconocido)
    if re.search(r"\b(hola|buenos\s+dias|buenas\s+tardes|buenas\s+noches|hey|buenas|que\s+tal|como\s+estas?)\b", t, re.IGNORECASE):
        return OllamaIntentResponse(
            stage="ask", intent="desconocido", confidence=0.4,
            message="¡Hola! Cuéntame qué necesitas: fichar, parada, vacaciones…",
        )

    # Sin match → desconocido, confidence baja para que Ollama lo intente
    return OllamaIntentResponse(
        stage="ask", intent="desconocido", confidence=0.1, message="",
    )


# ---------------------------------------------------------------------------
# Confirmación / negación (para flujo sí/no)
# ---------------------------------------------------------------------------
_RE_AFFIRMATIVE = re.compile(
    r"\b("
    r"si|s[ií]|yes|vale|ok|okey|claro|confirmo|confirmar|de\s+acuerdo|"
    r"adelante|venga|dale|perfecto|correcto|afirmativo|hecho|"
    r"por\s+supuesto|obvio|exacto|as[ií]\s+es|eso\s+es"
    r")\b",
    re.IGNORECASE,
)
_RE_NEGATIVE = re.compile(
    r"\b("
    r"no|nop|nope|negativo|cancelar|cancela|mejor\s+no|"
    r"no\s+gracias|deja|dejalo|d[eé]jalo|para|para\s+ya"
    r")\b",
    re.IGNORECASE,
)


def is_affirmative_reply(text: str) -> bool:
    """Detecta si el mensaje es una respuesta afirmativa (sí, vale, ok, confirmo...)."""
    t = normalize_whatsapp_text(text)
    if _RE_AFFIRMATIVE.search(t):
        return True
    if any(w in t for w in ("si quiero", "si ficho", "si confirmo", "si claro")):
        return True
    return False


def is_negative_reply(text: str) -> bool:
    """Detecta si el mensaje es una respuesta negativa (no, cancelar...)."""
    t = normalize_whatsapp_text(text)
    if _RE_NEGATIVE.search(t):
        return True
    return False


_RE_ACTION_ESCAPE = re.compile(
    r"\b("
    r"salgo|me\s+voy|me\s+marcho|termino|acabo|fin\s+de\s+jornada|"
    r"paro|pausa|descanso|a\s+comer|cafe|break|un\s+rato|momento|"
    r"vuelvo|regreso|sigo\s+trabajando|retomo|sigo|"
    r"vacaciones|dias\s+libres|dias\s+libre|"
    r"resumen|como\s+voy|que\s+he\s+hecho|hola|buenas"
    r")\b",
    re.IGNORECASE,
)


def is_cancel_or_new_intent(text: str) -> bool:
    """Detecta si el texto es una cancelación o nueva intención, no una selección de proyecto."""
    t = normalize_whatsapp_text(text)
    return bool(is_negative_reply(text) or _RE_ACTION_ESCAPE.search(t))


def build_confirmation_message(intent_code: str, employee_name: str) -> str:
    """Construye mensaje de confirmación sí/no para una intención detectada."""
    labels: dict[str, str] = {
        "fichar_entrada": "fichar la entrada",
        "fichar_salida": "fichar la salida",
        "inicio_parada": "iniciar una parada/descanso",
        "fin_parada": "finalizar la parada/descanso",
        "solicitar_vacaciones": "solicitar vacaciones",
        "consultar_saldo_vacaciones": "consultar tu saldo de vacaciones",
        "confirmar_documento": "confirmar un documento",
        "resumen_dia": "ver el resumen del día",
    }
    action_label = labels.get(intent_code, intent_code.replace("_", " "))
    return (
        f"Hola {employee_name}, entiendo que quieres *{action_label}*, "
        "¿es correcto?\n\n"
        "Responde *sí* o *no* por favor."
    )
