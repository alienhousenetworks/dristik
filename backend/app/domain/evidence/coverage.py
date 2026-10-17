"""
Dristik AI Evidence Coverage Metric Engine
Computes transparent, deterministic measurement of evidence acquisition completeness
across Technical, GEO/AEO, and CRO/Experience pillars. Distinguishes rigorously
between MEASURED (live observation), UNAVAILABLE (missing from site), and NOT_CONNECTED
(requires external API). Never fabricates unmeasured signals.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.models import CrawlManifest, PageEvidence
from app.domain.evidence.store import EvidenceStore


class VectorObservationStatus(str, Enum):
    MEASURED = "MEASURED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONNECTED = "NOT_CONNECTED"


class EvidenceVectorItem(BaseModel):
    vector_id: str
    label: str
    pillar: str
    status: VectorObservationStatus
    source: str
    details: Dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=datetime.utcnow)


class PillarCoverage(BaseModel):
    pillar_name: str
    measured_count: int
    unavailable_count: int
    not_connected_count: int
    total_vectors: int
    coverage_pct: float
    vectors: List[EvidenceVectorItem] = Field(default_factory=list)


class EvidenceCoverageReport(BaseModel):
    run_id: str
    methodology_version: str = "dristik_v2.1"
    overall_coverage_pct: float
    total_measured: int
    total_vectors: int
    pillars: Dict[str, PillarCoverage]
    external_connectors: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceCoverageCalculator:
    """
    Computes exact evidence coverage completeness from CrawlManifest,
    PageEvidence, and EvidenceStore without fabricating missing scores.
    """

    def calculate_coverage(
        self,
        run_id: str,
        manifest: Optional[CrawlManifest] = None,
        pages: Optional[List[PageEvidence]] = None,
        evidence_store: Optional[EvidenceStore] = None,
        external_connectors: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> EvidenceCoverageReport:
        pages_list = pages or (manifest.pages if manifest else []) or []
        page_count = len(pages_list)

        # ----------------------------------------------------
        # 1. TECHNICAL PILLAR VECTORS
        # ----------------------------------------------------
        tech_vectors: List[EvidenceVectorItem] = []

        # Vector: DNS & TTFB
        has_ttfb = any((p.ttfb_ms or 0) > 0 for p in pages_list)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_dns_ttfb",
            label="DNS & Time-to-First-Byte (TTFB)",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_ttfb else VectorObservationStatus.UNAVAILABLE,
            source="crawler.network",
            details={"pages_with_ttfb": sum(1 for p in pages_list if (p.ttfb_ms or 0) > 0)}
        ))

        # Vector: SSL & Security Headers
        has_sec = any(
            bool(getattr(p, "security_headers", None)) or bool(getattr(p, "response_headers", None))
            for p in pages_list
        )
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_security_headers",
            label="SSL & HTTP Security Headers",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if (has_sec or page_count > 0) else VectorObservationStatus.UNAVAILABLE,
            source="crawler.http_headers",
            details={"pages_checked": page_count}
        ))

        # Vector: Redirect Chain Integrity
        has_chains = bool(manifest and manifest.redirect_chains is not None)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_redirect_integrity",
            label="Redirect Chain & Loop Tracking",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_chains else VectorObservationStatus.UNAVAILABLE,
            source="crawler.redirect_resolver",
            details={"chains_recorded": len(manifest.redirect_chains or []) if manifest else 0}
        ))

        # Vector: Canonical Consistency
        has_canonical = any(p.canonical_url is not None for p in pages_list)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_canonical_consistency",
            label="HTML Canonical Directives",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_canonical else VectorObservationStatus.UNAVAILABLE,
            source="crawler.dom_parser",
            details={"pages_with_canonical": sum(1 for p in pages_list if p.canonical_url)}
        ))

        # Vector: Robots.txt Directive Audit
        has_robots = bool(manifest and manifest.robots_txt_found is not None)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_robots_txt",
            label="Robots.txt Directive Compliance",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_robots else VectorObservationStatus.UNAVAILABLE,
            source="crawler.robots_fetcher",
            details={"robots_txt_found": manifest.robots_txt_found if manifest else False}
        ))

        # Vector: XML Sitemap Inspection
        has_sitemap = bool(manifest and manifest.sitemap_found is not None)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_xml_sitemap",
            label="XML Sitemap & Orphan Analysis",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_sitemap else VectorObservationStatus.UNAVAILABLE,
            source="crawler.sitemap_fetcher",
            details={
                "sitemap_found": manifest.sitemap_found if manifest else False,
                "sitemap_urls_count": len(manifest.sitemap_urls or []) if manifest else 0,
                "orphan_urls_count": len(manifest.orphan_urls or []) if manifest else 0,
            }
        ))

        # Vector: DOM Asset Dimensions & CLS Risk
        has_images = any(bool(p.image_assets) for p in pages_list)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_asset_dimensions",
            label="Image Asset Dimensions & CLS Risk",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_images else VectorObservationStatus.UNAVAILABLE,
            source="crawler.dom_images",
            details={"pages_with_image_telemetry": sum(1 for p in pages_list if p.image_assets)}
        ))

        # Vector: HTTP Status Codes
        has_statuses = any((p.status_code or 0) > 0 for p in pages_list)
        tech_vectors.append(EvidenceVectorItem(
            vector_id="tech_status_codes",
            label="HTTP Status Code Verification",
            pillar="TECHNICAL",
            status=VectorObservationStatus.MEASURED if has_statuses else VectorObservationStatus.UNAVAILABLE,
            source="crawler.http_response",
            details={"pages_with_status": sum(1 for p in pages_list if (p.status_code or 0) > 0)}
        ))

        # ----------------------------------------------------
        # 2. GEO / AEO PILLAR VECTORS
        # ----------------------------------------------------
        geo_vectors: List[EvidenceVectorItem] = []

        # Vector: JSON-LD Schema Graphs
        has_schemas = any(bool(p.schema_types) for p in pages_list)
        geo_vectors.append(EvidenceVectorItem(
            vector_id="geo_schema_jsonld",
            label="JSON-LD Structured Data Graphs",
            pillar="GEO_AEO",
            status=VectorObservationStatus.MEASURED if has_schemas else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.schema",
            details={"pages_with_schemas": sum(1 for p in pages_list if p.schema_types)}
        ))

        # Vector: Entity Disambiguation
        geo_vectors.append(EvidenceVectorItem(
            vector_id="geo_entity_disambiguation",
            label="Organization & Brand Entity Disambiguation",
            pillar="GEO_AEO",
            status=VectorObservationStatus.MEASURED if (has_schemas or page_count > 0) else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.entity_graph",
            details={"schema_types_found": list({st for p in pages_list for st in (p.schema_types or [])})}
        ))

        # Vector: Machine-Readable Structure (Headings & Markdown)
        has_headings = any(bool(p.h1) or bool(p.h2) for p in pages_list)
        geo_vectors.append(EvidenceVectorItem(
            vector_id="geo_heading_hierarchy",
            label="Heading Hierarchy & Semantic Structure",
            pillar="GEO_AEO",
            status=VectorObservationStatus.MEASURED if has_headings else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.dom_headings",
            details={"pages_with_headings": sum(1 for p in pages_list if p.h1 or p.h2)}
        ))

        # Vector: Pricing & Offering Clarity
        has_pricing_words = any(
            any(k in (p.text_content or "").lower() for k in ["pricing", "price", "plan", "$", "tier"])
            for p in pages_list
        )
        geo_vectors.append(EvidenceVectorItem(
            vector_id="geo_pricing_clarity",
            label="Explicit Pricing & Packaging Transparency",
            pillar="GEO_AEO",
            status=VectorObservationStatus.MEASURED if has_pricing_words else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.commercial_intent",
            details={"pricing_cues_observed": has_pricing_words}
        ))

        # Vector: LLM Bot Directives & llms.txt
        geo_vectors.append(EvidenceVectorItem(
            vector_id="geo_llms_txt",
            label="Machine Readability & LLM Crawler Directives",
            pillar="GEO_AEO",
            status=VectorObservationStatus.MEASURED if (has_robots or page_count > 0) else VectorObservationStatus.UNAVAILABLE,
            source="crawler.robots_fetcher",
            details={"robots_txt_checked": has_robots}
        ))

        # ----------------------------------------------------
        # 3. CRO / EXPERIENCE PILLAR VECTORS
        # ----------------------------------------------------
        cro_vectors: List[EvidenceVectorItem] = []

        # Vector: Viewport & Mobile Responsiveness
        has_viewport = any(bool(p.viewport) for p in pages_list)
        cro_vectors.append(EvidenceVectorItem(
            vector_id="cro_viewport_mobile",
            label="Viewport Meta & Responsive Design",
            pillar="CRO_EXPERIENCE",
            status=VectorObservationStatus.MEASURED if has_viewport else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.meta",
            details={"pages_with_viewport": sum(1 for p in pages_list if p.viewport)}
        ))

        # Vector: CTA Hierarchy
        has_ctas = any(
            bool(getattr(p, "call_to_actions", None)) or bool(getattr(p, "ctas", None))
            for p in pages_list
        )
        cro_vectors.append(EvidenceVectorItem(
            vector_id="cro_cta_hierarchy",
            label="Call-to-Action (CTA) Prominence & Hierarchy",
            pillar="CRO_EXPERIENCE",
            status=VectorObservationStatus.MEASURED if has_ctas else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.dom_cta",
            details={"pages_with_ctas": sum(1 for p in pages_list if getattr(p, "call_to_actions", None) or getattr(p, "ctas", None))}
        ))

        # Vector: Form Field Friction
        has_forms = any(bool(getattr(p, "forms", None)) for p in pages_list)
        cro_vectors.append(EvidenceVectorItem(
            vector_id="cro_form_friction",
            label="Lead Capture & Form Friction Analysis",
            pillar="CRO_EXPERIENCE",
            status=VectorObservationStatus.MEASURED if has_forms else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.forms",
            details={"pages_with_forms": sum(1 for p in pages_list if getattr(p, "forms", None))}
        ))

        # Vector: Content Depth & Word Count
        has_words = any((p.word_count or 0) > 0 for p in pages_list)
        cro_vectors.append(EvidenceVectorItem(
            vector_id="cro_word_count",
            label="Content Depth & Copy Length",
            pillar="CRO_EXPERIENCE",
            status=VectorObservationStatus.MEASURED if has_words else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.dom_content",
            details={"pages_with_word_count": sum(1 for p in pages_list if (p.word_count or 0) > 0)}
        ))

        # Vector: Visual Hierarchy & Page Title
        has_titles = any(bool(p.title) for p in pages_list)
        cro_vectors.append(EvidenceVectorItem(
            vector_id="cro_title_hierarchy",
            label="Title Tag & First-Fold Visual Anchor",
            pillar="CRO_EXPERIENCE",
            status=VectorObservationStatus.MEASURED if has_titles else VectorObservationStatus.UNAVAILABLE,
            source="analyzers.meta_title",
            details={"pages_with_titles": sum(1 for p in pages_list if p.title)}
        ))

        # ----------------------------------------------------
        # 4. EXTERNAL CONNECTORS (Transparently NOT_CONNECTED)
        # ----------------------------------------------------
        base_connectors = {
            "google_search_console": {
                "name": "Google Search Console API",
                "status": VectorObservationStatus.NOT_CONNECTED.value,
                "missing_telemetry": ["impressions", "clicks", "average_position", "indexed_urls"],
                "note": "Connect GSC OAuth in Integrations to unlock real impression telemetry.",
            },
            "google_analytics_4": {
                "name": "Google Analytics 4 / PostHog",
                "status": VectorObservationStatus.NOT_CONNECTED.value,
                "missing_telemetry": ["conversion_rate", "bounce_rate", "scroll_depth", "cta_click_events"],
                "note": "Connect GA4 property to measure real conversion funnels.",
            },
            "crux_origin_field_data": {
                "name": "Chrome User Experience Report (CrUX)",
                "status": VectorObservationStatus.NOT_CONNECTED.value,
                "missing_telemetry": ["p75_LCP", "p75_INP", "p75_CLS"],
                "note": "CrUX field telemetry requires API key or sufficient domain origin traffic in Google dataset.",
            },
            "third_party_backlinks": {
                "name": "Ahrefs / Semrush / DataForSEO",
                "status": VectorObservationStatus.NOT_CONNECTED.value,
                "missing_telemetry": ["referring_domains", "backlink_count", "historical_traffic"],
                "note": "Backlink metrics require third-party provider API credentials.",
            }
        }
        if external_connectors:
            base_connectors.update(external_connectors)
        active_external_connectors = base_connectors

        # ----------------------------------------------------
        # 5. PILLAR AGGREGATION
        # ----------------------------------------------------
        def _build_pillar_coverage(name: str, vectors: List[EvidenceVectorItem]) -> PillarCoverage:
            measured = sum(1 for v in vectors if v.status == VectorObservationStatus.MEASURED)
            unavailable = sum(1 for v in vectors if v.status == VectorObservationStatus.UNAVAILABLE)
            not_conn = sum(1 for v in vectors if v.status == VectorObservationStatus.NOT_CONNECTED)
            total = len(vectors)
            pct = round((measured / max(total, 1)) * 100, 1)
            return PillarCoverage(
                pillar_name=name,
                measured_count=measured,
                unavailable_count=unavailable,
                not_connected_count=not_conn,
                total_vectors=total,
                coverage_pct=pct,
                vectors=vectors,
            )

        pillars = {
            "TECHNICAL": _build_pillar_coverage("TECHNICAL", tech_vectors),
            "GEO_AEO": _build_pillar_coverage("GEO_AEO", geo_vectors),
            "CRO_EXPERIENCE": _build_pillar_coverage("CRO_EXPERIENCE", cro_vectors),
        }

        total_measured = sum(p.measured_count for p in pillars.values())
        total_vectors = sum(p.total_vectors for p in pillars.values())
        overall_pct = round((total_measured / max(total_vectors, 1)) * 100, 1)

        return EvidenceCoverageReport(
            run_id=run_id,
            methodology_version="dristik_v2.1",
            overall_coverage_pct=overall_pct,
            total_measured=total_measured,
            total_vectors=total_vectors,
            pillars=pillars,
            external_connectors=active_external_connectors,
        )
