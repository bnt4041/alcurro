"""Tras registrar entrada: incidencia automática y aviso WhatsApp."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.models.incident import Incident
from app.models.models import ClockIn, Employee
from app.services.incident_service import (
    build_whatsapp_incident_message,
    check_late_clock_in,
    get_or_create_rules,
)


def process_clock_in_incidents(
    session: Session,
    *,
    tenant_id: UUID,
    employee: Employee,
    clock: ClockIn,
) -> Incident | None:
    return check_late_clock_in(session, tenant_id, employee, clock)


def should_notify_whatsapp(session: Session, tenant_id: UUID, incident: Incident) -> bool:
    rules = get_or_create_rules(session, tenant_id)
    return bool(
        rules.late_entrada_notify_whatsapp
        and incident.public_token
        and incident.source == "auto"
    )


def whatsapp_message_for_incident(session: Session, incident: Incident) -> str:
    return build_whatsapp_incident_message(session, incident)
