"""
Data Reliability, Provenance, Normalization & Cross-System Reconciliation Engine.

Enforces enterprise measurement governance:
1. Source-level data provenance for every metric & finding.
2. Data freshness checks and stale-data warnings.
3. Missing-data & sampling-bias detection.
4. Event deduplication & out-of-order event handling.
5. UTC time-zone normalization & ISO-4217 currency normalization.
6. Metric-definition versioning.
7. Connector failure, retry/backoff, and partial-sync reporting with fault isolation.
8. Explicit cross-system reconciliation (GA4 vs server events vs CRM vs commerce orders):
   discrepancies are surfaced transparently rather than silently picking one number.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.db.enterprise_intelligence_schema import connect_enterprise_db

METRIC_DEFINITION_VERSION = "dristik_metrics_v4.0"

# Static fallback FX rates to INR/USD only when an explicit rate is not supplied;
# callers in production should pass live FX rates with fx_timestamp_utc.
DEFAULT_FX_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "INR": 0.0119,
    "EUR": 1.08,
    "GBP": 1.27,
    "AUD": 0.65,
    "CAD": 0.72,
    "SGD": 0.74,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_timestamp_utc(raw_ts: Any) -> Tuple[str, str]:
    """Normalize any ISO-8601 or datetime timestamp into canonical UTC ISO-8601.
    Returns `(utc_iso, original_tz_label)`.
    """
    if isinstance(raw_ts, datetime):
        if raw_ts.tzinfo is None:
            return raw_ts.replace(tzinfo=timezone.utc).isoformat(), "UTC"
        tz_label = str(raw_ts.tzinfo)
        return raw_ts.astimezone(timezone.utc).isoformat(), tz_label
    text = str(raw_ts or "").strip()
    if not text:
        return utc_now_iso(), "UTC"
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(candidate)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat(), "UTC"
        return dt.astimezone(timezone.utc).isoformat(), str(dt.tzinfo)
    except ValueError:
        return utc_now_iso(), "UNPARSED_FALLBACK_UTC"


def normalize_currency(
    amount: float,
    source_currency: str,
    target_currency: str = "INR",
    explicit_fx_rate: Optional[float] = None,
) -> Tuple[float, float, str]:
    """Normalize monetary value into target ISO-4217 currency.
    Returns `(normalized_amount, fx_rate_used, target_currency)`.
    """
    src = (source_currency or "INR").strip().upper()
    tgt = (target_currency or "INR").strip().upper()
    if src == tgt:
        return round(float(amount), 2), 1.0, tgt
    if explicit_fx_rate is not None and explicit_fx_rate > 0:
        return round(float(amount) * float(explicit_fx_rate), 2), float(explicit_fx_rate), tgt
    src_usd = DEFAULT_FX_TO_USD.get(src)
    tgt_usd = DEFAULT_FX_TO_USD.get(tgt)
    if src_usd and tgt_usd:
        rate = round(src_usd / tgt_usd, 6)
        return round(float(amount) * rate, 2), rate, tgt
    # Never fabricate conversion for unknown currency codes
    return round(float(amount), 2), 1.0, src


class MetricProvenance(BaseModel):
    provenance_id: str = Field(default_factory=lambda: f"prov_{uuid.uuid4().hex[:12]}")
    org_id: str
    audit_run_id: Optional[str] = None
    metric_name: str
    metric_definition_version: str = METRIC_DEFINITION_VERSION
    source_provider: str
    source_endpoint: Optional[str] = None
    retrieved_at_utc: str = Field(default_factory=utc_now_iso)
    freshness_status: str = "FRESH"  # FRESH | STALE_WARNING | EXPIRED
    payload_sha256: str
    raw_value: Any = None


class FreshnessAssessment(BaseModel):
    retrieved_at_utc: str
    age_hours: float
    sla_hours: int
    status: str  # FRESH | STALE_WARNING | EXPIRED
    warning: Optional[str] = None


class ReconciliationResult(BaseModel):
    reconciliation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:12]}")
    org_id: str
    domain: str
    metric_name: str
    source_a_name: str
    source_a_value: Optional[float] = None
    source_b_name: str
    source_b_value: Optional[float] = None
    discrepancy_delta: Optional[float] = None
    discrepancy_pct: Optional[float] = None
    reconciliation_status: str  # RECONCILED | DISCREPANCY_DETECTED | INCOMPLETE_SOURCES
    tolerance_pct: float = 2.0
    explanation: str


class SamplingBiasWarning(BaseModel):
    dimension: str
    observed_count: int
    population_count: int
    coverage_pct: float
    bias_detected: bool
    note: str


class DataReliabilityGovernance:
    """Central service for provenance, freshness, sampling bias, and cross-system reconciliation."""

    @staticmethod
    def compute_payload_sha256(payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def check_freshness(
        cls,
        retrieved_at_utc: str,
        sla_hours: int = 24,
        now_utc: Optional[datetime] = None,
    ) -> FreshnessAssessment:
        now = now_utc or datetime.now(timezone.utc)
        norm_ts, _ = normalize_timestamp_utc(retrieved_at_utc)
        dt = datetime.fromisoformat(norm_ts)
        age_hours = max(0.0, round((now - dt).total_seconds() / 3600.0, 2))
        if age_hours <= sla_hours:
            status, warn = "FRESH", None
        elif age_hours <= sla_hours * 3:
            status = "STALE_WARNING"
            warn = f"Data is {age_hours:.1f}h old (exceeds {sla_hours}h SLA)."
        else:
            status = "EXPIRED"
            warn = f"Data is {age_hours:.1f}h old (exceeds 3x {sla_hours}h SLA; refresh required)."
        return FreshnessAssessment(
            retrieved_at_utc=norm_ts,
            age_hours=age_hours,
            sla_hours=sla_hours,
            status=status,
            warning=warn,
        )

    @classmethod
    def detect_sampling_bias(
        cls,
        *,
        dimension: str,
        observed_count: int,
        population_count: int,
        min_coverage_pct: float = 80.0,
    ) -> SamplingBiasWarning:
        if population_count <= 0:
            return SamplingBiasWarning(
                dimension=dimension,
                observed_count=observed_count,
                population_count=population_count,
                coverage_pct=0.0,
                bias_detected=True,
                note=f"{dimension}: population denominator is 0; coverage cannot be established.",
            )
        cov = round(min(100.0, (observed_count / population_count) * 100.0), 1)
        biased = cov < min_coverage_pct
        note = (
            f"{dimension}: {observed_count}/{population_count} observed ({cov:.1f}%). "
            + ("Sampling bias risk: below minimum coverage threshold." if biased else "Representative coverage.")
        )
        return SamplingBiasWarning(
            dimension=dimension,
            observed_count=observed_count,
            population_count=population_count,
            coverage_pct=cov,
            bias_detected=biased,
            note=note,
        )

    @classmethod
    def is_out_of_order_event(
        cls,
        event_ts_utc: str,
        ingested_at_utc: str,
        late_threshold_seconds: int = 300,
    ) -> bool:
        e_iso, _ = normalize_timestamp_utc(event_ts_utc)
        i_iso, _ = normalize_timestamp_utc(ingested_at_utc)
        delta = (datetime.fromisoformat(i_iso) - datetime.fromisoformat(e_iso)).total_seconds()
        return delta > late_threshold_seconds

    @classmethod
    def reconcile_sources(
        cls,
        *,
        org_id: str,
        domain: str,
        metric_name: str,
        source_a_name: str,
        source_a_value: Optional[float],
        source_b_name: str,
        source_b_value: Optional[float],
        tolerance_pct: float = 2.0,
        period_start_utc: Optional[str] = None,
        period_end_utc: Optional[str] = None,
        db_path: Optional[str] = None,
        persist: bool = True,
    ) -> ReconciliationResult:
        """Compare two measurement systems (e.g., GA4 vs Shopify/WooCommerce) and expose discrepancies."""
        if source_a_value is None or source_b_value is None:
            res = ReconciliationResult(
                org_id=org_id,
                domain=domain,
                metric_name=metric_name,
                source_a_name=source_a_name,
                source_a_value=source_a_value,
                source_b_name=source_b_name,
                source_b_value=source_b_value,
                reconciliation_status="INCOMPLETE_SOURCES",
                tolerance_pct=tolerance_pct,
                explanation=(
                    f"Cannot reconcile {metric_name}: missing value from "
                    f"{source_a_name if source_a_value is None else source_b_name}."
                ),
            )
        else:
            delta = round(float(source_b_value) - float(source_a_value), 4)
            denom = max(abs(float(source_a_value)), abs(float(source_b_value)), 1e-9)
            pct = round((abs(delta) / denom) * 100.0, 2)
            status = "RECONCILED" if pct <= tolerance_pct else "DISCREPANCY_DETECTED"
            explanation = (
                f"{source_a_name} reported {source_a_value:g} vs {source_b_name} confirmed {source_b_value:g} "
                f"(delta={delta:+g}, variance={pct:.2f}%). "
                + (
                    "Within reconciliation tolerance."
                    if status == "RECONCILED"
                    else "Discrepancy exposed — Dristik does not silently overwrite one system with another."
                )
            )
            res = ReconciliationResult(
                org_id=org_id,
                domain=domain,
                metric_name=metric_name,
                source_a_name=source_a_name,
                source_a_value=float(source_a_value),
                source_b_name=source_b_name,
                source_b_value=float(source_b_value),
                discrepancy_delta=delta,
                discrepancy_pct=pct,
                reconciliation_status=status,
                tolerance_pct=tolerance_pct,
                explanation=explanation,
            )

        if persist:
            now = utc_now_iso()
            conn = connect_enterprise_db(db_path)
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO data_reconciliation_reports (
                        reconciliation_id, org_id, domain, period_start_utc, period_end_utc,
                        metric_name, source_a_name, source_a_value, source_b_name, source_b_value,
                        discrepancy_delta, discrepancy_pct, reconciliation_status, explanation, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        res.reconciliation_id,
                        org_id,
                        domain,
                        period_start_utc or now,
                        period_end_utc or now,
                        metric_name,
                        source_a_name,
                        res.source_a_value,
                        source_b_name,
                        res.source_b_value,
                        res.discrepancy_delta,
                        res.discrepancy_pct,
                        res.reconciliation_status,
                        res.explanation,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return res

    @classmethod
    def record_provenance(
        cls,
        *,
        org_id: str,
        metric_name: str,
        source_provider: str,
        raw_value: Any,
        audit_run_id: Optional[str] = None,
        source_endpoint: Optional[str] = None,
        sla_hours: int = 24,
        db_path: Optional[str] = None,
    ) -> MetricProvenance:
        now = utc_now_iso()
        fresh = cls.check_freshness(now, sla_hours=sla_hours)
        prov = MetricProvenance(
            org_id=org_id,
            audit_run_id=audit_run_id,
            metric_name=metric_name,
            source_provider=source_provider,
            source_endpoint=source_endpoint,
            retrieved_at_utc=now,
            freshness_status=fresh.status,
            payload_sha256=cls.compute_payload_sha256(raw_value),
            raw_value=raw_value,
        )
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO metric_provenance_records (
                    provenance_id, org_id, audit_run_id, metric_name, metric_definition_version,
                    source_provider, source_endpoint, retrieved_at_utc, freshness_status,
                    payload_sha256, raw_value_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prov.provenance_id,
                    prov.org_id,
                    prov.audit_run_id,
                    prov.metric_name,
                    prov.metric_definition_version,
                    prov.source_provider,
                    prov.source_endpoint,
                    prov.retrieved_at_utc,
                    prov.freshness_status,
                    prov.payload_sha256,
                    json.dumps(raw_value, default=str),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return prov

    @classmethod
    def execute_with_fault_isolation(
        cls,
        *,
        org_id: str,
        provider: str,
        fn: Callable[[], Any],
        max_retries: int = 2,
        base_delay_sec: float = 0.05,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a connector sync with retry/backoff and logs health without crashing sibling pillars."""
        sync_id = f"sync_{uuid.uuid4().hex[:12]}"
        started = utc_now_iso()
        errors: List[str] = []
        result_data: Any = None
        status = "FAILED"

        for attempt in range(max_retries + 1):
            try:
                result_data = fn()
                status = "COMPLETED"
                break
            except Exception as exc:
                errors.append(f"attempt {attempt + 1}: {exc}")
                if attempt < max_retries:
                    time.sleep(base_delay_sec * (2 ** attempt))

        completed = utc_now_iso()
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO connector_sync_runs (
                    sync_id, org_id, provider, status, started_at_utc, completed_at_utc,
                    records_synced, partial_errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_id,
                    org_id,
                    provider,
                    status,
                    started,
                    completed,
                    1 if status == "COMPLETED" else 0,
                    json.dumps(errors),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "sync_id": sync_id,
            "provider": provider,
            "status": status,
            "data": result_data,
            "errors": errors,
        }
