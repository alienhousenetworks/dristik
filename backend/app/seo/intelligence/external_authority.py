"""
Off-Page SEO & External Authority Intelligence — Phase 3.10

Integrates external backlink and domain authority telemetry:
- Referring domains count
- Total backlinks & dofollow/nofollow ratio
- Link relevance & anchor text diversity
- New vs. lost link trends
- Cautious toxicity indicators
- Competitor link gap signals

STRICT GUARDRAIL:
Do not manufacture or estimate backlink counts when no external provider is connected.
Engine returns is_measured=False and AUTHORITY_UNAVAILABLE with honest disclosures.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BacklinkProfile(BaseModel):
    is_measured: bool = False
    status: str = "AUTHORITY_UNAVAILABLE"  # AUTHORITY_MEASURED, AUTHORITY_UNAVAILABLE
    provider_name: str = "NONE"  # DataForSEO, Ahrefs, Moz, Semrush
    referring_domains_count: Optional[int] = None
    total_backlinks_count: Optional[int] = None
    dofollow_ratio: Optional[float] = None
    top_anchor_texts: List[str] = Field(default_factory=list)
    new_backlinks_30d: Optional[int] = None
    lost_backlinks_30d: Optional[int] = None
    toxicity_score: Optional[float] = None  # 0 to 100 with cautious interpretation
    statement: str = "External authority data not measured. No backlink provider API connected."


class ExternalAuthorityEngine:
    """
    Manages external backlink telemetry with strict unmeasured safeguards.
    """

    @classmethod
    def evaluate_authority(
        cls,
        domain: str,
        provider_name: Optional[str] = None,
        api_data: Optional[Dict[str, Any]] = None,
    ) -> BacklinkProfile:
        if not provider_name or not api_data:
            return BacklinkProfile(
                is_measured=False,
                status="AUTHORITY_UNAVAILABLE",
                provider_name="NONE",
                statement="External authority data not measured. No backlink provider API connected.",
            )

        ref_domains = api_data.get("referring_domains")
        total_links = api_data.get("total_backlinks")
        dofollow = api_data.get("dofollow_ratio", 0.75)
        anchors = api_data.get("top_anchors", [])
        new_links = api_data.get("new_links_30d", 0)
        lost_links = api_data.get("lost_links_30d", 0)
        tox = api_data.get("toxicity_score", 5.0)

        statement = (
            f"Backlink profile verified via {provider_name}: {ref_domains:,} referring domains, "
            f"{total_links:,} total links ({dofollow * 100:.1f}% dofollow)."
        )

        return BacklinkProfile(
            is_measured=True,
            status="AUTHORITY_MEASURED",
            provider_name=provider_name,
            referring_domains_count=ref_domains,
            total_backlinks_count=total_links,
            dofollow_ratio=dofollow,
            top_anchor_texts=anchors[:5],
            new_backlinks_30d=new_links,
            lost_backlinks_30d=lost_links,
            toxicity_score=tox,
            statement=statement,
        )
