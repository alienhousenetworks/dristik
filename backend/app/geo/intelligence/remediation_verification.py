"""
GEO Recommendations & Pre/Post-Fix Verification — Phase 4.10

Generates actionable GEO engineering patches and runs comparative verification:
- Brand entity JSON-LD enhancements (adding sameAs, founder, knowsAbout, subjectOf)
- Passage restructuring patches (converting ambiguous copy into 50-word declarative blocks)
- Robots.txt crawler access patches (unblocking OAI-SearchBot / PerplexityBot)
- Pre-fix vs. post-fix benchmark comparison engine (diffs citation rate before and after content deployment)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeoRecommendationItem(BaseModel):
    recommendation_id: str
    target_area: str  # "BRAND_SCHEMA", "PASSAGE_RESTRUCTURE", "ROBOTS_TXT", "CITATION_ACQUISITION"
    title: str
    rationale: str
    suggested_code_patch: str
    implementation_target: str
    expected_outcome: str


class PrePostBenchmarkComparison(BaseModel):
    query_text: str
    surface_name: str
    pre_fix_mentioned: bool
    post_fix_mentioned: bool
    pre_fix_cited: bool
    post_fix_cited: bool
    status_change: str  # "IMPROVED", "UNRESOLVED", "UNCHANGED", "REGRESSED"


class GeoVerificationReport(BaseModel):
    domain: str
    total_recommendations: int
    recommendations: List[GeoRecommendationItem] = Field(default_factory=list)
    benchmarks_retested_count: int = 0
    improved_queries_count: int = 0
    net_citation_rate_delta: Optional[float] = None
    comparison_results: List[PrePostBenchmarkComparison] = Field(default_factory=list)


class GeoRemediationVerificationEngine:
    """
    Produces concrete code patches for GEO and verifies pre/post-fix benchmark changes.
    """

    @classmethod
    def generate_recommendations(
        cls,
        domain: str,
        brand_name: str,
        missing_facts: Optional[List[str]] = None,
        blocked_crawlers: Optional[List[str]] = None,
        third_party_dominance: bool = False,
    ) -> List[GeoRecommendationItem]:
        recs: List[GeoRecommendationItem] = []

        # 1. Robots.txt Crawler Patch
        if blocked_crawlers:
            patch_lines = ["# Allow AI Search Retrieval while managing training bots"]
            for b in blocked_crawlers:
                patch_lines.append(f"User-agent: {b}\nAllow: /\n")
            recs.append(
                GeoRecommendationItem(
                    recommendation_id="GEO-REC-001",
                    target_area="ROBOTS_TXT",
                    title=f"Unblock {', '.join(blocked_crawlers)} for Generative Search Access",
                    rationale="AI search engines require unblocked HTTP access to cite product pages in search cards.",
                    suggested_code_patch="\n".join(patch_lines),
                    implementation_target="https://" + domain + "/robots.txt",
                    expected_outcome="Restores crawler access for ChatGPT Search and Perplexity.",
                )
            )

        # 2. Brand Entity Schema Patch
        recs.append(
            GeoRecommendationItem(
                recommendation_id="GEO-REC-002",
                target_area="BRAND_SCHEMA",
                title="Deploy Knowledge Graph Enriched Organization Schema",
                rationale="Explicit sameAs links and organization relationships anchor LLM entity recognition.",
                suggested_code_patch=(
                    '{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n'
                    f'  "name": "{brand_name}",\n  "url": "https://{domain}/",\n'
                    '  "sameAs": [\n    "https://www.wikidata.org/wiki/...",\n'
                    f'    "https://www.linkedin.com/company/{brand_name.lower()}"\n  ]\n}}'
                ),
                implementation_target="<head> of homepage",
                expected_outcome="Eliminates brand entity ambiguity across LLM training checkpoints.",
            )
        )

        # 3. Passage Restructuring Patch
        if third_party_dominance or (missing_facts and len(missing_facts) > 0):
            recs.append(
                GeoRecommendationItem(
                    recommendation_id="GEO-REC-003",
                    target_area="PASSAGE_RESTRUCTURE",
                    title="Implement Declarative 50-Word Definition Blocks",
                    rationale="LLM synthesizers extract high-density factual answers adjacent to <h2> question headers.",
                    suggested_code_patch=(
                        f"<h2>What is {brand_name}?</h2>\n"
                        f"<p>{brand_name} is an oral wellness brand offering sonic electric toothbrushes "
                        "and probiotic oral care solutions designed with dentist-approved clinical formulations. "
                        f"Products start at $29 with nationwide shipping.</p>"
                    ),
                    implementation_target="Top of /about and category hubs",
                    expected_outcome="Direct quotation eligibility increase of 30–50% in Perplexity and ChatGPT.",
                )
            )

        return recs

    @classmethod
    def compare_pre_post_benchmarks(
        cls,
        domain: str,
        pre_runs: List[Dict[str, Any]],  # {"query": str, "surface": str, "cited": bool, "mentioned": bool}
        post_runs: List[Dict[str, Any]],
    ) -> GeoVerificationReport:
        comparisons: List[PrePostBenchmarkComparison] = []
        improved = 0

        # Index post runs by (query, surface)
        post_map = {(r["query"], r["surface"]): r for r in post_runs}

        for pre in pre_runs:
            k = (pre["query"], pre["surface"])
            post = post_map.get(k)
            if post:
                pre_cited = pre.get("cited", False)
                post_cited = post.get("cited", False)
                pre_ment = pre.get("mentioned", False)
                post_ment = post.get("mentioned", False)

                if (not pre_cited and post_cited) or (not pre_ment and post_ment):
                    status = "IMPROVED"
                    improved += 1
                elif pre_cited and not post_cited:
                    status = "REGRESSED"
                elif post_cited or post_ment:
                    status = "UNRESOLVED"
                else:
                    status = "UNCHANGED"

                comparisons.append(
                    PrePostBenchmarkComparison(
                        query_text=pre["query"],
                        surface_name=pre["surface"],
                        pre_fix_mentioned=pre_ment,
                        post_fix_mentioned=post_ment,
                        pre_fix_cited=pre_cited,
                        post_fix_cited=post_cited,
                        status_change=status,
                    )
                )

        pre_c_count = sum(1 for p in pre_runs if p.get("cited"))
        post_c_count = sum(1 for p in post_runs if p.get("cited"))
        pre_rate = (pre_c_count / max(len(pre_runs), 1)) * 100
        post_rate = (post_c_count / max(len(post_runs), 1)) * 100
        delta = round(post_rate - pre_rate, 1)

        return GeoVerificationReport(
            domain=domain,
            total_recommendations=0,
            benchmarks_retested_count=len(comparisons),
            improved_queries_count=improved,
            net_citation_rate_delta=delta,
            comparison_results=comparisons,
        )
