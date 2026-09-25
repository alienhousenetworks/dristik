"""
Cross-Page Entity Consistency & Semantic Fragmentation Detector.
Layer 1 Extractability: What Dristik can prove deterministically from the website itself.

Extracts primary entity definitions across 5 distinct surface areas:
1. Homepage (<title>, meta description, H1, hero copy)
2. About / Company page (/about, /company, /who-we-are)
3. Services / Products pages (/services/*, /products/*)
4. Structured Data (JSON-LD Organization, LocalBusiness, Service, Product)
5. Footer & Contact (/contact, footer legal name, address, copyright)

Detects Semantic Identity Fragmentation:
Flags when Homepage says "AI Development Company", About says "Software Consulting",
Schema says "IT Services", and Footer says "Digital Marketing Agency".
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.domain.models import BusinessProfile, PageEvidence


# Common category clusters for semantic matching across industries
CATEGORY_TAXONOMY: Dict[str, Set[str]] = {
    "ai_machine_learning": {
        "ai", "artificial intelligence", "machine learning", "ml", "genai",
        "generative ai", "deep learning", "llm", "nlp", "computer vision",
        "agentic ai", "neural networks"
    },
    "software_engineering": {
        "software development", "software engineering", "custom software",
        "app development", "application development", "web development",
        "full stack", "backend", "frontend", "api development", "mobile development"
    },
    "it_consulting_services": {
        "it services", "it consulting", "information technology", "tech consulting",
        "managed it", "cloud solutions", "devops", "cloud infrastructure",
        "system integration", "digital transformation"
    },
    "digital_marketing": {
        "digital marketing", "seo", "search engine optimization", "content marketing",
        "performance marketing", "growth marketing", "social media marketing",
        "branding agency", "advertising agency"
    },
    "design_creative": {
        "ui/ux", "product design", "graphic design", "creative agency",
        "brand identity", "web design", "ux research", "experience design"
    },
    "saas_product": {
        "saas", "software as a service", "b2b saas", "cloud platform",
        "automation platform", "subscription software", "enterprise software"
    },
    "fintech_financial": {
        "fintech", "financial services", "banking", "payments", "wealth management",
        "investment", "accounting", "tax", "crypto", "blockchain"
    },
    "healthcare_lifesciences": {
        "healthcare", "healthtech", "telemedicine", "medical", "clinic",
        "pharmaceutical", "biotech", "life sciences", "wellness"
    },
    "ecommerce_retail": {
        "ecommerce", "e-commerce", "retail", "marketplace", "online store",
        "direct to consumer", "d2c", "shopping"
    },
    "education_edtech": {
        "edtech", "education", "e-learning", "online learning", "training",
        "academy", "courseware", "tutoring"
    },
    "legal_professional": {
        "legal", "law firm", "attorneys", "compliance", "regulatory",
        "advisory", "management consulting"
    },
}

# Audience classification tokens
AUDIENCE_TAXONOMY: Dict[str, Set[str]] = {
    "enterprise": {"enterprise", "enterprises", "fortune 500", "large organizations", "global corporations"},
    "startups": {"startups", "early stage", "seed", "series a", "founders", "venture-backed", "y combinator"},
    "smb": {"smb", "sme", "small business", "small businesses", "mid-market", "local businesses"},
    "developers": {"developers", "engineers", "devops", "technical teams", "ctos", "architects"},
    "consumers": {"consumers", "individuals", "b2c", "everyday users", "families", "patients"},
    "b2b": {"b2b", "businesses", "companies", "corporate buyers", "institutions"},
}


class SurfaceAreaObservation(BaseModel):
    surface_name: str  # "homepage", "about", "services_products", "structured_data", "footer_contact"
    source_url: Optional[str] = None
    brand_name_observed: Optional[str] = None
    category_observed: Optional[str] = None
    category_clusters: List[str] = Field(default_factory=list)
    audience_observed: List[str] = Field(default_factory=list)
    locations_observed: List[str] = Field(default_factory=list)
    raw_evidence_snippet: str = ""
    confidence: float = 0.8


class EntityDiscrepancy(BaseModel):
    field: str  # "brand_name", "primary_category", "target_audience", "location"
    severity: str  # "HIGH", "MEDIUM", "LOW"
    surface_a: str
    value_a: str
    url_a: Optional[str] = None
    surface_b: str
    value_b: str
    url_b: Optional[str] = None
    explanation: str
    remediation: str


class EntityConsistencyResult(BaseModel):
    overall_consistency_score: float  # 0 to 100
    fragmentation_risk: str  # "LOW", "MODERATE", "SEVERE"
    canonical_brand: str
    canonical_category: str
    surfaces_analyzed_count: int
    surface_breakdown: Dict[str, SurfaceAreaObservation] = Field(default_factory=dict)
    discrepancies: List[EntityDiscrepancy] = Field(default_factory=list)
    is_fragmented: bool = False
    summary: str = ""


class GeoEntityConsistencyAnalyzer:
    """
    Evaluates cross-surface coherence for any website.
    Runs 100% deterministically from crawled HTML, JSON-LD, and page metadata.
    """

    def __init__(self, target_domain: str = "", default_brand: str = ""):
        self.target_domain = target_domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
        self.default_brand = default_brand

    def _extract_category_clusters(self, text: str) -> List[str]:
        low = text.lower()
        matched_clusters = []
        for cluster_name, tokens in CATEGORY_TAXONOMY.items():
            for t in tokens:
                if re.search(rf"\b{re.escape(t)}\b", low):
                    matched_clusters.append(cluster_name)
                    break
        return matched_clusters

    def _extract_audiences(self, text: str) -> List[str]:
        low = text.lower()
        matched = []
        for aud, tokens in AUDIENCE_TAXONOMY.items():
            for t in tokens:
                if re.search(rf"\b{re.escape(t)}\b", low):
                    matched.append(aud)
                    break
        return matched

    def _extract_locations(self, text: str) -> List[str]:
        low = text.lower()
        # Basic heuristic for common country/regional mentions
        regions = ["usa", "united states", "uk", "united kingdom", "india", "germany", "europe", "canada", "australia", "singapore", "california", "delaware", "london", "bengaluru", "kolkata", "san francisco", "new york"]
        found = []
        for r in regions:
            if re.search(rf"\b{re.escape(r)}\b", low):
                found.append(r.title())
        return found[:3]

    def _extract_brand_candidate(self, title: str, h1: List[str], fallback: str) -> str:
        # Check title delimiters: "Brand | Tagline", "Brand - Core Service", "Brand: What We Do"
        if title:
            for sep in ["|", "–", "—", "-", ":", "•"]:
                if sep in title:
                    candidate = title.split(sep)[0].strip()
                    if 2 <= len(candidate) <= 40:
                        return candidate
        if h1 and len(h1) > 0 and len(h1[0].strip()) <= 40:
            return h1[0].strip()
        return fallback

    def _classify_pages(self, pages: List[PageEvidence], base_url: str) -> Dict[str, List[PageEvidence]]:
        categorized: Dict[str, List[PageEvidence]] = {
            "homepage": [],
            "about": [],
            "services_products": [],
            "contact": [],
            "other": []
        }
        clean_base = base_url.rstrip("/")

        for p in pages:
            url_clean = (p.url or "").rstrip("/")
            path = urlparse(url_clean).path.lower().strip("/")

            if not path or url_clean == clean_base or path in ["index.html", "home"]:
                categorized["homepage"].append(p)
            elif any(s in path for s in ["about", "company", "who-we-are", "our-story", "team"]):
                categorized["about"].append(p)
            elif any(s in path for s in ["service", "product", "solution", "offering", "platform", "features"]):
                categorized["services_products"].append(p)
            elif any(s in path for s in ["contact", "reach-us", "get-in-touch", "locations"]):
                categorized["contact"].append(p)
            else:
                categorized["other"].append(p)

        return categorized

    def analyze(
        self,
        pages: List[PageEvidence],
        website_url: str = "",
        profile: Optional[BusinessProfile] = None
    ) -> EntityConsistencyResult:
        if not pages:
            return EntityConsistencyResult(
                overall_consistency_score=50.0,
                fragmentation_risk="MODERATE",
                canonical_brand=self.default_brand or "Unknown",
                canonical_category="General Technology / Digital Services",
                surfaces_analyzed_count=0,
                summary="No crawl pages provided to verify entity consistency.",
            )

        base_url = website_url or pages[0].url
        classified = self._classify_pages(pages, base_url)
        surfaces: Dict[str, SurfaceAreaObservation] = {}

        # Fallback canonical brand name
        brand_seed = (
            (profile.business_name if profile and profile.business_name not in ["Unknown", "Unknown Business", ""] else "")
            or self.default_brand
            or (urlparse(base_url).netloc.replace("www.", "").split(".")[0].capitalize())
        )

        # -------------------------------------------------------------
        # Surface 1: Homepage
        # -------------------------------------------------------------
        hp_page = classified["homepage"][0] if classified["homepage"] else pages[0]
        hp_title = hp_page.title or ""
        hp_h1_text = " ".join(hp_page.h1 or [])
        hp_body = hp_page.body_text or ""
        hp_meta = hp_page.meta_description or ""
        hp_combined = f"{hp_title} {hp_meta} {hp_h1_text} {hp_body[:1200]}"

        hp_brand = self._extract_brand_candidate(hp_title, hp_page.h1, brand_seed)
        hp_clusters = self._extract_category_clusters(hp_combined)
        hp_audiences = self._extract_audiences(hp_combined)
        hp_locations = self._extract_locations(hp_combined)

        surfaces["homepage"] = SurfaceAreaObservation(
            surface_name="homepage",
            source_url=hp_page.url,
            brand_name_observed=hp_brand,
            category_observed=hp_clusters[0] if hp_clusters else "general_business",
            category_clusters=hp_clusters,
            audience_observed=hp_audiences,
            locations_observed=hp_locations,
            raw_evidence_snippet=(hp_title + " | " + hp_h1_text)[:200],
            confidence=0.95
        )

        # -------------------------------------------------------------
        # Surface 2: About / Company Page
        # -------------------------------------------------------------
        if classified["about"]:
            ab_page = classified["about"][0]
            ab_combined = f"{ab_page.title or ''} {' '.join(ab_page.h1 or [])} {ab_page.body_text or ''}"
            ab_brand = self._extract_brand_candidate(ab_page.title or "", ab_page.h1, hp_brand)
            ab_clusters = self._extract_category_clusters(ab_combined)
            ab_audiences = self._extract_audiences(ab_combined)
            ab_locations = self._extract_locations(ab_combined)

            surfaces["about"] = SurfaceAreaObservation(
                surface_name="about",
                source_url=ab_page.url,
                brand_name_observed=ab_brand,
                category_observed=ab_clusters[0] if ab_clusters else (hp_clusters[0] if hp_clusters else "general_business"),
                category_clusters=ab_clusters,
                audience_observed=ab_audiences,
                locations_observed=ab_locations,
                raw_evidence_snippet=(ab_page.title or "")[:200],
                confidence=0.90
            )

        # -------------------------------------------------------------
        # Surface 3: Services / Products Pages
        # -------------------------------------------------------------
        if classified["services_products"]:
            sp_page = classified["services_products"][0]
            sp_combined = " ".join([
                f"{p.title or ''} {' '.join(p.h1 or [])} {' '.join(p.h2 or [])} {(p.body_text or '')[:800]}"
                for p in classified["services_products"][:3]
            ])
            sp_clusters = self._extract_category_clusters(sp_combined)
            sp_audiences = self._extract_audiences(sp_combined)

            surfaces["services_products"] = SurfaceAreaObservation(
                surface_name="services_products",
                source_url=sp_page.url,
                brand_name_observed=hp_brand,
                category_observed=sp_clusters[0] if sp_clusters else (hp_clusters[0] if hp_clusters else "general_business"),
                category_clusters=sp_clusters,
                audience_observed=sp_audiences,
                locations_observed=[],
                raw_evidence_snippet=(sp_page.title or "")[:200],
                confidence=0.88
            )

        # -------------------------------------------------------------
        # Surface 4: Structured Data (JSON-LD)
        # -------------------------------------------------------------
        schema_brand: Optional[str] = None
        schema_types_observed: List[str] = []
        schema_clusters: List[str] = []
        schema_areas: List[str] = []

        all_schemas = [s for p in pages for s in (p.raw_schema or [])]
        for sch in all_schemas:
            if not isinstance(sch, dict):
                continue
            stype = sch.get("@type", "")
            if isinstance(stype, list):
                schema_types_observed.extend(stype)
            elif isinstance(stype, str):
                schema_types_observed.append(stype)

            name = sch.get("name") or sch.get("legalName")
            if name and isinstance(name, str) and not schema_brand:
                schema_brand = name

            desc = sch.get("description", "")
            if desc and isinstance(desc, str):
                schema_clusters.extend(self._extract_category_clusters(desc))

            area = sch.get("areaServed")
            if isinstance(area, str):
                schema_areas.append(area)
            elif isinstance(area, list):
                schema_areas.extend([str(a) for a in area])

        if all_schemas or schema_types_observed:
            surfaces["structured_data"] = SurfaceAreaObservation(
                surface_name="structured_data",
                source_url=base_url,
                brand_name_observed=schema_brand or hp_brand,
                category_observed=schema_clusters[0] if schema_clusters else ", ".join(schema_types_observed[:2]),
                category_clusters=schema_clusters,
                audience_observed=[],
                locations_observed=schema_areas[:3],
                raw_evidence_snippet=f"Types: {', '.join(schema_types_observed[:4])} | Name: {schema_brand or 'none'}",
                confidence=0.92
            )

        # -------------------------------------------------------------
        # Surface 5: Footer & Contact Surface
        # -------------------------------------------------------------
        contact_page = classified["contact"][0] if classified["contact"] else None
        footer_text = ""
        # Search the bottom 600 chars of pages for copyright, legal entity, or contact
        for p in pages[:3]:
            body = p.body_text or ""
            if len(body) > 300:
                footer_text += " " + body[-600:]

        combined_contact = f"{contact_page.title or '' if contact_page else ''} {contact_page.body_text or '' if contact_page else ''} {footer_text}"
        c_brand = None
        c_m = re.search(r"(?:©|copyright|\(c\))\s*(?:20\d\d\s*)?([A-Za-z0-9\s,\.\-]{2,40}?)(?:\.|\n|all rights|inc|llc|ltd|pvt)", combined_contact, re.I)
        if c_m:
            c_brand = c_m.group(1).strip()

        c_clusters = self._extract_category_clusters(combined_contact)
        c_locations = self._extract_locations(combined_contact)

        surfaces["footer_contact"] = SurfaceAreaObservation(
            surface_name="footer_contact",
            source_url=contact_page.url if contact_page else base_url,
            brand_name_observed=c_brand or hp_brand,
            category_observed=c_clusters[0] if c_clusters else (hp_clusters[0] if hp_clusters else "general_business"),
            category_clusters=c_clusters,
            audience_observed=[],
            locations_observed=c_locations,
            raw_evidence_snippet=(footer_text[-180:] if footer_text else "Standard footer scan"),
            confidence=0.85
        )

        # -------------------------------------------------------------
        # Evaluate Discrepancies and Semantic Identity Alignment
        # -------------------------------------------------------------
        discrepancies: List[EntityDiscrepancy] = []
        deductions = 0.0

        canonical_brand = hp_brand or brand_seed
        canonical_category = (
            hp_clusters[0] if hp_clusters
            else (profile.industry if profile and profile.industry else "technology_solutions")
        )

        # 1. Brand name mismatch across surfaces
        for s_name, obs in surfaces.items():
            if s_name == "homepage":
                continue
            obs_b = obs.brand_name_observed or ""
            if obs_b and canonical_brand:
                # Normalize spaces and casing
                cb_norm = re.sub(r"[^a-z0-9]", "", canonical_brand.lower())
                ob_norm = re.sub(r"[^a-z0-9]", "", obs_b.lower())
                # If neither is a substring of the other and difference is significant
                if cb_norm not in ob_norm and ob_norm not in cb_norm and len(cb_norm) > 2 and len(ob_norm) > 2:
                    discrepancies.append(EntityDiscrepancy(
                        field="brand_name",
                        severity="HIGH",
                        surface_a="homepage",
                        value_a=canonical_brand,
                        url_a=surfaces["homepage"].source_url,
                        surface_b=s_name,
                        value_b=obs_b,
                        url_b=obs.source_url,
                        explanation=(
                            f"Entity brand mismatch: Homepage identifies as '{canonical_brand}', "
                            f"but {s_name} identifies as '{obs_b}'."
                        ),
                        remediation=f"Unify brand naming: use '{canonical_brand}' consistently across all page titles, headers, and footer legal mentions."
                    ))
                    deductions += 18.0

        # 2. Semantic category fragmentation across surfaces
        # Check if homepage cluster conflicts with about or schema cluster
        hp_cluster_set = set(hp_clusters)
        if hp_cluster_set:
            for s_name in ["about", "services_products", "structured_data"]:
                if s_name in surfaces and surfaces[s_name].category_clusters:
                    s_cluster_set = set(surfaces[s_name].category_clusters)
                    # If surface has categories but NONE overlap with homepage
                    if not (hp_cluster_set & s_cluster_set):
                        disc_sev = "HIGH" if s_name in ["about", "structured_data"] else "MEDIUM"
                        discrepancies.append(EntityDiscrepancy(
                            field="primary_category",
                            severity=disc_sev,
                            surface_a="homepage",
                            value_a=", ".join(hp_clusters[:2]).replace("_", " "),
                            url_a=surfaces["homepage"].source_url,
                            surface_b=s_name,
                            value_b=", ".join(surfaces[s_name].category_clusters[:2]).replace("_", " "),
                            url_b=surfaces[s_name].source_url,
                            explanation=(
                                f"Semantic identity fragmentation: Homepage positions company under "
                                f"[{', '.join(hp_clusters[:2])}], whereas {s_name} uses "
                                f"[{', '.join(surfaces[s_name].category_clusters[:2])}]."
                            ),
                            remediation=(
                                f"Align taxonomy: ensure {s_name} explicitly mentions the primary offering "
                                f"({', '.join(hp_clusters[:1]).replace('_', ' ')}) so AI engines do not fragment entity understanding."
                            )
                        ))
                        deductions += (14.0 if disc_sev == "HIGH" else 8.0)

        # 3. Audience fragmentation (e.g. Enterprise vs Startups vs Consumers)
        if "homepage" in surfaces and "about" in surfaces:
            hp_aud = set(surfaces["homepage"].audience_observed)
            ab_aud = set(surfaces["about"].audience_observed)
            if hp_aud and ab_aud and not (hp_aud & ab_aud):
                discrepancies.append(EntityDiscrepancy(
                    field="target_audience",
                    severity="LOW",
                    surface_a="homepage",
                    value_a=", ".join(hp_aud),
                    url_a=surfaces["homepage"].source_url,
                    surface_b="about",
                    value_b=", ".join(ab_aud),
                    url_b=surfaces["about"].source_url,
                    explanation=(
                        f"Target audience discrepancy: Homepage speaks to [{', '.join(hp_aud)}], "
                        f"while About page emphasizes [{', '.join(ab_aud)}]."
                    ),
                    remediation="Harmonize Ideal Customer Profile (ICP) messaging across the homepage hero and About page."
                ))
                deductions += 6.0

        # Calculate final consistency score
        consistency_score = max(20.0, min(100.0, 100.0 - deductions))
        fragmentation_risk = "LOW" if consistency_score >= 85 else ("MODERATE" if consistency_score >= 60 else "SEVERE")
        is_fragmented = len(discrepancies) > 0 and consistency_score < 80

        summary = (
            f"Entity consistency is {fragmentation_risk.lower()} risk ({consistency_score:.0f}/100 across {len(surfaces)} surfaces). "
            f"Canonical entity: '{canonical_brand}' ({canonical_category.replace('_', ' ')}). "
            f"{len(discrepancies)} cross-surface discrepancies detected."
        )

        return EntityConsistencyResult(
            overall_consistency_score=round(consistency_score, 1),
            fragmentation_risk=fragmentation_risk,
            canonical_brand=canonical_brand,
            canonical_category=canonical_category.replace("_", " ").title(),
            surfaces_analyzed_count=len(surfaces),
            surface_breakdown=surfaces,
            discrepancies=discrepancies,
            is_fragmented=is_fragmented,
            summary=summary,
        )


entity_consistency_analyzer = GeoEntityConsistencyAnalyzer()
