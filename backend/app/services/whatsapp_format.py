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
) -> str:
    lines = [
        f"✅ {bold(f'Fichaje {label}')}",
        f"🕐 Hora: {time_str}",
    ]
    if project_name:
        lines.append(f"📁 Proyecto: {bold(project_name)}")
    if latitude is not None and longitude is not None:
        lines.append(f"📍 Ubicación: {latitude:.5f}, {longitude:.5f}")
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
        return (
            "\n\n📍 _Comparte tu ubicación_ (clip → Ubicación) "
            "para fichar con geolocalización."
        )
    return (
        "\n\n📍 Puedes compartir tu *ubicación* al fichar "
        "(clip → Ubicación) si lo deseas."
    )


def format_help_actions(hints: list[str]) -> str:
    body = "\n".join(f"• {h}" for h in hints)
    return f"❓ {bold('No he entendido tu mensaje')}\n\nPuedes:\n{body}"


def format_daily_summary_header(employee_name: str, date_str: str) -> str:
    return f"📋 {bold('Resumen del día')}\n👤 {employee_name}\n📅 {date_str}\n"
