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
    scale_score: float = Field(0.25, ge=0.0, le=1.0)
    scale_confidence: float = Field(0.5, ge=0.0, le=1.0)
    scale_tier: str = "boutique"  # "boutique" | "mid_market" | "enterprise"
    scale_signals: Dict[str, Any] = Field(default_factory=dict)
    value_proposition_motto: str = ""
    target_buyer_persona: str = ""
    geography_scope: str = "Global"


class IntentExtractor:
    """
    Extracts the demand universe of an audited website from its crawl artifacts.
    Evaluates hard scale signals (team size, case studies, sales motion) to compute
    a continuous scale score (0.0 - 1.0) with confidence.
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

    def _compute_scale(
        self,
        business_profile: Optional[BusinessProfile],
        pages: Optional[List[PageEvidence]],
    ) -> tuple[float, float, str, Dict[str, Any]]:
        """
        Derives an objective continuous scale score (0.0 - 1.0) based on hard page evidence:
        - Team headcount mentions
        - Case studies & portfolio depth
        - Commercial motion (Self-serve / 'Book a call' vs 'Request RFP' / 'Enterprise Sales')
        - Career scale & office footprint
        """
        signals: Dict[str, Any] = {
            "headcount_signal": None,
            "case_study_count": 0,
            "commercial_motion": "unknown",
            "enterprise_cues": 0,
            "boutique_cues": 0,
        }

        # Check explicit profile hints first
        profile_scale_hint = getattr(business_profile, "target_org_scale", None) if business_profile else None
        
        all_text = ""
        case_studies = 0
        boutique_matches = 0
        enterprise_matches = 0

        for page in (pages or [])[:15]:
            body = (page.body_text or "").lower()
            all_text += " " + body
            url = (page.url or "").lower()

            # Case study / portfolio clues
            if any(term in url for term in ["/case-stud", "/work", "/portfolio", "/clients", "/project"]):
                case_studies += 1

            # Boutique signals
            if any(term in body for term in [
                "boutique studio", "boutique agency", "compact team", "agile team",
                "independent studio", "founder-led", "book a 15-min", "book a call",
                "schedule a call", "calendly.com", "small team", "dev shop"
            ]):
                boutique_matches += 1

            # Enterprise signals
            if any(term in body for term in [
                "request rfp", "contact enterprise sales", "procurement", "global offices",
                "fortune 500", "global 2000", "soc 2 type ii", "iso 27001",
                "investor relations", "annual report", "300,000 employees", "nasdaq:", "nyse:"
            ]):
                enterprise_matches += 1

        signals["case_study_count"] = case_studies
        signals["boutique_cues"] = boutique_matches
        signals["enterprise_cues"] = enterprise_matches

        # Headcount regex: e.g. "team of 18", "25+ engineers"
        headcount = None
        m = re.search(r"\b(?:team of|over|about)\s+(\d{1,5})\+?\s+(?:engineers|specialists|consultants|people|employees)\b", all_text)
        if m:
            try:
                headcount = int(m.group(1))
                signals["headcount_signal"] = headcount
            except ValueError:
                pass

        # Calculate continuous scale
        # Boutique default: 0.15 - 0.25 (e.g. AlienHouse, Thoughtbot, boutique studios)
        # Mid-market: 0.40 - 0.65
        # Enterprise: 0.80 - 1.0 (e.g. Accenture, Capgemini, Infosys)
        scale_score = 0.22  # Sensible default for boutique/SMB web presence
        confidence = 0.50

        if headcount:
            confidence = 0.85
            if headcount <= 30:
                scale_score = 0.15
            elif headcount <= 100:
                scale_score = 0.35
            elif headcount <= 500:
                scale_score = 0.55
            elif headcount <= 5000:
                scale_score = 0.80
            else:
                scale_score = 0.95
        else:
            if enterprise_matches > boutique_matches and enterprise_matches >= 2:
                scale_score = min(0.95, 0.70 + (enterprise_matches * 0.05))
                confidence = 0.75
                signals["commercial_motion"] = "enterprise_rfp"
            elif boutique_matches > 0 or case_studies > 0:
                scale_score = max(0.12, 0.25 - (boutique_matches * 0.03))
                confidence = 0.70
                signals["commercial_motion"] = "boutique_direct"
            elif profile_scale_hint:
                if str(profile_scale_hint).lower() == "enterprise":
                    scale_score = 0.85
                    confidence = 0.60
                elif str(profile_scale_hint).lower() == "mid_market":
                    scale_score = 0.50
                    confidence = 0.60
                else:
                    scale_score = 0.20
                    confidence = 0.60

        scale_score = round(max(0.05, min(0.98, scale_score)), 2)
        tier = "boutique" if scale_score <= 0.35 else "mid_market" if scale_score <= 0.70 else "enterprise"
        return scale_score, confidence, tier, signals

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
        motto = ""
        buyer = ""
        geo = "Global"

        if business_profile:
            if business_profile.niche and len(business_profile.niche.strip()) > 3:
                topics.add(business_profile.niche.strip())
            if business_profile.industry and len(business_profile.industry.strip()) > 3:
                topics.add(business_profile.industry.strip())
            if business_profile.target_audience:
                audiences.add(business_profile.target_audience.strip())
                buyer = business_profile.target_audience.strip()
            if getattr(business_profile, "economic_buyer_title", None):
                buyer = business_profile.economic_buyer_title.strip()
            if getattr(business_profile, "value_proposition", None):
                motto = business_profile.value_proposition.strip()
            if getattr(business_profile, "geography", None):
                geo = business_profile.geography.strip()

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
                    if not motto and len(h1_clean) > 10:
                        motto = h1_clean
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

        # 3. Derive scale score and tier from hard signals
        scale_score, scale_confidence, scale_tier, scale_signals = self._compute_scale(business_profile, pages)

        # 4. Synthesize commercial search intents & seed queries
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
            scale_score=scale_score,
            scale_confidence=scale_confidence,
            scale_tier=scale_tier,
            scale_signals=scale_signals,
            value_proposition_motto=motto or f"Digital solutions and services by {brand}",
            target_buyer_persona=buyer or "Technology and commercial leaders",
            geography_scope=geo,
        )


intent_extractor = IntentExtractor()
