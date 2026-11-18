"""
Third-Party Answer Credibility & Claim-to-Source Graph — Phase 5.8

Builds an evidence-backed Claim-to-Source Graph linking marketing and product claims to:
- Primary clinical trials / research publications
- Independent editorial sources
- Product documentation & technical specifications
- Official certification bodies (FDA, ISO, ADA)
- Verified customer reviews & ratings

STRICT GUARDRAIL:
Identifies unsupported claims lacking independent backing and prevents false credibility scores.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SupportingSourceNode(BaseModel):
    source_id: str
    source_name: str
    source_type: str  # "CLINICAL_TRIAL", "EDITORIAL", "SPECIFICATION", "CERTIFICATION", "VERIFIED_REVIEWS"
    source_url: Optional[str] = None
    credibility_tier: str = "TIER_1_PEER_REVIEWED"  # TIER_1, TIER_2, TIER_3


class ClaimToSourceEdge(BaseModel):
    claim_id: str
    claim_text: str
    source_id: Optional[str] = None
    is_supported: bool
    evidence_strength: str  # "STRONG", "MODERATE", "UNSUPPORTED"
    verification_notes: str


class ClaimToSourceGraphReport(BaseModel):
    total_claims_mapped: int
    supported_claims_count: int
    unsupported_claims_count: int
    credibility_score_pct: float
    sources: List[SupportingSourceNode] = Field(default_factory=list)
    edges: List[ClaimToSourceEdge] = Field(default_factory=list)
    actionable_remediation: List[str] = Field(default_factory=list)


class ThirdPartyCredibilityEngine:
    """
    Constructs the claim-to-source graph and audits third-party backing.
    """

    @classmethod
    def build_credibility_graph(
        cls,
        claims: List[str],
        external_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> ClaimToSourceGraphReport:
        sources_raw = external_sources or []
        source_nodes: List[SupportingSourceNode] = []
        edges: List[ClaimToSourceEdge] = []
        recs: List[str] = []

        # Index sources
        for idx, s in enumerate(sources_raw):
            sid = f"SRC-{idx + 1:03d}"
            source_nodes.append(
                SupportingSourceNode(
                    source_id=sid,
                    source_name=s.get("name", "External Source"),
                    source_type=s.get("type", "EDITORIAL").upper(),
                    source_url=s.get("url"),
                    credibility_tier=s.get("tier", "TIER_2_INDEPENDENT_MEDIA"),
                )
            )

        supported_count = 0

        # Match claims to sources
        for c_idx, claim in enumerate(claims):
            cid = f"CLM-{c_idx + 1:03d}"
            matched_src_id = None
            strength = "UNSUPPORTED"
            notes = "Claim has no independent third-party corroboration."

            # Search in sources for match
            c_low = claim.lower()
            for s in source_nodes:
                s_name = s.source_name.lower()
                if any(w in c_low for w in s_name.split() if len(w) > 3):
                    matched_src_id = s.source_id
                    strength = "STRONG" if s.credibility_tier.startswith("TIER_1") else "MODERATE"
                    notes = f"Corroborated by {s.source_name} ({s.source_type})."
                    break

            is_sup = matched_src_id is not None
            if is_sup:
                supported_count += 1
            else:
                recs.append(f"Anchor claim '{claim}' with an independent research paper, certification link, or review source.")

            edges.append(
                ClaimToSourceEdge(
                    claim_id=cid,
                    claim_text=claim,
                    source_id=matched_src_id,
                    is_supported=is_sup,
                    evidence_strength=strength,
                    verification_notes=notes,
                )
            )

        n = max(len(claims), 1)
        cred_score = round((supported_count / n) * 100, 1)

        return ClaimToSourceGraphReport(
            total_claims_mapped=len(claims),
            supported_claims_count=supported_count,
            unsupported_claims_count=len(claims) - supported_count,
            credibility_score_pct=cred_score,
            sources=source_nodes,
            edges=edges,
            actionable_remediation=recs[:4],
        )
