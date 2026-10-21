"""
Dristik AI Radar Service & Monthly Citation Pulse
Automates continuous monthly monitoring of saved commercial buyer prompts,
detects crawl change-log diffs (H1, meta, schema, pricing), calculates citation score deltas,
and generates regression alerts for ongoing retainer clients.
"""
import uuid
from datetime import datetime, timedelta
from difflib import SequenceMatcher
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
    drift_findings: List[Dict[str, Any]] = Field(default_factory=list)
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

def evaluate_seo_drift(prev: Dict[str, Any], curr: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates 17 comparison rules across 3 severity levels (CRITICAL, WARNING, INFO)
    between a stored baseline snapshot and current page state.
    Adapted from Claude SEO drift monitoring.
    """
    findings: List[Dict[str, Any]] = []

    def _get_h1(snap):
        h1 = snap.get("h1")
        if isinstance(h1, list):
            return h1[0] if h1 else None
        return h1

    # --- CRITICAL (Immediate Action Required) ---
    # Rule 1: Schema/JSON-LD Completely Removed
    prev_schema = prev.get("schema") or (["schema_present"] if prev.get("has_schema") else [])
    curr_schema = curr.get("schema") or (["schema_present"] if curr.get("has_schema") else [])
    if prev_schema and not curr_schema:
        findings.append({
            "rule_id": 1,
            "rule_name": "Schema/JSON-LD Completely Removed",
            "severity": "CRITICAL",
            "field": "Schema.org JSON-LD",
            "old": "Active",
            "new": "Missing",
            "status": "REMOVED",
            "impact": "Structured data removed. Eligible rich results (Product, Review, LocalBusiness) risk dropping from SERPs quickly.",
            "cross_ref": "schema.validation.v3"
        })

    # Rule 2: Canonical URL Changed
    prev_canon = prev.get("canonical")
    curr_canon = curr.get("canonical")
    if prev_canon and curr_canon and str(prev_canon).strip().rstrip("/") != str(curr_canon).strip().rstrip("/"):
        findings.append({
            "rule_id": 2,
            "rule_name": "Canonical URL Changed",
            "severity": "CRITICAL",
            "field": "Canonical URL",
            "old": prev_canon,
            "new": curr_canon,
            "status": "MODIFIED",
            "impact": "Canonical destination changed. Verify target URL is intentional; incorrect canonicals transfer equity away.",
            "cross_ref": "seo.indexability.v3"
        })

    # Rule 3: Canonical URL Removed
    if prev_canon and not curr_canon:
        findings.append({
            "rule_id": 3,
            "rule_name": "Canonical URL Removed",
            "severity": "CRITICAL",
            "field": "Canonical URL",
            "old": prev_canon,
            "new": None,
            "status": "REMOVED",
            "impact": "Canonical tag missing. Search engines will guess canonical target, risking duplicate indexation.",
            "cross_ref": "seo.indexability.v3"
        })

    # Rule 4: Noindex Directive Added
    prev_robots = str(prev.get("meta_robots") or "").lower()
    curr_robots = str(curr.get("meta_robots") or "").lower()
    if "noindex" not in prev_robots and "noindex" in curr_robots:
        findings.append({
            "rule_id": 4,
            "rule_name": "Noindex Directive Added",
            "severity": "CRITICAL",
            "field": "Meta Robots Directive",
            "old": prev.get("meta_robots") or "index,follow",
            "new": curr.get("meta_robots"),
            "status": "ADDED",
            "impact": "Unintentional noindex will deindex this URL from search engines within days.",
            "cross_ref": "seo.indexability.v3"
        })

    # Rule 5: H1 Tag Removed Entirely
    prev_h1 = _get_h1(prev)
    curr_h1 = _get_h1(curr)
    if prev_h1 and not curr_h1:
        findings.append({
            "rule_id": 5,
            "rule_name": "H1 Tag Removed Entirely",
            "severity": "CRITICAL",
            "field": "H1 Heading",
            "old": prev_h1,
            "new": None,
            "status": "REMOVED",
            "impact": "Primary topical heading signal missing. Impairs on-page semantic relevance and extractability.",
            "cross_ref": "seo.html.v3"
        })

    # Rule 6: H1 Text Changed Significantly
    elif prev_h1 and curr_h1 and prev_h1.strip() != curr_h1.strip():
        ratio = SequenceMatcher(None, prev_h1.strip().lower(), curr_h1.strip().lower()).ratio()
        if ratio < 0.5:
            findings.append({
                "rule_id": 6,
                "rule_name": "H1 Text Changed Significantly",
                "severity": "CRITICAL",
                "field": "H1 Heading",
                "old": prev_h1,
                "new": curr_h1,
                "status": "MODIFIED",
                "impact": f"H1 changed substantially (similarity: {ratio:.0%}). Verify alignment with target commercial intent.",
                "cross_ref": "seo.html.v3"
            })

    # Rule 7: Title Tag Removed Entirely
    prev_title = prev.get("title")
    curr_title = curr.get("title")
    if prev_title and not curr_title:
        findings.append({
            "rule_id": 7,
            "rule_name": "Title Tag Removed Entirely",
            "severity": "CRITICAL",
            "field": "Page Title",
            "old": prev_title,
            "new": None,
            "status": "REMOVED",
            "impact": "Title tag removed. Search engines will auto-generate SERP titles, typically degrading CTR.",
            "cross_ref": "seo.html.v3"
        })

    # Rule 8: HTTP Status Code Changed to Error
    prev_code = prev.get("status_code", 200)
    curr_code = curr.get("status_code", 200)
    if prev_code and curr_code and prev_code < 400 and curr_code >= 400:
        findings.append({
            "rule_id": 8,
            "rule_name": "HTTP Status Code Error",
            "severity": "CRITICAL",
            "field": "HTTP Status Code",
            "old": prev_code,
            "new": curr_code,
            "status": "REGRESSED",
            "impact": f"HTTP status regressed to {curr_code}. Broken page will be dropped from index.",
            "cross_ref": "seo.crawl.v3"
        })

    # --- WARNING (Investigate Within 1 Week) ---
    # Rule 9: Title Text Changed
    if prev_title and curr_title and prev_title.strip() != curr_title.strip():
        findings.append({
            "rule_id": 9,
            "rule_name": "Title Text Changed",
            "severity": "WARNING",
            "field": "Page Title",
            "old": prev_title,
            "new": curr_title,
            "status": "MODIFIED",
            "impact": "SERP title text modified. Monitor organic CTR and impressions in Search Console.",
            "cross_ref": "seo.html.v3"
        })

    # Rule 10: Meta Description Changed
    prev_desc = prev.get("meta_description")
    curr_desc = curr.get("meta_description")
    if prev_desc and curr_desc and prev_desc.strip() != curr_desc.strip():
        findings.append({
            "rule_id": 10,
            "rule_name": "Meta Description Changed",
            "severity": "WARNING",
            "field": "Meta Description",
            "old": prev_desc,
            "new": curr_desc,
            "status": "MODIFIED",
            "impact": "Meta description modified. Ensure CTA and commercial keywords remain intact.",
            "cross_ref": "seo.html.v3"
        })

    # Rule 11: Core Web Vitals Metric Regressed >20%
    prev_cwv = prev.get("cwv") or {}
    curr_cwv = curr.get("cwv") or {}
    for metric_key, metric_name in [("lcp", "LCP"), ("inp", "INP"), ("cls", "CLS")]:
        prev_val = prev_cwv.get(metric_key)
        curr_val = curr_cwv.get(metric_key)
        if prev_val is not None and curr_val is not None and prev_val > 0:
            pct_change = (curr_val - prev_val) / prev_val
            if pct_change > 0.20:
                findings.append({
                    "rule_id": 11,
                    "rule_name": f"Core Web Vitals {metric_name} Regressed >20%",
                    "severity": "WARNING",
                    "field": f"CWV {metric_name}",
                    "old": prev_val,
                    "new": curr_val,
                    "status": "REGRESSED",
                    "impact": f"{metric_name} worsened by {pct_change:.1%}. Check recent script or asset additions.",
                    "cross_ref": "seo.performance.v3"
                })

    # Rule 12: Lighthouse Performance Score Dropped >= 10 Points
    prev_perf = prev.get("performance_score")
    curr_perf = curr.get("performance_score")
    if prev_perf is not None and curr_perf is not None and (prev_perf - curr_perf) >= 10:
        findings.append({
            "rule_id": 12,
            "rule_name": "Lighthouse Performance Score Dropped >=10 Points",
            "severity": "WARNING",
            "field": "Performance Score",
            "old": prev_perf,
            "new": curr_perf,
            "status": "REGRESSED",
            "impact": f"Lighthouse performance dropped by {prev_perf - curr_perf:.0f} points.",
            "cross_ref": "seo.performance.v3"
        })

    # Rule 13: OG Tags Removed
    prev_og = prev.get("open_graph") or prev.get("og_tags")
    curr_og = curr.get("open_graph") or curr.get("og_tags")
    if prev_og and not curr_og:
        findings.append({
            "rule_id": 13,
            "rule_name": "Open Graph Tags Removed",
            "severity": "WARNING",
            "field": "Open Graph Metadata",
            "old": "Active",
            "new": "Missing",
            "status": "REMOVED",
            "impact": "Social sharing cards will render with generic or blank previews.",
            "cross_ref": "seo.html.v3"
        })

    # Rule 14: Schema/JSON-LD Content Modified
    prev_hash = prev.get("schema_hash")
    curr_hash = curr.get("schema_hash")
    if prev_schema and curr_schema and prev_hash and curr_hash and prev_hash != curr_hash:
        findings.append({
            "rule_id": 14,
            "rule_name": "Schema/JSON-LD Content Modified",
            "severity": "WARNING",
            "field": "Schema.org JSON-LD",
            "old": prev_hash[:8],
            "new": curr_hash[:8],
            "status": "MODIFIED",
            "impact": "Schema markup was updated. Validate required properties and syntax.",
            "cross_ref": "schema.validation.v3"
        })

    # --- INFO (Awareness Only) ---
    # Rule 15: New Schema/JSON-LD Added
    if not prev_schema and curr_schema:
        findings.append({
            "rule_id": 15,
            "rule_name": "New Schema/JSON-LD Added",
            "severity": "INFO",
            "field": "Schema.org JSON-LD",
            "old": "Missing",
            "new": "Active",
            "status": "ADDED",
            "impact": "Structured data added. Entity clarity and extractability improved.",
            "cross_ref": "schema.validation.v3"
        })

    # Rule 16: H2 Structure Changed
    prev_h2 = prev.get("h2") or []
    curr_h2 = curr.get("h2") or []
    if prev_h2 != curr_h2 and (len(prev_h2) > 0 or len(curr_h2) > 0):
        findings.append({
            "rule_id": 16,
            "rule_name": "H2 Subheading Structure Changed",
            "severity": "INFO",
            "field": "H2 Headings",
            "old": f"{len(prev_h2)} headings",
            "new": f"{len(curr_h2)} headings",
            "status": "MODIFIED",
            "impact": "H2 subheading hierarchy changed. Verify topic coverage remains complete.",
            "cross_ref": "content.topic_coverage.v3"
        })

    # Rule 17: Content Hash Changed
    prev_body = prev.get("html_hash") or prev.get("body_hash")
    curr_body = curr.get("html_hash") or curr.get("body_hash")
    if prev_body and curr_body and prev_body != curr_body:
        findings.append({
            "rule_id": 17,
            "rule_name": "Body Content Hash Changed",
            "severity": "INFO",
            "field": "Body HTML Hash",
            "old": prev_body[:8],
            "new": curr_body[:8],
            "status": "MODIFIED",
            "impact": "General body copy update detected.",
            "cross_ref": "content.depth.v3"
        })

    return findings

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


        # Evaluate 17 SEO drift comparison rules
        drift_findings = evaluate_seo_drift(prev_snapshot, curr_snap)

        # Determine overall alert severity
        alert_sev = "NONE"
        if any(f["severity"] == "CRITICAL" for f in drift_findings) or len(regressions) > 1:
            alert_sev = "CRITICAL"
        elif regressions or any(f["severity"] == "WARNING" for f in drift_findings) or deltas.get("ai_citation", 0) <= -10.0 or any(c["status"] == "REMOVED" for c in dom_changes):
            alert_sev = "HIGH"
        elif deltas.get("ai_citation", 0) < 0 or deltas.get("human", 0) < -5:
            alert_sev = "MEDIUM"

        citation_measurement = {"provenance": "NOT_MEASURED", "detail": "No live citation snapshot is stored for this domain."}
        try:
            from app.geo.pipeline_store import geo_pipeline_store
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
        critical_drifts = [f for f in drift_findings if f["severity"] == "CRITICAL"]
        warning_drifts = [f for f in drift_findings if f["severity"] == "WARNING"]
        if critical_drifts:
            digest_lines.append(f"🚨 CRITICAL SEO Drift: {len(critical_drifts)} urgent regressions detected ({', '.join(f['field'] for f in critical_drifts[:3])}).")
        if warning_drifts:
            digest_lines.append(f"⚠️ SEO Drift Warnings: {len(warning_drifts)} notable change(s) detected.")
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
            drift_findings=drift_findings,
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
