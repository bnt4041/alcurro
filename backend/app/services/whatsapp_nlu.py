"""Utilidades de texto para WhatsApp: normalización, saludos, confirmación sí/no."""

from __future__ import annotations

import re
import unicodedata

from app.schemas.ollama import OllamaIntentResponse

# Saludos: detectar aunque haya más texto después (ej. "Hola! comenzamos?")
_RE_GREETING = re.compile(
    r"^(hola|buenos\s+dias|buenas\s+tardes|buenas\s+noches|hey|buenas|que\s+tal)\b",
    re.IGNORECASE,
)

# Respuestas de confirmación / negación para el flujo de confirmación sí/no
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
    infer_fichar: object = None,
    infer_break: object = None,
) -> OllamaIntentResponse:
    """Respaldo mínimo: solo saludos. Ollama es quien clasifica la intención."""
    t = normalize_whatsapp_text(message_text)
    if _RE_GREETING.match(t.strip()):
        return OllamaIntentResponse(
            stage="ask",
            intent="desconocido",
            confidence=0.3,
            message="¡Hola! Cuéntame qué necesitas: fichar, parada, vacaciones…",
        )
    # Fallback cuando Ollama no está disponible
    return OllamaIntentResponse(
        stage="ask",
        intent="desconocido",
        confidence=0.1,
        message="",
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
