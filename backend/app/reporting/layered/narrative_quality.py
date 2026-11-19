"""Phase 11.6: Narrative Quality Engine.

Controls AI narrative generation through strict diagnostic data grounding:
1. Structured fact extraction
2. Evidence selection
3. Finding prioritization
4. Business interpretation
5. Recommendation synthesis
6. Independent factual critic (zero-metric-invention enforcement)
7. Duplicate narrative detection
8. Contradiction checking
9. Citation validation
10. Final report validation
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.reporting.layered.models import FactItem, NarrativeQualityVerdict


class NarrativeQualityEngine:
    """Enforces empirical fact-grounding and zero-fabrication standards on generated narrative text."""

    def __init__(self, ttfb_slow_threshold_ms: float = 800.0):
        self.ttfb_slow_threshold_ms = ttfb_slow_threshold_ms

    def extract_structured_facts(self, audit_data: dict[str, Any]) -> dict[str, FactItem]:
        """Step 1: Extract verified measurements into an immutable structured fact registry."""
        facts: dict[str, FactItem] = {}

        def _add(key: str, category: str, val: Any, ev_id: str):
            if val is not None:
                facts[key] = FactItem(
                    fact_id=f"fact_{key}",
                    category=category,
                    metric_key=key,
                    metric_value=val,
                    source_evidence_id=ev_id,
                )

        _add("seo_score", "SEO", audit_data.get("seo_score"), "ev_seo_score_01")
        _add("geo_score", "GEO", audit_data.get("geo_score"), "ev_geo_score_01")
        _add("aeo_score", "AEO", audit_data.get("aeo_score"), "ev_aeo_score_01")
        _add("cro_score", "CRO", audit_data.get("cro_score"), "ev_cro_score_01")
        _add("tech_score", "TECHNICAL", audit_data.get("tech_score"), "ev_tech_score_01")
        _add("crawled_urls", "CRAWL", audit_data.get("crawled_urls", audit_data.get("pages_crawled")), "ev_crawl_urls_01")
        _add("broken_links_count", "TECHNICAL", audit_data.get("broken_links_count"), "ev_broken_links_01")
        _add("ttfb_ms", "PERFORMANCE", audit_data.get("ttfb_ms"), "ev_ttfb_01")

        return facts

    def select_evidence(self, facts: dict[str, FactItem]) -> set[str]:
        """Step 2: Map established facts to valid evidence citation IDs."""
        return {f.source_evidence_id for f in facts.values()}

    def prioritize_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Step 3: Rank findings by severity and business impact."""
        severity_weights = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25, "INFO": 10}
        return sorted(
            findings,
            key=lambda f: severity_weights.get(str(f.get("severity", "")).upper(), 0),
            reverse=True,
        )

    def generate_business_interpretation(
        self, facts: dict[str, FactItem], prioritized_findings: list[dict[str, Any]]
    ) -> str:
        """Step 4: Synthesize plain English business interpretation bounded strictly to known facts."""
        seo = facts.get("seo_score")
        geo = facts.get("geo_score")
        crit_count = sum(1 for f in prioritized_findings if str(f.get("severity", "")).upper() == "CRITICAL")

        prose = []
        if seo and geo:
            prose.append(
                f"The target domain demonstrated an SEO performance index of {seo.metric_value} "
                f"and a GEO entity index of {geo.metric_value}."
            )
        if crit_count > 0:
            prose.append(f"Audit analysis revealed {crit_count} high-priority architectural risk items.")
        else:
            prose.append("Zero critical infrastructure deficiencies were identified during scanning.")
        return " ".join(prose)

    def synthesize_recommendations(self, prioritized_findings: list[dict[str, Any]]) -> list[str]:
        """Step 5: Pair prioritized findings with actionable developer remediations."""
        recs = []
        for f in prioritized_findings[:5]:
            action = f.get("recommendation", f.get("remediation_hint"))
            if action:
                recs.append(f"[{f.get('finding_id')}] {action}")
        return recs

    def independent_factual_critic(
        self, draft_narrative: str, facts: dict[str, FactItem]
    ) -> list[str]:
        """Step 6: Scans draft narrative for numbers and metrics not grounded in the fact registry.

        Never allow the report-writing model to invent metrics to make an executive summary
        sound more compelling.
        """
        rejected: list[str] = []
        known_numeric_values: set[str] = set()

        for f in facts.values():
            val = f.metric_value
            if isinstance(val, (int, float)):
                known_numeric_values.add(str(val))
                known_numeric_values.add(f"{val:.1f}")
                known_numeric_values.add(f"{int(val)}")

        # Extract numeric tokens from narrative (e.g. 95%, 450ms, 45)
        # Exclude standard year numbers like 2026, 2025, or step numbers like 1., 2.
        tokens = re.findall(r"\b\d+(?:\.\d+)?(?:%|ms|s|MB|KB)?\b", draft_narrative)
        for t in tokens:
            raw_num = re.sub(r"[^\d.]", "", t)
            if not raw_num:
                continue
            # Allow common years and small enumeration indices
            if raw_num in {"2024", "2025", "2026", "1", "2", "3", "4", "5", "10", "12", "13", "30", "60", "90", "100"}:
                continue
            if raw_num not in known_numeric_values:
                rejected.append(f"Unsubstantiated metric '{t}' not present in diagnostic fact registry.")

        return rejected

    def detect_duplicate_narratives(self, narrative_sections: list[str]) -> list[str]:
        """Step 7: Detects duplicate or near-verbatim paragraphs across report sections."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for s in narrative_sections:
            norm = " ".join(s.strip().lower().split())
            if not norm:
                continue
            if norm in seen:
                duplicates.append(f"Duplicate narrative section detected: '{s[:60]}...'")
            else:
                seen.add(norm)
        return duplicates

    def check_contradictions(self, narrative_text: str, facts: dict[str, FactItem]) -> list[str]:
        """Step 8: Checks narrative claims against empirical facts for direct contradictions."""
        contradictions: list[str] = []
        lower_text = narrative_text.lower()

        ttfb = facts.get("ttfb_ms")
        if ttfb and isinstance(ttfb.metric_value, (int, float)) and ttfb.metric_value >= self.ttfb_slow_threshold_ms:
            if "blazing fast" in lower_text or "instantaneous server response" in lower_text or "zero latency" in lower_text:
                contradictions.append(
                    f"Contradiction: Narrative claims 'fast response' but measured TTFB is {ttfb.metric_value}ms "
                    f"(>= {self.ttfb_slow_threshold_ms}ms)."
                )

        broken = facts.get("broken_links_count")
        if broken and isinstance(broken.metric_value, int) and broken.metric_value > 0:
            if "flawless internal linking" in lower_text or "zero broken links" in lower_text:
                contradictions.append(
                    f"Contradiction: Narrative claims 'zero broken links' but {broken.metric_value} broken links were recorded."
                )

        return contradictions

    def validate_citations(
        self, draft_citations: list[str], valid_evidence_ids: set[str]
    ) -> bool:
        """Step 9: Confirms every cited evidence token resolves to a verified evidence record."""
        if not draft_citations:
            return True
        for cit in draft_citations:
            if cit not in valid_evidence_ids:
                return False
        return True

    def validate_report_narrative(
        self,
        audit_data: dict[str, Any],
        draft_narrative: str,
        narrative_sections: Optional[list[str]] = None,
        draft_citations: Optional[list[str]] = None,
    ) -> NarrativeQualityVerdict:
        """Step 10: Master validation pipeline sealing the narrative quality verdict."""
        facts = self.extract_structured_facts(audit_data)
        valid_ev = self.select_evidence(facts)

        hallucinations = self.independent_factual_critic(draft_narrative, facts)
        duplicates = self.detect_duplicate_narratives(narrative_sections or [draft_narrative])
        contradictions = self.check_contradictions(draft_narrative, facts)
        citations_valid = self.validate_citations(draft_citations or list(valid_ev), valid_ev)

        critic_passed = (
            len(hallucinations) == 0
            and len(contradictions) == 0
            and len(duplicates) == 0
            and citations_valid
        )

        return NarrativeQualityVerdict(
            facts_extracted_count=len(facts),
            evidence_citations_validated=citations_valid,
            contradictions_detected=contradictions,
            duplicate_narratives_detected=duplicates,
            hallucinated_metrics_rejected=hallucinations,
            critic_passed=critic_passed,
            final_validation_status="APPROVED" if critic_passed else "REJECTED_BY_CRITIC",
        )
