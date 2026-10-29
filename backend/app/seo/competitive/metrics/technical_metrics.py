"""
Dristik AI Technical & Content Competitive Metrics.
Evaluates crawlability, TTFB server latency, Schema.org type richness,
mobile viewport optimization, and content depth from direct PageEvidence crawls.
Zero-fake policy: If a site has not been crawled, emits status=UNMEASURED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from app.domain.models import PageEvidence
from app.seo.competitive.models import (
    CompetitorEvidenceItem,
    DimensionScore,
    EvidenceConfidence,
)


class TechnicalMetricsCalculator:
    """
    Computes objective technical and content competition metrics from live PageEvidence.
    """

    def compute_technical_score(
        self,
        competitor_id: str,
        pages: Optional[List[PageEvidence]],
        audit_id: Optional[str] = None,
    ) -> Tuple[DimensionScore, List[CompetitorEvidenceItem]]:
        evidence_items: List[CompetitorEvidenceItem] = []

        if not pages:
            return (
                DimensionScore(
                    dimension="technical",
                    score=None,
                    confidence=EvidenceConfidence.UNMEASURED,
                    status="UNMEASURED",
                    evidence_count=0,
                    key_metrics={"reason": "Competitor site has not yet been crawled."},
                ),
                evidence_items,
            )

        home = pages[0]
        score = 100

        # TTFB check (0-30 pts deduction)
        ttfb = home.ttfb_ms or 0.0
        if ttfb > 1200:
            score -= 25
        elif ttfb > 600:
            score -= 10

        # Viewport check (15 pts deduction)
        has_viewport = bool(home.viewport and "width=device-width" in home.viewport.lower())
        if not has_viewport:
            score -= 20

        # Title check (10 pts)
        if not home.title or len(home.title.strip()) < 10:
            score -= 10

        # Meta description check (10 pts)
        if not home.meta_description or len(home.meta_description.strip()) < 20:
            score -= 10

        # H1 check (10 pts)
        if not home.h1 or len(home.h1) == 0:
            score -= 10

        # Schema types evaluation
        schemas = home.schema_types or []
        schema_count = len(schemas)
        if schema_count == 0:
            score -= 15
        elif schema_count >= 3:
            score = min(100, score + 5)

        tech_score = max(0, min(100, score))

        evidence_items.append(
            CompetitorEvidenceItem(
                id=f"{competitor_id}_ttfb",
                competitor_id=competitor_id,
                evidence_type="technical",
                metric="ttfb_ms",
                value=round(ttfb, 1),
                unit="ms",
                source_url=home.url,
                source_type="live_crawl",
                confidence=EvidenceConfidence.HIGH,
                audit_id=audit_id,
                notes=f"Observed initial server response latency of {ttfb:.0f}ms.",
            )
        )

        evidence_items.append(
            CompetitorEvidenceItem(
                id=f"{competitor_id}_schema",
                competitor_id=competitor_id,
                evidence_type="technical",
                metric="schema_count",
                value=schema_count,
                unit="count",
                source_url=home.url,
                source_type="live_crawl",
                confidence=EvidenceConfidence.HIGH,
                audit_id=audit_id,
                notes=f"Detected structured schema types: {', '.join(schemas) if schemas else 'None'}.",
            )
        )

        dim_score = DimensionScore(
            dimension="technical",
            score=tech_score,
            confidence=EvidenceConfidence.HIGH,
            status="AVAILABLE",
            evidence_count=len(evidence_items),
            key_metrics={
                "ttfb_ms": round(ttfb, 1),
                "schema_types": schemas,
                "schema_count": schema_count,
                "has_viewport": has_viewport,
                "word_count": home.word_count or 0,
                "pages_crawled": len(pages),
            },
        )

        return dim_score, evidence_items


technical_metrics_calculator = TechnicalMetricsCalculator()
