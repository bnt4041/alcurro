"""Formato de mensajes WhatsApp (*negrita*, listas, emojis)."""

from __future__ import annotations


def bold(text: str) -> str:
    return f"*{text}*"


def format_clock_registered(
    label: str,
    time_str: str,
    *,
    project_name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
) -> str:
    lines = [
        f"✅ {bold(f'Fichaje {label}')}",
        f"🕐 Hora: {time_str}",
    ]
    if project_name:
        lines.append(f"📁 Proyecto: {bold(project_name)}")
    if address:
        lines.append(f"📍 {address}")
    elif latitude is not None and longitude is not None:
        lines.append(f"📍 {latitude:.5f}, {longitude:.5f}")
    return "\n".join(lines)


def format_break_registered(label: str, time_str: str) -> str:
    icon = "☕" if "INICIO" in label.upper() else "✅"
    return f"{icon} {bold(label)}\n🕐 Hora: {time_str}"


def format_project_picker(record_label: str, projects: list) -> str:
    if not projects:
        return (
            f"⚠️ Para {bold(record_label)} necesitas un proyecto activo, "
            "pero no hay ninguno disponible. Contacta con RRHH."
        )
    lines = [
        f"📁 {bold('Selecciona el proyecto')} para {record_label}:",
        "",
        "Responde con el *número* o el *nombre* del proyecto:",
        "",
    ]
    for i, p in enumerate(projects, start=1):
        extra = f" — {p.address}" if getattr(p, "address", None) else ""
        hours = (
            f" ({p.planned_hours:g} h prev.)"
            if getattr(p, "planned_hours", None) is not None
            else ""
        )
        lines.append(f"*{i}.* {p.name} [{p.code}]{hours}{extra}")
    return "\n".join(lines)


def format_inbound_document_picker(pending_rows: list) -> str:
    """pending_rows: list with document_code, document_name."""
    lines = [
        f"📎 {bold('¿A qué documento corresponde este archivo?')}",
        "",
        "Responde con el *número* o el *nombre*:",
        "",
    ]
    for i, row in enumerate(pending_rows, start=1):
        name = getattr(row, "document_name", None) or row.get("document_name", "")
        lines.append(f"*{i}.* {name}")
    return "\n".join(lines)


def format_inbound_received(doc_name: str, remaining: int) -> str:
    if remaining:
        return (
            f"✅ {bold('Recibido')}: {doc_name}\n"
            f"Quedan {remaining} documento(s) pendiente(s)."
        )
    return (
        f"✅ {bold('Recibido')}: {doc_name}\n"
        "📋 Documentación de alta completada. ¡Gracias!"
    )


def format_denial_list(title: str, items: list[str]) -> str:
    if not items:
        return f"⛔ {bold(title)}"
    body = "\n".join(f"• {it}" for it in items)
    return f"⛔ {bold(title)}\n\n{body}"


def format_geo_hint(required: bool) -> str:
    if required:
        return ""
    return (
        "\n\n📍 Puedes compartir tu *ubicación* al fichar "
        "(clip → Ubicación) si lo deseas."
    )


def format_geo_request() -> str:
    return (
        "📍 *Necesito tu ubicación para fichar.*\n\n"
        "Pulsa el 📎 (adjuntar) → *Ubicación* → *Enviar tu ubicación actual*."
    )


def format_confirmation_cancelled(employee_name: str) -> str:
    return (
        f"Entendido {employee_name}, no pasa nada. "
        "Cuando necesites algo, aquí estoy. 😊"
    )


def format_pending_confirmation_reminder(
    intent_code: str, employee_name: str
) -> str:
    """Cuando el empleado envía un mensaje sin responder sí/no a la confirmación pendiente."""
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
        f"{employee_name}, antes de continuar necesito que me confirmes:\n\n"
        f"¿Quieres *{action_label}*?\n\n"
        "Responde *sí* o *no* por favor."
    )


def format_help_actions(hints: list[str]) -> str:
    body = "\n".join(f"• {h}" for h in hints)
    return f"❓ {bold('No he entendido tu mensaje')}\n\nPuedes:\n{body}"


def format_conversational_help(
    hints: list[str],
    *,
    employee_name: str | None = None,
    lead: str | None = None,
) -> str:
    """Ayuda cuando la intención no está clara — tono cercano, sin menú rígido."""
    first = (employee_name or "").strip().split()
    name_bit = f" {first[0]}" if first else ""
    intro = (lead or "").strip()
    if not intro:
        intro = (
            f"Hola{name_bit}, no he pillado del todo qué quieres hacer. "
            "Dímelo con tus palabras, por ejemplo:"
        )
    examples = (
        "«ficho ahora», «me voy», «vuelvo al trabajo», «pausa», «resumen del día»"
    )
    if len(hints) <= 4:
        body = "\n".join(f"• {h}" for h in hints)
        return f"👋 {intro}\n\n{body}\n\n_Ejemplos: {examples}_"
    return (
        f"👋 {intro}\n\n"
        f"Puedo ayudarte a fichar, paradas, vacaciones, documentos y más. "
        f"_Prueba con frases como {examples}._"
    )


def format_daily_summary_header(employee_name: str, date_str: str) -> str:
    return f"📋 {bold('Resumen del día')}\n👤 {employee_name}\n📅 {date_str}\n"
