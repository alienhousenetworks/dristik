"""
Dristik AI 5-Tier Pricing, Credit Costing, All-In Unit Economics & Feature Gating Catalog.

Single source of truth for:
  - The 5 user-selectable audit tiers (basic, starter, growth, premium, enterprise)
  - Orthogonal credit pricing: required_credits = base_credits + (pages * credits_per_page)
  - All-in COGS accounting (Server/Playwright + GA4/GSC/CrUX/Live-GEO Connectors + LLM Inference + Rendering + Razorpay 2.4%)
  - Strict feature-gating flags enforced by orchestrator, BudgetManager, and API routes
  - 5 Razorpay-purchasable Credit Top-Up Packs
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


CREDIT_LIST_PRICE_INR: int = 10
CREDIT_LIST_PRICE_USD: float = 0.12
RAZORPAY_FEE_PCT: float = 0.0236  # 2% + 18% GST on gateway fee


class AuditTierId(str, Enum):
    BASIC = "basic"
    STARTER = "starter"
    GROWTH = "growth"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# 10 core SEO/CRO specialists allowed in Starter AI tier
STARTER_SPECIALIST_IDS: Tuple[str, ...] = (
    "technical_seo_audit",
    "crawl_indexability_audit",
    "meta_onpage_audit",
    "heading_structure_audit",
    "internal_linking_audit",
    "content_clarity_audit",
    "cta_conversion_audit",
    "trust_signals_audit",
    "mobile_ux_audit",
    "value_proposition_audit",
)

# 20 specialists allowed in Growth Intelligence tier (Starter + AEO/GEO/CRO depth)
GROWTH_SPECIALIST_IDS: Tuple[str, ...] = STARTER_SPECIALIST_IDS + (
    "schema_structured_data_audit",
    "entity_authority_audit",
    "direct_answer_audit",
    "citation_readiness_score",
    "faq_question_coverage_audit",
    "information_gain_score",
    "form_friction_audit",
    "pricing_clarity_audit",
    "core_web_vitals_audit",
    "social_proof_audit",
)


@dataclass(frozen=True)
class TierFeatureFlags:
    max_pages: int
    enable_ai_verifier: bool
    specialist_limit: int  # 0 = none, 10 = starter, 20 = growth, 35 = all
    aeo_question_count: int  # 0, 25, or 100
    enable_live_geo_probes: bool
    enable_ga4_gsc: bool
    enable_psi_crux: bool
    copywriting_page_cap: int  # 0 = disabled, -1 = unlimited
    remediation_mode: str  # none | deterministic | ai_patch_pack | ai_pr_sync
    critic_mode: str  # none | sampled | full | cross_provider
    enable_competitor_bakeoff: bool
    report_documents_mode: str  # none | exec_pdf_template | exec_pair_ai | full_5_5_standard | full_5_5_deep
    report_sizing_mode: str  # none | standard | deep
    white_label_enabled: bool
    ai_depth_mode: str  # deterministic_only | fast_tier | tiered_frontier | frontier_all
    enable_patch_pack_download: bool
    enable_pptx_download: bool


@dataclass(frozen=True)
class TierCostModel:
    """All-in unit COGS model in INR (used for margin transparency & pricing guardrails)."""
    infra_base_inr: float
    infra_per_page_inr: float
    connector_base_inr: float
    connector_per_page_inr: float
    ai_base_inr: float
    ai_per_page_inr: float
    live_geo_inr: float
    render_inr: float


@dataclass(frozen=True)
class AuditTierSpec:
    id: str
    rank: int
    name: str
    tagline: str
    badge: str
    popular: bool
    base_credits: int
    credits_per_page: int
    features: TierFeatureFlags
    cost_model: TierCostModel
    included_highlights: Tuple[str, ...]
    locked_highlights: Tuple[str, ...]


AUDIT_TIERS: Dict[str, AuditTierSpec] = {
    AuditTierId.BASIC.value: AuditTierSpec(
        id="basic",
        rank=1,
        name="Basic Scan",
        tagline="Fast deterministic technical SEO & crawl hygiene — zero LLM overhead.",
        badge="Essential Crawl",
        popular=False,
        base_credits=5,
        credits_per_page=1,
        features=TierFeatureFlags(
            max_pages=25,
            enable_ai_verifier=False,
            specialist_limit=0,
            aeo_question_count=0,
            enable_live_geo_probes=False,
            enable_ga4_gsc=False,
            enable_psi_crux=False,
            copywriting_page_cap=0,
            remediation_mode="none",
            critic_mode="none",
            enable_competitor_bakeoff=False,
            report_documents_mode="none",
            report_sizing_mode="none",
            white_label_enabled=False,
            ai_depth_mode="deterministic_only",
            enable_patch_pack_download=False,
            enable_pptx_download=False,
        ),
        cost_model=TierCostModel(
            infra_base_inr=5.0,
            infra_per_page_inr=2.0,
            connector_base_inr=0.0,
            connector_per_page_inr=0.0,
            ai_base_inr=0.0,
            ai_per_page_inr=0.0,
            live_geo_inr=0.0,
            render_inr=1.0,
        ),
        included_highlights=(
            "18 deterministic Python technical SEO & crawl analyzers",
            "HTTP status, canonicals, headings, links, forms & security checks",
            "Interactive dashboard & JSON findings export",
        ),
        locked_highlights=(
            "No AI specialists or AEO/GEO evaluation",
            "No GA4 / GSC / CrUX connectors",
            "No AI copywriting, patch pack, or PDF/PPT executive suite",
        ),
    ),
    AuditTierId.STARTER.value: AuditTierSpec(
        id="starter",
        rank=2,
        name="Starter AI",
        tagline="Core fast-tier AI diagnostics for SEO & CRO plus a clean executive PDF.",
        badge="Small Sites",
        popular=False,
        base_credits=15,
        credits_per_page=2,
        features=TierFeatureFlags(
            max_pages=50,
            enable_ai_verifier=False,
            specialist_limit=10,
            aeo_question_count=0,
            enable_live_geo_probes=False,
            enable_ga4_gsc=False,
            enable_psi_crux=False,
            copywriting_page_cap=0,
            remediation_mode="deterministic",
            critic_mode="none",
            enable_competitor_bakeoff=False,
            report_documents_mode="exec_pdf_template",
            report_sizing_mode="standard",
            white_label_enabled=False,
            ai_depth_mode="fast_tier",
            enable_patch_pack_download=False,
            enable_pptx_download=False,
        ),
        cost_model=TierCostModel(
            infra_base_inr=6.0,
            infra_per_page_inr=2.2,
            connector_base_inr=0.0,
            connector_per_page_inr=0.0,
            ai_base_inr=15.0,
            ai_per_page_inr=4.0,
            live_geo_inr=0.0,
            render_inr=4.0,
        ),
        included_highlights=(
            "Everything in Basic + Fast-tier AI Business Understanding",
            "10 core SEO & CRO AI specialists",
            "Prioritized remediation roadmap & 1 Executive PDF",
        ),
        locked_highlights=(
            "No AEO RAG sandbox or Live GEO citation probes",
            "No GA4 / GSC / PageSpeed connectors",
            "No AI copywriting, developer patch pack, or PPT decks",
        ),
    ),
    AuditTierId.GROWTH.value: AuditTierSpec(
        id="growth",
        rank=3,
        name="Growth Intelligence",
        tagline="GA4 & GSC grounded audit with 20 AI specialists, 25-Q AEO RAG & Executive deck.",
        badge="Growing Teams",
        popular=False,
        base_credits=30,
        credits_per_page=4,
        features=TierFeatureFlags(
            max_pages=100,
            enable_ai_verifier=True,
            specialist_limit=20,
            aeo_question_count=25,
            enable_live_geo_probes=False,
            enable_ga4_gsc=True,
            enable_psi_crux=False,
            copywriting_page_cap=5,
            remediation_mode="deterministic",
            critic_mode="sampled",
            enable_competitor_bakeoff=False,
            report_documents_mode="exec_pair_ai",
            report_sizing_mode="standard",
            white_label_enabled=False,
            ai_depth_mode="tiered_frontier",
            enable_patch_pack_download=False,
            enable_pptx_download=True,
        ),
        cost_model=TierCostModel(
            infra_base_inr=8.0,
            infra_per_page_inr=2.5,
            connector_base_inr=8.0,
            connector_per_page_inr=0.5,
            ai_base_inr=30.0,
            ai_per_page_inr=12.0,
            live_geo_inr=0.0,
            render_inr=8.0,
        ),
        included_highlights=(
            "GA4 & Google Search Console connectors enabled",
            "20 AI specialists (SEO + AEO + CRO) + AI finding verifier",
            "25-Question AEO Hybrid RAG + Top-5 page AI copywriting",
            "AI-narrated Executive PDF + Executive PPTX deck",
        ),
        locked_highlights=(
            "No 100-Q AEO sandbox or Live GEO web-search probes",
            "No full 5-PDF / 5-PPT suite or AI Patch Pack ZIP",
            "No 3-Competitor Bake-Off",
        ),
    ),
    AuditTierId.PREMIUM.value: AuditTierSpec(
        id="premium",
        rank=4,
        name="Premium Full-Stack",
        tagline="Full ₹20–₹30/page Frontier AI workforce, 100-Q AEO, all connectors & 5 PDF + 5 PPT suite.",
        badge="Recommended Flagship",
        popular=True,
        base_credits=50,
        credits_per_page=6,
        features=TierFeatureFlags(
            max_pages=200,
            enable_ai_verifier=True,
            specialist_limit=35,
            aeo_question_count=100,
            enable_live_geo_probes=False,
            enable_ga4_gsc=True,
            enable_psi_crux=True,
            copywriting_page_cap=40,
            remediation_mode="ai_patch_pack",
            critic_mode="full",
            enable_competitor_bakeoff=False,
            report_documents_mode="full_5_5_standard",
            report_sizing_mode="standard",
            white_label_enabled=False,
            ai_depth_mode="tiered_frontier",
            enable_patch_pack_download=True,
            enable_pptx_download=True,
        ),
        cost_model=TierCostModel(
            infra_base_inr=10.0,
            infra_per_page_inr=2.5,
            connector_base_inr=10.0,
            connector_per_page_inr=1.5,
            ai_base_inr=45.0,
            ai_per_page_inr=22.0,
            live_geo_inr=0.0,
            render_inr=15.0,
        ),
        included_highlights=(
            "All 4 pillars & all 35 Frontier AI specialists + 100% Critic",
            "100-Question AEO Hybrid RAG + GEO citation readiness",
            "GA4, GSC, PageSpeed Insights & CrUX connectors",
            "Per-page AI copywriting + Developer Patch Pack (ZIP)",
            "Full 5 AI-narrated PDFs + 5 AI-narrated PPTXs",
        ),
        locked_highlights=(
            "No Live GEO web-search probes or 3-Competitor Bake-Off",
            "No White-Label export or GitHub/CMS PR sync",
        ),
    ),
    AuditTierId.ENTERPRISE.value: AuditTierSpec(
        id="enterprise",
        rank=5,
        name="Enterprise Command",
        tagline="Maximum reasoning models everywhere, Live GEO citations, 3-Competitor Bake-Off & White-Label.",
        badge="Agency & Enterprise",
        popular=False,
        base_credits=90,
        credits_per_page=10,
        features=TierFeatureFlags(
            max_pages=500,
            enable_ai_verifier=True,
            specialist_limit=35,
            aeo_question_count=100,
            enable_live_geo_probes=True,
            enable_ga4_gsc=True,
            enable_psi_crux=True,
            copywriting_page_cap=-1,
            remediation_mode="ai_pr_sync",
            critic_mode="cross_provider",
            enable_competitor_bakeoff=True,
            report_documents_mode="full_5_5_deep",
            report_sizing_mode="deep",
            white_label_enabled=True,
            ai_depth_mode="frontier_all",
            enable_patch_pack_download=True,
            enable_pptx_download=True,
        ),
        cost_model=TierCostModel(
            infra_base_inr=15.0,
            infra_per_page_inr=3.0,
            connector_base_inr=15.0,
            connector_per_page_inr=2.0,
            ai_base_inr=85.0,
            ai_per_page_inr=35.0,
            live_geo_inr=45.0,
            render_inr=25.0,
        ),
        included_highlights=(
            "Everything in Premium with top reasoning models (frontier_all)",
            "Cross-provider Adversarial Critic verification",
            "Live GEO citation probes (ChatGPT, Perplexity, Claude)",
            "Head-to-head 3-Competitor Bake-Off & battlecard",
            "Deep 5 PDF + 5 PPT suite with White-Label & GitHub/CMS PR sync",
        ),
        locked_highlights=(),
    ),
}

# Backward-compatible aliases from legacy plan IDs
_TIER_ALIASES: Dict[str, str] = {
    "free_scan": "basic",
    "professional": "growth",
    "diagnostic": "premium",
    "business": "premium",
    "diagnostic_bakeoff": "enterprise",
}

CREDIT_PACKS: List[Dict[str, Any]] = [
    {
        "id": "pack_50",
        "name": "50 Credits Starter Pack",
        "credits": 50,
        "price_inr": 500,
        "price_display": "₹500",
        "price_usd": 6,
        "effective_inr_per_credit": 10.0,
        "discount_pct": 0,
        "badge": "Pay As You Go",
        "popular": False,
    },
    {
        "id": "pack_150",
        "name": "150 Credits Growth Pack",
        "credits": 150,
        "price_inr": 1399,
        "price_display": "₹1,399",
        "price_usd": 17,
        "effective_inr_per_credit": 9.33,
        "discount_pct": 7,
        "badge": "Best for 1–2 Full Audits",
        "popular": False,
    },
    {
        "id": "pack_500",
        "name": "500 Credits Pro Pack",
        "credits": 500,
        "price_inr": 4299,
        "price_display": "₹4,299",
        "price_usd": 50,
        "effective_inr_per_credit": 8.60,
        "discount_pct": 14,
        "badge": "Most Popular",
        "popular": True,
    },
    {
        "id": "pack_1500",
        "name": "1,500 Credits Agency Pack",
        "credits": 1500,
        "price_inr": 11999,
        "price_display": "₹11,999",
        "price_usd": 140,
        "effective_inr_per_credit": 8.00,
        "discount_pct": 20,
        "badge": "Agency Volume",
        "popular": False,
    },
    {
        "id": "pack_5000",
        "name": "5,000 Credits Enterprise Pack",
        "credits": 5000,
        "price_inr": 34999,
        "price_display": "₹34,999",
        "price_usd": 410,
        "effective_inr_per_credit": 7.00,
        "discount_pct": 30,
        "badge": "Enterprise Volume",
        "popular": False,
    },
]


def normalize_tier_id(tier_id: Optional[str], default: str = "basic") -> str:
    raw = (tier_id or "").strip().lower()
    if raw in AUDIT_TIERS:
        return raw
    if raw in _TIER_ALIASES:
        return _TIER_ALIASES[raw]
    return default


def get_tier_spec(tier_id: Optional[str], default: str = "basic") -> AuditTierSpec:
    return AUDIT_TIERS[normalize_tier_id(tier_id, default=default)]


def get_credit_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    pid = (pack_id or "").strip().lower()
    return next((p for p in CREDIT_PACKS if p["id"] == pid), None)


def recommend_pack_for_shortfall(shortfall_credits: int) -> Dict[str, Any]:
    need = max(1, int(shortfall_credits))
    for pack in CREDIT_PACKS:
        if pack["credits"] >= need:
            return pack
    return CREDIT_PACKS[-1]


def estimate_audit_quote(tier_id: Optional[str], pages: int) -> Dict[str, Any]:
    """Compute credit cost, INR/USD list price, all-in COGS breakdown, and gross margin."""
    spec = get_tier_spec(tier_id)
    n = max(1, int(pages or 1))
    required_credits = spec.base_credits + (n * spec.credits_per_page)
    price_inr = required_credits * CREDIT_LIST_PRICE_INR
    price_usd = round(required_credits * CREDIT_LIST_PRICE_USD, 2)

    cm = spec.cost_model
    infra_inr = round(cm.infra_base_inr + (n * cm.infra_per_page_inr), 2)
    connectors_inr = round(cm.connector_base_inr + (n * cm.connector_per_page_inr), 2)
    ai_inr = round(cm.ai_base_inr + (n * cm.ai_per_page_inr), 2)
    live_geo_inr = round(cm.live_geo_inr, 2)
    render_inr = round(cm.render_inr, 2)
    gateway_fee_inr = round(price_inr * RAZORPAY_FEE_PCT, 2)
    total_cogs_inr = round(
        infra_inr + connectors_inr + ai_inr + live_geo_inr + render_inr + gateway_fee_inr,
        2,
    )
    margin_pct = round(((price_inr - total_cogs_inr) / price_inr) * 100.0, 1) if price_inr > 0 else 0.0

    return {
        "tier_id": spec.id,
        "tier_name": spec.name,
        "pages": n,
        "max_pages_allowed": spec.features.max_pages,
        "exceeds_max_pages": n > spec.features.max_pages,
        "base_credits": spec.base_credits,
        "credits_per_page": spec.credits_per_page,
        "required_credits": required_credits,
        "price_inr_est": price_inr,
        "price_usd_est": price_usd,
        "cogs_breakdown_inr": {
            "infra_and_crawl_inr": infra_inr,
            "connectors_ga4_gsc_crux_inr": connectors_inr,
            "llm_inference_inr": ai_inr,
            "live_geo_probes_inr": live_geo_inr,
            "pdf_ppt_render_inr": render_inr,
            "payment_gateway_fee_inr": gateway_fee_inr,
            "total_cogs_inr": total_cogs_inr,
        },
        "estimated_gross_margin_pct": margin_pct,
        "features": asdict(spec.features),
        "included_highlights": list(spec.included_highlights),
        "locked_highlights": list(spec.locked_highlights),
    }


def is_feature_enabled(tier_id: Optional[str], feature_name: str) -> bool:
    spec = get_tier_spec(tier_id)
    val = getattr(spec.features, feature_name, False)
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val != 0
    if isinstance(val, str):
        return val.lower() not in ("", "none", "disabled")
    return bool(val)


def serialize_tier(spec: AuditTierSpec) -> Dict[str, Any]:
    sample_10 = estimate_audit_quote(spec.id, 10)
    return {
        "id": spec.id,
        "rank": spec.rank,
        "name": spec.name,
        "tagline": spec.tagline,
        "badge": spec.badge,
        "popular": spec.popular,
        "base_credits": spec.base_credits,
        "credits_per_page": spec.credits_per_page,
        "sample_10_pages_credits": sample_10["required_credits"],
        "sample_10_pages_inr": sample_10["price_inr_est"],
        "sample_10_pages_usd": sample_10["price_usd_est"],
        "features": asdict(spec.features),
        "included_highlights": list(spec.included_highlights),
        "locked_highlights": list(spec.locked_highlights),
    }


def list_serialized_tiers() -> List[Dict[str, Any]]:
    ordered = sorted(AUDIT_TIERS.values(), key=lambda t: t.rank)
    return [serialize_tier(t) for t in ordered]


def specialist_allowed_for_tier(tier_id: Optional[str], agent_id: str, index_in_pool: int = 0) -> bool:
    """Determine if a specialist agent is unlocked for the given tier."""
    spec = get_tier_spec(tier_id)
    limit = spec.features.specialist_limit
    if limit <= 0:
        return False
    if limit >= 35:
        return True
    aid = (agent_id or "").strip().lower()
    if limit <= 10:
        return aid in STARTER_SPECIALIST_IDS or index_in_pool < limit
    if limit <= 20:
        return aid in GROWTH_SPECIALIST_IDS or index_in_pool < limit
    return index_in_pool < limit
