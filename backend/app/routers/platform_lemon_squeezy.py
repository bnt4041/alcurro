"""Endpoints de administración para Lemon Squeezy: estado y listado de cobros."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.config import get_settings
from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.billing import LemonSqueezyPayment
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.models.billing import PricingPlan
from app.services.lemon_squeezy_service import issue_refund_credit_note, ls_configured, sync_plan_to_ls
from pydantic import BaseModel

router = APIRouter(prefix="/platform/ls", tags=["platform-lemon-squeezy"])


class LsStatus(BaseModel):
    configured: bool
    store_id: str | None
    webhook_secret_set: bool
    webhook_url: str


class LsPaymentRead(BaseModel):
    id: UUID
    tenant_id: UUID | None
    tenant_name: str | None
    ls_order_id: str | None
    ls_invoice_id: str | None
    amount_cents: int
    currency: str
    status: str
    description: str | None
    receipt_url: str | None
    paid_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/status", response_model=LsStatus)
def ls_status(
    _: PlatformUser = Depends(get_platform_user),
) -> LsStatus:
    settings = get_settings()
    base = settings.public_app_url.rstrip("/")
    return LsStatus(
        configured=ls_configured(),
        store_id=settings.lemon_squeezy_store_id or None,
        webhook_secret_set=bool(settings.lemon_squeezy_webhook_secret.strip()),
        webhook_url=f"{base}/api/webhooks/lemon-squeezy",
    )


@router.get("/payments", response_model=list[LsPaymentRead])
def list_ls_payments(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[LsPaymentRead]:
    payments = list(
        session.exec(
            select(LemonSqueezyPayment)
            .order_by(LemonSqueezyPayment.created_at.desc())  # type: ignore[attr-defined]
            .limit(500)
        ).all()
    )
    result: list[LsPaymentRead] = []
    for p in payments:
        tenant_name: str | None = None
        if p.tenant_id:
            tenant = session.get(Tenant, p.tenant_id)
            if tenant:
                tenant_name = tenant.name
        result.append(
            LsPaymentRead(
                id=p.id,
                tenant_id=p.tenant_id,
                tenant_name=tenant_name,
                ls_order_id=p.ls_order_id,
                ls_invoice_id=p.ls_invoice_id,
                amount_cents=p.amount_cents,
                currency=p.currency,
                status=p.status.value if hasattr(p.status, "value") else str(p.status),
                description=p.description,
                receipt_url=p.receipt_url,
                paid_at=p.paid_at.isoformat() if p.paid_at else None,
                created_at=p.created_at.isoformat(),
            )
        )
    return result


class LsRefundResult(BaseModel):
    payment_id: UUID
    payment_status: str
    credit_note_number: str
    credit_note_id: UUID


@router.post("/refund/{payment_id}", response_model=LsRefundResult, status_code=201)
def issue_refund(
    payment_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> LsRefundResult:
    from fastapi import HTTPException

    try:
        payment, credit_note = issue_refund_credit_note(session, payment_id)
        session.commit()
        session.refresh(payment)
        session.refresh(credit_note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar el abono: {exc}") from exc

    return LsRefundResult(
        payment_id=payment.id,
        payment_status=payment.status.value if hasattr(payment.status, "value") else str(payment.status),
        credit_note_number=credit_note.number,
        credit_note_id=credit_note.id,
    )


class LsSyncPlanResult(BaseModel):
    plan_id: UUID
    ls_product_id: str | None
    ls_variant_id_monthly: str | None
    ls_variant_id_annual: str | None


@router.post("/sync-plan/{plan_id}", response_model=LsSyncPlanResult)
def sync_plan(
    plan_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> LsSyncPlanResult:
    from fastapi import HTTPException

    if not ls_configured():
        raise HTTPException(status_code=503, detail="Lemon Squeezy no está configurado")

    plan = session.get(PricingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")

    try:
        plan = sync_plan_to_ls(session, plan)
        session.commit()
        session.refresh(plan)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al sincronizar con Lemon Squeezy: {exc}") from exc

    return LsSyncPlanResult(
        plan_id=plan.id,
        ls_product_id=plan.ls_product_id,
        ls_variant_id_monthly=plan.ls_variant_id_monthly,
        ls_variant_id_annual=plan.ls_variant_id_annual,
    )
