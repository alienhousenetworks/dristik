"""
Dristik AI Capability Router & Execution Gateway
Routes requested capabilities to either:
1. $0 Deterministic Analyzer Engines (Fast, repeatable, zero token cost)
2. Cognitive Worker Pool (Tier B SLM -> Tier C Reasoning -> Tier D High Reasoning)
"""
from typing import Dict, Any, List, Optional
from app.domain.capability import CAPABILITY_REGISTRY, CapabilitySpec, ExecutionTier, CapabilityDomain
from app.domain.models import PageEvidence, CrawlManifest, Claim
from app.domain.enums import Category, Severity
from app.cognition.blackboard import CognitiveBlackboard

class CapabilityRouter:
    def __init__(self):
        self.registry = CAPABILITY_REGISTRY

    def get_tier(self, capability_id: str) -> ExecutionTier:
        spec = self.registry.get(capability_id)
        if spec:
            return spec.tier
        return ExecutionTier.TIER_B_SLM

    def is_deterministic(self, capability_id: str) -> bool:
        return self.get_tier(capability_id) == ExecutionTier.TIER_A_DETERMINISTIC

    def execute_deterministic_capability(
        self,
        capability_id: str,
        manifest: CrawlManifest,
        blackboard: CognitiveBlackboard
    ) -> List[Dict[str, Any]]:
        """
        Executes zero-token deterministic Python analysis for structured/technical capabilities.
        """
        results = []
        spec = self.registry.get(capability_id)
        if not spec:
            return results

        ch = manifest.crawl_health
        pages = manifest.pages

        if capability_id == "01_discovery":
            # Sitemap & Robots.txt health
            if not manifest.sitemap_found:
                results.append({
                    "statement": "XML Sitemap is missing or unreferenced in robots.txt / /sitemap.xml.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.HIGH,
                    "confidence": 0.98,
                    "recommendation": "Generate an automated XML sitemap and reference it in robots.txt."
                })
            if not manifest.robots_txt_found:
                results.append({
                    "statement": "robots.txt file was not detected at domain root.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.MEDIUM,
                    "confidence": 0.95,
                    "recommendation": "Deploy a valid robots.txt file to guide search and AI crawler crawling policies."
                })

        elif capability_id == "02_semantic_structure":
            # Missing or duplicate H1s
            missing_h1_count = ch.get("missing_h1_count", 0)
            if missing_h1_count > 0:
                urls = ch.get("missing_h1_urls", [])[:3]
                results.append({
                    "statement": f"Missing primary <h1> heading tag on {missing_h1_count} page(s) ({', '.join(urls)}).",
                    "category": Category.ON_PAGE_SEO,
                    "severity": Severity.HIGH,
                    "confidence": 0.98,
                    "recommendation": "Add a single semantic <h1> to each page summarizing its primary purpose."
                })

        elif capability_id == "03_indexability":
            # Canonical checks
            missing_canonicals = [p.url for p in pages if not p.canonical_url]
            if missing_canonicals:
                results.append({
                    "statement": f"{len(missing_canonicals)} page(s) lack a rel='canonical' tag.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.MEDIUM,
                    "confidence": 0.95,
                    "recommendation": "Specify canonical URLs on all public indexable pages to prevent duplicate content consolidation issues."
                })

        elif capability_id == "04_link_architecture":
            broken = ch.get("broken_links_count", 0)
            if broken > 0:
                results.append({
                    "statement": f"Found {broken} broken internal link references during the crawl.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.HIGH,
                    "confidence": 0.96,
                    "recommendation": "Audit and repair all internal 404/broken link references."
                })

        elif capability_id == "05_performance":
            avg_ttfb = ch.get("avg_ttfb_ms", 0.0)
            if avg_ttfb > 800:
                results.append({
                    "statement": f"Average Time To First Byte (TTFB) is high ({avg_ttfb:.0f}ms, benchmark is < 300ms).",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.HIGH if avg_ttfb > 1500 else Severity.MEDIUM,
                    "confidence": 0.92,
                    "recommendation": "Implement edge CDN caching and optimize backend database query latencies."
                })

        elif capability_id == "06_security":
            is_https = manifest.base_url.startswith("https://")
            if not is_https:
                results.append({
                    "statement": "Website does not default to secure HTTPS transport.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.CRITICAL,
                    "confidence": 1.0,
                    "recommendation": "Enforce HTTPS redirect and configure modern TLS 1.3 encryption."
                })

        elif capability_id == "07_asset_optimization":
            total_missing_alt = sum(p.images_without_alt for p in pages)
            if total_missing_alt > 0:
                results.append({
                    "statement": f"Detected {total_missing_alt} image(s) missing descriptive alt attributes.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.MEDIUM,
                    "confidence": 0.95,
                    "recommendation": "Add accessible, keyword-contextual alt descriptions to all meaningful image assets."
                })

        elif capability_id == "08_mobile_readiness":
            missing_viewport = [p.url for p in pages if not p.viewport]
            if missing_viewport:
                results.append({
                    "statement": f"{len(missing_viewport)} page(s) are missing a meta viewport declaration.",
                    "category": Category.TECHNICAL_SEO,
                    "severity": Severity.HIGH,
                    "confidence": 0.99,
                    "recommendation": "Add <meta name='viewport' content='width=device-width, initial-scale=1.0'>."
                })

        elif capability_id == "09_schema_syntax":
            pages_without_schema = [p.url for p in pages if len(p.schema_types) == 0]
            if len(pages_without_schema) == len(pages):
                results.append({
                    "statement": "No structured JSON-LD or Microdata schema detected across crawled pages.",
                    "category": Category.SCHEMA,
                    "severity": Severity.HIGH,
                    "confidence": 0.98,
                    "recommendation": "Implement Schema.org JSON-LD (e.g. Organization, WebSite, SoftwareApplication)."
                })

        elif capability_id == "11_opengraph_metadata":
            missing_og = [p.url for p in pages if not p.og_tags.get("og:title") or not p.og_tags.get("og:image")]
            if missing_og:
                results.append({
                    "statement": f"{len(missing_og)} page(s) lack complete OpenGraph social sharing meta tags (og:title / og:image).",
                    "category": Category.ON_PAGE_SEO,
                    "severity": Severity.LOW,
                    "confidence": 0.94,
                    "recommendation": "Implement complete og:title, og:description, and og:image tags for richer social previews."
                })

        elif capability_id == "19_readability":
            homepage = pages[0] if pages else None
            if homepage and homepage.readability_score > 0 and homepage.readability_score < 40:
                results.append({
                    "statement": f"Content readability index is very low ({homepage.readability_score:.1f}/100, difficult/academic phrasing).",
                    "category": Category.CONTENT,
                    "severity": Severity.MEDIUM,
                    "confidence": 0.88,
                    "recommendation": "Simplify complex sentences and avoid excessive dense jargon to improve consumer comprehension."
                })

        elif capability_id == "21_cannibalization":
            dup_titles = ch.get("duplicate_titles_count", 0)
            if dup_titles > 0:
                results.append({
                    "statement": f"Identified {dup_titles} instance(s) of duplicate <title> tags across subpages, risking search cannibalization.",
                    "category": Category.CONTENT,
                    "severity": Severity.HIGH,
                    "confidence": 0.95,
                    "recommendation": "Differentiate page titles to reflect distinct search and user intents."
                })

        return results
