"""Endpoints públicos del modo kiosko (sin auth: el token del centro es la credencial)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.database import get_session
from app.services.geocoding import reverse_geocode
from app.services.kiosk_service import KioskError, kiosk_clock, resolve_kiosk

router = APIRouter(prefix="/public/kiosk", tags=["kiosk"])


class KioskMeta(BaseModel):
    work_center_name: str
    company_name: str
    tenant_name: str
    tenant_slug: str


class KioskClockRequest(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    pin: str = Field(min_length=4, max_length=6, pattern=r"^\d+$")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class KioskClockResponse(BaseModel):
    action: str
    employee_name: str
    at: datetime
    entrada_at: datetime | None = None
    previous_expired: bool = False


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/{token}", response_model=KioskMeta)
def kiosk_meta(token: str, session: Session = Depends(get_session)) -> KioskMeta:
    try:
        ctx = resolve_kiosk(session, token)
    except KioskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    return KioskMeta(
        work_center_name=ctx.work_center.name,
        company_name=ctx.company.name,
        tenant_name=ctx.tenant.name,
        tenant_slug=ctx.tenant.slug,
    )


@router.post("/{token}/fichar", response_model=KioskClockResponse)
async def kiosk_fichar(
    token: str,
    data: KioskClockRequest,
    session: Session = Depends(get_session),
) -> KioskClockResponse:
    address = await reverse_geocode(data.latitude, data.longitude)
    # BD síncrona fuera del event loop (ver bloqueo del webhook de WhatsApp).
    try:
        result = await run_in_threadpool(
            kiosk_clock,
            session,
            token,
            employee_code=data.employee_code,
            pin=data.pin,
            latitude=data.latitude,
            longitude=data.longitude,
            address=address,
        )
    except KioskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    return KioskClockResponse(
        action=result.action,
        employee_name=result.employee_name,
        at=_utc(result.at),
        entrada_at=_utc(result.entrada_at) if result.entrada_at else None,
        previous_expired=result.previous_expired,
    )
