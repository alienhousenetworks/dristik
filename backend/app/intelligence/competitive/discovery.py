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
    status: str = "AVAILABLE"
    message: Optional[str] = None
    competitors: List[CompetitorProfile] = Field(default_factory=list)
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
            {"brand": "Thoughtworks", "domain": "thoughtworks.com", "overlap": "Direct: custom product engineering"},
            {"brand": "EPAM", "domain": "epam.com", "overlap": "Direct: digital engineering services"},
            {"brand": "Globant", "domain": "globant.com", "overlap": "Direct: software product studios"},
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
                "You identify REAL product-level competitors. "
                "A competitor sells the same primary offer to the same buyer in the same commercial motion and geography. "
                "Do NOT name Cloudflare, HubSpot, Salesforce, Shopify, Akamai, Fastly, Zendesk, Amazon, Google, or Microsoft "
                "unless the target actually sells that same product. "
                "Do NOT invent TAM, market share, search volume, or revenue. "
                "Return JSON only."
            )
            user = (
                f"Target domain: {domain}\n"
                f"Brand: {biz_name}\n"
                f"Industry: {industry}\n"
                f"Niche: {niche}\n"
                f"Audience: {audience}\n"
                f"Offerings: {offerings}\n\n"
                "Return: {\"competitors\":[{\"brand\":\"\",\"domain\":\"\",\"overlap\":\"Direct|Adjacent|Indirect\","
                "\"reason\":\"same offer + same buyer in one sentence\"}],"
                "\"market_size_status\":\"unknown\"}\n"
                "Exactly 3 competitors. Domains must be real registrable hostnames."
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
            for row in rows[:3]:
                c_domain = _normalize_domain(str(row.get("domain") or ""))
                brand = (row.get("brand") or "").strip()
                if not c_domain or "." not in c_domain:
                    continue
                if c_domain == domain:
                    continue
                if not _is_plausible_giant(c_domain, identity):
                    continue
                out.append({
                    "brand": brand or c_domain.split(".")[0].title(),
                    "domain": c_domain,
                    "overlap": str(row.get("overlap") or "Direct"),
                    "reason": str(row.get("reason") or "LLM product-level match from business identity."),
                    "confidence": 0.72,
                })
            return out[:3] if len(out) >= 2 else None
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
        for i, p in enumerate(peers[:3]):
            conf = float(p.get("confidence") or 0.4)
            profiles.append(
                CompetitorProfile(
                    competitor_id=f"comp_{i+1}",
                    domain=p["domain"],
                    brand_name=p["brand"],
                    market_overlap=p.get("overlap") or "Unverified overlap",
                    discovered_reason=p.get("reason") or f"Matched from {niche}.",
                    overall_score=None,
                    winning_queries=[],
                    vulnerabilities=[],
                    discovery_confidence=round(conf, 2),
                    score_basis="unmeasured",
                    product_overlap_reason=p.get("reason") or "",
                    market_size=None,
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
        honest_scores: Optional[Any] = None
    ) -> CompetitorBenchmarkMatrix:
        biz_name = (
            business_profile.business_name
            if business_profile and business_profile.business_name not in ["Unknown", "Unknown Business"]
            else "Target Enterprise"
        )
        niche = (business_profile.niche or "").strip() if business_profile else ""
        industry = (business_profile.industry or "").strip() if business_profile else ""
        if not niche:
            niche = industry or "unknown"
        audience = business_profile.target_audience if business_profile and business_profile.target_audience else ""
        offerings = ""
        if business_profile:
            parts = []
            if getattr(business_profile, "products", None):
                parts.extend(business_profile.products[:6])
            if getattr(business_profile, "services", None):
                parts.extend(business_profile.services[:6])
            if business_profile.value_proposition:
                parts.append(business_profile.value_proposition)
            offerings = "; ".join(str(p) for p in parts if p)
        domain = _normalize_domain(website_url) or "target-domain.com"
        identity = _identity_text(domain, niche, industry, biz_name, f"{audience} {offerings}")

        target_vectors = self._target_vectors(honest_scores)
        discovery_method = "none"
        peers: List[Dict[str, Any]] = []

        if competitor_urls:
            cleaned = [_normalize_domain(u) for u in competitor_urls if u and u.strip()]
            cleaned = [c for c in cleaned if c][:3]
            for c_domain in cleaned:
                c_brand = c_domain.split(".")[0].capitalize()
                peers.append({
                    "brand": c_brand,
                    "domain": c_domain,
                    "overlap": f"User-specified rival: {c_domain}",
                    "reason": f"You asked to benchmark {c_domain}. Rival scores stay null until that site is crawled.",
                    "confidence": 0.9,
                })
            discovery_method = "user_supplied"
        elif self._has_real_identity(business_profile):
            llm_peers = await self._llm_discover(
                biz_name=biz_name,
                industry=industry,
                niche=niche,
                domain=domain,
                audience=audience,
                offerings=offerings,
            )
            if llm_peers:
                peers = self._filter_giants(llm_peers, identity)
                discovery_method = "llm_identity"

        competitor_profiles = self._build_profiles(peers, niche, biz_name, discovery_method)
        table_rows = self._table(target_vectors, biz_name, len(competitor_profiles))

        if discovery_method == "user_supplied" and competitor_profiles:
            c1_name = competitor_profiles[0].brand_name
            primary_gap = (
                f"{biz_name} is listed against {c1_name} and any other URLs you entered. "
                "Rival scores are null (those sites were not crawled). Market size was not measured."
            )
            offensive_plays = [
                f"Crawl {c1_name} (or run a bake-off) before claiming a score gap.",
                "Add FAQPage + Organization schema from observed entities only.",
            ]
            method_label = "Used the competitor URLs you entered. Peer scores are null until those sites are crawled."
            status = "AVAILABLE"
        elif competitor_profiles:
            c1_name = competitor_profiles[0].brand_name
            primary_gap = (
                f"Identity match suggests {c1_name} as a product-level rival. "
                "This is a name from the model, not a live crawl. Peer scores and market size are null."
            )
            offensive_plays = [
                f"Add {c1_name}'s domain as a bake-off URL to measure it.",
                "Do not treat unmeasured rival columns as a lead or a lag.",
            ]
            method_label = f"Named rivals from the audited identity of {biz_name}. Scores remain null until crawled."
            status = "AVAILABLE"
        else:
            primary_gap = (
                "No rival was identified. Auto-discovery does not invent Cloudflare/HubSpot placeholders "
                "or copy your scores into empty columns. Add 1–3 rival domains to compare."
            )
            offensive_plays = [
                "Enter a real rival domain above. Until then competitor scores stay null.",
            ]
            method_label = (
                "No measured or model-identified rivals. Table shows your audit scores where they exist; "
                "everything else is null."
            )
            status = "UNAVAILABLE"
            discovery_method = "none"

        return CompetitorBenchmarkMatrix(
            target_domain=domain,
            target_brand=biz_name,
            market_niche=niche,
            status=status,
            message=method_label,
            competitors=competitor_profiles[:3],
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
