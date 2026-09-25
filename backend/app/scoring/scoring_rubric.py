"""
Dristik AI Scoring Rubric & Methodology Specification (v4.0)
Published mathematical definitions, weights, diminishing returns curves, and confidence gating rules.
"""
from typing import Dict, Any, List

SCORING_RUBRIC_V4: Dict[str, Any] = {
    "version": "enterprise_web_intel_v4",
    "specification_name": "Dristik Enterprise Web Intelligence & Audit Rubric",
    "last_revised": "September 2026",
    "philosophical_principles": [
        "No Fabricated Metrics: No invented CAC, TAM, or synthetic backlink scores.",
        "Diminishing Returns: Repeating issues hit less severely than novel architectural defects.",
        "Strict Confidence Gating: Single-source unverified claims cannot headline executive summaries or trigger critical severity penalties.",
        "Empirical Grounding: DOM-checkable facts are separated from cognitive AI advisories.",
    ],
    "five_pillars": [
        {
            "id": "search_seo",
            "name": "Pillar 1: Search Intelligence (Technical & On-Page SEO)",
            "weight_pct": 25,
            "core_signals": [
                "HTTP Status Codes & Canonical Headers",
                "Robots.txt & XML Sitemap Availability",
                "H1 Hierarchy & Title/Meta Tag Lengths",
                "DOM-Validated Schema.org Structured Data",
                "Mobile Viewport & Crawl Health (TTFB, 4xx/5xx errors)",
            ],
            "measurement_mode": "Empirical AST & DOM Crawl",
        },
        {
            "id": "ai_search_geo",
            "name": "Pillar 2: AI Search Intelligence (GEO / AEO / LLMO)",
            "weight_pct": 25,
            "core_signals": [
                "Live Cross-Engine Citations (Gemini, ChatGPT, Perplexity, Claude)",
                "Direct Definition & Entity Clarity in Top 200 Words",
                "Fact Extractability & Pricing Transparency for Answer Engines",
                "6-Query Canonical Buyer Inquiry Coverage",
            ],
            "measurement_mode": "Live Multi-Model Querying + DOM Semantic Extraction",
        },
        {
            "id": "experience_sxo",
            "name": "Pillar 3: Experience Intelligence (SXO & Readability)",
            "weight_pct": 20,
            "core_signals": [
                "Flesch-Kincaid / Gunning-Fog Readability Score (Target: 60-80)",
                "Layout Shift & Mobile Viewport Readiness",
                "Content Scannability & Proof-Point Density",
                "Navigation Breadcrumb Clarity",
            ],
            "measurement_mode": "Empirical Heuristics & Text Complexity",
        },
        {
            "id": "conversion_cro",
            "name": "Pillar 4: Conversion Intelligence (CRO & Funnels)",
            "weight_pct": 20,
            "core_signals": [
                "5-Second Value Proposition Clarity",
                "Primary Call-to-Action Action Verbs & Contrast",
                "Form Field Barrier Count (< 4 fields optimal)",
                "Competitive Commercial Bakeoff Delta",
            ],
            "measurement_mode": "Behavioral Heuristics + GA4 First-Party Data Connector",
        },
        {
            "id": "brand_trust",
            "name": "Pillar 5: Trust Intelligence (On-Page E-E-A-T Architecture)",
            "weight_pct": 10,
            "core_signals": [
                "HTTPS Encryption & Modern TLS",
                "Organization Schema with Valid @type and SameAs Links",
                "Published Privacy Policy & Terms of Service URLs",
                "Direct NAP (Name, Address, Phone) & Support Email",
                "Author / Leadership Attribution",
            ],
            "measurement_mode": "Verified On-Page Governance (External Backlink Graph Optional via Majestic/DataForSEO)",
        },
    ],
    "diminishing_returns": {
        "formula": "Deduction = BaseStep[occurrence_index]",
        "step_tables": {
            "CRITICAL": [25.0, 12.0, 8.0, 5.0],
            "HIGH": [15.0, 9.0, 6.0, 4.0],
            "MEDIUM": [8.0, 5.0, 3.0, 2.0],
            "LOW": [3.0, 2.0, 1.0, 1.0],
            "INFO": [0.0, 0.0, 0.0, 0.0],
        },
        "rationale": "The first critical defect (e.g. site returning 500 error or robots blocking index) fundamentally damages accessibility. Subsequent defects of equal severity erode performance at a diminishing rate to prevent score collapse on a single taxonomy of error.",
    },
    "confidence_gating_rules": {
        "verified_dom_facts": {
            "definition": "Directly measured from HTML DOM, HTTP response, or AST nodes.",
            "eligible_for_executive_blockers": True,
            "max_severity_allowed": "CRITICAL",
            "ui_tag": "🔬 VERIFIED DOM FACT",
        },
        "corroborated_findings": {
            "definition": "Supported by multiple independent agents or confirmed by external ground truth.",
            "eligible_for_executive_blockers": True,
            "max_severity_allowed": "CRITICAL",
            "ui_tag": "CORROBORATED",
        },
        "single_source_unverified": {
            "definition": "Cognitive inference or single-source observation without secondary corroboration or raw DOM token.",
            "eligible_for_executive_blockers": False,
            "max_severity_allowed": "MEDIUM (Capped at 4.0 pts deduction)",
            "ui_tag": "💡 COGNITIVE MODEL INFERENCE",
            "placement": "Routed exclusively to Exploratory Hypotheses",
        },
    },
    "score_bands": [
        {"band": "Category Benchmark", "min_score": 90, "max_score": 100, "status": "Best-in-class technical and citation posture"},
        {"band": "Citation Ready", "min_score": 75, "max_score": 89.9, "status": "Strong discoverability with minor friction points"},
        {"band": "Fragile Presence", "min_score": 50, "max_score": 74.9, "status": "At risk of being filtered by answer engines and search bots"},
        {"band": "Critical Vulnerability", "min_score": 0, "max_score": 49.9, "status": "Severe indexing or accessibility bottlenecks blocking revenue"},
    ],
}


def get_scoring_rubric_v4() -> Dict[str, Any]:
    return SCORING_RUBRIC_V4
