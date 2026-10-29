"""
Dristik AI Automated Competitor Discovery & 7-Vector Benchmark Engine

Discovers product-level rivals from the audited business identity.
Never treats category giants (Cloudflare, HubSpot, Salesforce, Shopify) as
default competitors. Never invents TAM/SAM/SOM or live rival scores.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.models import BusinessProfile
from app.seo.competitive.intent_extractor import intent_extractor
from app.seo.competitive.verification.liveness import candidate_verifier, is_aggregator_or_directory
from app.seo.competitive.scoring.similarity_scorer import similarity_scorer

logger = logging.getLogger("dristik.competitor_discovery")

VECTOR_KEYS = [
    "seo_visibility",
    "content_authority",
    "ai_citation",
    "commercial_clarity",
    "trust_proof",
    "technical_health",
    "conversion_strength",
]


class CompetitorMetric(BaseModel):
    name: str
    score: int = Field(..., ge=0, le=100)
    verdict: str
    gap_analysis: str


class CompetitorProfile(BaseModel):
    competitor_id: str
    domain: str
    brand_name: str
    market_overlap: str
    discovered_reason: str
    metrics: Dict[str, CompetitorMetric] = Field(default_factory=dict)
    overall_score: Optional[int] = None
    winning_queries: List[str] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)
    discovery_confidence: float = 0.4
    score_basis: str = "unmeasured_proxy"
    product_overlap_reason: str = ""
    market_size: Optional[str] = None
    scale_score: Optional[float] = None
    scale_tier: Optional[str] = None
    competitor_class: str = "DIRECT"  # "DIRECT" | "ASPIRATIONAL" | "INDIRECT" | "SEARCH_ONLY"
    source: str = "auto_discovered"   # "user_specified" | "auto_discovered" | "serp_overlap"
    similarity_score: Optional[float] = None
    similarity_breakdown: Dict[str, float] = Field(default_factory=dict)
    is_rejected: bool = False


class BenchmarkTableRow(BaseModel):
    dimension: str
    dimension_key: str
    target_score: Optional[int] = None
    competitor_1: Optional[int] = None
    competitor_2: Optional[int] = None
    competitor_3: Optional[int] = None
    gap_verdict: str


class CompetitorBenchmarkMatrix(BaseModel):
    target_domain: str
    target_brand: str
    market_niche: str
    target_scale_score: Optional[float] = None
    target_scale_tier: Optional[str] = None
    target_motto: Optional[str] = None
    target_buyer_persona: Optional[str] = None
    status: str = "AVAILABLE"
    message: Optional[str] = None
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    aspirational_competitors: List[CompetitorProfile] = Field(default_factory=list)
    rejected_domains: List[str] = Field(default_factory=list)
    comparative_table: List[Dict[str, Any]] = Field(default_factory=list)
    primary_competitive_gap: str = "No competitor data available"
    recommended_offensive_plays: List[str] = Field(default_factory=list)
    discovery_method: str = "heuristic"
    market_size_status: str = "not_measured"
    market_size_note: str = (
        "Market size (TAM/SAM/SOM) was not measured. Dristik does not invent market figures."
    )
    score_basis: str = "target_from_audit_peers_unmeasured"


# Giants may only be returned when the audited identity actually matches their product.
GIANT_REQUIRED_TOKENS: Dict[str, List[str]] = {
    "cloudflare.com": ["cdn", "ddos", "waf", "dns hosting", "edge network", "zero trust network"],
    "akamai.com": ["cdn", "waap", "edge cloud", "content delivery"],
    "fastly.com": ["cdn", "edge compute", "vcl", "content delivery"],
    "hubspot.com": ["crm", "inbound marketing", "marketing automation", "hubspot"],
    "salesforce.com": ["crm", "sales cloud", "service cloud", "revenue cloud"],
    "zendesk.com": ["help desk", "ticketing", "customer support platform", "zendesk"],
    "shopify.com": ["shopify", "ecommerce platform", "online store builder", "dtc platform"],
    "bigcommerce.com": ["ecommerce platform", "bigcommerce", "headless commerce"],
    "woocommerce.com": ["woocommerce", "wordpress commerce"],
    "paloaltonetworks.com": ["firewall", "sase", "ngfw", "network security"],
    "zscaler.com": ["zscaler", "zero trust exchange", "secure web gateway"],
    "crowdstrike.com": ["edr", "xdr", "endpoint protection", "crowdstrike"],
}

VERTICALS: List[Dict[str, Any]] = [
    {
        "id": "cdn_edge",
        "tokens": ["cdn", "ddos", "waf", "anycast", "edge network", "content delivery network", "dns hosting"],
        "peers": [
            {"brand": "Cloudflare", "domain": "cloudflare.com", "overlap": "Direct: edge, DNS, WAF, DDoS"},
            {"brand": "Akamai", "domain": "akamai.com", "overlap": "Direct: enterprise CDN and WAAP"},
            {"brand": "Fastly", "domain": "fastly.com", "overlap": "Direct: programmable edge CDN"},
        ],
    },
    {
        "id": "crm_inbound",
        "tokens": ["crm", "inbound marketing", "marketing automation", "revenue cloud", "salesforce", "hubspot"],
        "peers": [
            {"brand": "HubSpot", "domain": "hubspot.com", "overlap": "Direct: inbound CRM and automation"},
            {"brand": "Salesforce", "domain": "salesforce.com", "overlap": "Direct: enterprise CRM"},
            {"brand": "Pipedrive", "domain": "pipedrive.com", "overlap": "Adjacent: pipeline CRM for SMB"},
        ],
    },
    {
        "id": "ecommerce_platform",
        "tokens": ["shopify", "woocommerce", "bigcommerce", "ecommerce platform", "online store builder", "dtc platform"],
        "peers": [
            {"brand": "Shopify", "domain": "shopify.com", "overlap": "Direct: hosted commerce platform"},
            {"brand": "BigCommerce", "domain": "bigcommerce.com", "overlap": "Direct: open SaaS commerce"},
            {"brand": "WooCommerce", "domain": "woocommerce.com", "overlap": "Direct: WordPress commerce"},
        ],
    },
    {
        "id": "cybersecurity",
        "tokens": ["next-gen firewall", "sase", "endpoint protection", "xdr", "secure web gateway", "zero trust exchange"],
        "peers": [
            {"brand": "Palo Alto Networks", "domain": "paloaltonetworks.com", "overlap": "Direct: enterprise SASE / NGFW"},
            {"brand": "Zscaler", "domain": "zscaler.com", "overlap": "Direct: zero-trust exchange"},
            {"brand": "CrowdStrike", "domain": "crowdstrike.com", "overlap": "Adjacent: endpoint / XDR"},
        ],
    },
    {
        "id": "custom_software",
        "tokens": [
            "custom software", "software development company", "web development agency",
            "app development", "digital engineering", "product engineering", "it services firm",
        ],
        "peers": [
            {"brand": "Thoughtbot", "domain": "thoughtbot.com", "overlap": "Direct: boutique digital product studio"},
            {"brand": "STRV", "domain": "strv.com", "overlap": "Direct: digital engineering & product design studio"},
            {"brand": "Metalab", "domain": "metalab.com", "overlap": "Direct: interface and product engineering studio"},
        ],
    },
    {
        "id": "seo_geo_audit",
        "tokens": [
            "seo audit", "geo audit", "ai citation", "generative engine optimization",
            "website intelligence", "ai search audit", "answer engine optimization",
        ],
        "peers": [
            {"brand": "Profound", "domain": "tryprofound.com", "overlap": "Direct: AI answer-engine visibility"},
            {"brand": "Peec AI", "domain": "peec.ai", "overlap": "Direct: AI search monitoring"},
            {"brand": "Surfer", "domain": "surferseo.com", "overlap": "Adjacent: on-page SEO content scoring"},
        ],
    },
    {
        "id": "digital_agency",
        "tokens": ["digital marketing agency", "seo agency", "performance marketing", "creative agency", "branding agency"],
        "peers": [
            {"brand": "Tinuiti", "domain": "tinuiti.com", "overlap": "Direct: performance marketing agency"},
            {"brand": "Wpromote", "domain": "wpromote.com", "overlap": "Direct: digital performance agency"},
            {"brand": "Directive", "domain": "directiveconsulting.com", "overlap": "Direct: B2B demand agency"},
        ],
    },
    {
        "id": "legal",
        "tokens": ["law firm", "attorney", "legal services", "advocates", "solicitors"],
        "peers": [
            {"brand": "Clio", "domain": "clio.com", "overlap": "Adjacent: legal practice platform (not a law firm)"},
            {"brand": "LegalZoom", "domain": "legalzoom.com", "overlap": "Adjacent: packaged legal services"},
            {"brand": "Avvo", "domain": "avvo.com", "overlap": "Adjacent: lawyer directory"},
        ],
    },
    {
        "id": "healthcare_clinic",
        "tokens": ["clinic", "hospital", "dental", "physician", "healthcare practice", "patient portal"],
        "peers": [
            {"brand": "Zocdoc", "domain": "zocdoc.com", "overlap": "Adjacent: care discovery marketplace"},
            {"brand": "Practo", "domain": "practo.com", "overlap": "Adjacent: clinic discovery in India"},
            {"brand": "Healthgrades", "domain": "healthgrades.com", "overlap": "Adjacent: provider directory"},
        ],
    },
    {
        "id": "restaurant",
        "tokens": ["restaurant", "cafe", "bakery", "fine dining", "cloud kitchen", "food delivery brand"],
        "peers": [
            {"brand": "Zomato", "domain": "zomato.com", "overlap": "Adjacent: restaurant discovery (India)"},
            {"brand": "OpenTable", "domain": "opentable.com", "overlap": "Adjacent: reservations"},
            {"brand": "Swiggy", "domain": "swiggy.com", "overlap": "Adjacent: food delivery marketplace"},
        ],
    },
    {
        "id": "real_estate",
        "tokens": ["real estate", "realtor", "property listing", "brokerage", "housing"],
        "peers": [
            {"brand": "Zillow", "domain": "zillow.com", "overlap": "Adjacent: listings marketplace"},
            {"brand": "MagicBricks", "domain": "magicbricks.com", "overlap": "Adjacent: India listings"},
            {"brand": "99acres", "domain": "99acres.com", "overlap": "Adjacent: India listings"},
        ],
    },
    {
        "id": "fintech",
        "tokens": ["neobank", "payments api", "lending platform", "invoice financing", "upi", "core banking saas"],
        "peers": [
            {"brand": "Stripe", "domain": "stripe.com", "overlap": "Direct only if the offer is payments infrastructure"},
            {"brand": "Razorpay", "domain": "razorpay.com", "overlap": "Direct for India payments"},
            {"brand": "Plaid", "domain": "plaid.com", "overlap": "Adjacent: bank connectivity"},
        ],
    },
    {
        "id": "hr_payroll",
        "tokens": ["hris", "payroll software", "applicant tracking", "workforce management"],
        "peers": [
            {"brand": "Workday", "domain": "workday.com", "overlap": "Direct: enterprise HCM"},
            {"brand": "BambooHR", "domain": "bamboohr.com", "overlap": "Direct: SMB HRIS"},
            {"brand": "Rippling", "domain": "rippling.com", "overlap": "Direct: HR + IT + payroll"},
        ],
    },
    {
        "id": "education",
        "tokens": ["edtech", "lms", "online course platform", "coaching institute", "k12 school"],
        "peers": [
            {"brand": "Coursera", "domain": "coursera.com", "overlap": "Adjacent: course marketplace"},
            {"brand": "Udemy", "domain": "udemy.com", "overlap": "Adjacent: creator courses"},
            {"brand": "Teachable", "domain": "teachable.com", "overlap": "Direct if the offer is a course platform"},
        ],
    },
]


def _normalize_domain(raw: str) -> str:
    d = (raw or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split("?")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def _identity_text(domain: str, niche: str, industry: str, biz_name: str, extras: str = "") -> str:
    return f"{domain} {niche} {industry} {biz_name} {extras}".lower()


def _token_hit_count(text: str, tokens: List[str]) -> int:
    hits = 0
    for token in tokens:
        if " " in token:
            if token in text:
                hits += 2
        else:
            if re.search(rf"\b{re.escape(token)}\b", text):
                hits += 1
    return hits


def _is_plausible_giant(domain: str, identity: str) -> bool:
    required = GIANT_REQUIRED_TOKENS.get(domain)
    if not required:
        return True
    return any(tok in identity for tok in required)


class CompetitorDiscoveryEngine:
    """
    Product-level competitor discovery. Prefers LLM when a real business profile
    exists; otherwise a high-precision vertical match. Never defaults to CDN/CRM giants.
    """

    def _select_vertical(self, identity: str) -> Optional[Dict[str, Any]]:
        best = None
        best_score = 0
        for vertical in VERTICALS:
            score = _token_hit_count(identity, vertical["tokens"])
            if score > best_score:
                best_score = score
                best = vertical
        if best_score <= 0:
            return None
        return best

    def _fallback_peers(self, identity: str, niche: str) -> List[Dict[str, Any]]:
        """Heuristic names are guesses, not measurements. Return none — UI shows null until LLM or a user URL."""
        return []

    def _filter_giants(self, peers: List[Dict[str, Any]], identity: str) -> List[Dict[str, Any]]:
        kept = []
        for p in peers:
            domain = _normalize_domain(p.get("domain", ""))
            if not _is_plausible_giant(domain, identity):
                logger.info("Dropped implausible giant %s for identity=%s", domain, identity[:80])
                continue
            kept.append(p)
        return kept

    def _has_real_identity(self, bp: Optional[BusinessProfile]) -> bool:
        if not bp:
            return False
        name = (bp.business_name or "").strip()
        niche = (bp.niche or "").strip()
        industry = (bp.industry or "").strip()
        generic = {"unknown", "unknown business", "target enterprise", "enterprise technology", "software", "technology", ""}
        if name.lower() not in generic:
            return True
        if niche.lower() not in generic and len(niche) > 12:
            return True
        if industry.lower() not in generic and len(industry) > 12:
            return True
        return False

    async def _llm_discover(
        self,
        biz_name: str,
        industry: str,
        niche: str,
        domain: str,
        audience: str,
        offerings: str,
        scale_score: float = 0.25,
        scale_tier: str = "boutique",
        motto: str = "",
        buyer_persona: str = "",
    ) -> Optional[List[Dict[str, Any]]]:
        from app.core.config import settings
        if not settings.has_active_llm_key:
            return None
        try:
            from app.inference.llm_client import LLMClient
            from app.inference.json_repair import repair_and_parse_json

            client = LLMClient(timeout=12)
            creds = settings.get_llm_credentials()
            model = creds.get("model_fast") or creds.get("model_reasoning")
            system = (
                "You identify REAL peer-level competitors matching the target's exact commercial tier and offerings. "
                "A true direct competitor sells comparable services to the same buyer persona at similar organization scale. "
                "CRITICAL SCALE PARITY RULES:\n"
                "- If the target is a boutique agency, dev shop, or studio (scale <= 0.35), you MUST identify boutique agencies, dev shops, or specialized consultancies of similar size (10-50 team). NEVER name multi-billion dollar public conglomerates or massive IT outsourcing firms (such as Accenture, Capgemini, TCS, Infosys, Cognizant, Wipro, HCL, Deloitte, or IBM).\n"
                "- If the target is an enterprise platform, name enterprise platforms.\n"
                "- Do NOT name Cloudflare, HubSpot, Salesforce, Shopify, Akamai, Fastly, or Zendesk unless the target sells that exact software category.\n"
                "- Do NOT invent market size, search volume, or revenue figures.\n"
                "Return JSON only."
            )
            user = (
                f"Target domain: {domain}\n"
                f"Brand: {biz_name}\n"
                f"Industry: {industry}\n"
                f"Niche: {niche}\n"
                f"Value Proposition / Motto: {motto or 'Not specified'}\n"
                f"Target Buyer Persona: {buyer_persona or audience}\n"
                f"Commercial Scale: {scale_tier.upper()} (Scale Score: {scale_score}/1.0)\n"
                f"Offerings: {offerings}\n\n"
                "Return: {\"competitors\":[{\"brand\":\"\",\"domain\":\"\",\"overlap\":\"Direct|Adjacent|Indirect\","
                "\"scale_tier\":\"boutique|mid_market|enterprise\",\"reason\":\"same offer + same scale in one sentence\"}],"
                "\"market_size_status\":\"unknown\"}\n"
                "Provide 3-4 real peer competitor domains. Domains must be real registrable hostnames."
            )
            response = await client.generate_chat_completion(
                model=model,
                system_prompt=system,
                user_prompt=user,
                temperature=0.1,
                max_tokens=700,
                response_format="DEFAULT",
            )
            parsed = repair_and_parse_json(response.get("content") or "")
            if not parsed or not isinstance(parsed, dict):
                return None
            rows = parsed.get("competitors") or []
            out: List[Dict[str, Any]] = []
            identity = _identity_text(domain, niche, industry, biz_name, f"{audience} {offerings}")
            for row in rows[:4]:
                c_domain = _normalize_domain(str(row.get("domain") or ""))
                brand = (row.get("brand") or "").strip()
                if not c_domain or "." not in c_domain:
                    continue
                if c_domain == domain:
                    continue
                if is_aggregator_or_directory(c_domain):
                    continue
                if not _is_plausible_giant(c_domain, identity):
                    continue
                c_tier = str(row.get("scale_tier") or scale_tier).lower()
                c_scale = 0.20 if c_tier == "boutique" else 0.50 if c_tier == "mid_market" else 0.90
                out.append({
                    "brand": brand or c_domain.split(".")[0].title(),
                    "domain": c_domain,
                    "overlap": str(row.get("overlap") or "Direct"),
                    "reason": str(row.get("reason") or "Identified from business identity and scale match."),
                    "scale_score": c_scale,
                    "scale_tier": c_tier,
                    "confidence": 0.75,
                })
            return out if len(out) >= 1 else None
        except Exception as exc:
            logger.warning("LLM competitor discovery failed: %s", exc)
            return None

    @staticmethod
    def _measured_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def _target_vectors(self, honest_scores: Optional[Any]) -> Dict[str, Optional[int]]:
        """Only emit scores that were actually measured on this audit. Never default 38/72/76."""
        empty: Dict[str, Optional[int]] = {k: None for k in VECTOR_KEYS}
        if honest_scores is None:
            return empty
        h = self._measured_int(getattr(honest_scores, "human_score", None))
        g = self._measured_int(getattr(honest_scores, "google_score", None))
        ai = self._measured_int(getattr(honest_scores, "ai_citation_score", None))
        content = None if h is None or g is None else int(round((h + g) / 2))
        return {
            "seo_visibility": g,
            "content_authority": content,
            "ai_citation": ai,
            "commercial_clarity": h,
            "trust_proof": g,
            "technical_health": g,
            "conversion_strength": h,
        }

    def _build_profiles(
        self,
        peers: List[Dict[str, Any]],
        niche: str,
        biz_name: str,
        method: str,
    ) -> List[CompetitorProfile]:
        profiles: List[CompetitorProfile] = []
        for i, p in enumerate(peers):
            conf = float(p.get("confidence") or 0.5)
            comp_class = p.get("competitor_class") or "DIRECT"
            source = p.get("source") or ("user_specified" if "User-specified" in str(p.get("overlap", "")) else "auto_discovered")
            profiles.append(
                CompetitorProfile(
                    competitor_id=f"comp_{i+1}",
                    domain=p["domain"],
                    brand_name=p["brand"],
                    market_overlap=p.get("overlap") or "Verified peer overlap",
                    discovered_reason=p.get("reason") or f"Matched from {niche} at comparable scale.",
                    overall_score=None,
                    winning_queries=[],
                    vulnerabilities=[],
                    discovery_confidence=round(conf, 2),
                    score_basis="unmeasured",
                    product_overlap_reason=p.get("reason") or "",
                    market_size=None,
                    scale_score=p.get("scale_score"),
                    scale_tier=p.get("scale_tier"),
                    competitor_class=comp_class,
                    source=source,
                    similarity_score=p.get("similarity_score"),
                    similarity_breakdown=p.get("similarity_breakdown", {}),
                    is_rejected=bool(p.get("is_rejected", False)),
                )
            )
        return profiles

    def _table(
        self,
        target_vectors: Dict[str, Optional[int]],
        biz_name: str,
        peer_count: int,
    ) -> List[Dict[str, Any]]:
        rows = []
        labels = {
            "seo_visibility": "1. SEO Visibility",
            "content_authority": "2. Content Authority",
            "ai_citation": "3. AI Citation Presence",
            "commercial_clarity": "4. Commercial Clarity",
            "trust_proof": "5. Trust & Proof",
            "technical_health": "6. Technical Health",
            "conversion_strength": "7. Conversion Strength",
        }
        if peer_count == 0:
            verdict = (
                f"{biz_name}'s score is from this audit where measured; otherwise null. "
                "No rival was identified or crawled, so competitor columns are null."
            )
        else:
            verdict = (
                f"{biz_name}'s score is from this audit where measured. "
                "Rival columns are null until those sites are crawled. No invented marks."
            )
        for key, name in labels.items():
            rows.append({
                "dimension": name,
                "dimension_key": key,
                "target_score": target_vectors.get(key),
                "competitor_1": None,
                "competitor_2": None,
                "competitor_3": None,
                "gap_verdict": verdict,
            })
        return rows

    async def discover_and_benchmark(
        self,
        business_profile: Optional[BusinessProfile] = None,
        website_url: str = "",
        competitor_urls: Optional[List[str]] = None,
        honest_scores: Optional[Any] = None,
        rejected_domains: Optional[List[str]] = None,
    ) -> CompetitorBenchmarkMatrix:
        domain = _normalize_domain(website_url) or "target-domain.com"
        
        # 1. Extract rich intent universe with hard scale signals
        intent_univ = intent_extractor.extract_universe(
            domain=domain,
            business_profile=business_profile,
            pages=None,
        )

        biz_name = (
            business_profile.business_name
            if business_profile and business_profile.business_name not in ["Unknown", "Unknown Business", ""]
            else intent_univ.brand_name or "Target Enterprise"
        )
        niche = (business_profile.niche or "").strip() if business_profile else ""
        industry = (business_profile.industry or "").strip() if business_profile else ""
        if not niche:
            niche = industry or "unknown"
        audience = business_profile.target_audience if business_profile and business_profile.target_audience else ""
        offerings = "; ".join(intent_univ.products_services[:6]) if intent_univ.products_services else ""
        if not offerings and business_profile:
            parts = []
            if getattr(business_profile, "products", None):
                parts.extend(business_profile.products[:4])
            if getattr(business_profile, "services", None):
                parts.extend(business_profile.services[:4])
            offerings = "; ".join(str(p) for p in parts if p)

        identity = _identity_text(domain, niche, industry, biz_name, f"{audience} {offerings}")
        target_vectors = self._target_vectors(honest_scores)
        target_scale = intent_univ.scale_score
        target_tier = intent_univ.scale_tier
        target_motto = intent_univ.value_proposition_motto
        target_buyer = intent_univ.target_buyer_persona

        rejected_set = set([_normalize_domain(r) for r in (rejected_domains or []) if r])

        target_prof_dict = {
            "scale_score": target_scale,
            "services": intent_univ.products_services,
            "niche": niche,
            "target_buyer_persona": target_buyer,
            "brand_name": biz_name,
            "geography": intent_univ.geography_scope,
        }

        direct_peers: List[Dict[str, Any]] = []
        aspirational_peers: List[Dict[str, Any]] = []

        # 2. Process user-supplied competitors (Always preserved & tagged)
        if competitor_urls:
            cleaned_urls = [_normalize_domain(u) for u in competitor_urls if u and u.strip()]
            cleaned_urls = [c for c in cleaned_urls if c and c not in rejected_set]
            for c_domain in cleaned_urls[:3]:
                c_brand = c_domain.split(".")[0].capitalize()
                direct_peers.append({
                    "brand": c_brand,
                    "domain": c_domain,
                    "overlap": f"User-specified rival: {c_domain}",
                    "reason": f"Custom benchmark requested by user for {c_domain}.",
                    "scale_score": target_scale,
                    "scale_tier": target_tier,
                    "competitor_class": "DIRECT",
                    "source": "user_specified",
                    "similarity_score": 1.0,
                    "similarity_breakdown": {"user_specified": 1.0},
                    "confidence": 0.95,
                })

        # 3. Candidate discovery via LLM / Fallbacks
        candidate_pool: List[Dict[str, Any]] = []
        if self._has_real_identity(business_profile):
            llm_candidates = await self._llm_discover(
                biz_name=biz_name,
                industry=industry,
                niche=niche,
                domain=domain,
                audience=audience,
                offerings=offerings,
                scale_score=target_scale,
                scale_tier=target_tier,
                motto=target_motto,
                buyer_persona=target_buyer,
            )
            if llm_candidates:
                candidate_pool.extend(llm_candidates)

        # If sparse, add high-precision vertical peers
        if len(candidate_pool) < 2:
            vert = self._select_vertical(identity)
            if vert:
                candidate_pool.extend(vert.get("peers") or [])

        # 4. Filter, score, and classify candidate pool
        seen_domains = set([p["domain"] for p in direct_peers])
        seen_domains.add(domain)

        for cand in candidate_pool:
            c_domain = _normalize_domain(cand.get("domain", ""))
            if not c_domain or c_domain in seen_domains or c_domain in rejected_set:
                continue
            if is_aggregator_or_directory(c_domain):
                continue
            if not _is_plausible_giant(c_domain, identity):
                continue

            c_brand = cand.get("brand") or c_domain.split(".")[0].title()
            c_scale = float(cand.get("scale_score") or (0.95 if "Thoughtworks" in c_brand or "Accenture" in c_brand else target_scale))
            
            cand_prof_dict = {
                "domain": c_domain,
                "brand_name": c_brand,
                "scale_score": c_scale,
                "services": [cand.get("overlap", "")],
                "niche": niche,
                "target_buyer_persona": target_buyer,
                "geography": intent_univ.geography_scope,
            }

            sim_score, breakdown, comp_class, explanation = similarity_scorer.compute_similarity(
                target_profile=target_prof_dict,
                candidate_profile=cand_prof_dict,
                shared_queries=intent_univ.discovery_seed_queries[:3],
            )

            peer_entry = {
                "brand": c_brand,
                "domain": c_domain,
                "overlap": f"{comp_class.value}: {c_domain}",
                "reason": explanation,
                "scale_score": c_scale,
                "scale_tier": "enterprise" if c_scale >= 0.70 else "mid_market" if c_scale >= 0.35 else "boutique",
                "competitor_class": comp_class.value,
                "source": "auto_discovered",
                "similarity_score": sim_score,
                "similarity_breakdown": breakdown,
                "confidence": round(float(cand.get("confidence") or 0.60), 2),
            }

            if comp_class.value == "ASPIRATIONAL":
                aspirational_peers.append(peer_entry)
            else:
                direct_peers.append(peer_entry)
            seen_domains.add(c_domain)

        # 5. Build profiles
        active_direct = direct_peers[:4]
        active_aspirational = aspirational_peers[:3]

        competitor_profiles = self._build_profiles(active_direct, niche, biz_name, "evidence_discovery")
        aspirational_profiles = self._build_profiles(active_aspirational, niche, biz_name, "evidence_discovery")
        table_rows = self._table(target_vectors, biz_name, len(competitor_profiles))

        has_user_urls = any(p.source == "user_specified" for p in competitor_profiles)
        discovery_method = "user_and_auto" if has_user_urls and len(competitor_profiles) > 1 else "user_supplied" if has_user_urls else "evidence_match"

        if competitor_profiles:
            c1_name = competitor_profiles[0].brand_name
            primary_gap = (
                f"{biz_name} is evaluated against {c1_name} and peer-matched competitors at comparable commercial scale "
                f"({target_tier.title()}, Scale Score: {target_scale}). Scores stay null until competitor sites are crawled."
            )
            offensive_plays = [
                f"Run an audit on {c1_name} to measure empirical keyword and technical gaps.",
                f"Emphasize your core differentiator: '{target_motto[:60]}...'",
            ]
            method_label = f"Evidence-matched against {biz_name}'s {target_tier} market scale ({target_scale}/1.0). Uncrawled rival scores stay null."
            status = "AVAILABLE"
        else:
            primary_gap = (
                "No direct rivals identified matching this scale tier. Add 1–3 custom rival domains above to compare."
            )
            offensive_plays = [
                "Enter a real rival domain in the box above to benchmark.",
            ]
            method_label = "No direct peers identified. Table shows your audit scores; rival columns remain null."
            status = "UNAVAILABLE"
            discovery_method = "none"

        return CompetitorBenchmarkMatrix(
            target_domain=domain,
            target_brand=biz_name,
            market_niche=niche,
            target_scale_score=target_scale,
            target_scale_tier=target_tier,
            target_motto=target_motto,
            target_buyer_persona=target_buyer,
            status=status,
            message=method_label,
            competitors=competitor_profiles[:4],
            aspirational_competitors=aspirational_profiles[:3],
            rejected_domains=list(rejected_set),
            comparative_table=table_rows,
            primary_competitive_gap=primary_gap,
            recommended_offensive_plays=offensive_plays,
            discovery_method=discovery_method,
            market_size_status="not_measured",
            market_size_note="Market size (TAM/SAM/SOM) was not measured. Dristik does not invent market figures.",
            score_basis="target_measured_peers_null",
        )

    def discover_and_benchmark_sync(self, *args, **kwargs) -> CompetitorBenchmarkMatrix:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            raise RuntimeError("Use await discover_and_benchmark() inside an event loop")
        return asyncio.run(self.discover_and_benchmark(*args, **kwargs))


competitor_discovery_engine = CompetitorDiscoveryEngine()
