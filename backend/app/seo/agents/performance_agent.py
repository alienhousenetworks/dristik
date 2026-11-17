"""
Performance & Core Web Vitals Agent:
Evaluates server response speed (TTFB), client rendering performance,
DOM complexity, and Lighthouse Core Web Vitals readiness.
"""
from typing import Dict, Any, List
from app.orchestration.runtime.base_agent import BaseAgent
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, ClaimType
from app.domain.models import Finding, FindingEvidence


class PerformanceAgent(BaseAgent):
    """Audits page delivery performance, TTFB, and Core Web Vitals metrics."""
    def __init__(self, model_router=None):
        super().__init__(
            agent_id="seo.performance.v3",
            capability="performance",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        from app.crawl.crawler import compute_ttfb_stats

        manifest = getattr(blackboard, "crawl_manifest", None)
        pages = (
            list(manifest.pages)
            if manifest and getattr(manifest, "pages", None)
            else list(getattr(blackboard, "pages", []) or [])
        )
        ttfb_stats = (
            getattr(manifest, "ttfb_stats", None)
            if manifest and getattr(manifest, "ttfb_stats", None)
            else compute_ttfb_stats(pages)
        )
        slow_pages = [p for p in pages if getattr(p, "ttfb_ms", 0.0) > 800.0]
        slow_ttfb_count = len(slow_pages)
        slow_urls = [p.url for p in slow_pages if getattr(p, "url", None)]

        observations = {
            "total_pages": len(pages),
            "slow_ttfb_count": slow_ttfb_count,
            "mean_ttfb_ms": ttfb_stats.mean_ms,
            "median_ttfb_ms": ttfb_stats.median_ms,
            "max_ttfb_ms": ttfb_stats.max_ms,
            "min_ttfb_ms": ttfb_stats.min_ms,
            "p90_ttfb_ms": ttfb_stats.p90_ms,
            "outlier_urls": list(ttfb_stats.outlier_urls),
            "outlier_explanation": ttfb_stats.outlier_explanation,
        }

        claims = []
        findings: List[Finding] = []
        if slow_ttfb_count > 0:
            ev_list: List[FindingEvidence] = []
            ev_refs: List[str] = []
            ev_store = getattr(blackboard, "evidence_store", None)
            for idx, p in enumerate(slow_pages):
                ev_id = f"ev_perf_ttfb_{idx + 1}"
                if ev_store is not None and hasattr(ev_store, "add_evidence"):
                    stored = ev_store.add_evidence(
                        source_type="performance",
                        analyzer=self.agent_id,
                        url=p.url,
                        text=f"Measured TTFB of {p.ttfb_ms:.1f} ms on {p.url} (median across sample: {ttfb_stats.median_ms:.1f} ms).",
                        value={"ttfb_ms": p.ttfb_ms, "median_ttfb_ms": ttfb_stats.median_ms},
                    )
                    ev_id = getattr(stored, "id", None) or getattr(stored, "evidence_id", ev_id)
                ev_refs.append(ev_id)
                ev_list.append(
                    FindingEvidence(
                        evidence_id=ev_id,
                        url=p.url,
                        element="HTTP Response Timing (TTFB)",
                        value=f"{p.ttfb_ms:.1f} ms",
                        observed_value=p.ttfb_ms,
                        expected_condition="TTFB <= 800 ms",
                        snippet=f"TTFB {p.ttfb_ms:.1f} ms recorded on {p.url}",
                        source=self.agent_id,
                    )
                )

            is_isolated_outlier = bool(ttfb_stats.outlier_urls) and ttfb_stats.median_ms <= 800.0
            if is_isolated_outlier:
                statement = (
                    f"Isolated TTFB Outlier on {len(ttfb_stats.outlier_urls)} Sampled URL(s) "
                    f"(Median TTFB {ttfb_stats.median_ms:g} ms vs Max {ttfb_stats.max_ms:g} ms)"
                )
                description = ttfb_stats.outlier_explanation or statement
                sev = Severity.MEDIUM
                recommendation = (
                    f"Investigate the isolated slow response on {', '.join(ttfb_stats.outlier_urls)} "
                    f"({ttfb_stats.max_ms:g} ms) while noting that median site TTFB is healthy ({ttfb_stats.median_ms:g} ms)."
                )
            else:
                statement = (
                    f"Detected {slow_ttfb_count} page(s) with slow Time to First Byte "
                    f"(Median TTFB {ttfb_stats.median_ms:g} ms, Max {ttfb_stats.max_ms:g} ms)."
                )
                description = (
                    f"{slow_ttfb_count} of {len(pages)} sampled URLs exceeded 800 ms TTFB "
                    f"(median {ttfb_stats.median_ms:g} ms, mean {ttfb_stats.mean_ms:g} ms)."
                )
                sev = Severity.HIGH
                recommendation = (
                    "Optimize server response times using full-page edge caching (CDN), "
                    "database query indexing, and HTTP/2 or HTTP/3."
                )

            if hasattr(blackboard, "claim_registry") and blackboard.claim_registry is not None:
                claim = self.register_claim(
                    blackboard=blackboard,
                    statement=statement,
                    category=Category.TECHNICAL_SEO,
                    severity=sev,
                    claim_type=ClaimType.FACT,
                    evidence_refs=ev_refs,
                    confidence=0.94,
                    recommendation=recommendation,
                    impact=6 if is_isolated_outlier else 8,
                    effort=3,
                )
                claims.append(claim)

            finding = Finding(
                finding_id="finding_slow_ttfb",
                category=Category.TECHNICAL_SEO,
                severity=sev,
                title=statement,
                description=description,
                diagnosis=description,
                affected_urls=slow_urls,
                affected_url_count=len(slow_urls),
                evidence=ev_list,
                evidence_refs=ev_refs,
                evidence_ids=ev_refs,
                recommendation=recommendation,
                confidence=0.94,
                impact=6 if is_isolated_outlier else 8,
                effort=3,
                priority=6 if is_isolated_outlier else 8,
                agent_id=self.agent_id,
            )
            findings.append(finding)
            if hasattr(blackboard, "add_finding"):
                blackboard.add_finding(finding)
            elif hasattr(blackboard, "findings") and isinstance(blackboard.findings, list):
                blackboard.findings.append(finding)

        result = {
            "agent_id": self.agent_id,
            "domain": "seo",
            "specialty": "performance",
            "status": "completed",
            "observations": observations,
            "claims": [c.statement if hasattr(c, "statement") else str(c) for c in claims],
            "findings": findings,
        }
        return result
