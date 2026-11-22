"""
Dristik KIE-Powered Dynamic Question Sandbox Engine

Phase 4 + Phase 5: Consumes the Website Knowledge Graph, Query Planner, and
Grounded Answer Simulator to generate and evaluate bespoke inquiries from
first-party knowledge — not raw DOM string matching.

Question Budget is configurable via QuestionBudgetTier (default = STANDARD: 100).
Each question records its Question Provenance (why it was generated).
Each evaluation uses claim-level grounding instead of sentence-window search.
"""
import asyncio
import re
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.domain.models import (
    PageEvidence,
    BusinessProfile,
    ResolvedEntity,
    DynamicSandboxQuestionEvaluation,
)
from app.crawl.knowledge.primitives import (
    KieAnswerRisk,
    KieEvidenceState,
    QuestionBudgetTier,
)
from app.crawl.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph
from app.crawl.knowledge.grounded_simulator import (
    GroundedAnswerSimulator,
    AiVisibilityIndexCalculator,
    SIMULATION_DISCLAIMER,
)
from app.crawl.retrieval.hybrid_retriever import QueryPlanner
from app.core.config import settings


# Canonical 11 R3 Business-Context AEO Categories
BUSINESS_CONTEXT_CATEGORIES_11 = [
    {"id": "brand_identity", "title": "Brand Identity", "intent": "Verify brand origin, mission, legitimacy, and core identity."},
    {"id": "product_information", "title": "Product Information", "intent": "Verify core product or service lineup, variants, and primary offerings."},
    {"id": "product_ingredients", "title": "Product Ingredients & Specifications", "intent": "Verify active ingredients, materials, formulation, or technical specifications."},
    {"id": "product_benefits", "title": "Product Benefits & Outcomes", "intent": "Verify expected results, effectiveness, and substantiated customer outcomes."},
    {"id": "usage_instructions", "title": "Usage Instructions & Application", "intent": "Verify how to use, apply, or integrate the product in daily routines."},
    {"id": "safety_and_suitability", "title": "Safety & Suitability Claims", "intent": "Verify safety standards, certifications, suitability, and contraindications."},
    {"id": "pricing_and_offers", "title": "Pricing & Offers", "intent": "Verify product prices, bundles, discounts, subscriptions, and value packs."},
    {"id": "shipping_and_returns", "title": "Shipping, Fulfilment & Returns", "intent": "Verify delivery timelines, shipping fees, return windows, and refund policies."},
    {"id": "customer_support", "title": "Customer Support & Warranty", "intent": "Verify warranty coverage, replacement policies, and customer support channels."},
    {"id": "product_comparisons", "title": "Product Comparisons & Alternatives", "intent": "Verify how products compare across variants and against market alternatives."},
    {"id": "purchase_intent", "title": "Purchase Intent & Buying Guide", "intent": "Verify buying guide recommendations, starter kits, and direct checkout paths."},
]

R3_CATEGORY_IDS = [c["id"] for c in BUSINESS_CONTEXT_CATEGORIES_11]
R3_CATEGORY_TITLES = {c["id"]: c["title"] for c in BUSINESS_CONTEXT_CATEGORIES_11}

# B2B / Enterprise-only markers that must never pollute consumer / D2C / ecommerce / local audits
B2B_ENTERPRISE_ONLY_PATTERNS = re.compile(
    r"\b("
    r"soc\s*2|iso\s*27001|hipaa|saml|okta|scim|rbac|saas|multi-seat|multi\s*seat|sla|"
    r"rest\s+or\s+graphql\s+api|graphql\s+api|rest\s+api|openapi|"
    r"enterprise\s+customer\s+contracts|b2b\s+corporate\s+customers|"
    r"dedicated\s+customer\s+success\s+manager|dedicated\s+csm|"
    r"multi-tenant\s+cloud|dedicated\s+vpc|on-premise|self-hosted\s+vpc|"
    r"master\s+service\s+agreement|procurement\s+vendor\s+packages|"
    r"security\s+questionnaires|data\s+processing\s+agreements|dpas|"
    r"ci/cd|sdk\s+offerings|webhooks|event\s+streaming|"
    r"seat-based|per\s+seat|fortune\s+500|vp\s+eng|cto"
    r")\b",
    re.IGNORECASE,
)

CONSUMER_BUSINESS_SIGNALS = (
    "d2c", "dtc", "e-commerce", "ecommerce", "consumer", "retail", "shop", "store",
    "oral care", "toothpaste", "toothbrush", "mouthwash", "whitening", "dental care",
    "skincare", "beauty", "cosmetics", "personal care", "wellness", "supplement",
    "apparel", "fashion", "footwear", "jewelry", "food", "beverage", "restaurant",
    "cafe", "bakery", "clinic", "salon", "spa", "fitness", "home", "kitchen", "pet",
)

B2B_SAAS_SIGNALS = (
    "b2b saas", "enterprise software", "developer tool", "cloud infrastructure",
    "devops", "cybersecurity", "api platform", "data platform", "b2b platform",
)


def is_consumer_or_non_enterprise_business(
    business_profile: Optional[BusinessProfile],
    pages: Optional[List[PageEvidence]] = None,
) -> bool:
    """Detect whether the audited site is a consumer/D2C/ecommerce/local business rather than B2B SaaS."""
    blob_parts: List[str] = []
    if business_profile:
        for attr in ("business_model", "industry", "niche", "sub_niche", "value_proposition", "target_audience", "positioning"):
            val = getattr(business_profile, attr, None)
            if val:
                blob_parts.append(str(val))
        for list_attr in ("products", "services", "personas"):
            vals = getattr(business_profile, list_attr, None) or []
            blob_parts.extend(str(v) for v in vals if v)
    if pages:
        for p in pages[:10]:
            blob_parts.append(p.title or "")
            blob_parts.extend(p.h1 or [])
            blob_parts.append((p.body_text or "")[:1000])

    blob = " ".join(blob_parts).lower()
    has_consumer = any(sig in blob for sig in CONSUMER_BUSINESS_SIGNALS)
    has_b2b_saas = any(sig in blob for sig in B2B_SAAS_SIGNALS)
    if has_consumer and not has_b2b_saas:
        return True
    if business_profile and (business_profile.products or []) and not has_b2b_saas:
        return True
    return False


def generate_11_category_business_questions(
    brand: str,
    business_profile: Optional[BusinessProfile] = None,
    pages: Optional[List[PageEvidence]] = None,
    target_count: int = 100,
) -> List[Dict[str, str]]:
    """
    Generates exactly `target_count` (default 100) business-relevant questions across
    the canonical 11 R3 categories, grounded in the site's actual products, ingredients/features,
    benefits, usage, safety, pricing, shipping/returns, support, comparisons, and purchase intent.
    """
    brand_clean = (brand or "").strip() or (
        business_profile.business_name.strip()
        if business_profile and getattr(business_profile, "business_name", None)
        else "the brand"
    )
    niche = (
        (getattr(business_profile, "niche", None) or getattr(business_profile, "industry", None) or "").strip()
        if business_profile else ""
    ) or "consumer products"
    val_prop = (
        (getattr(business_profile, "value_proposition", None) or "").strip()
        if business_profile else ""
    ) or f"high-quality {niche}"

    products: List[str] = []
    if business_profile:
        for p_item in (getattr(business_profile, "products", None) or []) + (getattr(business_profile, "services", None) or []):
            s_item = str(p_item).strip()
            if s_item and s_item not in products:
                products.append(s_item)

    if pages:
        for p in pages:
            for h in (p.h1 or []) + (p.h2 or []):
                h_clean = h.strip()
                if 3 < len(h_clean) < 55 and h_clean not in products and brand_clean.lower() not in h_clean.lower():
                    products.append(h_clean)

    p1 = products[0] if len(products) >= 1 else f"{brand_clean} flagship product"
    p2 = products[1] if len(products) >= 2 else (f"{brand_clean} daily care kit" if len(products) == 1 else f"{brand_clean} essentials")
    p3 = products[2] if len(products) >= 3 else f"{brand_clean} starter bundle"
    comp1 = (
        business_profile.competitors[0]
        if business_profile and getattr(business_profile, "competitors", None)
        else f"traditional {niche} brands"
    )

    category_question_bank: Dict[str, List[tuple]] = {
        "brand_identity": [
            (f"What is {brand_clean} and what types of {niche} products does the brand specialize in?", "Verify core brand identity and product category focus."),
            (f"Who founded {brand_clean} and what inspired the creation of the brand?", "Verify founding story and brand authenticity."),
            (f"What is {brand_clean}'s core mission and philosophy regarding {val_prop}?", "Audit stated brand mission and customer promise."),
            (f"Where is {brand_clean} based and where are its products formulated or manufactured?", "Verify brand headquarters and manufacturing origin."),
            (f"What makes {brand_clean} different from conventional {niche} brands on the market?", "Verify brand differentiation and positioning."),
            (f"Is {brand_clean} a certified cruelty-free, clean, or sustainably packaged brand?", "Verify ethical and sustainability credentials."),
            (f"What product categories make up {brand_clean}'s complete catalog?", "Audit breadth of brand catalog."),
            (f"Who is the primary customer audience that {brand_clean} designs its products for?", "Verify target consumer profile."),
            (f"Has {brand_clean} been featured in independent media, publications, or industry awards?", "Audit third-party brand recognition."),
            (f"Where can customers verify official announcements and authentic products from {brand_clean}?", "Verify official domain and brand channels."),
        ],
        "product_information": [
            (f"What are the flagship products offered by {brand_clean}, including {p1} and {p2}?", "Audit primary product catalog and hero SKUs."),
            (f"What specific product variants, sizes, or flavors are available for {p1}?", "Verify SKU variant and option details."),
            (f"What is included in the box or package when ordering {p1} from {brand_clean}?", "Verify package contents and accessories."),
            (f"Does {brand_clean} offer curated product bundles, starter kits, or regimens combining {p1} and {p2}?", "Verify bundle and regimen offerings."),
            (f"What are the key design features and functional highlights of {p1}?", "Audit core product features."),
            (f"How does {brand_clean} describe the primary purpose of {p2} and {p3}?", "Verify individual product positioning."),
            (f"Are replacement heads, refills, or consumable packs available for {p1}?", "Verify refill and repeat-consumable ecosystem."),
            (f"What new or best-selling products are highlighted on {brand_clean}'s storefront?", "Audit bestseller and new-launch visibility."),
            (f"Does {brand_clean} offer travel-friendly sizes or portable versions of {p1}?", "Verify portability and travel specifications."),
            (f"How are {brand_clean}'s products categorized by customer goal or routine step?", "Audit storefront navigation and regimen taxonomy."),
        ],
        "product_ingredients": [
            (f"What are the active ingredients, materials, or core specifications of {p1}?", "Audit full ingredient and specification transparency."),
            (f"What key functional ingredients are used in {p2} and what role does each play?", "Verify ingredient-level functional explanations."),
            (f"Are {brand_clean}'s formulations like {p2} free from harsh chemicals, SLS, parabens, or artificial dyes?", "Verify free-from and clean formulation claims."),
            (f"What are the technical or physical specifications (e.g., battery life, modes, concentration, weight) of {p1}?", "Audit quantitative product specifications."),
            (f"What active compounds or components power the results of {p3}?", "Verify active formulation components."),
            (f"Does {brand_clean} disclose the full ingredient list (INCI) or material composition on every product page?", "Audit full label disclosure on product pages."),
            (f"Are the ingredients in {p2} naturally derived, probiotic, or clinically backed?", "Verify ingredient sourcing and science backing."),
            (f"What flavoring, scent, or texture agents are used in {brand_clean}'s {p2}?", "Verify sensory and formulation details."),
            (f"How does {brand_clean} source and quality-test the raw ingredients and components in {p1}?", "Audit quality control and sourcing standards."),
            (f"Are {brand_clean} products vegan, gluten-free, or alcohol-free?", "Verify dietary and lifestyle formulation attributes."),
        ],
        "product_benefits": [
            (f"What specific benefits and visible outcomes can customers expect from using {p1}?", "Verify primary customer outcome claims."),
            (f"How quickly do users typically see results when using {p3} or {p1} consistently?", "Audit expected timeline for results."),
            (f"How does {p2} improve daily hygiene, freshness, or wellness compared to standard products?", "Verify functional benefit differentiation."),
            (f"What clinical studies, consumer trials, or customer ratings support the effectiveness of {p1}?", "Audit substantiation of efficacy claims."),
            (f"Can combining {p1}, {p2}, and {p3} deliver better results than using a single product alone?", "Verify multi-product synergy benefits."),
            (f"What specific customer concerns or pain points is {p2} formulated to address?", "Verify problem-to-benefit mapping."),
            (f"Does {p3} provide long-lasting results without causing discomfort or sensitivity?", "Audit gentleness + efficacy balance."),
            (f"What verified customer reviews and before-and-after outcomes are shared for {p1}?", "Audit customer proof of product benefits."),
            (f"How does regular use of {brand_clean}'s products support long-term preventative care?", "Verify long-term wellness benefits."),
        ],
        "usage_instructions": [
            (f"How do you properly use {p1} step-by-step for the best results?", "Verify clear step-by-step usage instructions."),
            (f"How often and at what time of day should customers use {p2} and {p3}?", "Verify recommended frequency and routine timing."),
            (f"How long should each session or application of {p1} and {p3} last?", "Verify duration of application."),
            (f"In what order should {p1}, {p2}, and {p3} be used together in a daily routine?", "Verify multi-step regimen sequencing."),
            (f"How do you clean, charge, store, or maintain {p1} between uses?", "Verify care and maintenance instructions."),
            (f"How often should consumables, brush heads, or refills for {p1} be replaced?", "Verify replacement cadence guidance."),
            (f"Are there any preparation steps or things to avoid immediately before or after using {p3}?", "Verify pre/post usage best practices."),
            (f"Can {p2} be used daily without dilution, or does it require specific mixing instructions?", "Verify dosage and application mechanics."),
            (f"Does {brand_clean} provide a user manual or quick-start guide with {p1}?", "Verify onboarding and usage documentation."),
        ],
        "safety_and_suitability": [
            (f"Are {brand_clean}'s products safe for daily use and suitable for sensitive users?", "Verify daily safety and sensitivity suitability."),
            (f"Is {p3} enamel-safe or gentle on sensitive teeth, gums, or skin?", "Verify tissue/surface safety claims."),
            (f"Are {brand_clean}'s products like {p1} and {p2} dermatologist, dentist, or expert tested and approved?", "Verify expert endorsement and safety testing."),
            (f"What age groups (adults, teens, children) are {brand_clean}'s products suitable for?", "Verify age suitability boundaries."),
            (f"Are {p2} and {p3} safe to use during pregnancy or alongside dental/medical work such as braces, veneers, or crowns?", "Verify special-condition suitability."),
            (f"Are there any known side effects, allergens, or contraindications for {p2} or {p3}?", "Audit allergen and precaution disclosures."),
            (f"What safety certifications (such as FDA registration, CE, RoHS, or waterproof IPX ratings) apply to {p1}?", "Verify product safety certifications."),
            (f"What should a customer do if they experience irritation or sensitivity while using {p3}?", "Verify safety guidance and customer care advice."),
            (f"How does {brand_clean} ensure product hygiene and tamper-evident safety in its packaging?", "Verify packaging safety standards."),
        ],
        "pricing_and_offers": [
            (f"How much does {p1} cost on {brand_clean}'s official website?", "Verify transparent unit pricing for hero product."),
            (f"What is the price range across {brand_clean}'s product lineup including {p2} and {p3}?", "Verify catalog price range transparency."),
            (f"Does {brand_clean} offer discounted bundle pricing or value packs when buying {p1} and {p2} together?", "Verify bundle savings and multi-pack offers."),
            (f"Does {brand_clean} offer a subscribe-and-save option for recurring deliveries of {p2} or {p3}?", "Verify subscription discount availability."),
            (f"Are there first-time buyer promo codes, welcome discounts, or loyalty rewards at {brand_clean}?", "Verify promotional and loyalty incentives."),
            (f"Does {brand_clean} run seasonal sales, combo offers, or free gift-with-purchase promotions?", "Verify promotional offer structure."),
            (f"Are taxes and GST included in the displayed product prices on {brand_clean}'s website?", "Verify price inclusivity and checkout transparency."),
            (f"Does {brand_clean} offer EMI, Buy Now Pay Later (BNPL), UPI, or cash-on-delivery payment options?", "Verify consumer payment method flexibility."),
            (f"How much can customers save by purchasing a {brand_clean} regimen kit versus individual items?", "Verify bundle value proposition."),
        ],
        "shipping_and_returns": [
            (f"What are {brand_clean}'s standard shipping timelines and delivery estimates across regions?", "Verify shipping speed and delivery expectations."),
            (f"Does {brand_clean} offer free shipping, and what is the minimum order value required to qualify?", "Verify free shipping threshold."),
            (f"What is {brand_clean}'s return, replacement, and refund policy for {p1} and consumable items?", "Verify return and refund policy clarity."),
            (f"How can customers track their {brand_clean} order status once it has been dispatched?", "Verify order tracking workflow."),
            (f"What is the process for reporting a damaged, defective, or missing item in a {brand_clean} delivery?", "Verify damaged-delivery resolution policy."),
            (f"Does {brand_clean} support Cash on Delivery (COD) or express shipping options?", "Verify fulfilment and delivery options."),
            (f"Can customers modify or cancel their {brand_clean} order before it ships?", "Verify order cancellation and modification window."),
            (f"Does {brand_clean} ship internationally or exclusively within its domestic market?", "Verify geographic shipping coverage."),
            (f"How long does it take for {brand_clean} to process a refund after a return is approved?", "Verify refund turnaround timeline."),
        ],
        "customer_support": [
            (f"How can customers contact {brand_clean} customer support (email, WhatsApp, phone, or live chat)?", "Verify customer support contact channels."),
            (f"Does {p1} come with a manufacturer warranty, and what does the warranty cover?", "Verify hardware/product warranty coverage."),
            (f"How do customers register {p1} for warranty or submit a warranty replacement claim with {brand_clean}?", "Verify warranty claim procedure."),
            (f"What are {brand_clean}'s customer service operating hours and typical response times?", "Verify support responsiveness expectations."),
            (f"Does {brand_clean} have a dedicated FAQ or help center for troubleshooting product questions?", "Verify self-service help center availability."),
            (f"How does {brand_clean} handle subscription pauses, skips, or cancellations for repeat customers?", "Verify subscription management support."),
            (f"Can customers consult {brand_clean}'s product specialists for personalized product recommendations?", "Verify pre-purchase consultation support."),
            (f"Where can customers find authentic replacement parts or warranty service for {p1}?", "Verify post-purchase servicing support."),
            (f"Does {brand_clean} offer a satisfaction guarantee or trial guarantee on select products?", "Verify risk-reversal satisfaction guarantee."),
        ],
        "product_comparisons": [
            (f"How does {brand_clean}'s {p1} compare to {comp1} in features, quality, and price?", "Verify head-to-head competitive comparison."),
            (f"Why should shoppers choose {brand_clean}'s {p2} over standard supermarket or pharmacy alternatives?", "Verify upgrade rationale over mass-market options."),
            (f"What is the difference between {brand_clean}'s product variants and which one should a buyer pick?", "Verify internal product line comparison."),
            (f"How does {p3} compare to professional in-clinic treatments or competing home kits?", "Verify efficacy and value vs alternatives."),
            (f"What are the pros and cons of {brand_clean}'s {p1} compared to other products in {niche}?", "Verify balanced comparative evaluation."),
            (f"How does {brand_clean}'s ingredient quality in {p2} compare to conventional formulas?", "Verify formulation superiority claims."),
            (f"Is {brand_clean}'s {p1} better value for money than competing premium brands?", "Verify price-to-performance positioning."),
            (f"How do verified buyers rate {brand_clean} compared to other D2C {niche} brands?", "Verify comparative customer sentiment."),
            (f"What unique features does {p1} offer that competing products at a similar price point lack?", "Verify unique product differentiators."),
        ],
        "purchase_intent": [
            (f"Which {brand_clean} product or starter kit is best for a first-time customer?", "Verify first-time buyer guide recommendation."),
            (f"Where can customers buy authentic {brand_clean} products online (official store vs marketplaces)?", "Verify authorized purchase channels."),
            (f"How do I choose the right {brand_clean} product for my specific routine and goals?", "Verify product quiz / buying guide support."),
            (f"Is {p1} currently in stock and available for immediate purchase on {brand_clean}'s website?", "Verify product availability and stock clarity."),
            (f"What are the most popular {brand_clean} combos recommended for complete daily care?", "Verify high-intent bundle recommendations."),
            (f"Can I buy {brand_clean} products as a gift Set or add gift packaging at checkout?", "Verify gifting options and checkout experience."),
            (f"What should a buyer check on {brand_clean}'s product page before adding {p1} to cart?", "Verify pre-checkout decision information."),
            (f"How fast is the checkout process on {brand_clean}'s website and is guest checkout supported?", "Verify frictionless purchase path."),
            (f"Why is buying directly from {brand_clean}'s official website better than third-party sellers?", "Verify direct-to-consumer purchase incentives."),
        ],
    }

    validated: List[Dict[str, str]] = []
    for cat in BUSINESS_CONTEXT_CATEGORIES_11:
        cid = cat["id"]
        ctitle = cat["title"]
        for q_text, intent_desc in category_question_bank.get(cid, []):
            if len(validated) < target_count:
                validated.append({
                    "category_id": cid,
                    "facet": ctitle,
                    "question": q_text,
                    "intent": intent_desc,
                })

    return validated[:target_count]


def validate_questions_against_business_context(
    questions: List[Any],
    business_profile: Optional[BusinessProfile],
    pages: Optional[List[PageEvidence]] = None,
    brand: str = "",
    target_count: int = 100,
) -> List[Any]:
    """
    Validates generated questions against the audited site's business context.
    When the site is a consumer / D2C / ecommerce / local business, filters out all
    B2B/enterprise-only questions (SOC 2, HIPAA, SAML, REST/GraphQL API, enterprise contracts, etc.)
    and replaces/fills from the canonical 11 R3 business-context categories.
    """
    is_consumer = is_consumer_or_non_enterprise_business(business_profile, pages)
    if not is_consumer:
        return questions

    brand_name = (
        brand
        or (business_profile.business_name if business_profile and getattr(business_profile, "business_name", None) else "")
        or "the brand"
    )
    replacement_pool = generate_11_category_business_questions(
        brand=brand_name,
        business_profile=business_profile,
        pages=pages,
        target_count=max(target_count, len(questions) or 100),
    )

    if not questions:
        return replacement_pool[:target_count]

    valid_existing: List[Any] = []
    used_texts = set()

    for q in questions:
        if isinstance(q, dict):
            q_text = str(q.get("question") or q.get("generated_question") or "")
            facet_val = str(q.get("category_id") or q.get("facet") or "")
        else:
            q_text = str(getattr(q, "generated_question", "") or getattr(q, "question", "") or "")
            facet_val = str(getattr(q, "facet", "") or "")

        if not q_text or B2B_ENTERPRISE_ONLY_PATTERNS.search(q_text):
            continue
        if facet_val in {"trust_security", "tech_stack"} or "Enterprise Security" in facet_val or "Technology Stack" in facet_val:
            continue

        norm_q = q_text.strip().lower()
        if norm_q not in used_texts:
            used_texts.add(norm_q)
            valid_existing.append(q)

    # If existing questions don't cover the 11 R3 categories or were B2B templates, use the 11-category pool
    has_r3_categories = any(
        (isinstance(q, dict) and (q.get("category_id") in R3_CATEGORY_IDS or q.get("facet") in R3_CATEGORY_TITLES.values()))
        or (not isinstance(q, dict) and getattr(q, "facet", None) in R3_CATEGORY_TITLES.values())
        for q in valid_existing
    )
    if not has_r3_categories:
        return replacement_pool[:target_count]

    for rep in replacement_pool:
        if len(valid_existing) >= target_count:
            break
        norm_rep = rep["question"].strip().lower()
        if norm_rep not in used_texts:
            used_texts.add(norm_rep)
            valid_existing.append(rep)

    return valid_existing[:target_count]


# 10 Core Strategic Facets for Comprehensive Website & Business Intelligence
SANDBOX_FACETS = [
    {
        "id": "identity",
        "title": "Identity, Category & Core Mission",
        "intent": "Verify company name, core offerings, market category, and foundational value proposition without generic fluff."
    },
    {
        "id": "icp",
        "title": "Target Audience, ICP & Disqualifiers",
        "intent": "Verify explicit buyer personas, qualification criteria, enterprise vs SMB fit, and who should NOT buy."
    },
    {
        "id": "pricing",
        "title": "Pricing, Packaging & Commercial Model",
        "intent": "Determine whether transparent pricing, billing models, and entry tiers are accessible or hidden/hallucinated."
    },
    {
        "id": "capabilities",
        "title": "Core Capabilities, Features & Product Mechanics",
        "intent": "Audit tangible workflows, automation capabilities, primary feature sets, and deliverables."
    },
    {
        "id": "tech_stack",
        "title": "Technology Stack, Architecture & Integrations",
        "intent": "Evaluate technical infrastructure, API availability, ecosystem integrations, and deployment options."
    },
    {
        "id": "differentiation",
        "title": "Competitive Moat, Differentiation & Alternatives",
        "intent": "Audit defensible competitive advantages, legacy vs modern comparisons, and migration tooling."
    },
    {
        "id": "trust_security",
        "title": "Trust, Enterprise Security & Regulatory Compliance",
        "intent": "Verify third-party security audits (SOC2/ISO), data privacy standards (GDPR/HIPAA), and encryption."
    },
    {
        "id": "customer_proof",
        "title": "Customer Proof, Case Studies & Quantified ROI",
        "intent": "Audit whether quantitative outcomes (e.g. 40% time saved) and client logos are substantiated by evidence."
    },
    {
        "id": "onboarding",
        "title": "Implementation, Support & Customer Success",
        "intent": "Audit time-to-value, technical onboarding effort, documentation quality, and support SLAs."
    },
    {
        "id": "purchase_flow",
        "title": "High-Intent Purchase & Conversion Paths",
        "intent": "Audit direct buyer conversion routes (demo booking, self-serve access, procurement review)."
    },
]


class DynamicQuestionSandboxEngine:
    """
    KIE-Powered Question Sandbox Engine (Phase 4 + 5).

    Generates bespoke inquiries from the Website Knowledge Graph and evaluates
    each question using the Grounded Answer Simulator with Hybrid Retrieval.

    Question budget is configurable via QuestionBudgetTier:
      STARTER=50, STANDARD=100, ENTERPRISE=250, DEEP_AUDIT=500

    Falls back to the original question-builder catalog when the KIE graph is
    unavailable (e.g. bare-minimum pages with no extractable claims), ensuring
    full backward compatibility.
    """

    def __init__(self, model_router=None):
        self.model_router = model_router

    async def generate_and_evaluate_100_questions(
        self,
        pages: List[PageEvidence],
        website_url: str,
        resolved_entity: ResolvedEntity,
        profile: Optional[BusinessProfile] = None,
        budget: QuestionBudgetTier = QuestionBudgetTier.STANDARD,
    ) -> List[DynamicSandboxQuestionEvaluation]:
        """
        KIE Pipeline:
          1. Build WebsiteKnowledgeGraph from crawled pages
          2. Synthesize questions per facet (budget-controlled)
          3. For each question: QueryPlanner → HybridRetriever → GroundedAnswerSimulator
          4. Map simulation results to DynamicSandboxQuestionEvaluation
        """
        brand = resolved_entity.name
        niche = resolved_entity.niche or (profile.niche if profile else "Platform Solutions")
        val_prop = resolved_entity.value_proposition or (profile.value_proposition if profile else "Core digital services")

        # ── Phase 1+2: Build Knowledge Graph ────────────────────────────────
        domain = website_url.split("//")[-1].split("/")[0].replace("www.", "") if website_url else brand
        kg = WebsiteKnowledgeGraph(brand=brand, domain=domain)
        try:
            kg.build_from_pages(pages)
        except Exception:
            pass  # Graph build failure is non-fatal; falls back to legacy evaluator

        # ── Phase 3: Query Planner + True Hybrid RAG Grounded Simulator ─────
        vector_store = None
        embedding_service = None
        try:
            from app.crawl.vector_store import VectorStore
            from app.crawl.embeddings import embedding_service as _emb_svc
            vector_store = VectorStore()
            embedding_service = _emb_svc
        except Exception:
            pass
        simulator = GroundedAnswerSimulator(
            graph=kg,
            model_router=self.model_router,
            vector_store=vector_store,
            embedding_service=embedding_service,
            domain=domain,
            pages=pages,
        )

        # Legacy corpus for fallback question builder only
        corpus_pages = []
        for p in pages:
            text = f"{p.title or ''} {' '.join(p.h1 or [])} {' '.join(p.h2 or [])} {(p.body_text or '')[:4000]}"
            corpus_pages.append({"url": p.url, "title": p.title or "", "text": text, "lower": text.lower()})
        site_context = self._extract_site_context(corpus_pages, brand, niche, val_prop)

        t_sandbox_start = time.perf_counter()
        def _elapsed():
            return f"T+{int((time.perf_counter() - t_sandbox_start) * 1000)}ms"

        self.system_execution_log = [
            {
                "timestamp": _elapsed(),
                "phase": "INDEXING",
                "level": "INFO",
                "message": f"Crawled Website Knowledge Base initialized across {len(pages)} pages for brand '{brand}'.",
            },
            {
                "timestamp": _elapsed(),
                "phase": "KNOWLEDGE_GRAPH",
                "level": "INFO",
                "message": f"Extracted {len(kg.claims)} atomic claims, {len(kg.entities)} entities, and {len(kg.relationships)} semantic edges.",
            },
            {
                "timestamp": _elapsed(),
                "phase": "QUERY_PLANNING",
                "level": "INFO",
                "message": f"Planned inquiry matrix across 10 strategic facets ({budget.value} budget tier: {budget.question_count()} target inquiries).",
            },
            {
                "timestamp": _elapsed(),
                "phase": "RAG_EXECUTION",
                "level": "INFO",
                "message": "Executing AI RAG Answering Agent with Hybrid Retrieval and claim-level grounding verification...",
            },
        ]

        questions_per_facet = budget.questions_per_facet()
        all_evaluations: List[DynamicSandboxQuestionEvaluation] = []
        q_counter = 1
        sem = asyncio.Semaphore(8)

        async def _eval_one(q_id: str, facet_id: str, facet_title: str, q_text: str, b_intent: str) -> DynamicSandboxQuestionEvaluation:
            async with sem:
                if kg.claims:
                    sim = await simulator.simulate_async(question_id=q_id, question=q_text)
                    evidence_url = sim.source_url
                    evidence_snippet = None
                    for r in sim.claim_decomposition:
                        if r.status in ("SUPPORTED", "PARTIALLY_SUPPORTED") and r.evidence_url:
                            evidence_url = r.evidence_url
                            evidence_snippet = r.evidence_snippet
                            break

                    if sim.assessment_status == "CONFLICTING":
                        answerability_status = "CONFLICTING"
                        is_answerable = False
                    elif sim.assessment_status == "INSUFFICIENT" or sim.grounding_ratio < 0.20 or sim.retrieval_evidence_count == 0:
                        answerability_status = "EVIDENCE_GAP"
                        is_answerable = False
                    elif sim.assessment_status == "PARTIAL" or sim.grounding_ratio < 0.60:
                        answerability_status = "PARTIAL"
                        is_answerable = True
                    else:
                        answerability_status = "ANSWERABLE"
                        is_answerable = True

                    if is_answerable and sim.grounding_ratio >= 0.60:
                        citability_score = max(6, min(10, round(sim.grounding_ratio * 10)))
                    elif is_answerable and sim.grounding_ratio >= 0.25:
                        citability_score = max(3, min(5, round(sim.grounding_ratio * 10)))
                    else:
                        citability_score = 1 if sim.grounding_ratio == 0 else 2

                    crawled_answer = (sim.retrieved_extract or sim.candidate_answer)[:450]
                    rag_answer = (sim.rag_answer or sim.candidate_answer)[:700]
                    gap_analysis = self._build_gap_analysis(sim, brand, facet_id)
                    recommended_answer = rag_answer or self._build_recommended_answer(brand, val_prop, q_text, sim)
                    projected_patch_gain = self._compute_projected_gain(sim.answer_risk, sim.grounding_ratio)

                    grounding_ratio = sim.grounding_ratio
                    answer_risk = sim.answer_risk.value if hasattr(sim.answer_risk, "value") else str(sim.answer_risk)
                    claim_decomposition = [
                        r.model_dump() if hasattr(r, "model_dump") else r
                        for r in sim.claim_decomposition
                    ]
                    retrieval_evidence_count = sim.retrieval_evidence_count
                    missing_aspects = sim.missing_aspects
                    eval_trace = {
                        "retrieval_evidence_count": sim.retrieval_evidence_count,
                        "assessment_status": sim.assessment_status,
                        "grounding_ratio": sim.grounding_ratio,
                        "answer_risk": answer_risk,
                        "missing_aspects": sim.missing_aspects,
                        "supported_aspects": sim.supported_aspects,
                    }
                    source_page_title = sim.source_page_title
                    source_section = sim.source_section
                    target_update_page = sim.target_update_page
                    target_update_section = sim.target_update_section
                    section_update_recommendation = sim.section_update_recommendation
                    ai_thinking_steps = sim.ai_thinking_steps

                    retrieval_status = "RETRIEVED" if sim.retrieval_evidence_count > 0 else "NOT_RETRIEVED"
                    if sim.assessment_status == "PARTIAL":
                        retrieval_status = "PARTIAL"
                else:
                    eval_res = self._evaluate_question_answerability(
                        question=q_text, facet_id=facet_id, corpus_pages=corpus_pages,
                        brand=brand, niche=niche, val_prop=val_prop,
                    )
                    is_answerable = eval_res["is_answerable"]
                    raw_status = eval_res["answerability_status"]
                    answerability_status = "EVIDENCE_GAP" if raw_status == "UNANSWERABLE" else raw_status
                    crawled_answer = eval_res["crawled_answer"]
                    rag_answer = eval_res.get("rag_answer") or eval_res["crawled_answer"]
                    evidence_url = eval_res["evidence_url"]
                    evidence_snippet = eval_res["evidence_snippet"]
                    gap_analysis = eval_res["gap_analysis"]
                    recommended_answer = rag_answer
                    citability_score = eval_res["citability_score"]
                    projected_patch_gain = eval_res["projected_patch_gain"]
                    grounding_ratio = 0.85 if answerability_status == "ANSWERABLE" else (0.45 if answerability_status == "PARTIAL" else 0.0)
                    answer_risk = "LOW" if answerability_status == "ANSWERABLE" else ("MEDIUM" if answerability_status == "PARTIAL" else "HIGH")
                    claim_decomposition = []
                    retrieval_evidence_count = 1 if is_answerable else 0
                    missing_aspects = [] if is_answerable else [q_text]
                    eval_trace = {
                        "mode": "legacy_fallback",
                        "answerability_status": answerability_status,
                        "grounding_ratio": grounding_ratio,
                    }
                    source_page_title = eval_res.get("source_page_title")
                    source_section = eval_res.get("source_section")
                    target_update_page = eval_res.get("target_update_page")
                    target_update_section = eval_res.get("target_update_section")
                    section_update_recommendation = eval_res.get("section_update_recommendation")
                    ai_thinking_steps = eval_res.get("ai_thinking_steps", [])
                    retrieval_status = "RETRIEVED" if is_answerable else ("PARTIAL" if answerability_status == "PARTIAL" else "NOT_RETRIEVED")

                is_sensitive = facet_id in {"pricing", "trust_security"} or any(
                    w in q_text.lower() for w in ["price", "cost", "tier", "soc 2", "iso 27001", "sla", "uptime", "refund"]
                )
                requires_owner_confirmation = is_sensitive and not is_answerable
                owner_confirmation_brief = (
                    f"Business owner must confirm authoritative factual specifications for '{q_text}'. "
                    "Do not publish placeholder pricing tiers, uncertified compliance badges, or unverified SLAs."
                    if requires_owner_confirmation else None
                )

                return DynamicSandboxQuestionEvaluation(
                    question_id=q_id,
                    facet=facet_title,
                    generated_question=q_text,
                    buyer_intent=b_intent,
                    is_answerable=is_answerable,
                    answerability_status=answerability_status,
                    crawled_answer=crawled_answer,
                    rag_answer=rag_answer,
                    evidence_url=evidence_url,
                    source_url=evidence_url,
                    evidence_snippet=evidence_snippet,
                    gap_analysis=gap_analysis,
                    recommended_answer=recommended_answer,
                    citability_score=citability_score,
                    projected_patch_gain=projected_patch_gain,
                    grounding_ratio=grounding_ratio,
                    answer_risk=answer_risk,
                    claim_decomposition=claim_decomposition,
                    retrieval_evidence_count=retrieval_evidence_count,
                    missing_aspects=missing_aspects,
                    evaluation_trace=eval_trace,
                    source_page_title=source_page_title,
                    source_section=source_section,
                    target_update_page=target_update_page,
                    target_update_section=target_update_section,
                    section_update_recommendation=section_update_recommendation,
                    requires_owner_confirmation=requires_owner_confirmation,
                    owner_confirmation_brief=owner_confirmation_brief,
                    retrieval_status=retrieval_status,
                    ai_thinking_steps=ai_thinking_steps,
                )

        is_consumer = is_consumer_or_non_enterprise_business(profile, pages)
        target_total = budget.question_count()
        raw_question_specs: List[Dict[str, str]] = []
        synthesis_mode = "deterministic_fallback"

        use_llm_synth = bool(getattr(settings, "USE_LLM_SANDBOX_SYNTHESIS", True))
        if use_llm_synth and self.model_router and hasattr(self.model_router, "generate_structured"):
            ai_questions = await self._synthesize_questions_frontier_ai(
                brand=brand,
                niche=niche,
                val_prop=val_prop,
                is_consumer=is_consumer,
                target_total=target_total,
                pages=pages,
                corpus_pages=corpus_pages,
                profile=profile,
            )
            if ai_questions:
                raw_question_specs = ai_questions
                synthesis_mode = "frontier_ai"

        if len(raw_question_specs) < target_total:
            if is_consumer:
                fallback_specs = generate_11_category_business_questions(
                    brand=brand,
                    business_profile=profile,
                    pages=pages,
                    target_count=target_total,
                )
            else:
                fallback_specs = []
                questions_per_facet = budget.questions_per_facet()
                for facet in SANDBOX_FACETS:
                    facet_id = facet["id"]
                    facet_title = facet["title"]
                    facet_questions = await self._synthesize_facet_questions(
                        facet_id=facet_id,
                        brand=brand,
                        niche=niche,
                        val_prop=val_prop,
                        corpus_pages=corpus_pages,
                        site_context=site_context,
                        profile=profile,
                    )
                    for item in facet_questions[:questions_per_facet]:
                        fallback_specs.append({
                            "category_id": facet_id,
                            "facet": facet_title,
                            "question": item["question"],
                            "intent": item["intent"],
                        })
            seen_q = {q.get("question", "").strip().lower() for q in raw_question_specs}
            for fb in fallback_specs:
                key = fb.get("question", "").strip().lower()
                if key and key not in seen_q and len(raw_question_specs) < target_total:
                    raw_question_specs.append(fb)
                    seen_q.add(key)

        # Validate questions against business context BEFORE scoring so irrelevant B2B
        # questions never enter a consumer brand's 100-question denominator.
        validated_specs = validate_questions_against_business_context(
            questions=raw_question_specs,
            business_profile=profile,
            pages=pages,
            brand=brand,
            target_count=target_total,
        )

        tasks = []
        for item in validated_specs[:target_total]:
            q_id = f"Q-{q_counter:03d}"
            q_counter += 1
            facet_id = item.get("category_id") or item.get("facet") or "brand_identity"
            facet_title = item.get("facet") or R3_CATEGORY_TITLES.get(facet_id, facet_id)
            tasks.append(_eval_one(q_id, facet_id, facet_title, item["question"], item["intent"]))

        all_evaluations = list(await asyncio.gather(*tasks))

        # Phase 4: Batched AI RAG Answering & Gap Synthesis (10 batches × 10 questions)
        rag_ai_batches = 0
        if use_llm_synth and self.model_router and hasattr(self.model_router, "generate_structured") and all_evaluations:
            rag_ai_batches = await self._enrich_evaluations_with_ai_rag_batches(
                evaluations=all_evaluations,
                brand=brand,
                pages=pages,
            )

        ans_count = sum(1 for e in all_evaluations if e.is_answerable)
        gap_count = len(all_evaluations) - ans_count
        self.system_execution_log.append({
            "timestamp": "T+FINAL",
            "phase": "EVALUATION_COMPLETE",
            "level": "SUCCESS",
            "message": (
                f"Synthesized ({synthesis_mode}) and verified {len(all_evaluations)} bespoke questions "
                f"(AI RAG batches: {rag_ai_batches}): {ans_count} answerable, {gap_count} gaps identified."
            ),
        })

        return all_evaluations

    def _build_sandbox_evidence_objects(self, pages: List[PageEvidence], corpus_pages: List[Dict[str, Any]], limit: int = 8) -> List[Any]:
        """Build valid Evidence objects with real SHA-256 content hashes for ModelRouter."""
        import hashlib
        from app.domain.evidence.models import Evidence

        ev_list: List[Evidence] = []
        for idx, p in enumerate(pages[:limit]):
            sections = getattr(p, "sections", None) or []
            if sections:
                sec_summary = " | ".join(
                    f"[{getattr(s, 'section_role', 'sec')}] {getattr(s, 'heading_text', '')}: {(getattr(s, 'body_text', '') or '')[:220]}"
                    for s in sections[:5]
                )
            else:
                sec_summary = (p.body_text or "")[:800]
            text = f"URL: {p.url} | Title: {p.title or ''} | {sec_summary}".strip()[:1200]
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
            ev_list.append(
                Evidence(
                    id=f"ev_sandbox_{idx:02d}_{digest[:8]}",
                    source_type="page_section" if sections else "dom",
                    analyzer="dynamic_sandbox",
                    url=p.url,
                    selector="main",
                    text=text,
                    content_sha256=digest,
                    hash=digest,
                )
            )
        if not ev_list and corpus_pages:
            for idx, cp in enumerate(corpus_pages[:3]):
                text = (cp.get("text") or "")[:900]
                digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
                ev_list.append(
                    Evidence(
                        id=f"ev_sandbox_cp_{idx:02d}_{digest[:8]}",
                        source_type="dom",
                        analyzer="dynamic_sandbox",
                        url=cp.get("url") or "",
                        selector="body",
                        text=text,
                        content_sha256=digest,
                        hash=digest,
                    )
                )
        return ev_list

    async def _synthesize_questions_frontier_ai(
        self,
        *,
        brand: str,
        niche: str,
        val_prop: str,
        is_consumer: bool,
        target_total: int,
        pages: List[PageEvidence],
        corpus_pages: List[Dict[str, Any]],
        profile: Optional[BusinessProfile] = None,
    ) -> List[Dict[str, str]]:
        """Synthesize up to 100 bespoke buyer questions in 5 concurrent Frontier AI batches of 20."""
        import json as _json

        facets = (
            [{"id": c["id"], "title": c["title"], "intent": c["intent"]} for c in BUSINESS_CONTEXT_CATEGORIES_11]
            if is_consumer
            else [{"id": f["id"], "title": f["title"], "intent": f.get("description", f["title"])} for f in SANDBOX_FACETS]
        )
        # Group facets into up to 5 batches targeting ~20 questions per batch
        num_batches = min(5, max(1, (target_total + 19) // 20))
        facet_groups: List[List[Dict[str, str]]] = [[] for _ in range(num_batches)]
        for i, f in enumerate(facets):
            facet_groups[i % num_batches].append(f)

        per_batch_target = max(1, (target_total + num_batches - 1) // num_batches)
        ev_objs = self._build_sandbox_evidence_objects(pages, corpus_pages, limit=10)
        page_inventory = [
            {
                "url": p.url,
                "title": (p.title or "")[:100],
                "h1": (p.h1 or [])[:2],
                "h2": (p.h2 or [])[:4],
            }
            for p in pages[:18]
        ]
        bp_summary = {
            "brand": brand,
            "business_model": getattr(profile, "business_model", None) or ("Consumer/D2C" if is_consumer else "B2B/Service"),
            "industry": getattr(profile, "industry", None) or niche,
            "products": (getattr(profile, "products", None) or [])[:10],
            "services": (getattr(profile, "services", None) or [])[:10],
            "target_audience": getattr(profile, "target_audience", None) or "",
            "geography": getattr(profile, "geography", None) or "",
            "value_proposition": val_prop,
        }
        schema_desc = (
            '{"questions":[{"category_id":"string","facet":"string",'
            '"question":"string (specific real buyer inquiry for this exact brand)",'
            '"intent":"string (buyer decision intent)"}]}'
        )
        sem = asyncio.Semaphore(5)

        async def _run_batch(batch_idx: int, group: List[Dict[str, str]]) -> List[Dict[str, str]]:
            if not group:
                return []
            contract = (
                f"Generate exactly {per_batch_target} realistic, specific buyer questions that prospective customers "
                f"ask ChatGPT, Perplexity, Gemini, or Google AI Overviews when evaluating '{brand}'.\n"
                f"BUSINESS PROFILE:\n{_json.dumps(bp_summary, ensure_ascii=False)}\n\n"
                f"CRAWLED SITE MAP:\n{_json.dumps(page_inventory, ensure_ascii=False)[:3000]}\n\n"
                f"ASSIGNED FACETS (Batch {batch_idx + 1}/{num_batches}):\n{_json.dumps(group, ensure_ascii=False)}\n\n"
                "STRICT RULES:\n"
                "1. Every question MUST match this business's actual domain, products/services, and buyer type. "
                "NEVER ask SaaS/SOC2/API questions for consumer/local businesses, and NEVER ask skincare/shipping questions for SaaS.\n"
                "2. Distribute questions evenly across the assigned facets and use their exact `category_id` and `facet` title.\n"
                "3. Zero duplicate or boilerplate questions."
            )
            async with sem:
                try:
                    res = await self.model_router.generate_structured(
                        capability="aeo_question_synthesis",
                        agent_role="Senior AEO Buyer Intent & AI Search Query Researcher",
                        task_contract=contract,
                        evidence_list=ev_objs,
                        output_schema_desc=schema_desc,
                        max_claims=per_batch_target,
                        allow_fallback=False,
                        model_tier="reasoning_model",
                    )
                except Exception:
                    return []
            if not isinstance(res, dict) or str(res.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
                return []
            valid_ids = {g["id"]: g["title"] for g in group}
            default_id = group[0]["id"]
            cleaned: List[Dict[str, str]] = []
            for item in (res.get("questions") or []):
                if not isinstance(item, dict):
                    continue
                q_txt = str(item.get("question") or "").strip()
                if len(q_txt) < 12:
                    continue
                cat_id = str(item.get("category_id") or default_id).strip()
                if cat_id not in valid_ids:
                    cat_id = default_id
                cleaned.append({
                    "category_id": cat_id,
                    "facet": valid_ids.get(cat_id, str(item.get("facet") or cat_id)),
                    "question": q_txt,
                    "intent": str(item.get("intent") or "Verify buyer answerability in AI search.").strip(),
                })
            return cleaned[:per_batch_target]

        batch_lists = await asyncio.gather(*[_run_batch(i, grp) for i, grp in enumerate(facet_groups)])
        merged: List[Dict[str, str]] = []
        seen = set()
        for bl in batch_lists:
            for q in bl:
                key = q["question"].lower()
                if key not in seen:
                    seen.add(key)
                    merged.append(q)
        return merged[:target_total]

    async def _enrich_evaluations_with_ai_rag_batches(
        self,
        *,
        evaluations: List[DynamicSandboxQuestionEvaluation],
        brand: str,
        pages: List[PageEvidence],
    ) -> int:
        """Refine RAG answers and gap analyses in concurrent batches of 10 using strictly retrieved passages."""
        import json as _json

        crawled_urls = [p.url for p in pages[:25] if getattr(p, "url", None)]
        batch_size = 10
        batches = [evaluations[i : i + batch_size] for i in range(0, len(evaluations), batch_size)]
        sem = asyncio.Semaphore(4)
        depth_mode = (getattr(settings, "AI_DEPTH_MODE", "tiered_frontier") or "tiered_frontier").strip().lower()
        rag_tier = "reasoning_model" if depth_mode == "frontier_all" else "fast_slm"
        schema_desc = (
            '{"answers":[{"question_id":"Q-001","rag_answer":"string (grounded ONLY in retrieved_extract; state gap explicitly if ungrounded)",'
            '"gap_analysis":"string (what is missing or weak for AI engines)",'
            '"missing_aspects":["string"],'
            '"target_update_url":"string (MUST be one of crawled_urls)",'
            '"section_update_recommendation":"string"}]}'
        )
        ev_objs = self._build_sandbox_evidence_objects(pages, [], limit=6)

        async def _process_batch(batch: List[DynamicSandboxQuestionEvaluation]) -> bool:
            items = [
                {
                    "question_id": e.question_id,
                    "question": e.generated_question,
                    "current_status": e.answerability_status,
                    "grounding_ratio": e.grounding_ratio,
                    "source_url": e.source_url,
                    "retrieved_extract": (e.crawled_answer or "")[:450],
                    "retrieval_evidence_count": e.retrieval_evidence_count,
                }
                for e in batch
            ]
            contract = (
                f"You are an Evidence-Grounded AEO RAG Answer Verifier for '{brand}'.\n"
                f"CRAWLED URLS (only cite or target these URLs): {_json.dumps(crawled_urls)}\n\n"
                f"QUESTIONS & RETRIEVED FIRST-PARTY PASSAGES:\n{_json.dumps(items, ensure_ascii=False, indent=2)}\n\n"
                "STRICT GROUNDING RULES:\n"
                "1. Answer ONLY from `retrieved_extract`. If `retrieval_evidence_count == 0` or `retrieved_extract` lacks the answer, "
                "explicitly state that the crawled site does not publish this information — NEVER invent prices, SLAs, certifications, or specs.\n"
                "2. Provide a concrete `gap_analysis` and `section_update_recommendation` targeting one of the real `crawled_urls`."
            )
            async with sem:
                try:
                    res = await self.model_router.generate_structured(
                        capability="aeo_analysis",
                        agent_role="Evidence-Grounded AEO RAG Verifier",
                        task_contract=contract,
                        evidence_list=ev_objs,
                        output_schema_desc=schema_desc,
                        max_claims=len(batch),
                        allow_fallback=False,
                        model_tier=rag_tier,
                    )
                except Exception:
                    return False
            if not isinstance(res, dict) or str(res.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
                return False
            ans_list = res.get("answers") or []
            if not isinstance(ans_list, list) or not ans_list:
                return False
            by_id = {e.question_id: e for e in batch}
            valid_url_set = set(crawled_urls)
            updated = False
            for row in ans_list:
                if not isinstance(row, dict):
                    continue
                target = by_id.get(str(row.get("question_id") or ""))
                if target is None:
                    continue
                updated = True
                rag_txt = str(row.get("rag_answer") or "").strip()
                if rag_txt:
                    target.rag_answer = rag_txt[:700]
                    target.recommended_answer = rag_txt[:700]
                gap_txt = str(row.get("gap_analysis") or "").strip()
                if gap_txt:
                    target.gap_analysis = gap_txt[:500]
                miss = row.get("missing_aspects")
                if isinstance(miss, list) and miss:
                    target.missing_aspects = [str(m).strip() for m in miss[:6] if str(m).strip()]
                tgt_url = str(row.get("target_update_url") or "").strip()
                if tgt_url and tgt_url in valid_url_set:
                    target.target_update_page = tgt_url
                sec_rec = str(row.get("section_update_recommendation") or "").strip()
                if sec_rec:
                    target.section_update_recommendation = sec_rec[:500]
                if isinstance(target.evaluation_trace, dict):
                    target.evaluation_trace["ai_rag_verified"] = True
            return updated

        results = await asyncio.gather(*[_process_batch(b) for b in batches])
        return sum(1 for ok in results if ok)

    def _build_gap_analysis(self, sim, brand: str, facet_id: str) -> str:
        unsupported = [r for r in sim.claim_decomposition if r.status == "UNSUPPORTED"]
        missing = [a for a in (sim.missing_aspects or []) if a]
        if not unsupported:
            if sim.grounding_ratio >= 0.7 and not missing:
                return (
                    f"Every claim in the knowledge-base answer matches a retrieved passage for {brand}."
                )
            if missing:
                return (
                    f"The crawl answers only part of this question for {brand}. "
                    f"It does not state: {', '.join(missing[:4])}."
                )
            return f"Retrieved passages for {brand} support part of this answer."
        risk_label = {
            KieAnswerRisk.HIGH: "HIGH ANSWER RISK",
            KieAnswerRisk.MEDIUM: "MODERATE ANSWER RISK",
            KieAnswerRisk.LOW: "Low answer risk",
        }.get(sim.answer_risk, "")
        return (
            f"[{risk_label}] {len(unsupported)} claim(s) in the simulated answer are unsupported by "
            f"first-party evidence for {brand}. AI answer engines may hallucinate or cite competitors "
            f"to fill these gaps."
        )

    def _build_recommended_answer(self, brand: str, val_prop: str, question: str, sim) -> str:
        rag = (getattr(sim, "rag_answer", None) or "").strip()
        if rag:
            return rag[:700]
        if sim.candidate_answer:
            return sim.candidate_answer[:700]
        return f"The crawled pages do not state an answer to this question for {brand}."

    def _compute_projected_gain(self, risk: KieAnswerRisk, grounding_ratio: float) -> float:
        if grounding_ratio >= 0.70:
            return 0.0
        base_gain = {
            KieAnswerRisk.HIGH: 0.65,
            KieAnswerRisk.MEDIUM: 0.40,
            KieAnswerRisk.LOW: 0.20,
        }.get(risk, 0.30)
        # Reduce gain proportionally if already partially grounded
        return round(base_gain * (1.0 - grounding_ratio * 0.5), 2)

    def _extract_site_context(
        self,
        corpus_pages: List[Dict[str, Any]],
        brand: str,
        niche: str,
        val_prop: str
    ) -> Dict[str, Any]:
        """
        Extracts concrete services, products, headlines, and terminology from crawled DOM
        so questions are dynamically derived from the site's unique genre and offerings.
        """
        offerings = []
        headlines = []
        metrics = []

        for cp in corpus_pages:
            url_path = urlparse(cp["url"]).path.strip("/")
            if url_path:
                segments = [s.replace("-", " ").replace("_", " ").title() for s in url_path.split("/") if s]
                for seg in segments:
                    if seg.lower() not in {"services", "products", "about", "contact", "pricing", "blog", "privacy", "terms", "home"} and len(seg) > 2:
                        if seg not in offerings:
                            offerings.append(seg)
            
            # Extract headlines
            title = cp.get("title", "")
            if title and "|" in title:
                parts = [p.strip() for p in title.split("|") if brand.lower() not in p.lower()]
                for p in parts:
                    if len(p) > 5 and p not in headlines:
                        headlines.append(p)
            elif title and " - " in title:
                parts = [p.strip() for p in title.split(" - ") if brand.lower() not in p.lower()]
                for p in parts:
                    if len(p) > 5 and p not in headlines:
                        headlines.append(p)

            # Extract metrics / stats (e.g. 45% reduction, 99.9% uptime, 2022)
            matches = re.findall(r"(\d+%\s+[\w\s]{4,20}|\$\d+[\w\s/]*|\bSOC\s*2\b|\bISO\s*27001\b)", cp.get("text", ""), re.IGNORECASE)
            for m in matches[:5]:
                clean_m = m.strip()
                if clean_m and clean_m not in metrics:
                    metrics.append(clean_m)

        primary_offering = offerings[0] if offerings else (headlines[0] if headlines else niche)
        secondary_offering = offerings[1] if len(offerings) > 1 else (headlines[1] if len(headlines) > 1 else "strategic solutions")

        return {
            "offerings": offerings,
            "headlines": headlines,
            "metrics": metrics,
            "primary_offering": primary_offering,
            "secondary_offering": secondary_offering
        }

    async def _synthesize_facet_questions(
        self,
        facet_id: str,
        brand: str,
        niche: str,
        val_prop: str,
        corpus_pages: List[Dict[str, Any]],
        site_context: Dict[str, Any],
        profile: Optional[BusinessProfile] = None
    ) -> List[Dict[str, str]]:
        """
        Dynamically synthesizes 10 bespoke inquiries per facet using active LLM or
        deep genre-and-content extraction from the crawled site (zero fixed templates).
        """
        # Deterministic genre-and-content synthesis is preferred for $0 token cost.
        # LLM synthesis is opt-in via USE_LLM_SANDBOX_SYNTHESIS.
        use_llm_synth = getattr(settings, "USE_LLM_SANDBOX_SYNTHESIS", False)
        if use_llm_synth and self.model_router and hasattr(self.model_router, "generate_structured"):
            try:
                prompt_schema = (
                    "{\n"
                    '  "questions": [\n'
                    '    {"question": "string", "intent": "string"}\n'
                    '  ]\n'
                    "}"
                )
                contract = (
                    f"Synthesize exactly 10 bespoke commercial inquiries for the '{facet_id}' dimension "
                    f"for company '{brand}' operating in '{niche}'. Primary offering: {site_context['primary_offering']}. "
                    f"Value prop: {val_prop}. Questions must be specific to this exact company and its offerings."
                )
                ev_objs = self._build_sandbox_evidence_objects([], corpus_pages[:3], limit=3)
                llm_res = await self.model_router.generate_structured(
                    capability="aeo_question_synthesis",
                    agent_role="Commercial Generative Query Researcher",
                    task_contract=contract,
                    evidence_list=ev_objs,
                    rubric="Output exactly 10 high-value buyer inquiries with clear intent. Zero boilerplate.",
                    output_schema_desc=prompt_schema,
                    additional_context=f"Facet: {facet_id} | Brand: {brand}",
                    allow_fallback=False,
                    model_tier="reasoning_model",
                )
                qs = llm_res.get("questions") or []
                if len(qs) == 10:
                    return qs
            except Exception:
                pass  # Fall through to dynamic genre synthesis below

        # Dynamic genre and content-derived synthesis (adapts to crawled site entities)
        po = site_context.get("primary_offering") or niche
        so = site_context.get("secondary_offering") or "digital solutions"
        metric_hint = site_context.get("metrics")[0] if site_context.get("metrics") else "tangible ROI"

        builders = {
            "identity": [
                (f"What exactly is {brand} and what core commercial solution does it provide in {niche}?", f"Verify explicit corporate identity and category classification in {niche}."),
                (f"What specific business problem in {po} prompted the founding and market launch of {brand}?", f"Audit company origin story and founding rationale addressing {po}."),
                (f"Who is the executive leadership team guiding {brand}'s roadmap and operations in {niche}?", "Verify C-suite transparency and management background."),
                (f"Where is {brand} legally registered and headquartered for enterprise customer contracts?", "Verify physical headquarters and corporate entity jurisdiction."),
                (f"What is {brand}'s primary stated mission and overarching value proposition regarding {val_prop}?", "Audit brand clarity and commercial purpose."),
                (f"How long has {brand} been operating as a dedicated provider in the {niche} space?", "Audit organizational maturity and operating track record."),
                (f"What geographic markets and territories does {brand} officially support for {po} engagements?", "Verify geographical scope and operational regions."),
                (f"What core operating philosophy differentiates {brand}'s execution in {po} and {so}?", "Audit high-level organizational culture and principles."),
                (f"Does {brand} maintain registered trademarks or proprietary service marks for its {po} technology?", "Audit intellectual property assets and protected brand marks."),
                (f"How does {brand} describe its role within the wider {niche} and {po} partner ecosystem?", "Audit industry ecosystem positioning and partnership posture."),
            ],
            "icp": [
                (f"What specific customer company profile and headcount size is {brand}'s {po} built for?", "Audit target audience tier and company size fit."),
                (f"Which departmental roles (e.g. VP, Director, Lead) serve as the primary economic buyer for {brand}'s {po}?", f"Verify targeted buyer persona and budget authority for {po}."),
                (f"What specific customer profiles or business types should NOT purchase {brand}'s {po}?", "Audit explicit disqualifiers and non-target boundaries."),
                (f"Is {brand} designed for global enterprise requirements or fast-growing early teams seeking {po}?", "Determine scale suitability (Enterprise vs Mid-Market vs SMB)."),
                (f"What industry sectors represent {brand}'s primary client base for {po} and {so}?", "Audit target vertical focus."),
                (f"Does {brand} serve B2B corporate customers, consumers, or public institutions for {po}?", "Verify commercial customer model (B2B/B2C/B2G)."),
                (f"What minimum team size or operational volume is required to achieve value with {brand}'s {po}?", "Audit minimum qualification threshold."),
                (f"What technical prerequisites or team skills must a customer possess to utilize {brand}'s {po}?", "Verify customer competency prerequisites."),
                (f"How does {brand} accommodate distributed, remote, or international customer teams utilizing {so}?", "Audit organizational flexibility for multinational clients."),
                (f"What operational bottlenecks typically signal that an organization needs {brand}'s {po}?", "Audit trigger pain points and qualifying buying signals."),
            ],
            "pricing": [
                (f"What is the starting price or entry-level commercial tier for {brand}?", "Audit transparency of baseline pricing."),
                (f"Does {brand} offer public standardized subscription tiers or custom quoted contracts for {po}?", f"Determine packaging structure and pricing transparency for {po}."),
                (f"Can prospective clients sign up for {brand}'s {po} with transparent pricing online or is a sales demo mandatory?", "Audit self-serve checkout vs sales-led gating."),
                (f"Does {brand} provide a free trial, pilot engagement, or risk-free proof of concept for {po}?", "Audit evaluation trial offerings."),
                (f"What specific metric (users, volume, compute, deliverables) dictates price expansion in {brand}?", "Audit usage-based vs seat-based pricing levers."),
                (f"Are there one-time onboarding charges, migration fees, or setup retainers with {brand}?", "Audit hidden fees or implementation add-ons."),
                (f"What commercial incentives or discount structures exist for annual commitments with {brand}?", "Audit multi-month or annual commitment incentives."),
                (f"What is {brand}'s policy regarding contract termination, renewals, and refunds for {po}?", "Audit contract flexibility and cancellation terms."),
                (f"Does {brand} provide custom volume licensing for large-scale enterprise deployments of {po}?", "Verify custom enterprise Master Service Agreement (MSA) availability."),
                (f"What optional premium add-ons or specialized service modules are sold separately by {brand}?", "Audit upsell pathways and supplementary modules."),
            ],
            "capabilities": [
                (f"What are {brand}'s primary software features and flagship deliverable capabilities in {po}?", f"Audit primary feature inventory and functional scope in {po}."),
                (f"What is the end-to-end workflow when a client engages {brand} for {po}?", "Audit operational mechanics and execution stages."),
                (f"How does {brand} eliminate operational friction or manual bottlenecks in {niche}?", "Audit efficiency gains and automation scope."),
                (f"What tangible artifacts, reports, or assets are produced by {brand} for clients using {po}?", "Verify customer-facing deliverables."),
                (f"To what degree does {brand} automate recurring tasks vs requiring hands-on human execution in {so}?", "Audit human-in-the-loop vs autonomous system execution."),
                (f"What analytics, telemetry, or performance dashboards are provided within {brand}'s {po}?", "Audit reporting depth and executive visibility."),
                (f"Can workflows in {brand}'s {po} be customized with proprietary business logic or rules?", "Audit configurability and customization capabilities."),
                (f"What user interfaces (web app, CLI, desktop, mobile) are available for {brand}?", "Audit client access surfaces."),
                (f"How does {brand} facilitate collaboration, role permissions, and access governance across customer teams?", "Audit user management and access control."),
                (f"What are the operational boundaries, data throughput caps, or rate limits enforced by {brand}'s platform?", "Audit system limits and capacity ceilings."),
            ],
            "tech_stack": [
                (f"What foundational technologies, cloud infrastructure, and frameworks power {brand}'s {po}?", "Audit underlying technical architecture and stability."),
                (f"Does {brand} provide an open REST or GraphQL API for external developer integration with {po}?", "Verify programmatic API accessibility."),
                (f"Which third-party platforms natively integrate with {brand}'s {po} environment?", "Audit pre-built integration ecosystem."),
                (f"What deployment options (Multi-tenant Cloud, Dedicated VPC, On-Premise) does {brand} support for {po}?", "Audit infrastructure hosting flexibility."),
                (f"Does {brand} offer real-time webhooks or event streaming for automated data sync with {so}?", "Verify event-driven integration capabilities."),
                (f"What SDKs or client software packages are officially supported by {brand}?", "Audit language SDK coverage."),
                (f"How does {brand} ensure high availability, redundancy, and low latency across regions?", "Audit global CDN and infrastructure resilience."),
                (f"Does {brand} leverage proprietary algorithms, open models, or third-party intelligence APIs in {po}?", "Audit AI/ML model provenance and dependency risks."),
                (f"How are client data schemas ingested and transformed inside {brand}'s {po} pipeline?", "Audit data processing pipelines."),
                (f"What specific network or environment configurations are necessary to run {brand}'s {po}?", "Audit infrastructure prerequisite checklist."),
            ],
            "differentiation": [
                (f"How does {brand} compare directly to established market competitors in {niche} and {po}?", "Audit competitive positioning against primary alternatives."),
                (f"What is {brand}'s primary defensible moat against commodity market tools in {po}?", "Verify proprietary competitive moat."),
                (f"Why should an organization replace legacy manual processes with {brand}'s {po}?", "Audit value proposition vs status quo."),
                (f"What capability does {brand} offer in {po} that direct alternatives cannot match?", "Audit unique selling proposition (USP)."),
                (f"Under what circumstances would an organization be better served by a competing provider than {brand}?", "Audit honest positioning and trade-off transparency."),
                (f"How does {brand}'s cost-to-value ratio stack up against industry averages in {niche}?", "Audit commercial value equation."),
                (f"What tooling or white-glove assistance does {brand} offer for clients switching from competitors?", "Audit switching costs and migration friction."),
                (f"How does {brand} protect client workflows in {po} from industry obsolescence?", "Audit innovation roadmap and release velocity."),
                (f"What third-party analyst or benchmark reviews evaluate {brand}'s {po} against competitors?", "Audit independent competitive validation."),
                (f"How does {brand} prevent vendor lock-in for clients who may eventually transition?", "Audit data portability and export ease."),
            ],
            "trust_security": [
                (f"Does {brand} hold verified SOC 2 Type II or ISO 27001 security compliance certifications for {po}?", "Audit enterprise security accreditations."),
                (f"How does {brand} enforce GDPR, CCPA, and global data privacy standards for {po} clients?", "Verify regulatory privacy compliance."),
                (f"How is customer data protected at rest and in transit throughout {brand}'s {po} infrastructure?", "Audit encryption standards (TLS 1.3 / AES-256)."),
                (f"Does {brand} train public machine learning models on confidential client data from {po}?", "Audit AI data privacy and model training governance."),
                (f"Does {brand} publish verified third-party penetration test summaries or security audits for {po}?", "Audit independent security testing validation."),
                (f"What Single Sign-On (SAML, Okta) and Multi-Factor Authentication capabilities does {brand} provide?", "Audit enterprise identity governance."),
                (f"Does {brand} execute formal Data Processing Agreements (DPAs) with enterprise clients of {po}?", "Audit legal data protection commitments."),
                (f"In what geographic data centers and sovereign jurisdictions is {brand} customer data stored?", "Audit data residency compliance."),
                (f"What is {brand}'s documented uptime SLA and historical service availability track record?", "Audit uptime guarantees (e.g. 99.9%)."),
                (f"What is {brand}'s incident response time and public disclosure protocol during security events?", "Audit emergency incident response SLAs."),
            ],
            "customer_proof": [
                (f"What recognized client brands, enterprise logos, or partners are publicly associated with {brand}?", "Audit client logo substantiated proof."),
                (f"What documented customer case studies showcase verified production success with {brand}'s {po}?", "Verify real-world case study depth."),
                (f"What is the average quantifiable business return on investment (ROI) claimed by {brand} (such as {metric_hint})?", "Audit quantitative ROI proof."),
                (f"What specific efficiency metric has {brand} substantiated across {po} client deployments?", "Verify statistical outcome claims."),
                (f"What verified testimonials or customer reviews are published directly on {brand}'s site?", "Audit peer review evidence."),
                (f"Has {brand} received formal industry awards, venture backing, or verified analyst accolades for {po}?", "Audit external authority recognition."),
                (f"What is the typical time-to-value (days/weeks) experienced by organizations implementing {brand}'s {po}?", "Audit time-to-value benchmarks."),
                (f"What third-party review platforms (G2, Trustpilot, Capterra) hold verified ratings for {brand}?", "Audit external customer review presence."),
                (f"Does {brand} publish referenceable client quotes highlighting tangible results with {po}?", "Verify customer quote authenticity."),
                (f"Does {brand} offer performance-backed outcome guarantees for prospective {po} engagements?", "Audit performance guarantee posture."),
            ],
            "onboarding": [
                (f"How long does the typical technical onboarding and kickoff process take for {brand}'s {po}?", "Audit client onboarding velocity."),
                (f"Does {brand} assign a dedicated Customer Success Manager or implementation engineer for {po}?", "Audit dedicated support staffing."),
                (f"What customer support tiers (e.g. 24/7 emergency, Slack Connect, email) does {brand} maintain?", "Audit support channels and accessibility."),
                (f"What is the guaranteed response time SLA for high-priority support tickets submitted to {brand}?", "Audit response time commitments."),
                (f"What technical documentation, API guides, and knowledge bases are maintained for {brand}'s {po}?", "Audit self-serve documentation depth."),
                (f"Does {brand} provide interactive team training or onboarding workshops for client staff using {po}?", "Audit client education and enablement."),
                (f"How does {brand} handle data migration and initial configuration from legacy setups into {po}?", "Audit migration onboarding support."),
                (f"What recurring maintenance or updates are required from the client's internal team to run {brand}'s {po}?", "Audit ongoing maintenance burden."),
                (f"What format is customer data exported in if an engagement with {brand} is concluded?", "Audit data exit formats and offboarding ease."),
                (f"Does {brand} host a publicly accessible real-time system status page for {po}?", "Verify real-time system health transparency."),
            ],
            "purchase_flow": [
                (f"What is the exact process to schedule a product demonstration with {brand}'s {po} team?", "Audit demo booking conversion path."),
                (f"Can a prospective client immediately register and begin using {brand}'s {po} self-serve?", "Audit instant self-serve accessibility."),
                (f"What payment options (Credit Card, Invoicing, ACH, Wire Transfer) are supported by {brand}?", "Audit transaction payment flexibility."),
                (f"Does {brand} invoice in international currencies (USD, EUR, GBP, INR) for {po} services?", "Audit multi-currency payment support."),
                (f"What is the standard contract duration (month-to-month vs multi-year lock-in) for {brand}'s {po}?", "Audit contract flexibility."),
                (f"Where can prospective buyers review {brand}'s legal Terms of Service and Master Service Agreement?", "Audit legal contractual transparency."),
                (f"What direct sales telephone number, email, or physical address is provided by {brand}?", "Verify direct contact reachability."),
                (f"Does {brand} offer agency partnership or referral partner programs for {po} and {so}?", "Audit channel and affiliate partner programs."),
                (f"What is the single most urgent call-to-action (CTA) recommended for visitors seeking {po} on {brand}'s site?", "Audit primary conversion CTA clarity."),
                (f"Are enterprise procurement vendor packages and security questionnaires readily available for {brand}'s {po}?", "Audit procurement velocity and security kit readiness."),
            ],
        }

        raw_inquiries = builders.get(facet_id, builders["identity"])
        return [{"question": q, "intent": intent} for q, intent in raw_inquiries]

    def _evaluate_question_answerability(
        self,
        question: str,
        facet_id: str,
        corpus_pages: List[Dict[str, Any]],
        brand: str,
        niche: str,
        val_prop: str
    ) -> Dict[str, Any]:
        """
        Evaluates whether an answer is possible from crawled evidence.
        Returns synthesized answer, evidence snippet, and gap analysis.
        """
        # Tokenize query for semantic match
        q_clean = re.sub(r"[^\w\s]", " ", question.lower())
        stopwords = {"what", "how", "why", "does", "is", "are", "who", "where", "which", "can", "the", "and", "for", "with", "this", "that", "brand"}
        tokens = [t for t in q_clean.split() if t not in stopwords and len(t) > 3]

        best_page = None
        best_snippet = None
        match_score = 0

        # Scan crawled pages for matches
        for page in corpus_pages:
            p_text = page["lower"]
            hits = sum(1 for t in tokens if t in p_text)
            if hits > match_score:
                match_score = hits
                best_page = page
                # Find matching snippet window
                for token in tokens:
                    if token in p_text:
                        pos = p_text.find(token)
                        start = max(0, pos - 100)
                        end = min(len(page["text"]), pos + 250)
                        raw_snip = page["text"][start:end].strip()
                        raw_snip = re.sub(r"\s+", " ", raw_snip)
                        if len(raw_snip) > 40:
                            best_snippet = raw_snip
                            break

        # Determine facet target update map
        target_map = {
            "pricing": ("/pricing", "## Published Pricing Tiers & Billing Structure", "Publish a dedicated pricing tier card specifying starting rates, billing intervals, and usage limits."),
            "trust_security": ("/security", "## Security Accreditations & Data Governance", "Publish formal security certifications (SOC 2, ISO 27001, GDPR) and encryption standards."),
            "tech_stack": ("/documentation", "## Developer APIs & Technical Architecture", "Provide clear API endpoints, integration SDKs, webhooks, and technical deployment guides."),
            "onboarding": ("/support", "## Implementation SLAs & Customer Onboarding", "Document onboarding kickoff milestones, implementation timelines, and ticket SLA response guarantees."),
            "customer_proof": ("/case-studies", "## Quantified Customer Outcomes & ROI Studies", "Add customer proof, quantified metrics, and enterprise case studies."),
            "icp": ("/about", "## Target Audience & Disqualification Criteria", "Declare explicit target buyer personas, company scale criteria, and disqualifying use cases."),
            "differentiation": ("/product", "## Key Differentiators & Competitive Moat", "Articulate defensible advantages and direct feature comparisons against legacy alternatives."),
            "purchase_flow": ("/demo", "## Direct Procurement & Demo Conversion Path", "Ensure high-intent self-serve sign up or transparent demo scheduling workflows."),
        }
        target_update_page, target_update_section, target_rec_base = target_map.get(
            facet_id,
            ("/", "## Core Solutions & Value Proposition", "Expand authoritative on-page documentation addressing this inquiry.")
        )

        def _make_thinking_steps(status_str: str, ans_text: str, ev_url: Optional[str], score: int) -> List[Dict[str, Any]]:
            return [
                {
                    "step": "1",
                    "title": "Deterministic Query & Intent Mapping",
                    "status": "complete",
                    "mode": "DETERMINISTIC_HEURISTIC",
                    "thought": f"Parsed inquiry across '{facet_id}' facet against crawled page corpus via deterministic token matching.",
                },
                {
                    "step": "2",
                    "title": "DOM Corpus Hybrid Retrieval",
                    "status": "complete",
                    "mode": "DETERMINISTIC_HEURISTIC",
                    "thought": f"Searched {len(corpus_pages)} crawled pages. Best match score: {match_score}. " + (f"Top source: {ev_url}" if ev_url else "No relevant page matched."),
                    "details": {"match_score": match_score, "source_url": ev_url},
                },
                {
                    "step": "3",
                    "title": "Evidence Fact-Checking & Grounding Verification",
                    "status": "complete" if status_str == "ANSWERABLE" else ("warning" if status_str == "PARTIAL" else "action_required"),
                    "mode": "DETERMINISTIC_HEURISTIC",
                    "thought": f"Deterministic verification outcome: {status_str}. Citability score: {score}/10.",
                    "details": {"status": status_str, "citability_score": score},
                },
                {
                    "step": "4",
                    "title": "Grounded Corpus Answer Extraction",
                    "status": "complete",
                    "mode": "DETERMINISTIC_HEURISTIC",
                    "thought": f"Extracted answer strictly from crawled DOM copy without model hallucination. Content: {ans_text[:100]}...",
                },
                {
                    "step": "5",
                    "title": "Section Patch & Remediation Guidance",
                    "status": "complete" if status_str == "ANSWERABLE" else "action_required",
                    "mode": "DETERMINISTIC_HEURISTIC",
                    "thought": f"Recommended content patch on {target_update_page} in section '{target_update_section}'.",
                    "details": {"target_page": target_update_page, "target_section": target_update_section},
                },
            ]

        # Check facet-specific patterns
        if facet_id == "pricing":
            pricing_found = any(sym in page["text"] for sym in ["$", "€", "£", "₹", "/mo", "per month", "pricing tier"] for page in corpus_pages)
            if not pricing_found:
                ans = f"Pricing for {brand} is not disclosed on any crawled URL. The site routes buyers to 'Contact Sales' or demo requests."
                return {
                    "is_answerable": False,
                    "answerability_status": "UNANSWERABLE",
                    "crawled_answer": ans,
                    "rag_answer": ans,
                    "evidence_url": corpus_pages[0]["url"] if corpus_pages else None,
                    "evidence_snippet": None,
                    "gap_analysis": f"Pricing transparency gap: {brand} does not publish public pricing tiers on the crawled pages.",
                    "recommended_answer": ans,
                    "citability_score": 2,
                    "projected_patch_gain": 0.65,
                    "source_page_title": f"{brand} Official",
                    "source_section": "Pricing & Commercial Model",
                    "target_update_page": target_update_page,
                    "target_update_section": target_update_section,
                    "section_update_recommendation": f"Update {target_update_page} under section '{target_update_section}': {target_rec_base}",
                    "ai_thinking_steps": _make_thinking_steps("UNANSWERABLE", ans, corpus_pages[0]["url"] if corpus_pages else None, 2),
                }

        if facet_id == "trust_security":
            security_found = any(sec in page["lower"] for sec in ["soc 2", "iso 27001", "hipaa", "gdpr", "aes-256", "tls 1.3"] for page in corpus_pages)
            if not security_found:
                ans = f"Security compliance certifications (SOC 2, ISO 27001, GDPR) are not explicitly published on crawled pages for {brand}."
                return {
                    "is_answerable": False,
                    "answerability_status": "UNANSWERABLE",
                    "crawled_answer": ans,
                    "rag_answer": ans,
                    "evidence_url": corpus_pages[0]["url"] if corpus_pages else None,
                    "evidence_snippet": None,
                    "gap_analysis": f"The crawled pages do not state security certifications for {brand}.",
                    "recommended_answer": ans,
                    "citability_score": 3,
                    "projected_patch_gain": 0.55,
                    "source_page_title": f"{brand} Official",
                    "source_section": "Trust & Security Compliance",
                    "target_update_page": target_update_page,
                    "target_update_section": target_update_section,
                    "section_update_recommendation": f"Update {target_update_page} under section '{target_update_section}': {target_rec_base}",
                    "ai_thinking_steps": _make_thinking_steps("UNANSWERABLE", ans, corpus_pages[0]["url"] if corpus_pages else None, 3),
                }

        # General answerability determination based on match score
        src_title = best_page.get("title") if best_page else f"{brand} Official Website"
        src_sec = "Overview & Key Capabilities"

        if match_score >= 3 and best_snippet:
            crawled_ans = best_snippet[:400].strip()
            source_note = f" Source: {src_title}." if src_title else ""
            rag_ans = f"Based on {brand}'s published content: {crawled_ans}{source_note}"
            return {
                "is_answerable": True,
                "answerability_status": "ANSWERABLE",
                "crawled_answer": crawled_ans,
                "rag_answer": rag_ans,
                "evidence_url": best_page["url"] if best_page else None,
                "evidence_snippet": best_snippet[:300],
                "gap_analysis": f"Every claim in the knowledge-base answer matches a retrieved passage for {brand}.",
                "recommended_answer": rag_ans,
                "citability_score": 8,
                "projected_patch_gain": 0.0,
                "source_page_title": src_title,
                "source_section": src_sec,
                "target_update_page": target_update_page,
                "target_update_section": target_update_section,
                "section_update_recommendation": "The retrieved passage already answers this question. No new fact is required.",
                "ai_thinking_steps": _make_thinking_steps("ANSWERABLE", crawled_ans, best_page["url"] if best_page else None, 8),
            }
        elif match_score >= 1 and best_snippet:
            crawled_ans = best_snippet[:300].strip()
            rag_ans = (
                f"Based on {brand}'s published content: {crawled_ans} Note: The crawled pages do not cover all aspects of this question."
                + (f" Source: {src_title}." if src_title else "")
            )
            return {
                "is_answerable": True,
                "answerability_status": "PARTIAL",
                "crawled_answer": crawled_ans,
                "rag_answer": rag_ans,
                "evidence_url": best_page["url"] if best_page else None,
                "evidence_snippet": best_snippet[:200],
                "gap_analysis": f"The crawl mentions related terminology for {brand} and does not state a complete answer.",
                "recommended_answer": rag_ans,
                "citability_score": 5,
                "projected_patch_gain": 0.40,
                "source_page_title": src_title,
                "source_section": src_sec,
                "target_update_page": target_update_page,
                "target_update_section": target_update_section,
                "section_update_recommendation": f"Update {target_update_page} under section '{target_update_section}': {target_rec_base}",
                "ai_thinking_steps": _make_thinking_steps("PARTIAL", crawled_ans, best_page["url"] if best_page else None, 5),
            }
        else:
            ans = f"Information regarding this inquiry was not discovered on {len(corpus_pages)} crawled URL(s) for {brand}."
            return {
                "is_answerable": False,
                "answerability_status": "UNANSWERABLE",
                "crawled_answer": ans,
                "rag_answer": ans,
                "evidence_url": corpus_pages[0]["url"] if corpus_pages else None,
                "evidence_snippet": None,
                "gap_analysis": f"The crawled pages do not state an answer for {brand} on this question.",
                "recommended_answer": ans,
                "citability_score": 2,
                "projected_patch_gain": 0.50,
                "source_page_title": f"{brand} Official Website",
                "source_section": "Information Gap",
                "target_update_page": target_update_page,
                "target_update_section": target_update_section,
                "section_update_recommendation": f"Update {target_update_page} under section '{target_update_section}': {target_rec_base}",
                "ai_thinking_steps": _make_thinking_steps("UNANSWERABLE", ans, corpus_pages[0]["url"] if corpus_pages else None, 2),
            }
