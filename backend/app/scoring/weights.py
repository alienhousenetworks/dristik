"""
Dristik AI Intent-Adaptive Scoring Weights
Defines baseline category weights and dynamic re-balancing multipliers based on business intent.
"""
from typing import Dict
from app.domain.enums import BusinessIntent, Category

BASELINE_WEIGHTS: Dict[Category, float] = {
    Category.TECHNICAL_SEO: 0.15,
    Category.ON_PAGE_SEO: 0.10,
    Category.CONTENT: 0.15,
    Category.GEO: 0.15,
    Category.AI_SEARCH: 0.15,
    Category.SCHEMA: 0.10,
    Category.UX_CONVERSION: 0.10,
    Category.TRUST_AUTHORITY: 0.10,
}

INTENT_MULTIPLIERS: Dict[BusinessIntent, Dict[Category, float]] = {
    BusinessIntent.SAAS: {
        Category.AI_SEARCH: 1.25,
        Category.GEO: 1.20,
        Category.UX_CONVERSION: 1.15,
        Category.TECHNICAL_SEO: 0.90,
    },
    BusinessIntent.ECOMMERCE: {
        Category.SCHEMA: 1.35,
        Category.UX_CONVERSION: 1.30,
        Category.TRUST_AUTHORITY: 1.20,
        Category.GEO: 0.85,
    },
    BusinessIntent.LEAD_GENERATION: {
        Category.UX_CONVERSION: 1.30,
        Category.TRUST_AUTHORITY: 1.25,
        Category.AI_SEARCH: 1.15,
    },
    BusinessIntent.CONTENT_PUBLISHING: {
        Category.CONTENT: 1.35,
        Category.GEO: 1.25,
        Category.TECHNICAL_SEO: 1.15,
        Category.UX_CONVERSION: 0.75,
    },
    BusinessIntent.AGENCY: {
        Category.TRUST_AUTHORITY: 1.30,
        Category.UX_CONVERSION: 1.20,
        Category.GEO: 1.15,
    }
}

def compute_intent_adjusted_weights(intent: BusinessIntent) -> Dict[Category, float]:
    multipliers = INTENT_MULTIPLIERS.get(intent, {})
    adjusted = {}
    
    for cat, base_w in BASELINE_WEIGHTS.items():
        mult = multipliers.get(cat, 1.0)
        adjusted[cat] = base_w * mult
        
    total = sum(adjusted.values())
    # Normalize accurately
    return {cat: (w / total) for cat, w in adjusted.items()}
