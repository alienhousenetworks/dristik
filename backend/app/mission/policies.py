"""
Dristik AI Industry Policy Packs & Audit Modes
Provides domain-specific evaluation weights, required entities, and audit mode configurations.
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class IndustryPolicy(BaseModel):
    industry_id: str
    display_name: str
    required_signals: List[str]
    important_entities: List[str]
    scoring_weight_modifiers: Dict[str, float]
    compliance_signals: List[str]
    buyer_intents: List[str]
    risk_rules: List[str]

INDUSTRY_POLICIES: Dict[str, IndustryPolicy] = {
    "saas": IndustryPolicy(
        industry_id="saas",
        display_name="Enterprise & B2B SaaS",
        required_signals=["pricing_tiers", "security_compliance", "api_docs", "integrations", "free_trial_demo"],
        important_entities=["SoftwareApplication", "Organization", "Offer", "Product"],
        scoring_weight_modifiers={"BUSINESS": 1.2, "AI_SEARCH": 1.25, "GEO": 1.15, "TECHNICAL": 1.0},
        compliance_signals=["SOC2", "GDPR", "HIPAA", "ISO27001"],
        buyer_intents=["enterprise_procurement", "software_comparison", "roi_evaluation"],
        risk_rules=["Ambiguous self-serve vs enterprise sales path", "Missing data privacy security documentation"]
    ),
    "ecommerce": IndustryPolicy(
        industry_id="ecommerce",
        display_name="E-Commerce & DTC",
        required_signals=["product_catalog", "pricing_transparency", "return_policy", "customer_reviews", "checkout_security"],
        important_entities=["Product", "Offer", "AggregateRating", "Brand"],
        scoring_weight_modifiers={"UX_CONVERSION": 1.3, "TECHNICAL": 1.1, "STRUCTURED_DATA": 1.25, "BUSINESS": 0.9},
        compliance_signals=["PCI-DSS", "SSL", "Return Policy", "Cookie Consent"],
        buyer_intents=["transactional", "product_comparison", "coupon_discount"],
        risk_rules=["Missing product schema", "High cart/checkout friction", "Unclear return policy"]
    ),
    "local_business": IndustryPolicy(
        industry_id="local_business",
        display_name="Local & Service Business",
        required_signals=["nap_consistency", "service_areas", "google_maps_schema", "local_reviews", "phone_contact"],
        important_entities=["LocalBusiness", "PostalAddress", "OpeningHoursSpecification", "GeoCoordinates"],
        scoring_weight_modifiers={"STRUCTURED_DATA": 1.3, "TECHNICAL": 1.1, "UX_CONVERSION": 1.2, "AI_SEARCH": 1.0},
        compliance_signals=["License", "Insurance", "Privacy Policy"],
        buyer_intents=["near_me", "service_booking", "quote_request"],
        risk_rules=["Inconsistent NAP across pages", "Missing LocalBusiness schema"]
    ),
    "general": IndustryPolicy(
        industry_id="general",
        display_name="General Commercial Website",
        required_signals=["value_proposition", "contact_info", "about_us", "terms_privacy", "clear_ctas"],
        important_entities=["Organization", "WebSite", "ContactPoint"],
        scoring_weight_modifiers={"TECHNICAL": 1.0, "BUSINESS": 1.0, "AI_SEARCH": 1.0, "GEO": 1.0},
        compliance_signals=["HTTPS", "Privacy Policy"],
        buyer_intents=["informational", "lead_generation", "brand_discovery"],
        risk_rules=["Unclear value proposition", "Broken contact funnel"]
    )
}

def get_industry_policy(industry_key: str) -> IndustryPolicy:
    clean_key = (industry_key or "").lower().strip()
    for key, policy in INDUSTRY_POLICIES.items():
        if key in clean_key:
            return policy
    return INDUSTRY_POLICIES["general"]
