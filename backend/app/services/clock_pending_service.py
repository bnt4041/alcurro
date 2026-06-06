"""Fichaje pendiente de proyecto o confirmación (WhatsApp)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from app.models.project import ClockPendingFichaje


def get_pending(session: Session, employee_id: UUID) -> ClockPendingFichaje | None:
    return session.get(ClockPendingFichaje, employee_id)


def set_pending(
    session: Session,
    *,
    employee_id: UUID,
    record_type: str,
    latitude: float | None = None,
    longitude: float | None = None,
    whatsapp_message_id: str | None = None,
    pending_confirmation: bool = False,
    pending_intent: str | None = None,
    pending_meta: dict | None = None,
) -> ClockPendingFichaje:
    row = session.get(ClockPendingFichaje, employee_id)
    if row:
        row.record_type = record_type if isinstance(record_type, str) else record_type.value
        row.latitude = latitude
        row.longitude = longitude
        row.whatsapp_message_id = whatsapp_message_id
        row.pending_confirmation = pending_confirmation
        row.pending_intent = pending_intent
        row.pending_meta = pending_meta
        row.created_at = datetime.utcnow()
    else:
        row = ClockPendingFichaje(
            employee_id=employee_id,
            record_type=record_type if isinstance(record_type, str) else record_type.value,
            latitude=latitude,
            longitude=longitude,
            whatsapp_message_id=whatsapp_message_id,
            pending_confirmation=pending_confirmation,
            pending_intent=pending_intent,
            pending_meta=pending_meta,
        )
        session.add(row)
    session.flush()
    return row


def clear_pending(session: Session, employee_id: UUID) -> None:
    row = session.get(ClockPendingFichaje, employee_id)
    if row:
        session.delete(row)
        session.flush()


def is_pending_confirmation(session: Session, employee_id: UUID) -> bool:
    """True si hay una acción esperando confirmación sí/no."""
    row = session.get(ClockPendingFichaje, employee_id)
    return row is not None and row.pending_confirmation
