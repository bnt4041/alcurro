"""Configuración global de IA (administrador de plataforma)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.ai import AiConversationRule
from app.models.rbac import PlatformUser
from app.schemas.ai import (
    AiActionMatrixRow,
    AiActionMatrixUpdate,
    AiConversationRuleCreate,
    AiConversationRuleRead,
    AiConversationRuleUpdate,
    AiPlatformOverview,
    AiRulesReorder,
    AiTenantUsageDetail,
    AiUsageSummary,
)
from app.services.ai_config_service import (
    AI_PROFILES,
    ensure_ai_catalog,
    get_action_matrix,
    list_rules,
    reorder_rules,
    update_action_matrix,
)
from app.services.ai_usage_service import tenant_usage_detail, tenant_usage_summaries

router = APIRouter(prefix="/platform/ai", tags=["platform-ai"])


@router.get("/overview", response_model=AiPlatformOverview)
def ai_overview(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    days: int = Query(30, ge=1, le=365),
) -> AiPlatformOverview:
    ensure_ai_catalog(session)
    session.commit()
    return AiPlatformOverview(
        profiles=[{"key": k, "label": l} for k, l in AI_PROFILES],
        action_matrix=get_action_matrix(session),
        rules=list_rules(session),
        tenant_usage=tenant_usage_summaries(session, days=days),
    )


@router.get("/actions/matrix", response_model=list[AiActionMatrixRow])
def get_matrix(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[AiActionMatrixRow]:
    return get_action_matrix(session)


@router.put("/actions/matrix", response_model=list[AiActionMatrixRow])
def put_matrix(
    data: AiActionMatrixUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[AiActionMatrixRow]:
    result = update_action_matrix(session, data.cells)
    session.commit()
    return result


@router.get("/rules", response_model=list[AiConversationRuleRead])
def get_rules(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[AiConversationRuleRead]:
    return list_rules(session)


@router.post("/rules", response_model=AiConversationRuleRead, status_code=201)
def create_rule(
    data: AiConversationRuleCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> AiConversationRule:
    row = AiConversationRule(**data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return AiConversationRuleRead.model_validate(row)


@router.patch("/rules/{rule_id}", response_model=AiConversationRuleRead)
def update_rule(
    rule_id: UUID,
    data: AiConversationRuleUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> AiConversationRule:
    row = session.get(AiConversationRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return AiConversationRuleRead.model_validate(row)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> None:
    row = session.get(AiConversationRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    session.delete(row)
    session.commit()


@router.post("/rules/reorder", response_model=list[AiConversationRuleRead])
def reorder_rules_endpoint(
    data: AiRulesReorder,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[AiConversationRuleRead]:
    result = reorder_rules(session, data.rule_ids)
    session.commit()
    return result


@router.get("/usage", response_model=list[AiUsageSummary])
def list_usage(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    days: int = Query(30, ge=1, le=365),
) -> list[AiUsageSummary]:
    return tenant_usage_summaries(session, days=days)


@router.get("/usage/tenants/{tenant_id}", response_model=AiTenantUsageDetail)
def tenant_usage(
    tenant_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    days: int = Query(30, ge=1, le=365),
) -> AiTenantUsageDetail:
    return tenant_usage_detail(session, tenant_id, days=days)
