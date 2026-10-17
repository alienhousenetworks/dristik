"""Helpers for building normalized records inside providers."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.connectors.authority.models import ExternalRecord, isoformat, stable_id
from app.connectors.authority.providers.base import CollectContext


def record(
    ctx: CollectContext,
    *,
    record_type: str,
    metric: str,
    value: Optional[float] = None,
    value_text: Optional[str] = None,
    unit: Optional[str] = None,
    url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    comparison: str = "current",
    evidence_basis: str = "DIRECT_PROVIDER_EVIDENCE",
    status: str = "MEASURED",
    evidence_url: Optional[str] = None,
    raw_ref: Optional[str] = None,
    confidence: float = 1.0,
    metric_type: Optional[str] = None,
    source: Optional[str] = None,
) -> ExternalRecord:
    if comparison == "previous":
        start, end = ctx.previous_start, ctx.previous_end
    else:
        start, end = ctx.period_start, ctx.period_end
    meta = dict(metadata or {})
    meta["comparison"] = comparison
    identity = (
        ctx.project_id,
        ctx.provider_id,
        record_type,
        metric,
        url,
        start,
        end,
        meta.get("query"),
        meta.get("page"),
        meta.get("country"),
        meta.get("device"),
        meta.get("search_appearance"),
        meta.get("source_url"),
        meta.get("anchor"),
        meta.get("listing_url"),
        meta.get("mention_url"),
        meta.get("competitor_domain"),
        meta.get("signal"),
        value_text,
    )
    return ExternalRecord(
        record_id=stable_id("rec_", *identity),
        record_type=record_type,
        project_id=ctx.project_id,
        provider=ctx.provider_id,
        source=source or ctx.provider_id,
        external_account_id=ctx.external_account_id,
        external_property_id=ctx.property_id,
        domain=ctx.domain,
        url=url,
        metric=metric,
        metric_type=metric_type,
        value=value,
        value_text=value_text,
        unit=unit,
        period_start=start,
        period_end=end,
        collected_at=isoformat(ctx.now),
        evidence_url=evidence_url,
        raw_provider_reference=raw_ref,
        confidence=confidence,
        status=status,
        evidence_basis=evidence_basis,  # type: ignore[arg-type]
        metadata=meta,
    )
