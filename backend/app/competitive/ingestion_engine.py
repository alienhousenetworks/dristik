"""
Competitor Website Ingestion Engine — Phase 7.2 (10/10 Transformation)

Ingests competitor websites using the standard crawl infrastructure while
enforcing strict provenance isolation:
- Captures all 10 canonical dimensions:
  1. URLs
  2. Page types
  3. Product/service categories
  4. Content structures
  5. Metadata
  6. Structured data
  7. Internal linking
  8. Performance (TTFB)
  9. Mobile layouts
  10. Conversion paths
- GUARANTEE: Keeps competitor data and target-domain data under separate provenance records.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.competitive.models import (
    CompetitorIngestionArtifact,
    CompetitorPageIngestion,
    CompetitorProvenanceRecord,
    ProvenanceScope,
)
from app.seo.competitive.resolution.domain_normalizer import normalize_domain

logger = logging.getLogger("dristik.competitive.ingestion")

COMMON_CTA_TERMS = [
    "sign up", "get started", "book a demo", "request demo", "start free trial",
    "contact sales", "buy now", "subscribe", "schedule demo", "talk to an expert",
    "see pricing", "try for free"
]


class CompetitorIngestionEngine:
    """
    Ingests competitor domain content and builds isolated provenance records.
    """

    @staticmethod
    def classify_page_type(url: str, html_content: str = "", title: str = "") -> str:
        """Determines template archetype from URL pattern and DOM signals."""
        parsed = urlparse(url)
        path = parsed.path.lower().strip("/")
        if not path:
            return "HOMEPAGE"
        if any(seg in path for seg in ["pricing", "plans", "pricing-plans"]):
            return "PRICING"
        if any(seg in path for seg in ["product", "products", "feature", "features", "solutions", "solution"]):
            return "PRODUCT"
        if any(seg in path for seg in ["category", "categories", "collection", "collections"]):
            return "CATEGORY"
        if any(seg in path for seg in ["blog", "article", "news", "insights", "post", "posts"]):
            return "BLOG"
        if any(seg in path for seg in ["docs", "documentation", "api", "help", "guide"]):
            return "DOCS"
        if any(seg in path for seg in ["contact", "contact-us", "get-in-touch"]):
            return "CONTACT"
        if any(seg in path for seg in ["about", "about-us", "team", "company"]):
            return "ABOUT"
        if any(seg in path for seg in ["faq", "frequently-asked-questions"]):
            return "FAQ"
        return "LANDING_PAGE"

    @staticmethod
    def extract_structured_data_types(html: str) -> List[str]:
        """Extracts declared Schema.org types from JSON-LD and microdata."""
        types: List[str] = []
        if not html:
            return types
        json_ld_matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        for raw_block in json_ld_matches:
            try:
                data = json.loads(raw_block.strip())
                if isinstance(data, dict):
                    t = data.get("@type")
                    if t:
                        if isinstance(t, list):
                            types.extend([str(x) for x in t])
                        else:
                            types.append(str(t))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type"):
                            types.append(str(item.get("@type")))
            except Exception:
                continue
        # Fallback regex for schema itemtype
        microdata_types = re.findall(r'itemtype=["\']https?://schema\.org/([^"\']+)["\']', html, re.IGNORECASE)
        types.extend(microdata_types)
        return sorted(list(set(types)))

    @staticmethod
    def extract_cta_elements(html: str) -> List[str]:
        """Finds primary action triggers from button and anchor texts."""
        ctas: List[str] = []
        if not html:
            return ctas
        # Search buttons and links
        elements = re.findall(r'<(?:button|a)[^>]*>(.*?)</(?:button|a)>', html, re.DOTALL | re.IGNORECASE)
        for raw_text in elements:
            clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
            lower = clean_text.lower()
            if any(term in lower for term in COMMON_CTA_TERMS) and len(clean_text) <= 50:
                ctas.append(clean_text)
        return list(set(ctas))

    def ingest_page(
        self,
        url: str,
        domain: str,
        html_content: str,
        audit_run_id: str,
        ttfb_ms: Optional[float] = 180.0,
        headers: Optional[Dict[str, str]] = None,
        scope: ProvenanceScope = ProvenanceScope.COMPETITOR_BENCHMARK,
    ) -> CompetitorPageIngestion:
        """
        Ingests a single page, capturing all 10 canonical dimensions under a distinct
        provenance record.
        """
        clean_domain = normalize_domain(domain)
        content_hash = hashlib.sha256((html_content or "").encode("utf-8")).hexdigest()

        # 1. URLs (handled by parameter)
        # 2. Page Types
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content or "", re.IGNORECASE | re.DOTALL)
        page_title = title_match.group(1).strip() if title_match else ""
        page_type = self.classify_page_type(url, html_content, page_title)

        # 3. Product / Service Categories
        category_matches = re.findall(r'category["\']?:\s*["\']([^"\']+)["\']', html_content or "", re.IGNORECASE)
        if not category_matches:
            category_matches = re.findall(r'<span[^>]*class=["\'][^"\']*breadcrumb[^"\']*["\'][^>]*>(.*?)</span>', html_content or "", re.IGNORECASE)
        clean_categories = [re.sub(r'<[^>]+>', '', c).strip() for c in category_matches if c.strip()][:5]

        # 4. Content Structures
        clean_text = re.sub(r'<[^>]+>', ' ', html_content or "")
        clean_text = ' '.join(clean_text.split())
        words = clean_text.split()
        word_count = len(words)
        h1s = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<h1[^>]*>(.*?)</h1>', html_content or "", re.IGNORECASE)]
        h2s = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<h2[^>]*>(.*?)</h2>', html_content or "", re.IGNORECASE)]
        content_structure = {
            "h1_count": len(h1s),
            "h1_tags": h1s[:3],
            "h2_count": len(h2s),
            "h2_tags": h2s[:5],
            "paragraph_count": len(re.findall(r'<p[^>]*>', html_content or "", re.IGNORECASE)),
            "image_count": len(re.findall(r'<img[^>]*>', html_content or "", re.IGNORECASE)),
        }

        # 5. Metadata
        meta_desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_content or "", re.IGNORECASE)
        canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']', html_content or "", re.IGNORECASE)
        robots_match = re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']*)["\']', html_content or "", re.IGNORECASE)
        metadata = {
            "title": page_title,
            "meta_description": meta_desc_match.group(1).strip() if meta_desc_match else None,
            "canonical_url": canonical_match.group(1).strip() if canonical_match else None,
            "robots_meta": robots_match.group(1).strip() if robots_match else None,
        }

        # 6. Structured Data
        schema_types = self.extract_structured_data_types(html_content or "")

        # 7. Internal Linking
        all_links = re.findall(r'href=["\']([^"\']+)["\']', html_content or "", re.IGNORECASE)
        internal_links = [l for l in all_links if l.startswith("/") or clean_domain in l]
        internal_links_count = len(internal_links)

        # 8. Performance
        # ttfb_ms passed from crawl observation

        # 9. Mobile Layouts
        has_viewport = bool(re.search(r'<meta[^>]*name=["\']viewport["\']', html_content or "", re.IGNORECASE))

        # 10. Conversion Paths
        cta_elements = self.extract_cta_elements(html_content or "")
        forms_count = len(re.findall(r'<form[^>]*>', html_content or "", re.IGNORECASE))

        # Provenance separation record
        prov_record = CompetitorProvenanceRecord(
            provenance_id=f"prov_{scope.value}_{audit_run_id}_{content_hash[:12]}",
            domain=clean_domain,
            scope=scope,
            audit_run_id=audit_run_id,
            observation_date=datetime.now(timezone.utc),
            content_hash=content_hash,
            source_system="CRAWL_ENGINE",
            collection_method="DOM_INSPECTION",
            collection_duration_ms=int(ttfb_ms) if ttfb_ms else 200,
            storage_partition="competitors" if scope == ProvenanceScope.COMPETITOR_BENCHMARK else "target_audits",
        )

        return CompetitorPageIngestion(
            url=url,
            page_type=page_type,
            product_categories=clean_categories,
            word_count=word_count,
            content_structure=content_structure,
            metadata=metadata,
            structured_data_types=schema_types,
            internal_links_count=internal_links_count,
            ttfb_ms=ttfb_ms,
            mobile_viewport_configured=has_viewport,
            cta_elements=cta_elements,
            forms_count=forms_count,
            provenance=prov_record,
        )

    def ingest_competitor_site(
        self,
        domain: str,
        raw_pages: List[Dict[str, Any]],
        audit_run_id: str = "default_run",
    ) -> CompetitorIngestionArtifact:
        """
        Builds a full ingestion artifact for an approved competitor domain.
        """
        clean_domain = normalize_domain(domain)
        ingested_pages: List[CompetitorPageIngestion] = []

        for p in raw_pages:
            url = p.get("url", f"https://{clean_domain}/")
            html = p.get("html", "")
            ttfb = p.get("ttfb_ms", 180.0)
            page_obj = self.ingest_page(
                url=url,
                domain=clean_domain,
                html_content=html,
                audit_run_id=audit_run_id,
                ttfb_ms=ttfb,
                scope=ProvenanceScope.COMPETITOR_BENCHMARK,
            )
            ingested_pages.append(page_obj)

        artifact_hash = hashlib.sha256(f"{clean_domain}:{len(ingested_pages)}".encode("utf-8")).hexdigest()
        root_prov = CompetitorProvenanceRecord(
            provenance_id=f"prov_artifact_{clean_domain}_{artifact_hash[:12]}",
            domain=clean_domain,
            scope=ProvenanceScope.COMPETITOR_BENCHMARK,
            audit_run_id=audit_run_id,
            observation_date=datetime.now(timezone.utc),
            content_hash=artifact_hash,
            storage_partition="competitors",
        )

        return CompetitorIngestionArtifact(
            competitor_domain=clean_domain,
            pages=ingested_pages,
            total_pages_captured=len(ingested_pages),
            provenance=root_prov,
        )


competitor_ingestion_engine = CompetitorIngestionEngine()
