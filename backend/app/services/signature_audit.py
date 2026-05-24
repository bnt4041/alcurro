"""Cadena de auditoría con hash encadenado por envelope."""

import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.signature import SignatureEvent


def append_event(
    session: Session,
    envelope_id: UUID,
    event_type: str,
    payload: dict,
) -> SignatureEvent:
    prev = session.exec(
        select(SignatureEvent)
        .where(SignatureEvent.envelope_id == envelope_id)
        .order_by(SignatureEvent.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    prev_hash = prev.event_hash if prev else None
    body = {
        "envelope_id": str(envelope_id),
        "event_type": event_type,
        "payload": payload,
        "prev_hash": prev_hash,
        "at": datetime.utcnow().isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    row = SignatureEvent(
        envelope_id=envelope_id,
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
        prev_hash=prev_hash,
        event_hash=digest,
    )
    session.add(row)
    session.flush()
    return row
