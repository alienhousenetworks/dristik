"""
Dristik AI Radar Service & Monthly Citation Pulse
Automates continuous monthly monitoring of saved commercial buyer prompts,
detects crawl change-log diffs (H1, meta, schema, pricing), calculates citation score deltas,
and generates regression alerts for ongoing retainer clients.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field

class RadarSubscription(BaseModel):
    subscription_id: str
    org_id: str = "org_default"
    target_url: str
    domain: str
    plan_id: str = "monthly_pulse"
    status: str = "active"  # active, paused, cancelled
    frequency: str = "monthly"  # monthly, biweekly
    saved_prompts: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_run_id: Optional[str] = None
    last_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    last_snapshot: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, Any]] = Field(default_factory=list)

class RadarDiffResult(BaseModel):
    diff_id: str
    subscription_id: str
    domain: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    previous_run_id: Optional[str] = None
    current_run_id: str
    score_deltas: Dict[str, float] = Field(default_factory=dict)
    current_scores: Dict[str, float] = Field(default_factory=dict)
    dom_changes: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    regression_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    executive_delta_digest: str
    alert_severity: str = "NONE"  # NONE, LOW, MEDIUM, CRITICAL
    citation_measurement: Optional[Dict[str, Any]] = None
    notification: Optional[Dict[str, Any]] = None

DEFAULT_SAVED_PROMPTS = [
    "What does {domain} do, and who is the ideal customer?",
    "How much does {domain} cost and what are the pricing tiers?",
    "What are the top alternatives to {domain} and trade-offs?",
    "Can I trust {domain}? What customer proof or certifications exist?",
    "What is the expected ROI and payback time of {domain}?"
]

class RadarService:
    def __init__(self):
        self._subscriptions: Dict[str, RadarSubscription] = {}

    def create_subscription(
        self,
        target_url: str,
        org_id: str = "org_default",
        plan_id: str = "monthly_pulse",
        saved_prompts: Optional[List[str]] = None,
        initial_scores: Optional[Dict[str, float]] = None,
        initial_snapshot: Optional[Dict[str, Any]] = None,
    ) -> RadarSubscription:
        parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
        domain = parsed.netloc or parsed.path
        sub_id = f"sub_{uuid.uuid4().hex[:10]}"

        prompts = saved_prompts or [p.format(domain=domain) for p in DEFAULT_SAVED_PROMPTS]
        now = datetime.now()
        next_run = now + timedelta(days=30)

        sub = RadarSubscription(
            subscription_id=sub_id,
            org_id=org_id,
            target_url=target_url,
            domain=domain,
            plan_id=plan_id,
            saved_prompts=prompts,
            created_at=now.isoformat(),
            next_run_at=next_run.isoformat(),
            last_scores=initial_scores or {},
            last_snapshot=initial_snapshot or {}
        )
        self._subscriptions[sub_id] = sub
        return sub

    def get_subscription(self, subscription_id: str) -> Optional[RadarSubscription]:
        return self._subscriptions.get(subscription_id)

    def list_subscriptions(self, org_id: Optional[str] = None) -> List[RadarSubscription]:
        if org_id:
            return [s for s in self._subscriptions.values() if s.org_id == org_id]
        return list(self._subscriptions.values())

    def run_pulse_check(
        self,
        subscription_id: str,
        current_snapshot: Optional[Dict[str, Any]] = None,
        new_scores: Optional[Dict[str, float]] = None,
    ) -> RadarDiffResult:
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription {subscription_id} not found.")

        if not current_snapshot and not new_scores:
            raise ValueError(
                f"Cannot compute pulse diff for {sub.domain}: A current crawl snapshot or verified scores are required."
            )

        run_id = f"pulse_{uuid.uuid4().hex[:8]}"
        prev_run_id = sub.last_run_id
        prev_scores = sub.last_scores or {}
        prev_snapshot = sub.last_snapshot or {}

        curr_snap = current_snapshot or {}
        curr_scores = new_scores or {}

        # Calculate score deltas from actual verified numbers only
        deltas = {}
        for k, v in curr_scores.items():
            if k in prev_scores and prev_scores[k] is not None and v is not None:
                deltas[k] = round(v - prev_scores[k], 1)


        # Detect DOM change-logs
        dom_changes = []
        if curr_snap.get("h1") != prev_snapshot.get("h1"):
            dom_changes.append({
                "field": "H1 Heading",
                "old": prev_snapshot.get("h1"),
                "new": curr_snap.get("h1"),
                "status": "MODIFIED",
                "impact": "Core headline was updated; check ICP qualification clarity."
            })
        if curr_snap.get("title") != prev_snapshot.get("title"):
            dom_changes.append({
                "field": "Page Title",
                "old": prev_snapshot.get("title"),
                "new": curr_snap.get("title"),
                "status": "MODIFIED",
                "impact": "SERP title changed."
            })
        if curr_snap.get("has_schema") and not prev_snapshot.get("has_schema"):
            dom_changes.append({
                "field": "Schema.org JSON-LD",
                "old": "Missing",
                "new": "Active (Organization + SoftwareApplication)",
                "status": "ADDED",
                "impact": "Entity clarity improved; answer engines can extract offerings."
            })
        elif not curr_snap.get("has_schema") and prev_snapshot.get("has_schema"):
            dom_changes.append({
                "field": "Schema.org JSON-LD",
                "old": "Active",
                "new": "Missing",
                "status": "REMOVED",
                "impact": "Regression: Schema was removed in deployment."
            })

        # Evaluate prompt citations across saved buyer questions
        prompt_evals = []
        regressions = []
        prompt_measurements = curr_snap.get("prompt_readiness") or {}
        prev_measurements = prev_snapshot.get("prompt_readiness") or {}

        for prompt in sub.saved_prompts:
            # Zero-Fake Rule: Citation readiness must come from live measurements or be None
            readiness = prompt_measurements.get(prompt)
            prev_prompt_readiness = prev_measurements.get(prompt)

            if readiness is not None and prev_prompt_readiness is not None:
                p_delta = round(readiness - prev_prompt_readiness, 1)
                p_status = "IMPROVED" if p_delta > 0 else ("REGRESSED" if p_delta < 0 else "STABLE")
            else:
                p_delta = None
                p_status = "UNAVAILABLE"

            p_eval = {
                "prompt": prompt,
                "citation_readiness": round(readiness, 1) if readiness is not None else None,
                "previous_readiness": round(prev_prompt_readiness, 1) if prev_prompt_readiness is not None else None,
                "delta": p_delta,
                "status": p_status,
            }
            prompt_evals.append(p_eval)

            if p_delta is not None and p_delta < -5.0:
                regressions.append({
                    "prompt": prompt,
                    "severity": "HIGH",
                    "reason": f"Citation readiness fell by {abs(p_delta)}% vs last month."
                })


        # Determine overall alert severity
        alert_sev = "NONE"
        if regressions:
            alert_sev = "CRITICAL" if len(regressions) > 1 else "HIGH"
        elif deltas.get("ai_citation", 0) <= -10.0 or any(c["status"] == "REMOVED" for c in dom_changes):
            alert_sev = "HIGH"
        elif deltas.get("ai_citation", 0) < 0 or deltas.get("human", 0) < -5:
            alert_sev = "MEDIUM"

        citation_measurement = {"provenance": "NOT_MEASURED", "detail": "No live citation snapshot is stored for this domain."}
        try:
            from app.intelligence.geo.pipeline_store import geo_pipeline_store
            snap = geo_pipeline_store.get_latest_snapshot(sub.domain)
            if snap and (snap.engines_measured_count or 0) > 0 and snap.overall_score is not None:
                citation_measurement = {
                    "provenance": "MEASURED",
                    "snapshot_id": snap.snapshot_id,
                    "overall_score": snap.overall_score,
                    "engines_measured_count": snap.engines_measured_count,
                    "engine_scores": snap.engine_scores or {},
                }
        except Exception:
            citation_measurement = {"provenance": "NOT_MEASURED", "detail": "Citation snapshot store was unavailable."}

        # Executive delta digest uses only scores that were supplied. It does not invent a citation number.
        digest_lines = [f"Monthly Citation Pulse Delta for {sub.domain}:"]
        labels = {
            "ai_citation": "AI Citation Readiness",
            "human": "Human Conversion Score",
            "google": "Google Technical Score",
        }
        for key, label in labels.items():
            if key in curr_scores and curr_scores[key] is not None and key in deltas:
                sign = "+" if deltas[key] >= 0 else ""
                digest_lines.append(f"• {label}: {curr_scores[key]:.0f}% ({sign}{deltas[key]}%)")
        if citation_measurement.get("provenance") == "MEASURED":
            digest_lines.append(
                f"• Live citation snapshot: {citation_measurement['overall_score']} across "
                f"{citation_measurement['engines_measured_count']} engine(s)."
            )
        else:
            digest_lines.append("• Live citation snapshot: not measured.")
        digest_lines.append(f"• Tracked Buyer Prompts: {len(sub.saved_prompts)} prompts active.")
        if dom_changes:
            digest_lines.append(f"• DOM Changes Detected: {len(dom_changes)} key structural updates recorded.")
        if regressions:
            digest_lines.append(f"⚠️ Regression Alert: {len(regressions)} prompt(s) experienced citability drops.")
        else:
            digest_lines.append("✓ No citability regressions detected this month.")

        digest = "\n".join(digest_lines)

        diff = RadarDiffResult(
            diff_id=f"diff_{uuid.uuid4().hex[:8]}",
            subscription_id=subscription_id,
            domain=sub.domain,
            previous_run_id=prev_run_id,
            current_run_id=run_id,
            score_deltas=deltas,
            current_scores=curr_scores,
            dom_changes=dom_changes,
            prompt_evaluations=prompt_evals,
            regression_alerts=regressions,
            executive_delta_digest=digest,
            alert_severity=alert_sev,
            citation_measurement=citation_measurement,
        )
        if alert_sev in ("HIGH", "CRITICAL"):
            try:
                from app.notifications.dispatcher import notify
                diff.notification = notify(
                    event="radar_regression",
                    subject=f"Dristik radar {alert_sev} for {sub.domain}",
                    body=digest,
                )
            except Exception:
                diff.notification = {"event": "radar_regression", "delivery_status": "failed"}

        # Update subscription state
        now = datetime.now()
        sub.last_run_at = now.isoformat()
        sub.next_run_at = (now + timedelta(days=30)).isoformat()
        sub.last_run_id = run_id
        sub.last_scores = curr_scores
        sub.last_snapshot = curr_snap
        sub.history.append(diff.model_dump())

        return diff

radar_service = RadarService()
