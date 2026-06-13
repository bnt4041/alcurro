"""Webhook de Lemon Squeezy."""

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.services.lemon_squeezy_service import handle_webhook_event, ls_configured

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/lemon-squeezy")
async def lemon_squeezy_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not ls_configured():
        raise HTTPException(status_code=503, detail="Lemon Squeezy no configurado")

    body = await request.body()
    signature = request.headers.get("x-signature", "")

    secret = get_settings().lemon_squeezy_webhook_secret
    if secret:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Firma inválida")

    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Payload inválido") from exc

    handle_webhook_event(session, payload)
    return {"status": "ok"}
