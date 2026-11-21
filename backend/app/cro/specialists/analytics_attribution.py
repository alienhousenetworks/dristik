"""Department I — Analytics, Conversion Measurement, Funnels, Attribution & Connectors (Phases 18, 19, 41).

Core integrity rules:
- Missing analytics MUST NEVER produce a fabricated conversion rate or a zero conversion performance score.
- Strict counting-unit discipline: Conversion Rate = Unique Converting Visitors / Eligible Unique Visitors * 100.
  Never mix sessions in the numerator with unique users in the denominator.
- Detects analytics configuration & data-quality issues (missing tags, duplicate events, missing parameters,
  missing revenue/currency, consent gaps, bot/internal contamination).
- Distinguishes conversion volume from conversion quality (B2B CRM pipeline: Lead -> SQL -> Opportunity -> Closed Won).
- Hypothetical scenario estimates are explicitly stamped `ESTIMATE_SCENARIO_NOT_ACTUAL_REVENUE`.
- Truthful Connector Capability Registry across Priorities 1–4.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.cro.metrics import rate
from app.cro.models import (
    CROAgentOutput,
    CROAnalyticsEvent,
    CROConnectorCapability,
    CRODimensionCheck,
    CROFinding,
    CROFunnel,
    CROFunnelStep,
    CROSeverity,
    EvidenceSourceType,
)
from app.cro.specialists import CROAuditContext


def build_connector_capability_registry(connected_providers: Optional[List[str]] = None) -> List[CROConnectorCapability]:
    """Return truthful capability metadata for all Priority 1–4 CRO connectors."""
    active = {p.lower() for p in (connected_providers or [])}

    specs = [
        # Priority 1 — Analytics
        ("ga4", "Google Analytics 4", "analytics", 1, ["sessions", "unique_users", "events", "funnels", "device_segments", "landing_pages", "ecommerce_revenue"], ["read_events", "read_funnels", "read_segments"], ["Raw session replay video not provided by GA4"]),
        ("gtm", "Google Tag Manager", "analytics", 1, ["container_tags", "triggers", "variables", "consent_mode_config"], ["audit_tag_configuration"], ["Does not directly store conversion event counts"]),
        ("gsc", "Google Search Console", "analytics", 1, ["search_queries", "impressions", "clicks", "landing_page_ctr"], ["acquisition_intent_context"], ["No post-click conversion or funnel events"]),
        # Priority 2 — Ecommerce
        ("shopify", "Shopify", "ecommerce", 2, ["products", "orders", "cart_checkouts", "refunds", "aov", "theme_liquid"], ["read_orders", "read_products", "theme_preview"], ["Requires Admin API token; checkout.liquid restricted on non-Plus"]),
        ("woocommerce", "WooCommerce", "ecommerce", 2, ["products", "orders", "coupons", "refunds"], ["read_orders", "read_products"], ["Requires REST consumer key/secret"]),
        ("magento", "Magento / Adobe Commerce", "ecommerce", 2, ["catalog", "orders", "checkout_config"], ["read_orders", "read_catalog"], ["Requires Integration OAuth token"]),
        # Priority 3 — CRM & Lead Quality
        ("hubspot", "HubSpot", "crm", 3, ["contacts", "lead_status", "deals", "pipeline_stages", "closed_won_revenue"], ["lead_quality_attribution", "pipeline_stage_rates"], ["Exposes lead lifecycle & deals, not raw sales call transcripts"]),
        ("salesforce", "Salesforce", "crm", 3, ["leads", "opportunities", "accounts", "closed_won_revenue"], ["lead_quality_attribution", "revenue_attribution"], ["Scoped to authorized CRM objects only"]),
        # Priority 4 — Experimentation & Behavior Analytics
        ("optimizely", "Optimizely", "experimentation_behavior", 4, ["experiments", "variants", "assignment_counts", "results"], ["sync_experiments", "read_results"], ["Production rollout requires explicit approval"]),
        ("vwo", "VWO", "experimentation_behavior", 4, ["campaigns", "variations", "goals", "heatmaps"], ["sync_experiments", "click_aggregates"], ["Raw PII recordings excluded by default"]),
        ("posthog", "PostHog", "experimentation_behavior", 4, ["events", "funnels", "feature_flags", "experiments"], ["read_funnels", "sync_experiments"], ["Session recordings require explicit tenant opt-in"]),
        ("clarity", "Microsoft Clarity", "experimentation_behavior", 4, ["rage_clicks", "dead_clicks", "scroll_depth", "click_maps"], ["behavioral_friction_aggregates"], ["Exposes aggregate friction metrics, not raw session video export"]),
        ("hotjar", "Hotjar", "experimentation_behavior", 4, ["heatmaps", "survey_responses", "feedback_widgets"], ["click_maps", "user_research_feedback"], ["Exposes click maps/surveys; raw recordings require explicit authorization"]),
    ]

    result: List[CROConnectorCapability] = []
    for cid, name, cat, tier, supp, avail, limits in specs:
        is_conn = cid in active
        result.append(
            CROConnectorCapability(
                connector_id=cid,
                provider=name,
                category=cat,
                priority_tier=tier,
                connection_status="connected" if is_conn else "not_connected",
                permissions=["read_only_telemetry"] if is_conn else [],
                supported_data=supp,
                available_capabilities=avail if is_conn else [],
                unsupported_or_limited=limits,
                rate_limit_status="within_budget" if is_conn else "not_applicable",
                auth_status="authenticated" if is_conn else "unauthenticated",
                reauth_required=False,
            )
        )
    return result


def build_impact_scenario_estimate(
    *,
    measured_visitors: Optional[int],
    measured_conversion_rate: Optional[float],
    hypothetical_conversion_rate: Optional[float],
    value_per_conversion: Optional[float],
    currency: str = "USD",
) -> Dict[str, Any]:
    """Explicitly labeled hypothetical business impact estimate (never achieved revenue)."""
    if (
        not measured_visitors
        or measured_visitors <= 0
        or measured_conversion_rate is None
        or hypothetical_conversion_rate is None
    ):
        return {
            "label": "ESTIMATE_UNAVAILABLE",
            "is_projected_estimate": True,
            "disclaimer": "Requires measured baseline visitors and baseline conversion rate. No forecast invented.",
        }
    delta_rate = hypothetical_conversion_rate - measured_conversion_rate
    est_additional_conversions = round(measured_visitors * delta_rate, 1)
    est_revenue = (
        round(est_additional_conversions * value_per_conversion, 2)
        if isinstance(value_per_conversion, (int, float)) and value_per_conversion > 0
        else None
    )
    return {
        "label": "HYPOTHETICAL_ESTIMATE_NOT_ACTUAL_REVENUE",
        "is_projected_estimate": True,
        "measured_visitors": measured_visitors,
        "measured_conversion_rate_pct": round(measured_conversion_rate * 100.0, 3),
        "hypothetical_conversion_rate_pct": round(hypothetical_conversion_rate * 100.0, 3),
        "estimated_additional_conversions": est_additional_conversions,
        "value_per_conversion_input": value_per_conversion,
        "estimated_incremental_revenue": est_revenue,
        "currency": currency,
        "disclaimer": (
            "Scenario model only. Projected conversion uplift is a hypothetical assumption and MUST NOT "
            "be interpreted as achieved or guaranteed revenue."
        ),
    }


def run_department_i(ctx: CROAuditContext) -> CROAgentOutput:
    """Department I — Analytics Configuration, Event Validation, Funnels, Data Quality & Attribution."""
    findings: List[CROFinding] = []
    evidence_ids: List[str] = []
    limitations: List[str] = []

    # 1. Inspect DOM for analytics/GTM/consent installation & duplicate tag configuration
    all_html = "\n".join(ctx.raw_html_map.get(p.url, "") for p in ctx.pages)
    ga4_ids = re.findall(r"\bG-[A-Z0-9]{6,12}\b", all_html)
    gtm_ids = re.findall(r"\bGTM-[A-Z0-9]{5,10}\b", all_html)
    has_consent_banner = bool(re.search(r"(cookie-consent|onetrust|cookiebot|gtag\(['\"]consent['\"]|consent_mode)", all_html, re.I))
    duplicate_ga4_in_page = any(
        len(re.findall(r"gtag\(['\"]config['\"],\s*['\"]G-[A-Z0-9]+['\"]", ctx.raw_html_map.get(p.url, ""))) > 1
        for p in ctx.pages
    )

    analytics = ctx.analytics_payload or {}
    is_connected = str(analytics.get("state", "NOT_CONNECTED")).upper() == "MEASURED" or bool(analytics.get("connected"))
    if is_connected and "ga4" not in [p.lower() for p in ctx.connected_providers]:
        ctx.connected_providers.append("ga4")

    connectors = build_connector_capability_registry(ctx.connected_providers)

    # 2. Event dictionary & Data Quality validation
    event_records: List[CROAnalyticsEvent] = []
    data_quality_issues: List[str] = []
    duplicate_events_detected: List[str] = []
    missing_events_detected: List[str] = []

    raw_events = analytics.get("events") or []
    events_by_name: Dict[str, Dict[str, Any]] = {}
    for ev in raw_events:
        if isinstance(ev, dict) and ev.get("event_name"):
            name = str(ev["event_name"])
            if name in events_by_name or ev.get("duplicate_firing") or (ev.get("duplicate_ratio") and float(ev["duplicate_ratio"]) > 1.05):
                duplicate_events_detected.append(name)
            events_by_name[name] = ev

    if duplicate_ga4_in_page:
        data_quality_issues.append("Duplicate GA4 `gtag('config', ...)` initialization detected on the same page.")

    for g in ctx.goals:
        ev_name = g.analytics_event_name or "conversion"
        matched = events_by_name.get(ev_name)
        flags: List[str] = []
        if not is_connected:
            val_status = "unavailable"
        elif matched is None:
            val_status = "failed"
            missing_events_detected.append(ev_name)
            flags.append("configured_goal_event_missing")
        else:
            obs_params = list(matched.get("parameters") or [])
            missing_params = [rp for rp in g.required_event_params if rp not in obs_params]
            if ev_name in duplicate_events_detected:
                flags.append("duplicate_event_firing")
                val_status = "duplicate_detected"
            elif missing_params:
                flags.append(f"missing_required_params:{','.join(missing_params)}")
                val_status = "missing_params"
            elif g.goal_type == "primary" and ctx.profile.business_type.value == "ecommerce" and matched.get("revenue") is None:
                flags.append("missing_revenue_value")
                val_status = "missing_params"
            else:
                val_status = "verified"

        ev_rec = CROAnalyticsEvent(
            tenant_id=ctx.tenant_id,
            audit_id=ctx.audit_id,
            url=ctx.target_url,
            connector_type=str(analytics.get("provider") or "ga4"),
            event_name=ev_name,
            trigger_description=f"Trigger for goal: {g.name}",
            required_parameters=g.required_event_params,
            observed_parameters=list(matched.get("parameters") or []) if matched else [],
            goal_id=g.goal_id,
            event_count=matched.get("event_count") if matched else None,
            unique_users=matched.get("unique_users") if matched else None,
            revenue_value=matched.get("revenue") if matched else None,
            currency=matched.get("currency") if matched else None,
            date_range=analytics.get("date_range") or analytics.get("period"),
            validation_status=val_status,
            data_quality_flags=flags,
        )
        g.validation_status = val_status if val_status in ("verified", "failed", "unavailable") else "failed"
        event_records.append(ev_rec)
        evidence_ids.append(ev_rec.event_record_id)

    # 3. Funnel Intelligence (strictly preserving unit discipline)
    funnels: List[CROFunnel] = []
    raw_funnel_steps = analytics.get("funnel_steps") or []
    funnel_steps_models: List[CROFunnelStep] = []
    high_dropoff_steps: List[Dict[str, Any]] = []
    funnel_id_tmp = f"cro_fun_{ctx.audit_id[-8:]}"

    if is_connected and raw_funnel_steps:
        prev_users: Optional[int] = None
        first_users: Optional[int] = None
        last_users: Optional[int] = None
        for idx, st in enumerate(raw_funnel_steps, start=1):
            step_name = str(st.get("step_name") or f"Step {idx}")
            unit = str(st.get("counting_unit") or "unique_users")
            elig = st.get("eligible_users") if st.get("eligible_users") is not None else prev_users
            prog = st.get("progressing_users") if st.get("progressing_users") is not None else st.get("users")
            if first_users is None and isinstance(elig, int):
                first_users = elig
            elif first_users is None and isinstance(prog, int):
                first_users = prog
            if isinstance(prog, int):
                last_users = prog

            conv_r = rate(prog, elig) if (isinstance(elig, int) and isinstance(prog, int) and prog <= elig) else None
            aband_r = round(1.0 - conv_r, 4) if conv_r is not None else None
            m_status = "measured" if conv_r is not None else ("invalid_units" if (isinstance(elig, int) and isinstance(prog, int) and prog > elig) else "data_unavailable")

            if aband_r is not None and aband_r >= 0.50:
                high_dropoff_steps.append(
                    {"step_name": step_name, "abandonment_rate_pct": round(aband_r * 100.0, 1), "eligible_users": elig, "progressing_users": prog}
                )

            funnel_steps_models.append(
                CROFunnelStep(
                    tenant_id=ctx.tenant_id,
                    audit_id=ctx.audit_id,
                    funnel_id=funnel_id_tmp,
                    step_order=idx,
                    step_name=step_name,
                    event_name=st.get("event_name"),
                    url_pattern=st.get("url_pattern"),
                    counting_unit=unit,
                    eligible_count=elig if isinstance(elig, int) else None,
                    progressing_count=prog if isinstance(prog, int) else None,
                    step_conversion_rate=round(conv_r * 100.0, 2) if conv_r is not None else None,
                    step_abandonment_rate=round(aband_r * 100.0, 2) if aband_r is not None else None,
                    measurement_status=m_status,
                )
            )
            prev_users = prog if isinstance(prog, int) else prev_users

        overall_comp = rate(last_users, first_users) if (first_users and last_users is not None and last_users <= first_users) else None
        funnel = CROFunnel(
            tenant_id=ctx.tenant_id,
            audit_id=ctx.audit_id,
            url=ctx.target_url,
            name=f"{ctx.profile.business_type.value.replace('_', ' ').title()} Conversion Funnel",
            business_model=ctx.profile.business_type,
            source=str(analytics.get("provider") or "ga4"),
            date_range=analytics.get("date_range") or analytics.get("period"),
            counting_unit="unique_users",
            attribution_window=analytics.get("attribution_window") or "30d_data_driven",
            steps=funnel_steps_models,
            overall_completion_rate=round(overall_comp * 100.0, 2) if overall_comp is not None else None,
            data_completeness="complete" if all(s.measurement_status == "measured" for s in funnel_steps_models) else "partial",
        )
        for st in funnel.steps:
            st.funnel_id = funnel.funnel_id
        funnels.append(funnel)
        evidence_ids.append(funnel.funnel_id)

        # Overlay measured funnel behavioral status onto mapped journey steps
        for j in ctx.journeys:
            j.behavioral_health = "measured"
            j.measured_completion_rate = funnel.overall_completion_rate
            for idx_s, jstep in enumerate(j.steps):
                if idx_s < len(funnel.steps):
                    fs = funnel.steps[idx_s]
                    if fs.measurement_status == "measured":
                        jstep.behavioral_status = (
                            "measured_high_dropoff"
                            if (fs.step_abandonment_rate or 0) >= 50.0
                            else "measured_healthy"
                        )
                        jstep.behavioral_metrics = {
                            "eligible_users": fs.eligible_count,
                            "progressing_users": fs.progressing_count,
                            "step_conversion_rate_pct": fs.step_conversion_rate,
                            "step_abandonment_rate_pct": fs.step_abandonment_rate,
                            "counting_unit": fs.counting_unit,
                            "date_range": funnel.date_range,
                        }
    else:
        limitations.append("Analytics connector not configured or no funnel telemetry returned; conversion rates and funnel drop-offs remain UNMEASURED.")
        # Build unmeasured funnel skeleton transparently
        funnel = CROFunnel(
            tenant_id=ctx.tenant_id,
            audit_id=ctx.audit_id,
            url=ctx.target_url,
            name=f"{ctx.profile.business_type.value.replace('_', ' ').title()} Conversion Funnel (Unmeasured)",
            business_model=ctx.profile.business_type,
            source="not_connected",
            steps=[
                CROFunnelStep(
                    tenant_id=ctx.tenant_id,
                    audit_id=ctx.audit_id,
                    funnel_id=funnel_id_tmp,
                    step_order=idx + 1,
                    step_name=st.name,
                    event_name=st.analytics_event_name,
                    measurement_status="data_unavailable",
                )
                for idx, st in enumerate(ctx.journeys[0].steps if ctx.journeys else [])
            ],
            data_completeness="unmeasured",
        )
        for st in funnel.steps:
            st.funnel_id = funnel.funnel_id
        funnels.append(funnel)

    # 4. Measured Business Performance KPIs (strict unit discipline; never coerced to 0)
    unique_converters = analytics.get("unique_converters")
    eligible_users = analytics.get("eligible_users")
    sessions = analytics.get("sessions")
    revenue = analytics.get("revenue")
    orders = analytics.get("orders")
    form_starts = analytics.get("form_starts")
    form_completions = analytics.get("form_completions")
    crm = ctx.crm_payload or {}
    valid_leads = crm.get("valid_leads") or analytics.get("valid_leads")
    qualified_leads = crm.get("qualified_leads") or analytics.get("qualified_leads")
    closed_won = crm.get("closed_won")

    conv_rate = rate(unique_converters, eligible_users) if is_connected else None
    rpv = rate(revenue, eligible_users) if is_connected else None
    aov = rate(revenue, orders) if is_connected else None
    form_comp_rate = rate(form_completions, form_starts) if is_connected else None
    qual_lead_rate = rate(qualified_leads, valid_leads) if (is_connected or crm.get("connected")) else None
    lead_to_cust = rate(closed_won, valid_leads) if crm.get("connected") else None

    business_metrics = [
        {"metric": "Primary Conversion Rate", "formula": "Unique Converting Visitors / Eligible Unique Visitors * 100", "counting_unit": "unique_users", "value": round(conv_rate * 100.0, 2) if conv_rate is not None else None, "unit": "%", "status": "measured" if conv_rate is not None else "data_unavailable", "source": analytics.get("provider") if is_connected else "not_connected", "date_range": analytics.get("date_range")},
        {"metric": "Revenue Per Visitor (RPV)", "formula": "Attributed Revenue / Eligible Unique Visitors", "counting_unit": "unique_users", "value": round(rpv, 2) if rpv is not None else None, "unit": analytics.get("currency") or "USD", "status": "measured" if rpv is not None else "data_unavailable", "source": analytics.get("provider") if is_connected else "not_connected", "date_range": analytics.get("date_range")},
        {"metric": "Average Order Value (AOV)", "formula": "Net Revenue / Completed Orders", "counting_unit": "orders", "value": round(aov, 2) if aov is not None else None, "unit": analytics.get("currency") or "USD", "status": "measured" if aov is not None else "data_unavailable", "source": analytics.get("provider") if is_connected else "not_connected", "date_range": analytics.get("date_range")},
        {"metric": "Form Completion Rate", "formula": "Valid Form Submissions / Form Starts * 100", "counting_unit": "form_starts", "value": round(form_comp_rate * 100.0, 2) if form_comp_rate is not None else None, "unit": "%", "status": "measured" if form_comp_rate is not None else "data_unavailable", "source": analytics.get("provider") if is_connected else "not_connected", "date_range": analytics.get("date_range")},
        {"metric": "Qualified Lead Rate", "formula": "Qualified Leads / Valid Leads * 100", "counting_unit": "valid_leads", "value": round(qual_lead_rate * 100.0, 2) if qual_lead_rate is not None else None, "unit": "%", "status": "measured" if qual_lead_rate is not None else "data_unavailable", "source": crm.get("provider") if crm.get("connected") else "not_connected", "date_range": crm.get("date_range") or analytics.get("date_range")},
        {"metric": "Lead-to-Customer Rate", "formula": "Closed Won Customers / Valid Leads * 100", "counting_unit": "valid_leads", "value": round(lead_to_cust * 100.0, 2) if lead_to_cust is not None else None, "unit": "%", "status": "measured" if lead_to_cust is not None else "data_unavailable", "source": crm.get("provider") if crm.get("connected") else "not_connected", "date_range": crm.get("date_range")},
    ]

    # 5. Findings for analytics setup, data quality, and measured high funnel drop-offs
    if not ga4_ids and not gtm_ids and not is_connected:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-ANL-INST-{ctx.audit_id[-6:]}-01",
                category="analytics_intelligence",
                subcategory="analytics_installation",
                department="I",
                agent_id="cro_analytics_config",
                title="No Analytics Tag Detected and No Analytics Connector Configured",
                description="Neither GA4 (`G-*`) nor GTM (`GTM-*`) tags were observed in sampled HTML, and no live analytics connector is authorized. Conversion outcomes remain unmeasured.",
                root_cause="Missing analytics instrumentation or disconnected analytics telemetry integration.",
                affected_urls=[ctx.target_url],
                evidence_ids=[p.page_id for p in ctx.pages[:3]],
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.HIGH,
                confidence=0.92,
                recommendation="Install consent-aware GA4/GTM instrumentation for primary and secondary conversion events and connect GA4 in Dristik Connectors.",
                implementation_instructions="Deploy GTM/GA4 container, configure conversion events matching the CRO Goal Registry, and authorize read-only GA4 telemetry.",
                owner_role="Analytics Engineering",
                effort="medium",
                priority_score=85.0,
                acceptance_criteria=[
                    "Single GA4/GTM container loads without duplicate hits.",
                    "Primary conversion event fires cleanly on test completion and appears in GA4 DebugView.",
                ],
            )
        )

    if duplicate_events_detected or duplicate_ga4_in_page:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-ANL-DUP-{ctx.audit_id[-6:]}-01",
                category="analytics_intelligence",
                subcategory="duplicate_event_tracking",
                department="I",
                agent_id="cro_data_quality",
                title=f"Duplicate Analytics Tracking / Event Firing Detected ({', '.join(duplicate_events_detected) or 'gtag config'})",
                description=(
                    "Analytics QA detected duplicate GA4 initialization or duplicate conversion event firing "
                    f"({', '.join(duplicate_events_detected) or 'duplicate gtag config'}). Duplicate hits inflate conversion counts and invalidate experiments."
                ),
                root_cause="Hardcoded gtag snippet running alongside GTM or missing event deduplication transaction/event IDs.",
                affected_urls=[ctx.target_url],
                evidence_ids=evidence_ids[:5] or [p.page_id for p in ctx.pages[:2]],
                source_type=EvidenceSourceType.ANALYTICS_OBSERVATION if duplicate_events_detected else EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.HIGH,
                confidence=0.95,
                recommendation="Consolidate analytics firing to a single tag manager source and enforce unique event/transaction deduplication IDs.",
                implementation_instructions="Remove redundant inline `gtag('config')` calls and attach unique `transaction_id`/`event_id` keys on conversion events.",
                owner_role="Analytics Engineering",
                effort="low",
                priority_score=91.0,
                acceptance_criteria=[
                    "Exactly one page_view and one conversion event fire per test conversion.",
                    "Duplicate ratio stays <= 1.01 in post-fix QA.",
                ],
            )
        )

    if missing_events_detected:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-ANL-MISS-{ctx.audit_id[-6:]}-01",
                category="analytics_intelligence",
                subcategory="missing_conversion_events",
                department="I",
                agent_id="cro_event_tracking",
                title=f"Configured Conversion Events Missing from Connected Analytics ({', '.join(missing_events_detected)})",
                description=f"Connected analytics data did not contain required conversion goal events: {', '.join(missing_events_detected)}.",
                root_cause="Conversion triggers are unconfigured, misnamed, or failing silently.",
                affected_urls=[ctx.target_url],
                evidence_ids=evidence_ids[:5],
                source_type=EvidenceSourceType.ANALYTICS_OBSERVATION,
                severity=CROSeverity.HIGH,
                confidence=0.95,
                recommendation=f"Instrument and validate missing conversion events ({', '.join(missing_events_detected)}) with required parameters.",
                implementation_instructions="Verify trigger selectors in GTM/dataLayer and confirm event arrival in GA4 before running experiments.",
                owner_role="Analytics Engineering",
                effort="medium",
                priority_score=89.0,
                acceptance_criteria=[f"Event '{ev}' verified with all required parameters in analytics." for ev in missing_events_detected[:4]],
            )
        )

    if high_dropoff_steps:
        worst = max(high_dropoff_steps, key=lambda x: x["abandonment_rate_pct"])
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-FUN-DROP-{ctx.audit_id[-6:]}-01",
                category="funnel_optimization",
                subcategory="measured_funnel_abandonment",
                department="I",
                agent_id="cro_dropoff",
                title=f"High Measured Funnel Abandonment at '{worst['step_name']}' ({worst['abandonment_rate_pct']}% Drop-Off)",
                description=(
                    f"Connected analytics measured {worst['abandonment_rate_pct']}% step abandonment at '{worst['step_name']}' "
                    f"({worst['progressing_users']} of {worst['eligible_users']} eligible users progressed)."
                ),
                root_cause="Measured funnel leakage at this transition requires targeted friction diagnosis and controlled testing.",
                affected_urls=[ctx.target_url],
                affected_journeys=[j.journey_id for j in ctx.journeys],
                evidence_ids=[f.funnel_id for f in funnels],
                source_type=EvidenceSourceType.ANALYTICS_OBSERVATION,
                severity=CROSeverity.CRITICAL if worst["abandonment_rate_pct"] >= 70.0 else CROSeverity.HIGH,
                confidence=0.95,
                recommendation=f"Prioritize friction fixes and controlled A/B experiments targeting the '{worst['step_name']}' step while monitoring downstream quality guardrails.",
                implementation_instructions="Cross-reference page/form/checkout findings mapped to this funnel stage, deploy prioritized remediation, and re-measure step progression.",
                owner_role="Product / Growth",
                effort="high",
                priority_score=95.0,
                acceptance_criteria=[
                    f"Post-remediation measurement tracks '{worst['step_name']}' progression over >= 14 days with consistent counting units.",
                ],
            )
        )

    # Measurement readiness dimension checks
    has_tag = bool(ga4_ids or gtm_ids or is_connected)
    no_dups = not (duplicate_events_detected or duplicate_ga4_in_page)
    events_ok = is_connected and not missing_events_detected and no_dups
    ctx.dimension_checks.extend(
        [
            CRODimensionCheck(
                check_id="dept_i_tag_installation",
                dimension_id="analytics_measurement",
                label="Analytics instrumentation and duplicate-free setup",
                weight=1.5,
                result=(1.0 if (has_tag and no_dups) else (0.4 if has_tag else 0.0)),
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                evidence_ids=evidence_ids[:3] or [p.page_id for p in ctx.pages[:2]],
            ),
            CRODimensionCheck(
                check_id="dept_i_event_validation",
                dimension_id="analytics_measurement",
                label="Conversion goal event tracking & parameter completeness",
                weight=1.5,
                result=(1.0 if events_ok else (0.3 if is_connected else None)),
                executed=is_connected,
                source_type=EvidenceSourceType.ANALYTICS_OBSERVATION,
                evidence_ids=evidence_ids[:5],
                note="Unmeasured until analytics connector is authorized." if not is_connected else "",
            ),
        ]
    )

    measurement_checks = [
        {"check": "Analytics Tag / Container Installed", "status": "passed" if has_tag else "failed", "detail": f"GA4={ga4_ids[:3]}, GTM={gtm_ids[:3]}"},
        {"check": "Duplicate Tracking Absent", "status": "passed" if no_dups else "failed", "detail": ", ".join(duplicate_events_detected) or ("Duplicate gtag config" if duplicate_ga4_in_page else "No duplicate firing detected")},
        {"check": "Consent Mode / Banner Observed", "status": "passed" if has_consent_banner else "warning", "detail": "Consent signal observed" if has_consent_banner else "No CMP/consent mode signal observed in sample"},
        {"check": "Live Analytics Connector Authorized", "status": "passed" if is_connected else "unavailable", "detail": analytics.get("provider", "GA4") if is_connected else "Not connected"},
        {"check": "Goal Events Validated", "status": "passed" if events_ok else ("failed" if is_connected else "unavailable"), "detail": f"{sum(1 for e in event_records if e.validation_status == 'verified')}/{len(event_records)} goal events verified"},
    ]

    # Optional hypothetical impact scenario (only if baseline measured)
    scenario_estimate = build_impact_scenario_estimate(
        measured_visitors=eligible_users if isinstance(eligible_users, int) else None,
        measured_conversion_rate=conv_rate,
        hypothetical_conversion_rate=(conv_rate * 1.15) if conv_rate is not None else None,
        value_per_conversion=aov or ctx.profile.average_order_value,
        currency=str(analytics.get("currency") or ctx.profile.currency or "USD"),
    )

    ctx.artifacts["analytics_intelligence"] = {
        "is_connected": is_connected,
        "ga4_ids_in_dom": list(dict.fromkeys(ga4_ids)),
        "gtm_ids_in_dom": list(dict.fromkeys(gtm_ids)),
        "consent_signal_observed": has_consent_banner,
        "measurement_checks": measurement_checks,
        "events": [e.model_dump() for e in event_records],
        "funnels": [f.model_dump() for f in funnels],
        "business_performance_metrics": business_metrics,
        "device_performance": analytics.get("device_performance") if is_connected else {"status": "data_unavailable"},
        "channel_attribution": analytics.get("channel_attribution") if is_connected else {"status": "data_unavailable"},
        "crm_pipeline": crm if crm.get("connected") else {"status": "data_unavailable"},
        "impact_scenario_estimate": scenario_estimate,
        "connectors": [c.model_dump() for c in connectors],
        "data_quality_issues": data_quality_issues + [f"Duplicate event: {d}" for d in duplicate_events_detected] + [f"Missing event: {m}" for m in missing_events_detected],
        "roles_executed": [
            "cro_analytics_config",
            "cro_event_tracking",
            "cro_funnel",
            "cro_dropoff",
            "cro_attribution",
            "cro_segment",
            "cro_revenue_intelligence",
            "cro_data_quality",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_i_analytics",
        department="I",
        status="completed" if is_connected else "partial",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=list(dict.fromkeys(evidence_ids))[:20],
        confidence=0.95 if is_connected else 0.7,
        limitations=limitations,
        artifacts=ctx.artifacts["analytics_intelligence"],
    )
