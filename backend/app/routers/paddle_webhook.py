"""Webhook de Paddle (Billing API v2)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.services.paddle_service import (
    handle_webhook_event,
    paddle_configured,
    verify_webhook_signature,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/paddle")
async def paddle_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not paddle_configured():
        raise HTTPException(status_code=503, detail="Paddle no configurado")

    body = await request.body()
    signature = request.headers.get("paddle-signature", "")

    secret = get_settings().paddle_webhook_secret
    if secret and not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Firma inválida")

    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Payload inválido") from exc

    handle_webhook_event(session, payload)
    return {"status": "ok"}
