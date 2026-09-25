"""
Dristik AI Competitive Intelligence Engine
Performs evidence-grounded comparative benchmarking against specified competitors.
Compares positioning, schema presence, pricing transparency, and AI answer readiness.
Never hallucinates competitor facts without evidence.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.models import BusinessProfile, PageEvidence

class CompetitorBenchmark(BaseModel):
    competitor_name: str
    relative_positioning: str  # Stronger, Parity, Weaker, Unmeasured
    pricing_transparency: str  # High, Medium, Low, Opaque, Unmeasured
    schema_coverage: str      # Advanced, Basic, None, Unmeasured
    citation_readiness: Optional[float] = None
    key_advantages: List[str] = Field(default_factory=list)
    key_vulnerabilities: List[str] = Field(default_factory=list)

class CompetitiveAnalysisResult(BaseModel):
    target_domain: str
    benchmarks: List[CompetitorBenchmark] = Field(default_factory=list)
    summary: str

class CompetitiveIntelligenceEngine:
    """
    Benchmarks target website against user-specified or discovered competitors.
    Uncrawled rivals stay Unmeasured — no invented scores or market size.
    """

    def analyze_competitive_landscape(
        self,
        business_profile: BusinessProfile,
        competitors: List[str],
        target_pages: List[PageEvidence]
    ) -> CompetitiveAnalysisResult:
        benchmarks: List[CompetitorBenchmark] = []
        niche = business_profile.niche or business_profile.industry or "this category"

        for comp in competitors[:3]:
            benchmarks.append(CompetitorBenchmark(
                competitor_name=comp,
                relative_positioning="Unmeasured",
                pricing_transparency="Unmeasured",
                schema_coverage="Unmeasured",
                citation_readiness=None,
                key_advantages=[
                    f"{comp} was named as a rival but was not crawled in this run, so advantages are unknown."
                ],
                key_vulnerabilities=[
                    "Crawl this rival (or run a bake-off URL) before claiming a gap. No TAM or citation rate was invented."
                ]
            ))

        if competitors:
            summary = (
                f"{business_profile.business_name} was compared by name to {len(competitors)} listed rival(s) in {niche}. "
                f"Those rival sites were not crawled here, so positioning/schema/citation fields stay Unmeasured. "
                f"Market size was not measured."
            )
        else:
            summary = (
                f"No rival URLs were supplied for {business_profile.business_name}. "
                f"Competitive fields stay empty rather than inventing Cloudflare/HubSpot/Salesforce or a TAM."
            )

        return CompetitiveAnalysisResult(
            target_domain=business_profile.business_name,
            benchmarks=benchmarks,
            summary=summary
        )
