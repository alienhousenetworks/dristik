"""
Visual UX and CRO notes from a real crawl and visual inspection engine.

Viewport coordinates, contrast ratios, and analytics rates are omitted
until a render, DOM evidence, or a connector query actually produces them.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.domain.models import (
    VisualUxInspectionReport,
    ViewportInspection,
    CroEvidenceDissection,
    Finding,
)
from app.domain.enums import Category, Severity, EvidenceClass
from app.cro.visual_inspector import VisualInspector, VIEWPORT_PROFILES, VIEWPORT_DISCLOSURE


class VisualUxTester:
    def inspect_website_visual_ux(
        self,
        domain: str,
        website_url: str,
        dom_evidence: Optional[Dict[str, Any]] = None,
        pages_metadata: Optional[List[Dict[str, Any]]] = None,
        analytics_connected: bool = False,
    ) -> VisualUxInspectionReport:
        if not dom_evidence and not pages_metadata:
            return VisualUxInspectionReport(
                inspected_at=datetime.now(timezone.utc).isoformat(),
                tested_devices=[],
                viewports={},
                overall_visual_ux_score=None,
                critical_visual_defects=[],
                combined_intelligence={
                    "status": "not_measured",
                    "reason": "No desktop, tablet, or mobile render was captured for this audit.",
                    "website_url": website_url,
                    "domain": domain,
                },
            )

        # Inspect using VisualInspector
        raw_html = ""
        if dom_evidence:
            raw_html = dom_evidence.get("html") or dom_evidence.get("raw_html") or ""
        if not raw_html and pages_metadata:
            raw_html = pages_metadata[0].get("raw_html") or pages_metadata[0].get("html") or ""

        now_iso = datetime.now(timezone.utc).isoformat()
        res = VisualInspector.inspect(
            url=website_url or f"https://{domain}",
            html=raw_html,
            inspected_at=now_iso,
        )

        viewports_dict: Dict[str, ViewportInspection] = {}
        for vp_name, vp_state in res.viewports.items():
            viewports_dict[vp_name] = ViewportInspection(
                device=vp_state.device_type,
                width=vp_state.width,
                height=vp_state.height,
                above_the_fold={
                    "height": vp_state.above_the_fold_height,
                    "cta_count": vp_state.above_fold_cta_count,
                    "sticky_cta": vp_state.sticky_cta_detected,
                    "navigation_state": vp_state.navigation_state,
                },
                detected_defects=[d.get("defect", str(d)) if isinstance(d, dict) else str(d) for d in vp_state.defects],
                screenshot_url=None,
                dom_anchors=vp_state.sticky_cta_texts,
            )

        return VisualUxInspectionReport(
            inspected_at=now_iso,
            tested_devices=res.device_configurations,
            viewports=viewports_dict,
            overall_visual_ux_score=res.overall_visual_ux_score,
            critical_visual_defects=res.critical_visual_defects,
            combined_intelligence={
                "status": "measured",
                "website_url": website_url,
                "domain": domain,
                "sticky_ctas": res.sticky_ctas,
                "detected_modals": res.detected_modals,
                "page_type": res.page_type,
                "disclosure": VIEWPORT_DISCLOSURE,
            },
        )

    def generate_grounded_cro_finding(
        self,
        domain: str,
        website_url: str,
        analytics_connected: bool = False,
        pages: Optional[List[Any]] = None,
    ) -> Optional[Finding]:
        """State only CTA labels and pricing URLs present on crawled pages."""
        ctas: List[str] = []
        pricing_urls: List[str] = []
        for page in pages or []:
            for cta in getattr(page, "ctas", None) or []:
                text = str(cta).strip()
                if text and text not in ctas:
                    ctas.append(text)
            url = str(getattr(page, "url", "") or "")
            page_type = str(getattr(page, "page_type", "") or "")
            if url and (page_type == "pricing" or "pricing" in url.lower() or "/plans" in url.lower()):
                if url not in pricing_urls:
                    pricing_urls.append(url)

        if not pages:
            return None

        facts = [f"CTAs observed on crawled pages: {', '.join(ctas[:8])}"] if ctas else [
            "No CTA strings were extracted from the crawled pages."
        ]
        if pricing_urls:
            facts.append(f"Pricing URL in the crawl: {pricing_urls[0]}")
        else:
            facts.append("No pricing or plans URL was in this crawl.")

        dissection = CroEvidenceDissection(
            observed_facts=facts,
            inferred_impact="",
            requires_analytics={
                "actual_abandonment_rate": "UNKNOWN",
                "cta_conversion_rate": "UNKNOWN",
                "form_completion_rate": "UNKNOWN",
            },
            analytics_connected=False,
            grounded_metrics=None,
        )
        return Finding(
            finding_id="find_cro_001",
            title="Conversion signals from the crawl",
            description=" ".join(facts),
            category=Category.UX_CONVERSION,
            severity=Severity.INFO if hasattr(Severity, "INFO") else Severity.LOW,
            impact=1,
            effort=1,
            priority=1,
            recommendation="Abandonment and form completion stay blank until GA4 or a CRM returns them.",
            why_it_matters="These lines are the CTA and pricing URLs from the crawl. They are not a viewport test and not a conversion rate.",
            evidence_class=EvidenceClass.OBSERVED,
            evidence_subtype="DOM",
            epistemic_level="Crawl text only",
            cro_dissection=dissection,
        )


visual_ux_tester = VisualUxTester()
