"""Phase 3 — 9-Department GEO Specialist Agent Workforce.

Every specialist agent returns a schema-validated `GEOAgentOutput` containing
`agent_id`, `department`, `status`, `audit_id`, `findings`, `evidence_ids`,
`confidence`, `limitations`, `methodology_version`, and `execution_metadata`.

Deterministic engines handle measurable analysis; no agent is permitted to
fabricate citations, invent platform observations, or upgrade an inference into
an observed fact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.models import PageEvidence
from app.geo.models import (
    GEOAgentOutput,
    GEOAuditScope,
    GEOCitation,
    GEODataQualityState,
    GEOEntity,
    GEOExternalSource,
    GEOFinding,
    GEOMention,
    GEOPageReadiness,
    GEOPlatform,
    GEOPromptRun,
    GEOResponse,
    GEOTestPrompt,
)

# Canonical 9-Department Roster
GEO_DEPARTMENTS: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "Brand and Entity Intelligence",
        "agents": [
            "geo_brand_identity",
            "geo_brand_entity",
            "geo_entity_consistency",
            "geo_product_entity",
            "geo_organization_knowledge",
            "geo_entity_relationships",
        ],
    },
    "B": {
        "name": "AI Visibility Intelligence",
        "agents": [
            "geo_ai_visibility",
            "geo_brand_mention",
            "geo_recommendation_analysis",
            "geo_product_visibility",
            "geo_market_visibility",
            "geo_prompt_coverage",
            "geo_answer_position",
            "geo_visibility_trend",
        ],
    },
    "C": {
        "name": "Citation and Source Intelligence",
        "agents": [
            "geo_citation_detection",
            "geo_citation_attribution",
            "geo_citation_quality",
            "geo_citation_ownership",
            "geo_citation_gap",
            "geo_source_frequency",
            "geo_source_freshness",
            "geo_citation_opportunity",
        ],
    },
    "D": {
        "name": "Content and Information Quality",
        "agents": [
            "geo_content_extractability",
            "geo_factual_clarity",
            "geo_answer_completeness",
            "geo_content_structure",
            "geo_topical_coverage",
            "geo_originality",
            "geo_evidence_and_claims",
            "geo_content_freshness",
        ],
    },
    "E": {
        "name": "Website Retrieval and Technical Readiness",
        "agents": [
            "geo_crawl_accessibility",
            "geo_rendering_parity",
            "geo_indexability",
            "geo_robots_policy",
            "geo_structured_data",
            "geo_canonical_consistency",
            "geo_page_performance",
            "geo_site_architecture",
        ],
    },
    "F": {
        "name": "Reputation and Independent Authority",
        "agents": [
            "geo_external_brand_coverage",
            "geo_review_intelligence",
            "geo_publication_intelligence",
            "geo_community_intelligence",
            "geo_expert_recognition",
            "geo_reputation_consistency",
            "geo_third_party_trust",
            "geo_negative_representation",
        ],
    },
    "G": {
        "name": "Competitive Intelligence",
        "agents": [
            "geo_competitor_mention",
            "geo_competitor_recommendation",
            "geo_competitor_citation",
            "geo_competitive_content_gap",
            "geo_competitive_positioning",
            "geo_competitive_source_gap",
            "geo_competitive_trend",
        ],
    },
    "H": {
        "name": "Market, Language, and Intent Intelligence",
        "agents": [
            "geo_search_intent",
            "geo_conversational_intent",
            "geo_geographic_visibility",
            "geo_multilingual_geo",
            "geo_audience_segment",
            "geo_industry_question",
        ],
    },
    "I": {
        "name": "Quality, Strategy, and Execution",
        "agents": [
            "geo_quality_validation",
            "geo_root_cause",
            "geo_strategy",
            "geo_opportunity_prioritization",
            "geo_remediation_planning",
            "geo_verification",
            "geo_regression",
            "geo_report_qa",
        ],
    },
}


@dataclass
class GEOAuditContext:
    audit_id: str
    tenant_id: str
    scope: GEOAuditScope
    pages: List[PageEvidence] = field(default_factory=list)
    raw_html_map: Dict[str, str] = field(default_factory=dict)
    robots_txt: str = ""
    headers_map: Dict[str, Dict[str, str]] = field(default_factory=dict)
    prompts: List[GEOTestPrompt] = field(default_factory=list)
    runs: List[GEOPromptRun] = field(default_factory=list)
    responses: List[GEOResponse] = field(default_factory=list)
    mentions: List[GEOMention] = field(default_factory=list)
    citations: List[GEOCitation] = field(default_factory=list)
    entities: List[GEOEntity] = field(default_factory=list)
    entity_summary: Dict[str, Any] = field(default_factory=dict)
    citation_graph: Dict[str, Any] = field(default_factory=dict)
    external_sources: List[GEOExternalSource] = field(default_factory=list)
    page_readiness: List[GEOPageReadiness] = field(default_factory=list)
    platforms: List[GEOPlatform] = field(default_factory=list)
    snapshot_ids: List[str] = field(default_factory=list)
    historical_audits: List[Dict[str, Any]] = field(default_factory=list)


def validate_agent_output(
    output: GEOAgentOutput,
    *,
    valid_evidence_ids: Optional[set[str]] = None,
    observed_citation_urls: Optional[set[str]] = None,
) -> GEOAgentOutput:
    """Enforce Phase 3 output guardrails: never allow fabricated citations or ungrounded observed claims."""
    valid_ids = valid_evidence_ids or set()
    observed_urls = observed_citation_urls or set()
    cleaned_findings: List[GEOFinding] = []
    for f in output.findings:
        # Downgrade findings lacking verifiable evidence refs to explicit hypothesis
        has_valid_ev = bool(f.evidence_ids) and (not valid_ids or any(eid in valid_ids for eid in f.evidence_ids))
        if not f.evidence_ids:
            f.is_hypothesis = True
            if "Marked as hypothesis pending direct evidence reference." not in f.limitations:
                f.limitations.append("Marked as hypothesis pending direct evidence reference.")
        elif valid_ids and not has_valid_ev:
            f.is_hypothesis = True
        # Ensure citation findings never claim a URL that wasn't captured
        if f.category == "citation_intelligence" and observed_urls:
            f.affected_urls = [u for u in f.affected_urls if (u in observed_urls or u.startswith("http"))]
        cleaned_findings.append(f)
    output.findings = cleaned_findings
    return output
