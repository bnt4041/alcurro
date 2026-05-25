"""Registro y agregación de uso de IA por cuenta."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.ai import AiUsageRecord
from app.models.tenant import Tenant
from app.schemas.ai import AiTenantUsageDetail, AiUsageSummary
from app.services.ai_config_service import _role_to_profile


def log_usage(
    session: Session,
    *,
    tenant_id: UUID,
    profile_key: str | None,
    action_code: str | None,
    source: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: int,
    success: bool = True,
) -> AiUsageRecord:
    total = prompt_tokens + completion_tokens
    row = AiUsageRecord(
        tenant_id=tenant_id,
        profile_key=profile_key,
        action_code=action_code,
        source=source,
        model=model[:80],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        duration_ms=duration_ms,
        success=success,
    )
    session.add(row)
    session.flush()
    return row


def tenant_usage_summaries(
    session: Session, *, days: int = 30
) -> list[AiUsageSummary]:
    since = datetime.utcnow() - timedelta(days=days)
    tenants = {t.id: t for t in session.exec(select(Tenant)).all()}

    stmt = (
        select(
            AiUsageRecord.tenant_id,
            func.count(AiUsageRecord.id),
            func.coalesce(func.sum(AiUsageRecord.total_tokens), 0),
            func.coalesce(func.sum(AiUsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(AiUsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(AiUsageRecord.duration_ms), 0),
            func.max(AiUsageRecord.created_at),
        )
        .where(AiUsageRecord.created_at >= since)
        .group_by(AiUsageRecord.tenant_id)
    )
    rows = session.exec(stmt).all()
    summaries: list[AiUsageSummary] = []
    used_ids: set[UUID] = set()
    for tid, cnt, tokens, pt, ct, dur, last in rows:
        t = tenants.get(tid)
        summaries.append(
            AiUsageSummary(
                tenant_id=tid,
                tenant_name=t.name if t else "—",
                tenant_slug=t.slug if t else "",
                request_count=int(cnt),
                total_tokens=int(tokens),
                prompt_tokens=int(pt),
                completion_tokens=int(ct),
                total_duration_ms=int(dur),
                last_used_at=last,
            )
        )
        used_ids.add(tid)
    for tid, t in tenants.items():
        if tid not in used_ids:
            summaries.append(
                AiUsageSummary(
                    tenant_id=tid,
                    tenant_name=t.name,
                    tenant_slug=t.slug,
                    request_count=0,
                    total_tokens=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_duration_ms=0,
                    last_used_at=None,
                )
            )
    summaries.sort(key=lambda s: (-s.total_tokens, s.tenant_name))
    return summaries


def tenant_usage_detail(
    session: Session, tenant_id: UUID, *, days: int = 30
) -> AiTenantUsageDetail:
    since = datetime.utcnow() - timedelta(days=days)
    base = select(AiUsageRecord).where(
        AiUsageRecord.tenant_id == tenant_id,
        AiUsageRecord.created_at >= since,
    )
    records = list(session.exec(base.order_by(AiUsageRecord.created_at.desc()).limit(200)).all())  # type: ignore[attr-defined]

    total_tokens = sum(r.total_tokens for r in records)
    total_duration = sum(r.duration_ms for r in records)

    by_action: dict[str, dict] = {}
    by_profile: dict[str, dict] = {}
    for r in records:
        ac = r.action_code or "—"
        if ac not in by_action:
            by_action[ac] = {"action_code": ac, "count": 0, "tokens": 0, "duration_ms": 0}
        by_action[ac]["count"] += 1
        by_action[ac]["tokens"] += r.total_tokens
        by_action[ac]["duration_ms"] += r.duration_ms

        pk = r.profile_key or "—"
        if pk not in by_profile:
            by_profile[pk] = {"profile_key": pk, "count": 0, "tokens": 0}
        by_profile[pk]["count"] += 1
        by_profile[pk]["tokens"] += r.total_tokens

    return AiTenantUsageDetail(
        tenant_id=tenant_id,
        period_label=f"Últimos {days} días",
        request_count=len(records),
        total_tokens=total_tokens,
        total_duration_ms=total_duration,
        by_action=sorted(by_action.values(), key=lambda x: -x["tokens"]),
        by_profile=sorted(by_profile.values(), key=lambda x: -x["tokens"]),
        recent=[
            {
                "created_at": r.created_at.isoformat(),
                "action_code": r.action_code,
                "profile_key": r.profile_key,
                "total_tokens": r.total_tokens,
                "duration_ms": r.duration_ms,
                "model": r.model,
                "success": r.success,
            }
            for r in records[:50]
        ],
    )


def profile_key_for_employee(role) -> str:
    return _role_to_profile(role)
