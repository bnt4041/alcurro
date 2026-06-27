"""Asistente comercial por WhatsApp para números no registrados (leads del landing).

El histórico se agrupa por teléfono. La IA responde dudas comerciales/servicio
apoyándose en la documentación (kb_service). No crea tickets ni accede a datos de
ninguna cuenta.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models.commercial import CommercialMessage
from app.services import kb_service
from app.services.gowa_service import GoWAService
from app.services.ollama_service import OllamaService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 6
MAX_MESSAGE_AGE_DAYS = 30
MAX_CONTENT_LEN = 2000

_FALLBACK = (
    "¡Hola! Soy el asistente de Alcurro 🤖. Ahora mismo no puedo responderte, "
    "pero un humano te atenderá en breve. También puedes escribirnos a "
    "soporte@alcurro.es. ¿En qué te puedo ayudar?"
)


def _append(session: Session, *, phone: str, role: str, content: str) -> None:
    text = (content or "").strip()[:MAX_CONTENT_LEN]
    if not text:
        return
    session.add(CommercialMessage(phone=phone, role=role, content=text))
    session.flush()


def _trim(session: Session, phone: str) -> None:
    cutoff = datetime.utcnow() - timedelta(days=MAX_MESSAGE_AGE_DAYS)
    rows = list(
        session.exec(
            select(CommercialMessage)
            .where(CommercialMessage.phone == phone)
            .order_by(CommercialMessage.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )
    keep = 20  # conserva las últimas 20 por teléfono
    for row in rows[keep:]:
        session.delete(row)
    for row in rows:
        if row.created_at and row.created_at < cutoff:
            session.delete(row)
    session.flush()


def _history(session: Session, phone: str, *, exclude_last_user: str | None = None) -> list[dict[str, str]]:
    rows = list(
        session.exec(
            select(CommercialMessage)
            .where(CommercialMessage.phone == phone)
            .order_by(CommercialMessage.created_at.asc())  # type: ignore[attr-defined]
        ).all()
    )
    tail = rows[-MAX_HISTORY_MESSAGES:]
    out = [
        {"role": r.role if r.role in ("user", "assistant") else "user", "content": r.content}
        for r in tail
    ]
    if (
        exclude_last_user
        and out
        and out[-1]["role"] == "user"
        and out[-1]["content"].strip() == exclude_last_user.strip()
    ):
        out = out[:-1]
    return out


def _system_prompt(kb_context: str) -> str:
    lines = [
        "Eres el asistente comercial de *Alcurro*, un SaaS de RRHH donde los empleados",
        "fichan y gestionan vacaciones, permisos e incidencias por WhatsApp, y las",
        "empresas lo controlan todo desde un panel web.",
        "",
        "Tu objetivo: resolver dudas comerciales y de servicio de posibles clientes,",
        "de forma cercana, breve y en español (tutea).",
        "",
        "ESTADO DEL PRODUCTO (muy importante):",
        "- Alcurro está EN FASE DE PRUEBAS y aún NO está disponible comercialmente.",
        "- NO ofrecemos acceso gratuito, ni periodo de prueba, ni demo.",
        "- El acceso es de pago y por invitación: si alguien está interesado, invítale a",
        "  *solicitar acceso* en https://alcurro.es/registro o a dejar sus datos de contacto",
        "  para que el equipo le avise cuando pueda incorporarse.",
        "",
        "Reglas:",
        "- Responde SOLO sobre Alcurro y RRHH. Si preguntan otra cosa, redirige amablemente.",
        "- NUNCA prometas que es gratis, ni ofrezcas demos, pruebas o descuentos.",
        "- No inventes precios ni funciones que no conozcas; si no estás seguro, ofrece",
        "  poner en contacto con el equipo (soporte@alcurro.es).",
        "- No pidas datos sensibles. No prometas plazos ni fechas de lanzamiento concretas.",
        "- Mensajes cortos, tono WhatsApp, con algún emoji ocasional.",
    ]
    if kb_context:
        lines.extend(
            [
                "",
                "══ DOCUMENTACIÓN RELEVANTE (úsala como fuente principal) ══",
                kb_context,
            ]
        )
    return "\n".join(lines)


async def handle_lead(session: Session, phone: str, text: str) -> dict:
    """Procesa un mensaje de un número no registrado y responde por WhatsApp."""
    settings = SettingsService(session).get_or_create()
    if not getattr(settings, "commercial_ai_enabled", True):
        return {"ok": True, "action": "commercial_disabled"}

    _append(session, phone=phone, role="user", content=text)
    session.commit()

    kb_context = kb_service.build_context(text)
    history = _history(session, phone, exclude_last_user=text)

    try:
        reply = await OllamaService(session=session).chat_text(
            system_prompt=_system_prompt(kb_context),
            user_message=text,
            history=history,
        )
    except Exception as exc:
        logger.warning("Asistente comercial falló para %s: %s", phone, exc)
        reply = ""

    if not reply:
        reply = _FALLBACK

    _append(session, phone=phone, role="assistant", content=reply)
    _trim(session, phone)
    session.commit()

    try:
        await GoWAService(session).send_text(phone, reply)
    except Exception as exc:
        logger.warning("Envío WhatsApp comercial falló para %s: %s", phone, exc)
        return {"ok": False, "action": "commercial_send_failed"}

    return {"ok": True, "action": "commercial_reply"}
