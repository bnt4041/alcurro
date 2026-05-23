import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.services.stripe_service import handle_webhook_event, stripe_configured

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not stripe_configured():
        raise HTTPException(status_code=503, detail="Stripe no configurado")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    settings = get_settings()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Payload inválido") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Firma inválida") from exc

    handle_webhook_event(session, event)
    return {"status": "ok"}
