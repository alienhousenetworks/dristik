"""
Dristik Universal Entity Resolver
Deterministic, single-source-of-truth brand & entity resolution engine.
Guarantees that no downstream worker, prompt, patch generator, or PDF report
ever produces or falls back to "Unknown Business".
"""
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from app.domain.models import PageEvidence, BusinessProfile, ResolvedEntity

# Blacklist of meaningless generic names that should never be accepted as the resolved brand
BANNED_NAMES = {
    "unknown",
    "unknown business",
    "unknown business model",
    "the target company",
    "the target enterprise",
    "identified platform",
    "your company",
    "target entity",
    "n/a",
    "none",
    "",
}


class UniversalEntityResolver:
    """
    Extracts and standardizes the true entity name and profile using a strict
    waterfall cascade:
    1. Valid schema.org/Organization (legalName, name)
    2. OpenGraph og:site_name metadata
    3. Prominent logo image alt text / header brand anchor
    4. Deterministic Hostname Brand Tokenization (always valid fallback)
    """

    @classmethod
    def resolve_from_evidence(
        cls,
        website_url: str,
        pages: List[PageEvidence],
        profile: Optional[BusinessProfile] = None
    ) -> ResolvedEntity:
        clean_url = website_url or (pages[0].url if pages else "https://target-domain.com")
        parsed = urlparse(clean_url)
        host = parsed.netloc.lower().replace("www.", "")
        if not host and clean_url:
            host = clean_url.split("/")[0].replace("www.", "")

        # Hostname brand token extraction (guaranteed fallback baseline)
        host_stem = host.split(":")[0].split(".")[0] if host else "company"
        tokenized_host = cls._clean_host_to_brand_name(host_stem)

        resolved_name = ""
        legal_name = None
        source = "DOMAIN_HEURISTIC"
        confidence = 0.70

        # Step 1: Check existing profile if already high-fidelity and non-generic
        if profile and profile.business_name and profile.business_name.strip().lower() not in BANNED_NAMES:
            resolved_name = profile.business_name.strip()
            confidence = 0.90
            source = "PROFILE_VERIFIED"

        # Step 2: Check schema.org Organization JSON-LD across all crawled pages
        schema_details = cls._extract_schema_details(pages)
        if not resolved_name or confidence < 0.90:
            if schema_details.get("name"):
                resolved_name = schema_details["name"]
                legal_name = schema_details.get("legal_name")
                source = "ORGANIZATION_SCHEMA"
                confidence = 0.98

        # Step 3: Check OpenGraph og:site_name
        og_details = cls._extract_from_opengraph(pages)
        if not resolved_name and og_details.get("site_name"):
            resolved_name = og_details["site_name"]
            source = "OG_SITE_NAME"
            confidence = 0.92

        # Step 4: Check homepage logo alt / brand anchor text
        if not resolved_name:
            dom_brand = cls._extract_from_dom_branding(pages)
            if dom_brand and dom_brand.lower() not in BANNED_NAMES:
                resolved_name = dom_brand
                source = "DOM_BRANDING"
                confidence = 0.85

        # Step 5: Check homepage title clean extraction
        if not resolved_name:
            title_brand = cls._extract_from_title(pages)
            if title_brand and title_brand.lower() not in BANNED_NAMES:
                resolved_name = title_brand
                source = "PAGE_TITLE"
                confidence = 0.80

        # Step 6: Fail-safe guarantee — Tokenized host name (Never Unknown Business!)
        if not resolved_name or resolved_name.lower() in BANNED_NAMES:
            resolved_name = tokenized_host
            source = "DOMAIN_TOKEN"
            confidence = 0.75

        # Infer category and niche from schema, profile, or page text
        niche = (
            profile.niche
            if (profile and profile.niche)
            else (schema_details.get("category") or "Digital Solutions & Services")
        )
        category = (
            profile.industry
            if (profile and profile.industry)
            else (schema_details.get("category") or "Enterprise Platform")
        )
        val_prop = (
            profile.value_proposition
            if (profile and profile.value_proposition)
            else (schema_details.get("description") or og_details.get("description") or "Core commercial offerings")
        )
        description = schema_details.get("description") or og_details.get("description") or (pages[0].meta_description if pages else None) or val_prop
        logo = schema_details.get("logo") or og_details.get("image")
        location = schema_details.get("location") or (profile.geography if profile else None)
        same_as = schema_details.get("same_as", [])

        entity = ResolvedEntity(
            name=resolved_name,
            legal_name=legal_name or resolved_name,
            domain=host,
            clean_host=host,
            description=description,
            logo=logo,
            category=category,
            location=location,
            same_as=same_as,
            niche=niche,
            value_proposition=val_prop,
            confidence=confidence,
            extraction_source=source,
        )

        # Synchronize back to profile if provided
        if profile:
            profile.business_name = resolved_name
            if not profile.niche:
                profile.niche = niche
            if not profile.industry:
                profile.industry = category
            if location and not profile.geography:
                profile.geography = location

        return entity

    @classmethod
    def _clean_host_to_brand_name(cls, host_stem: str) -> str:
        """
        Converts 'alienhouse' to 'AlienHouse' or 'acmemetrics' to 'AcmeMetrics'.
        """
        if not host_stem:
            return "Target Enterprise"
        # Split camelCase or hyphens/underscores
        parts = re.split(r"[-_.]+", host_stem)
        cleaned_parts = [p.capitalize() for p in parts if p]
        brand = " ".join(cleaned_parts)
        # Check common brand compound suffixes (e.g. AlienHouse)
        for compound in ["house", "tech", "network", "networks", "cloud", "group", "labs", "pay", "metrics", "analytics", "software", "security"]:
            pattern = re.compile(rf"^([a-z]+)({compound})$", re.I)
            m = pattern.match(host_stem)
            if m:
                return f"{m.group(1).capitalize()}{m.group(2).capitalize()}"
        return brand or "Target Enterprise"

    @classmethod
    def _extract_schema_details(cls, pages: List[PageEvidence]) -> Dict[str, Any]:
        details: Dict[str, Any] = {"same_as": []}
        for page in pages:
            schemas = getattr(page, "structured_data", None) or getattr(page, "raw_schema", None) or []
            if isinstance(schemas, dict):
                schemas = [schemas]
            for s in schemas:
                if not isinstance(s, dict):
                    continue
                s_type = s.get("@type") or ""
                if isinstance(s_type, list):
                    s_type = " ".join(str(x) for x in s_type)
                s_type_lower = str(s_type).lower()
                if any(t in s_type_lower for t in ["organization", "corporation", "localbusiness", "brand", "company"]):
                    name = s.get("name")
                    legal = s.get("legalName")
                    if name and str(name).strip().lower() not in BANNED_NAMES and not details.get("name"):
                        details["name"] = str(name).strip()
                    if legal and str(legal).strip().lower() not in BANNED_NAMES and not details.get("legal_name"):
                        details["legal_name"] = str(legal).strip()
                    if s.get("logo") and not details.get("logo"):
                        logo_val = s["logo"]
                        details["logo"] = logo_val if isinstance(logo_val, str) else logo_val.get("url")
                    if s.get("description") and not details.get("description"):
                        details["description"] = str(s["description"]).strip()
                    if s.get("sameAs") and not details.get("same_as"):
                        s_as = s["sameAs"]
                        details["same_as"] = [str(u).strip() for u in (s_as if isinstance(s_as, list) else [s_as]) if str(u).strip()]
                    if s.get("address") and not details.get("location"):
                        addr = s["address"]
                        if isinstance(addr, str):
                            details["location"] = addr.strip()
                        elif isinstance(addr, dict):
                            parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                            details["location"] = ", ".join(p for p in parts if p)
                    if s.get("knowsAbout") and not details.get("category"):
                        ka = s["knowsAbout"]
                        details["category"] = ka if isinstance(ka, str) else (", ".join(ka[:3]) if isinstance(ka, list) else None)
        return details

    @classmethod
    def _extract_from_opengraph(cls, pages: List[PageEvidence]) -> Dict[str, Optional[str]]:
        res: Dict[str, Optional[str]] = {"site_name": None, "image": None, "description": None}
        for page in pages:
            meta = getattr(page, "meta_tags", None) or getattr(page, "og_tags", None) or {}
            og_site = meta.get("og:site_name") or meta.get("og:site-name")
            if og_site and str(og_site).strip().lower() not in BANNED_NAMES and not res["site_name"]:
                res["site_name"] = str(og_site).strip()
            if meta.get("og:image") and not res["image"]:
                res["image"] = str(meta["og:image"]).strip()
            if meta.get("og:description") and not res["description"]:
                res["description"] = str(meta["og:description"]).strip()
        return res

    @classmethod
    def _extract_from_dom_branding(cls, pages: List[PageEvidence]) -> Optional[str]:
        if not pages:
            return None
        # Check first page (usually homepage)
        first_page = pages[0]
        for img in getattr(first_page, "images", []) or []:
            alt = img.get("alt", "") if isinstance(img, dict) else getattr(img, "alt", "")
            if alt and "logo" in alt.lower():
                # Extract brand before or after 'logo' (e.g. "AlienHouse Networks Logo")
                cleaned = re.sub(r"(?i)\s*(?:official\s*)?logo\s*", "", alt).strip()
                if cleaned and cleaned.lower() not in BANNED_NAMES and len(cleaned) < 40:
                    return cleaned
        return None

    @classmethod
    def _extract_from_title(cls, pages: List[PageEvidence]) -> Optional[str]:
        if not pages:
            return None
        first_page = pages[0]
        title = first_page.title or ""
        # Common title format: "Page Title | Brand Name" or "Brand Name: Value Prop"
        delimiters = [" | ", " - ", " – ", " — ", " : ", ": "]
        for d in delimiters:
            if d in title:
                parts = title.split(d)
                # Typically brand is at the end ("Services | AlienHouse Networks") or at the beginning
                candidate_end = parts[-1].strip()
                if candidate_end and len(candidate_end) < 35 and candidate_end.lower() not in BANNED_NAMES:
                    return candidate_end
                candidate_start = parts[0].strip()
                if candidate_start and len(candidate_start) < 35 and candidate_start.lower() not in BANNED_NAMES:
                    return candidate_start
        return None
