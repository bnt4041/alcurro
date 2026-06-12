import hashlib
import hmac
import json
import secrets
from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.developer import ApiKey, WebhookDelivery, WebhookEndpoint

router = APIRouter(prefix="/developer", tags=["developer"])

_PERM = Depends(require_permission(Permission.WRITE, "tenant"))

SUPPORTED_EVENTS = [
    "employee.created",
    "employee.updated",
    "employee.deactivated",
    "clockin.created",
    "clockin.updated",
    "break.created",
    "leave.requested",
    "leave.approved",
    "leave.rejected",
    "incident.created",
    "incident.managed",
    "document.delivered",
    "document.signed",
    "signature.completed",
]


# ── API Keys ───────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyRead(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: str
    last_used_at: str | None


class ApiKeyCreated(ApiKeyRead):
    full_key: str


def _generate_key() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(32)
    full_key = f"ak_{token}"
    prefix = f"ak_{token[:8]}..."
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


@router.get("/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    rows = session.exec(
        select(ApiKey)
        .where(ApiKey.tenant_id == ctx.tenant.id, ApiKey.is_active == True)
        .order_by(ApiKey.created_at.desc())
    ).all()
    return [
        ApiKeyRead(
            id=str(r.id),
            name=r.name,
            key_prefix=r.key_prefix,
            is_active=r.is_active,
            created_at=r.created_at.isoformat(),
            last_used_at=r.last_used_at.isoformat() if r.last_used_at else None,
        )
        for r in rows
    ]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    full_key, prefix, key_hash = _generate_key()
    row = ApiKey(
        tenant_id=ctx.tenant.id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        created_by_id=ctx.user.id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return ApiKeyCreated(
        id=str(row.id),
        name=row.name,
        key_prefix=row.key_prefix,
        is_active=row.is_active,
        created_at=row.created_at.isoformat(),
        last_used_at=None,
        full_key=full_key,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    row = session.get(ApiKey, key_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(404)
    row.is_active = False
    session.add(row)
    session.commit()


# ── Webhooks ───────────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    url: str
    description: str | None = None
    events: list[str]


class WebhookRead(BaseModel):
    id: str
    url: str
    description: str | None
    events: list[str]
    secret: str
    is_active: bool
    created_at: str
    last_triggered_at: str | None
    failure_count: int


class WebhookDeliveryRead(BaseModel):
    id: str
    event_type: str
    status: str
    response_status: int | None
    attempts: int
    created_at: str
    delivered_at: str | None


@router.get("/webhooks/events")
def list_supported_events():
    return {"events": SUPPORTED_EVENTS}


@router.get("/webhooks", response_model=list[WebhookRead])
def list_webhooks(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    rows = session.exec(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.tenant_id == ctx.tenant.id)
        .order_by(WebhookEndpoint.created_at.desc())
    ).all()
    return [_wh_read(r) for r in rows]


@router.post("/webhooks", response_model=WebhookRead, status_code=201)
def create_webhook(
    body: WebhookCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    _check_events(body.events)
    row = WebhookEndpoint(
        tenant_id=ctx.tenant.id,
        url=body.url,
        description=body.description,
        events=body.events,
        secret=secrets.token_hex(32),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _wh_read(row)


@router.patch("/webhooks/{wh_id}", response_model=WebhookRead)
def update_webhook(
    wh_id: UUID,
    body: WebhookCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    row = _get_wh(session, wh_id, ctx)
    _check_events(body.events)
    row.url = body.url
    row.description = body.description
    row.events = body.events
    session.add(row)
    session.commit()
    session.refresh(row)
    return _wh_read(row)


@router.delete("/webhooks/{wh_id}", status_code=204)
def delete_webhook(
    wh_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    row = _get_wh(session, wh_id, ctx)
    session.delete(row)
    session.commit()


@router.post("/webhooks/{wh_id}/test")
def test_webhook(
    wh_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    row = _get_wh(session, wh_id, ctx)
    delivery = _send_sync(session, row, "test", {
        "message": "Evento de prueba desde alcurro",
        "tenant": ctx.tenant.slug,
    })
    return {
        "status": delivery.status,
        "response_status": delivery.response_status,
        "id": str(delivery.id),
    }


@router.get("/webhooks/{wh_id}/deliveries", response_model=list[WebhookDeliveryRead])
def list_deliveries(
    wh_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _=_PERM,
):
    _get_wh(session, wh_id, ctx)
    rows = session.exec(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == wh_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
    ).all()
    return [
        WebhookDeliveryRead(
            id=str(r.id),
            event_type=r.event_type,
            status=r.status,
            response_status=r.response_status,
            attempts=r.attempts,
            created_at=r.created_at.isoformat(),
            delivered_at=r.delivered_at.isoformat() if r.delivered_at else None,
        )
        for r in rows
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _wh_read(r: WebhookEndpoint) -> WebhookRead:
    return WebhookRead(
        id=str(r.id),
        url=r.url,
        description=r.description,
        events=r.events or [],
        secret=r.secret,
        is_active=r.is_active,
        created_at=r.created_at.isoformat(),
        last_triggered_at=r.last_triggered_at.isoformat() if r.last_triggered_at else None,
        failure_count=r.failure_count,
    )


def _get_wh(session: Session, wh_id: UUID, ctx: OrgContext) -> WebhookEndpoint:
    row = session.get(WebhookEndpoint, wh_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(404)
    return row


def _check_events(events: list[str]) -> None:
    bad = [e for e in events if e not in SUPPORTED_EVENTS and e != "*"]
    if bad:
        raise HTTPException(400, detail=f"Eventos no soportados: {', '.join(bad)}")


def _send_sync(
    session: Session,
    webhook: WebhookEndpoint,
    event_type: str,
    data: dict,
) -> WebhookDelivery:
    payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data,
    }
    body_bytes = json.dumps(payload, ensure_ascii=False).encode()
    sig = hmac.new(webhook.secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Alcurro-Signature": f"sha256={sig}",
        "X-Alcurro-Event": event_type,
        "User-Agent": "alcurro-webhooks/1.0",
    }

    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload,
        attempts=1,
    )
    session.add(delivery)

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(webhook.url, content=body_bytes, headers=headers)
        delivery.status = "success" if resp.status_code < 400 else "failed"
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:2000]
        delivery.delivered_at = datetime.utcnow()
        webhook.last_triggered_at = datetime.utcnow()
        webhook.failure_count = 0 if delivery.status == "success" else (webhook.failure_count + 1)
    except Exception as exc:
        delivery.status = "failed"
        delivery.response_body = str(exc)[:2000]
        webhook.failure_count += 1

    session.add(webhook)
    session.commit()
    session.refresh(delivery)
    return delivery
