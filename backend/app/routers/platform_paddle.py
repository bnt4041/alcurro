"""Endpoints de administración para Paddle: estado, listado de cobros, reembolsos y sync de planes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.billing import PaddlePayment, PricingPlan
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.services.paddle_service import (
    issue_refund_credit_note,
    paddle_configured,
    sync_plan_to_paddle,
)

router = APIRouter(prefix="/platform/paddle", tags=["platform-paddle"])


class PaddleStatus(BaseModel):
    configured: bool
    env: str
    client_token_set: bool
    webhook_secret_set: bool
    webhook_url: str


class PaddlePaymentRead(BaseModel):
    id: UUID
    tenant_id: UUID | None
    tenant_name: str | None
    paddle_invoice_id: str | None
    paddle_transaction_id: str | None
    amount_cents: int
    currency: str
    status: str
    description: str | None
    receipt_url: str | None
    paid_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/status", response_model=PaddleStatus)
def paddle_status(
    _: PlatformUser = Depends(get_platform_user),
) -> PaddleStatus:
    settings = get_settings()
    base = settings.public_app_url.rstrip("/")
    return PaddleStatus(
        configured=paddle_configured(),
        env=settings.paddle_env,
        client_token_set=bool(settings.paddle_client_token.strip()),
        webhook_secret_set=bool(settings.paddle_webhook_secret.strip()),
        webhook_url=f"{base}/api/webhooks/paddle",
    )


@router.get("/payments", response_model=list[PaddlePaymentRead])
def list_paddle_payments(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[PaddlePaymentRead]:
    payments = list(
        session.exec(
            select(PaddlePayment)
            .order_by(PaddlePayment.created_at.desc())  # type: ignore[attr-defined]
            .limit(500)
        ).all()
    )
    result: list[PaddlePaymentRead] = []
    for p in payments:
        tenant_name: str | None = None
        if p.tenant_id:
            tenant = session.get(Tenant, p.tenant_id)
            if tenant:
                tenant_name = tenant.name
        result.append(
            PaddlePaymentRead(
                id=p.id,
                tenant_id=p.tenant_id,
                tenant_name=tenant_name,
                paddle_invoice_id=p.paddle_invoice_id,
                paddle_transaction_id=p.paddle_transaction_id,
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


class PaddleRefundResult(BaseModel):
    payment_id: UUID
    payment_status: str
    credit_note_number: str
    credit_note_id: UUID


@router.post("/refund/{payment_id}", response_model=PaddleRefundResult, status_code=201)
def issue_refund(
    payment_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PaddleRefundResult:
    try:
        payment, credit_note = issue_refund_credit_note(session, payment_id)
        session.commit()
        session.refresh(payment)
        session.refresh(credit_note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar el abono: {exc}") from exc

    return PaddleRefundResult(
        payment_id=payment.id,
        payment_status=payment.status.value if hasattr(payment.status, "value") else str(payment.status),
        credit_note_number=credit_note.number,
        credit_note_id=credit_note.id,
    )


class PaddleSyncPlanResult(BaseModel):
    plan_id: UUID
    paddle_product_id: str | None
    paddle_price_id_monthly: str | None
    paddle_price_id_annual: str | None


@router.post("/sync-plan/{plan_id}", response_model=PaddleSyncPlanResult)
def sync_plan(
    plan_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PaddleSyncPlanResult:
    if not paddle_configured():
        raise HTTPException(status_code=503, detail="Paddle no está configurado")

    plan = session.get(PricingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")

    try:
        plan = sync_plan_to_paddle(session, plan)
        session.commit()
        session.refresh(plan)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al sincronizar con Paddle: {exc}") from exc

    return PaddleSyncPlanResult(
        plan_id=plan.id,
        paddle_product_id=plan.paddle_product_id,
        paddle_price_id_monthly=plan.paddle_price_id_monthly,
        paddle_price_id_annual=plan.paddle_price_id_annual,
    )
