"""
Outcome Tracking Agent (post-delivery, 30/60/90 days).

Does not run during the audit. Rechecks original findings against a fresh
crawl + external-enrichment snapshot, emits OUTCOME_RECORD rows, and feeds
the benchmark calibration table.

Correlation is not causation: attribution is LOW|MEDIUM|HIGH with explicit
confound flags.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.models import CrawlManifest, Finding, PageEvidence


class SiteSnapshot(BaseModel):
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    robots_txt_found: bool = False
    sitemap_found: bool = False
    https: bool = True
    title: Optional[str] = None
    title_length: int = 0
    h1: List[str] = Field(default_factory=list)
    missing_h1_count: int = 0
    canonical_missing_count: int = 0
    schema_types: List[str] = Field(default_factory=list)
    images_without_alt: int = 0
    viewport_missing_count: int = 0
    ttfb_ms: float = 0.0
    word_count: int = 0
    ctas: List[str] = Field(default_factory=list)
    body_text: str = ""
    pricing_present: bool = False
    privacy_present: bool = False
    field_fingerprint: Dict[str, Any] = Field(default_factory=dict)
    external_metrics: Dict[str, Optional[float]] = Field(default_factory=dict)


class ExternalMetricDelta(BaseModel):
    metric: str
    before: Optional[float] = None
    after: Optional[float] = None
    delta: Optional[float] = None
    direction: str = "unavailable"  # improved | worsened | unchanged | unavailable
    note: str = ""


class OutcomeRecord(BaseModel):
    finding_id: str
    finding_type: str
    predicted_impact: str
    remediated: bool
    evidence_condition_resolved: bool
    condition_key: Optional[str] = None
    condition_detail: str = ""
    external_metric_delta: Dict[str, Any] = Field(default_factory=dict)
    confidence_this_delta_is_attributable_to_the_fix: str = "LOW"
    confounds: List[str] = Field(default_factory=list)
    causal_bottleneck_id: Optional[str] = None
    expected_mechanism: Optional[str] = None
    observed_outcome: str = "unresolved_no_change"
    attribution_disclaimer: str = (
        "A metric delta coincident with a fix is correlation, not proof of causation."
    )
    horizon_days: int = 30
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OutcomeRunResult(BaseModel):
    run_id: str
    analysis_id: str
    horizon_days: int
    recorded_at: str
    records: List[OutcomeRecord] = Field(default_factory=list)
    confounds_global: List[str] = Field(default_factory=list)
    benchmark_rows: List[Dict[str, Any]] = Field(default_factory=list)


class BenchmarkRow(BaseModel):
    finding_type: str
    predicted_impact: str
    sample_size: int
    resolved_rate: float
    metric_improved_rate: float
    high_attribution_rate: float
    observed_outcome_mix: Dict[str, int] = Field(default_factory=dict)


_PRICING_MARKERS = ("₹", "$", "€", "/mo", "/month", "pricing", "plan")
_PRIVACY_MARKERS = ("privacy policy", "privacy", "/privacy")


def snapshot_from_manifest(
    manifest: Optional[CrawlManifest],
    *,
    website_url: str = "",
    external_metrics: Optional[Dict[str, Optional[float]]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> SiteSnapshot:
    extra = extra or {}
    pages: List[PageEvidence] = list(manifest.pages or []) if manifest else []
    home = pages[0] if pages else None
    health = (manifest.crawl_health if manifest else None) or {}
    body = (home.body_text or "") if home else ""
    body_l = body.lower()
    h1 = list(home.h1 or []) if home else []
    schema: List[str] = []
    for p in pages:
        schema.extend(p.schema_types or [])
    snap = SiteSnapshot(
        robots_txt_found=bool(manifest.robots_txt_found) if manifest else bool(extra.get("robots_txt_found")),
        sitemap_found=bool(manifest.sitemap_found) if manifest else bool(extra.get("sitemap_found")),
        https=(website_url or (manifest.base_url if manifest else "")).startswith("https://"),
        title=home.title if home else extra.get("title"),
        title_length=len(home.title) if home and home.title else int(extra.get("title_length") or 0),
        h1=h1 or list(extra.get("h1") or []),
        missing_h1_count=sum(1 for p in pages if not p.h1) if pages else int(extra.get("missing_h1_count") or 0),
        canonical_missing_count=sum(1 for p in pages if not p.canonical_url) if pages else int(extra.get("canonical_missing_count") or 0),
        schema_types=sorted(set(schema)) or list(extra.get("schema_types") or []),
        images_without_alt=sum(getattr(p, "images_without_alt", 0) or 0 for p in pages) if pages else int(extra.get("images_without_alt") or 0),
        viewport_missing_count=sum(1 for p in pages if not getattr(p, "viewport", None)) if pages else int(extra.get("viewport_missing_count") or 0),
        ttfb_ms=float(health.get("avg_ttfb_ms") or (home.ttfb_ms if home else extra.get("ttfb_ms") or 0) or 0),
        word_count=int(health.get("total_words_across_site") or (home.word_count if home else extra.get("word_count") or 0) or 0),
        ctas=list(home.ctas or []) if home else list(extra.get("ctas") or []),
        body_text=body,
        pricing_present=any(m in body_l for m in _PRICING_MARKERS) or bool(extra.get("pricing_present")),
        privacy_present=any(m in body_l for m in _PRIVACY_MARKERS) or bool(extra.get("privacy_present")),
        external_metrics=dict(external_metrics or extra.get("external_metrics") or {}),
    )
    if extra.get("title") and not snap.title:
        snap.title = extra["title"]
        snap.title_length = len(str(extra["title"]))
    snap.field_fingerprint = {
        "h1": snap.h1,
        "title": snap.title,
        "robots": snap.robots_txt_found,
        "sitemap": snap.sitemap_found,
        "schema": snap.schema_types,
        "https": snap.https,
        "ctas": snap.ctas[:5],
    }
    return snap


def snapshot_from_dict(data: Dict[str, Any]) -> SiteSnapshot:
    if "field_fingerprint" in data or "robots_txt_found" in data or "external_metrics" in data:
        return SiteSnapshot(**{k: v for k, v in data.items() if k in SiteSnapshot.model_fields})
    return snapshot_from_manifest(None, extra=data, external_metrics=data.get("external_metrics"))


def classify_finding_type(finding: Finding) -> str:
    if finding.rule_id:
        return finding.rule_id
    if finding.claim_family:
        return f"{finding.category.value}:{finding.claim_family.value}"
    blob = f"{finding.title} {finding.description} {finding.recommendation}".lower()
    for key, needles in (
        ("title_length", ("title", "50-60", "characters")),
        ("missing_h1", ("h1",)),
        ("robots", ("robots.txt", "robots")),
        ("sitemap", ("sitemap",)),
        ("canonical", ("canonical",)),
        ("schema", ("schema", "json-ld")),
        ("alt_text", ("alt text", "missing alt")),
        ("viewport", ("viewport",)),
        ("https", ("https", "tls", "ssl")),
        ("privacy", ("privacy",)),
        ("cta", ("cta", "call-to-action", "call to action")),
        ("pricing", ("pricing", "price", "not_in_evidence")),
        ("ttfb", ("ttfb",)),
        ("cwv", ("lcp", "inp", "cls", "core web vital")),
        ("trust", ("testimonial", "review", "trust")),
    ):
        if any(n in blob for n in needles):
            return f"{finding.category.value}:{key}"
    return finding.category.value


def predicted_impact_band(finding: Finding) -> str:
    sev = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
    return f"{sev}:impact_{finding.impact}"


def _blob(finding: Finding) -> str:
    return f"{finding.title} {finding.description} {finding.recommendation} {finding.finding}".lower()


def check_condition(finding: Finding, now: SiteSnapshot) -> Tuple[bool, str, Optional[str]]:
    """Return (resolved, detail, condition_key)."""
    text = _blob(finding)

    if "robots" in text:
        return now.robots_txt_found, (
            "robots.txt is present" if now.robots_txt_found else "robots.txt still missing"
        ), "robots_txt_present"
    if "sitemap" in text:
        return now.sitemap_found, (
            "XML sitemap is present" if now.sitemap_found else "sitemap still missing"
        ), "sitemap_present"
    if re.search(r"\bh1\b", text) and ("missing" in text or "lack" in text or "no h1" in text):
        resolved = now.missing_h1_count == 0 and bool(now.h1)
        return resolved, f"missing_h1_count={now.missing_h1_count} h1={now.h1[:2]}", "h1_present"
    if "title" in text and ("50" in text or "60" in text or "character" in text):
        ok = 50 <= now.title_length <= 60
        return ok, f"title_length={now.title_length} title={now.title!r}", "title_length_50_60"
    if "canonical" in text:
        resolved = now.canonical_missing_count == 0
        return resolved, f"pages_missing_canonical={now.canonical_missing_count}", "canonical_present"
    if "schema" in text or "json-ld" in text:
        resolved = len(now.schema_types) > 0
        return resolved, f"schema_types={now.schema_types}", "schema_present"
    if "alt" in text:
        resolved = now.images_without_alt == 0
        return resolved, f"images_without_alt={now.images_without_alt}", "images_have_alt"
    if "viewport" in text:
        resolved = now.viewport_missing_count == 0
        return resolved, f"viewport_missing_count={now.viewport_missing_count}", "viewport_present"
    if "https" in text or "http homepage" in text or "not https" in text:
        return now.https, f"https={now.https}", "https"
    if "privacy" in text:
        return now.privacy_present, f"privacy_present={now.privacy_present}", "privacy_present"
    if "cta" in text or "call-to-action" in text or "call to action" in text:
        resolved = len(now.ctas) > 0
        return resolved, f"ctas={now.ctas[:5]}", "cta_present"
    if "pricing" in text or "not_in_evidence" in text or "price" in text:
        return now.pricing_present, f"pricing_present={now.pricing_present}", "pricing_in_evidence"
    if "ttfb" in text:
        nums = [int(n) for n in re.findall(r"(\d+)\s*ms", text)]
        threshold = nums[0] if nums else 800
        resolved = now.ttfb_ms > 0 and now.ttfb_ms <= threshold
        return resolved, f"ttfb_ms={now.ttfb_ms} threshold={threshold}", "ttfb_within_threshold"
    return False, "No deterministic checker for this finding; treated as unresolved.", None


_METRIC_IMPROVE_WHEN_DOWN = {"lcp", "lcp_ms", "inp", "inp_ms", "cls", "ttfb_ms", "avg_position"}
_METRIC_KEYS = (
    "lcp", "lcp_ms", "inp", "inp_ms", "cls", "organic_traffic", "review_count",
    "rating", "referring_domains", "avg_position", "ttfb_ms",
)


def metric_deltas(
    before: Dict[str, Optional[float]],
    after: Dict[str, Optional[float]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    keys = set(before or {}) | set(after or {}) | set(_METRIC_KEYS)
    for key in sorted(keys):
        b = (before or {}).get(key)
        a = (after or {}).get(key)
        if b is None and a is None:
            continue
        if b is None or a is None:
            out[key] = ExternalMetricDelta(
                metric=key, before=b, after=a, delta=None, direction="unavailable",
                note="Baseline or current value missing; delta not computed.",
            ).model_dump()
            continue
        delta = round(float(a) - float(b), 4)
        down_is_better = key in _METRIC_IMPROVE_WHEN_DOWN
        if delta == 0:
            direction = "unchanged"
        elif (delta < 0 and down_is_better) or (delta > 0 and not down_is_better):
            direction = "improved"
        else:
            direction = "worsened"
        out[key] = ExternalMetricDelta(
            metric=key, before=float(b), after=float(a), delta=delta, direction=direction,
        ).model_dump()
    return out


def detect_confounds(
    before: SiteSnapshot,
    after: SiteSnapshot,
    *,
    condition_key: Optional[str],
    client_confirmed: bool,
    horizon_days: int,
    resolved_count: int,
    finding_count: int,
) -> List[str]:
    flags: List[str] = []
    unrelated = 0
    for field in ("h1", "title", "robots", "sitemap", "schema", "https", "ctas"):
        if before.field_fingerprint.get(field) != after.field_fingerprint.get(field):
            if condition_key and field.split("_")[0] in (condition_key or ""):
                continue
            unrelated += 1
    if unrelated:
        flags.append(f"other_simultaneous_dom_changes:{unrelated}")
    if resolved_count >= 2:
        flags.append("multiple_findings_resolved_same_window")
    if horizon_days >= 90:
        flags.append("seasonal_traffic_window_possible")
    if not client_confirmed:
        flags.append("no_client_remediation_confirmation")
    if finding_count > 8 and unrelated:
        flags.append("broad_site_changes_confound_single_fix")
    return flags


def attribution_confidence(
    *,
    condition_resolved: bool,
    metric_direction: Optional[str],
    client_confirmed: bool,
    confounds: List[str],
) -> str:
    if not condition_resolved:
        return "LOW"
    if metric_direction in (None, "unavailable", "unchanged"):
        return "LOW"
    if metric_direction == "worsened":
        return "LOW"
    confound_n = len([c for c in confounds if not c.startswith("no_client")])
    if client_confirmed and metric_direction == "improved" and confound_n == 0:
        return "HIGH"
    if metric_direction == "improved":
        return "MEDIUM"
    return "LOW"


def observed_outcome(resolved: bool, metric_direction: Optional[str]) -> str:
    if resolved:
        if metric_direction == "improved":
            return "resolved_metric_improved"
        if metric_direction == "worsened":
            return "resolved_metric_worsened"
        if metric_direction == "unchanged":
            return "resolved_metric_unchanged"
        return "resolved_no_metric"
    if metric_direction == "improved":
        return "unresolved_metric_improved"
    if metric_direction == "worsened":
        return "unresolved_metric_worsened"
    return "unresolved_no_change"


def primary_metric_direction(deltas: Dict[str, Any]) -> Optional[str]:
    if not deltas:
        return None
    for preferred in ("lcp", "lcp_ms", "organic_traffic", "review_count", "rating", "ttfb_ms"):
        if preferred in deltas:
            return deltas[preferred].get("direction")
    for item in deltas.values():
        if isinstance(item, dict) and item.get("direction") != "unavailable":
            return item.get("direction")
    return "unavailable"


class OutcomeTrackingAgent:
    """Post-audit 30/60/90-day recheck. Not part of the live audit DAG."""

    agent_id = "outcome.tracking.v1"

    def evaluate(
        self,
        findings: Iterable[Finding],
        baseline: SiteSnapshot,
        current: SiteSnapshot,
        *,
        client_remediated_ids: Optional[Iterable[str]] = None,
        horizon_days: int = 30,
        analysis_id: str = "",
    ) -> OutcomeRunResult:
        findings_list = list(findings)
        confirmed = set(client_remediated_ids or [])
        pre_resolved = []
        for f in findings_list:
            resolved, _, key = check_condition(f, current)
            pre_resolved.append((f, resolved, key))
        resolved_count = sum(1 for _, r, k in pre_resolved if r and k)

        records: List[OutcomeRecord] = []
        for finding, resolved, key in pre_resolved:
            client_hit = finding.finding_id in confirmed
            remediated = bool(client_hit or resolved)
            deltas = metric_deltas(baseline.external_metrics, current.external_metrics)
            direction = primary_metric_direction(deltas)
            confounds = detect_confounds(
                baseline,
                current,
                condition_key=key,
                client_confirmed=client_hit,
                horizon_days=horizon_days,
                resolved_count=resolved_count,
                finding_count=len(findings_list),
            )
            if direction == "improved" and not resolved:
                confounds.append("metric_moved_without_condition_resolved")
            if not deltas:
                confounds.append("no_baseline_or_current_external_metric")
            _, detail, _ = check_condition(finding, current)
            attr = attribution_confidence(
                condition_resolved=resolved,
                metric_direction=direction,
                client_confirmed=client_hit,
                confounds=confounds,
            )
            ftype = classify_finding_type(finding)
            records.append(OutcomeRecord(
                finding_id=finding.finding_id,
                finding_type=ftype,
                predicted_impact=predicted_impact_band(finding),
                remediated=remediated,
                evidence_condition_resolved=resolved,
                condition_key=key,
                condition_detail=detail,
                external_metric_delta=deltas,
                confidence_this_delta_is_attributable_to_the_fix=attr,
                confounds=confounds,
                observed_outcome=observed_outcome(resolved, direction),
                horizon_days=horizon_days,
            ))

        global_confounds = sorted({c for rec in records for c in rec.confounds})
        return OutcomeRunResult(
            run_id=f"outcome_{uuid4().hex[:12]}",
            analysis_id=analysis_id,
            horizon_days=horizon_days,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            records=records,
            confounds_global=global_confounds,
            benchmark_rows=summarize_benchmark(records),
        )


def summarize_benchmark(records: Iterable[OutcomeRecord]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str], List[OutcomeRecord]] = {}
    for rec in records:
        buckets.setdefault((rec.finding_type, rec.predicted_impact), []).append(rec)
    rows = []
    for (ftype, impact), items in sorted(buckets.items()):
        n = len(items)
        resolved = sum(1 for i in items if i.evidence_condition_resolved)
        improved = sum(
            1 for i in items
            if primary_metric_direction(i.external_metric_delta) == "improved"
        )
        high = sum(1 for i in items if i.confidence_this_delta_is_attributable_to_the_fix == "HIGH")
        mix: Dict[str, int] = {}
        for i in items:
            mix[i.observed_outcome] = mix.get(i.observed_outcome, 0) + 1
        rows.append(BenchmarkRow(
            finding_type=ftype,
            predicted_impact=impact,
            sample_size=n,
            resolved_rate=round(resolved / n, 3),
            metric_improved_rate=round(improved / n, 3),
            high_attribution_rate=round(high / n, 3),
            observed_outcome_mix=mix,
        ).model_dump())
    return rows


outcome_agent = OutcomeTrackingAgent()
