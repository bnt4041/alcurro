from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.tenant import Tenant
from app.schemas.whatsapp import GoWAWebhookPayload
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["webhook"])


def _get_tenant(session: Session, tenant_slug: str) -> Tenant:
    tenant = session.exec(
        select(Tenant).where(Tenant.slug == tenant_slug.lower())
    ).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


@router.post("/webhook/whatsapp/{tenant_slug}")
async def whatsapp_webhook_tenant(
    tenant_slug: str,
    payload: GoWAWebhookPayload,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    tenant = _get_tenant(session, tenant_slug)
    try:
        service = WebhookService(session, tenant_id=tenant.id)
        return await service.process(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook: {exc}",
        ) from exc


@router.post("/webhook/whatsapp")
async def whatsapp_webhook_legacy(
    payload: GoWAWebhookPayload,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Compatibilidad: usa el primer tenant activo o slug 'demo'."""
    tenant = session.exec(
        select(Tenant).where(Tenant.slug == "demo")
    ).first()
    if not tenant:
        tenant = session.exec(select(Tenant)).first()
    if not tenant:
        raise HTTPException(status_code=503, detail="Sin tenant configurado")
    service = WebhookService(session, tenant_id=tenant.id)
    return await service.process(payload)
