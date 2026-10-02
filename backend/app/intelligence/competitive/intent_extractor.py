"""
Dristik AI Intent & Demand Extractor
Extracts topic universe, commercial search intents, entities, and product positioning
directly from the customer's crawled pages and business profile.
Discovers competitors against actual business demand rather than generic keywords.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.domain.models import BusinessProfile, PageEvidence


class ExtractedIntentUniverse(BaseModel):
    brand_name: str
    target_domain: str
    primary_topics: List[str] = Field(default_factory=list)
    commercial_intents: List[str] = Field(default_factory=list)
    products_services: List[str] = Field(default_factory=list)
    target_entities: List[str] = Field(default_factory=list)
    audience_segments: List[str] = Field(default_factory=list)
    discovery_seed_queries: List[str] = Field(default_factory=list)


class IntentExtractor:
    """
    Extracts the demand universe of an audited website from its crawl artifacts.
    """

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "by", "about", "against", "between", "into", "through", "during", "before",
        "after", "above", "below", "from", "up", "down", "in", "out", "on", "off",
        "over", "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "any", "both", "each", "few", "more", "most",
        "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
        "home", "about", "contact", "privacy", "terms", "policy", "login", "signup",
        "sign", "get", "started", "learn", "more", "read", "view", "menu"
    }

    def extract_universe(
        self,
        domain: str,
        business_profile: Optional[BusinessProfile] = None,
        pages: Optional[List[PageEvidence]] = None,
    ) -> ExtractedIntentUniverse:
        clean_domain = (domain or "").lower().replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "")
        brand = (
            business_profile.business_name
            if business_profile and business_profile.business_name not in ["Unknown", "Unknown Business", ""]
            else clean_domain.split(".")[0].capitalize()
        )

        topics: Set[str] = set()
        commercial_intents: Set[str] = set()
        products_services: Set[str] = set()
        entities: Set[str] = set()
        audiences: Set[str] = set()

        # 1. Ingest from BusinessProfile
        if business_profile:
            if business_profile.niche and len(business_profile.niche.strip()) > 3:
                topics.add(business_profile.niche.strip())
            if business_profile.industry and len(business_profile.industry.strip()) > 3:
                topics.add(business_profile.industry.strip())
            if business_profile.target_audience:
                audiences.add(business_profile.target_audience.strip())

            for prod in getattr(business_profile, "products", []) or []:
                p_clean = str(prod).strip()
                if p_clean and len(p_clean) > 2:
                    products_services.add(p_clean)
                    topics.add(p_clean)

            for srv in getattr(business_profile, "services", []) or []:
                s_clean = str(srv).strip()
                if s_clean and len(s_clean) > 2:
                    products_services.add(s_clean)
                    topics.add(s_clean)

            for ent in getattr(business_profile, "entities", []) or []:
                e_clean = str(ent).strip()
                if e_clean and len(e_clean) > 2:
                    entities.add(e_clean)

        # 2. Ingest from crawled PageEvidence
        for page in (pages or [])[:15]:
            # H1 headings are high-intent category/solution declarations
            for h1 in page.h1 or []:
                h1_clean = re.sub(r"[^\w\s-]", "", h1).strip()
                if 5 < len(h1_clean) < 60:
                    topics.add(h1_clean)
                    if any(kw in h1_clean.lower() for kw in ["software", "platform", "solution", "tool", "service", "app"]):
                        commercial_intents.add(f"{h1_clean.lower()} commercial")

            # Page title signals
            if page.title:
                parts = [p.strip() for p in re.split(r"[-|•·:]", page.title) if p.strip()]
                for p in parts:
                    if p.lower() != brand.lower() and 4 < len(p) < 45:
                        topics.add(p)

            # Schema types reveal business entity model
            for st in page.schema_types or []:
                if st not in ["WebSite", "WebPage", "BreadcrumbList"]:
                    entities.add(st)

        # 3. Synthesize commercial search intents & seed queries
        topic_list = sorted(list(topics), key=len, reverse=True)[:8]
        prod_list = sorted(list(products_services), key=len, reverse=True)[:6]

        seed_queries: List[str] = []
        for t in topic_list[:4]:
            seed_queries.append(f"best {t.lower()}")
            seed_queries.append(f"{t.lower()} alternatives")
            commercial_intents.add(f"{t.lower()} software")
            commercial_intents.add(f"{t.lower()} platform")

        for p in prod_list[:3]:
            seed_queries.append(f"{p.lower()} pricing")
            seed_queries.append(f"{p.lower()} vs")

        # Fallback if sparse evidence
        if not topic_list:
            fallback = clean_domain.split(".")[0]
            topic_list = [fallback]
            commercial_intents.add(f"{fallback} services")
            seed_queries.append(f"{fallback} competitors")

        return ExtractedIntentUniverse(
            brand_name=brand,
            target_domain=clean_domain,
            primary_topics=topic_list,
            commercial_intents=sorted(list(commercial_intents))[:10],
            products_services=prod_list,
            target_entities=sorted(list(entities))[:8],
            audience_segments=sorted(list(audiences))[:4],
            discovery_seed_queries=seed_queries[:10],
        )


intent_extractor = IntentExtractor()
