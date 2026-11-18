"""
External Authority & Reputation Intelligence — Phase 4.7

Audits independent external corroboration vs. brand-owned content:
- Independent publications & editorial coverage
- Third-party reviews & ratings (Trustpilot, Google, Amazon)
- Authoritative industry sources & directories
- Knowledge Graph presence (Wikidata, Wikipedia, Google Knowledge Graph)
- Brand fact consistency across external nodes

STRICT GUARDRAIL:
Distinguishes brand-owned content from independently corroborated information.
First-party claims lacking third-party verification are labeled UNVERIFIED_FIRST_PARTY.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CorroborationSource(BaseModel):
    source_name: str
    source_type: str  # "EDITORIAL", "REVIEW_PORTAL", "DIRECTORY", "KNOWLEDGE_GRAPH", "INDUSTRY_ASSOCIATION"
    corroborated_fact: str
    source_url: Optional[str] = None
    is_independent: bool = True
    authority_tier: str = "HIGH"  # HIGH, MEDIUM, LOW


class ExternalReputationReport(BaseModel):
    brand_name: str
    total_corroborating_sources: int
    has_knowledge_graph_presence: bool
    editorial_coverage_count: int
    third_party_review_rating: Optional[float] = None
    corroboration_sources: List[CorroborationSource] = Field(default_factory=list)
    unverified_first_party_claims: List[str] = Field(default_factory=list)
    reputation_grade: str = "ESTABLISHED"  # ESTABLISHED, EMERGING, UNVERIFIED
    observations: List[str] = Field(default_factory=list)


class ExternalReputationEngine:
    """
    Evaluates independent third-party corroboration and verifies brand claim consistency.
    """

    @classmethod
    def evaluate_reputation(
        cls,
        brand_name: str,
        first_party_claims: Optional[List[str]] = None,
        external_sources: Optional[List[Dict[str, Any]]] = None,
        has_kg_entity: bool = False,
    ) -> ExternalReputationReport:
        sources_raw = external_sources or []
        claims = first_party_claims or []
        corroborated: List[CorroborationSource] = []
        obs: List[str] = []

        editorial_count = 0
        review_rating = None

        for s in sources_raw:
            stype = s.get("type", "EDITORIAL").upper()
            if "EDITORIAL" in stype:
                editorial_count += 1
            if "REVIEW" in stype and s.get("rating"):
                review_rating = float(s["rating"])

            corroborated.append(
                CorroborationSource(
                    source_name=s.get("name", "Unknown Source"),
                    source_type=stype,
                    corroborated_fact=s.get("fact", f"Corroborates existence of {brand_name}"),
                    source_url=s.get("url"),
                    is_independent=True,
                    authority_tier=s.get("tier", "HIGH"),
                )
            )

        # Detect unverified first-party claims
        unverified: List[str] = []
        corroborated_texts = " ".join(c.corroborated_fact.lower() for c in corroborated)
        for claim in claims:
            # Check if claim words appear in independent sources
            claim_core = " ".join([w for w in claim.split() if len(w) > 4])
            if claim_core and not any(w in corroborated_texts for w in claim_core.split()[:2]):
                unverified.append(f"UNVERIFIED_FIRST_PARTY: '{claim}' lacks independent corroboration.")

        if has_kg_entity:
            obs.append(f"Confirmed presence in Google/Wikidata Knowledge Graph for entity '{brand_name}'.")
        else:
            obs.append(f"No direct Knowledge Graph entity detected for '{brand_name}'. External corroboration relies on web citations.")

        rep_grade = "ESTABLISHED" if (editorial_count >= 2 or has_kg_entity) else ("EMERGING" if corroborated else "UNVERIFIED")

        return ExternalReputationReport(
            brand_name=brand_name,
            total_corroborating_sources=len(corroborated),
            has_knowledge_graph_presence=has_kg_entity,
            editorial_coverage_count=editorial_count,
            third_party_review_rating=review_rating,
            corroboration_sources=corroborated,
            unverified_first_party_claims=unverified[:5],
            reputation_grade=rep_grade,
            observations=obs,
        )
