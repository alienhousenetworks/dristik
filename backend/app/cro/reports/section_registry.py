"""Phase 37 & 39 — 65-Section CRO Audit Book Registry, 14 Dynamic Appendices & 14 Report Profiles.

Every section defines applicability conditions so only applicable, evidence-supported
chapters are published (zero blank or filler chapters).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# (number, part, key, title, category_filter, applicability)
CRO_BOOK_SECTIONS: Tuple[Dict[str, Any], ...] = (
    # Front Matter (1–10)
    {"num": 1, "part": "Front Matter", "key": "cover", "title": "Cover", "domain": "front"},
    {"num": 2, "part": "Front Matter", "key": "client_business_details", "title": "Client and Business Details", "domain": "front"},
    {"num": 3, "part": "Front Matter", "key": "executive_summary", "title": "Executive Summary", "domain": "front"},
    {"num": 4, "part": "Front Matter", "key": "cro_scorecard", "title": "CRO Scorecard (Experience · Measurement · Business Performance)", "domain": "front"},
    {"num": 5, "part": "Front Matter", "key": "business_objectives", "title": "Business Objectives", "domain": "front"},
    {"num": 6, "part": "Front Matter", "key": "audit_scope", "title": "Audit Scope", "domain": "front"},
    {"num": 7, "part": "Front Matter", "key": "tested_pages_journeys", "title": "Tested Pages and Journeys", "domain": "front"},
    {"num": 8, "part": "Front Matter", "key": "data_sources_connectors", "title": "Data Sources and Connectors", "domain": "front"},
    {"num": 9, "part": "Front Matter", "key": "methodology", "title": "Methodology", "domain": "front"},
    {"num": 10, "part": "Front Matter", "key": "limitations_coverage", "title": "Limitations and Measurement Coverage", "domain": "front"},
    # Part I — Business and Conversion Strategy (11–16)
    {"num": 11, "part": "Part I — Business and Conversion Strategy", "key": "business_model_analysis", "title": "Business Model Analysis", "domain": "strategy"},
    {"num": 12, "part": "Part I — Business and Conversion Strategy", "key": "conversion_goal_definition", "title": "Conversion Goal Definition", "domain": "strategy"},
    {"num": 13, "part": "Part I — Business and Conversion Strategy", "key": "primary_secondary_conversions", "title": "Primary and Secondary Conversions", "domain": "strategy"},
    {"num": 14, "part": "Part I — Business and Conversion Strategy", "key": "audience_intent_analysis", "title": "Audience and Intent Analysis", "domain": "strategy"},
    {"num": 15, "part": "Part I — Business and Conversion Strategy", "key": "offer_value_proposition", "title": "Offer and Value Proposition", "domain": "strategy"},
    {"num": 16, "part": "Part I — Business and Conversion Strategy", "key": "customer_journey_architecture", "title": "Customer Journey Architecture", "domain": "strategy"},
    # Part II — UX and Usability (17–25)
    {"num": 17, "part": "Part II — UX and Usability", "key": "ux_overview", "title": "UX Overview", "domain": "ux"},
    {"num": 18, "part": "Part II — UX and Usability", "key": "navigation", "title": "Navigation", "domain": "ux"},
    {"num": 19, "part": "Part II — UX and Usability", "key": "information_architecture", "title": "Information Architecture", "domain": "ux"},
    {"num": 20, "part": "Part II — UX and Usability", "key": "usability_interaction", "title": "Usability and Interaction", "domain": "ux"},
    {"num": 21, "part": "Part II — UX and Usability", "key": "cognitive_load", "title": "Cognitive Load", "domain": "ux"},
    {"num": 22, "part": "Part II — UX and Usability", "key": "readability", "title": "Readability", "domain": "ux"},
    {"num": 23, "part": "Part II — UX and Usability", "key": "user_journey_friction", "title": "User Journey Friction", "domain": "ux"},
    {"num": 24, "part": "Part II — UX and Usability", "key": "accessibility", "title": "Accessibility (WCAG 2.2 AA)", "domain": "accessibility"},
    {"num": 25, "part": "Part II — UX and Usability", "key": "mobile_usability", "title": "Mobile Usability", "domain": "mobile"},
    # Part III — UI and Visual Design (26–33)
    {"num": 26, "part": "Part III — UI and Visual Design", "key": "visual_hierarchy", "title": "Visual Hierarchy", "domain": "ui"},
    {"num": 27, "part": "Part III — UI and Visual Design", "key": "above_the_fold", "title": "Above-the-Fold Experience", "domain": "ui"},
    {"num": 28, "part": "Part III — UI and Visual Design", "key": "layout_spacing", "title": "Layout and Spacing", "domain": "ui"},
    {"num": 29, "part": "Part III — UI and Visual Design", "key": "typography", "title": "Typography", "domain": "ui"},
    {"num": 30, "part": "Part III — UI and Visual Design", "key": "color_contrast", "title": "Color and Contrast", "domain": "ui"},
    {"num": 31, "part": "Part III — UI and Visual Design", "key": "cta_visibility", "title": "CTA Visibility", "domain": "ui"},
    {"num": 32, "part": "Part III — UI and Visual Design", "key": "responsive_design", "title": "Responsive Design", "domain": "mobile"},
    {"num": 33, "part": "Part III — UI and Visual Design", "key": "design_consistency", "title": "Design Consistency", "domain": "ui"},
    # Part IV — Landing Pages and Copywriting (34–43)
    {"num": 34, "part": "Part IV — Landing Pages and Copywriting", "key": "landing_page_overview", "title": "Landing Page Overview", "domain": "landing"},
    {"num": 35, "part": "Part IV — Landing Pages and Copywriting", "key": "message_match", "title": "Message Match", "domain": "landing"},
    {"num": 36, "part": "Part IV — Landing Pages and Copywriting", "key": "headlines_subheadlines", "title": "Headlines and Subheadlines", "domain": "copywriting"},
    {"num": 37, "part": "Part IV — Landing Pages and Copywriting", "key": "value_proposition", "title": "Value Proposition", "domain": "copywriting"},
    {"num": 38, "part": "Part IV — Landing Pages and Copywriting", "key": "benefit_communication", "title": "Benefit Communication", "domain": "copywriting"},
    {"num": 39, "part": "Part IV — Landing Pages and Copywriting", "key": "differentiation", "title": "Differentiation", "domain": "copywriting"},
    {"num": 40, "part": "Part IV — Landing Pages and Copywriting", "key": "objection_handling", "title": "Objection Handling", "domain": "copywriting"},
    {"num": 41, "part": "Part IV — Landing Pages and Copywriting", "key": "copywriting_quality", "title": "Copywriting Quality", "domain": "copywriting"},
    {"num": 42, "part": "Part IV — Landing Pages and Copywriting", "key": "cta_messaging", "title": "CTA Messaging", "domain": "copywriting"},
    {"num": 43, "part": "Part IV — Landing Pages and Copywriting", "key": "wireframe_recommendations", "title": "Page Structure and Wireframe Recommendations", "domain": "landing"},
    # Part V — Conversion Interactions (44–52)
    {"num": 44, "part": "Part V — Conversion Interactions", "key": "cta_inventory", "title": "CTA Inventory and Behavior", "domain": "cta"},
    {"num": 45, "part": "Part V — Conversion Interactions", "key": "form_inventory", "title": "Form Inventory", "domain": "forms"},
    {"num": 46, "part": "Part V — Conversion Interactions", "key": "form_field_optimization", "title": "Form Field Optimization", "domain": "forms"},
    {"num": 47, "part": "Part V — Conversion Interactions", "key": "form_validation_errors", "title": "Form Validation and Errors", "domain": "forms"},
    {"num": 48, "part": "Part V — Conversion Interactions", "key": "lead_generation_journey", "title": "Lead-Generation Journey", "domain": "leadgen"},
    {"num": 49, "part": "Part V — Conversion Interactions", "key": "product_pages", "title": "Product Pages", "domain": "ecommerce", "requires_ecommerce": True},
    {"num": 50, "part": "Part V — Conversion Interactions", "key": "cart_experience", "title": "Cart Experience", "domain": "ecommerce", "requires_ecommerce": True},
    {"num": 51, "part": "Part V — Conversion Interactions", "key": "checkout_experience", "title": "Checkout Experience", "domain": "checkout", "requires_ecommerce": True},
    {"num": 52, "part": "Part V — Conversion Interactions", "key": "payment_experience", "title": "Payment Experience", "domain": "checkout", "requires_ecommerce": True},
    # Part VI — Trust and Technical Experience (53–59)
    {"num": 53, "part": "Part VI — Trust and Technical Experience", "key": "trust_credibility", "title": "Trust and Credibility", "domain": "trust"},
    {"num": 54, "part": "Part VI — Trust and Technical Experience", "key": "reviews_testimonials", "title": "Reviews and Testimonials", "domain": "trust"},
    {"num": 55, "part": "Part VI — Trust and Technical Experience", "key": "pricing_policy_transparency", "title": "Pricing and Policy Transparency", "domain": "trust"},
    {"num": 56, "part": "Part VI — Trust and Technical Experience", "key": "performance_cwv", "title": "Performance and Core Web Vitals", "domain": "performance"},
    {"num": 57, "part": "Part VI — Trust and Technical Experience", "key": "js_interaction_reliability", "title": "JavaScript and Interaction Reliability", "domain": "performance"},
    {"num": 58, "part": "Part VI — Trust and Technical Experience", "key": "device_browser_compatibility", "title": "Device and Browser Compatibility", "domain": "mobile"},
    {"num": 59, "part": "Part VI — Trust and Technical Experience", "key": "mobile_conversion_experience", "title": "Mobile Conversion Experience", "domain": "mobile"},
    # Part VII — Analytics and Business Performance (60–64)
    {"num": 60, "part": "Part VII — Analytics and Business Performance", "key": "analytics_configuration", "title": "Analytics Configuration", "domain": "analytics"},
    {"num": 61, "part": "Part VII — Analytics and Business Performance", "key": "event_tracking_validation", "title": "Event Tracking and Validation", "domain": "analytics"},
    {"num": 62, "part": "Part VII — Analytics and Business Performance", "key": "funnel_analysis", "title": "Funnel Analysis", "domain": "analytics"},
    {"num": 63, "part": "Part VII — Analytics and Business Performance", "key": "attribution_revenue", "title": "Attribution and Revenue Intelligence", "domain": "analytics"},
    {"num": 64, "part": "Part VII — Analytics and Business Performance", "key": "conversion_segment_analysis", "title": "Conversion Performance and Segment Analysis", "domain": "analytics"},
    # Part VIII — Execution and Improvement (65)
    {"num": 65, "part": "Part VIII — Execution and Improvement", "key": "consolidated_findings_roadmap", "title": "Consolidated Findings and Remediation Roadmap", "domain": "remediation"},
)

CRO_DYNAMIC_APPENDICES: Tuple[Dict[str, str], ...] = (
    {"id": "A1", "key": "page_inventory", "title": "Complete Page Inventory"},
    {"id": "A2", "key": "journey_maps", "title": "Journey Maps"},
    {"id": "A3", "key": "browser_test_results", "title": "Browser Test Results"},
    {"id": "A4", "key": "screenshots", "title": "Screenshots & Visual Snapshots"},
    {"id": "A5", "key": "dom_element_evidence", "title": "DOM and Element Evidence"},
    {"id": "A6", "key": "form_cta_inventories", "title": "Form and CTA Inventories"},
    {"id": "A7", "key": "analytics_event_dictionary", "title": "Analytics Event Dictionary"},
    {"id": "A8", "key": "funnel_datasets", "title": "Funnel Datasets"},
    {"id": "A9", "key": "experiment_designs_results", "title": "Experiment Designs and Results"},
    {"id": "A10", "key": "finding_registry", "title": "Finding Registry"},
    {"id": "A11", "key": "remediation_tasks", "title": "Remediation Tasks"},
    {"id": "A12", "key": "verification_records", "title": "Verification Records"},
    {"id": "A13", "key": "methodology", "title": "Methodology"},
    {"id": "A14", "key": "data_limitations", "title": "Data Limitations"},
)

# All 14 Audience-Specific Report Profiles (Phase 39)
CRO_REPORT_PROFILES: Dict[str, Dict[str, Any]] = {
    "executive_brief": {
        "title": "CRO Executive Brief",
        "audience": "CEO and Leadership",
        "domains": ["front", "strategy", "analytics", "remediation"],
        "appendices": ["A10", "A11", "A14"],
    },
    "complete_audit_book": {
        "title": "Complete Enterprise CRO Audit Book",
        "audience": "Enterprise Clients",
        "domains": ["*"],
        "appendices": ["*"],
    },
    "ux_ui_audit": {
        "title": "UX/UI Conversion Audit",
        "audience": "Design and Product Teams",
        "domains": ["front", "ux", "ui", "accessibility", "mobile", "remediation"],
        "appendices": ["A1", "A3", "A4", "A5", "A10"],
    },
    "landing_page_report": {
        "title": "Landing Page Optimization Report",
        "audience": "Marketing Teams",
        "domains": ["front", "landing", "copywriting", "cta", "trust", "remediation"],
        "appendices": ["A1", "A6", "A10", "A11"],
    },
    "copywriting_report": {
        "title": "Copywriting Improvement Report",
        "audience": "Content and Marketing Teams",
        "domains": ["front", "copywriting", "trust", "remediation"],
        "appendices": ["A6", "A10", "A11"],
    },
    "forms_leadgen_report": {
        "title": "Forms and Lead Generation Report",
        "audience": "Sales and Marketing Teams",
        "domains": ["front", "forms", "cta", "leadgen", "trust", "remediation"],
        "appendices": ["A3", "A6", "A10", "A11"],
    },
    "ecommerce_cro_report": {
        "title": "Ecommerce CRO Report",
        "audience": "Ecommerce Operators",
        "domains": ["front", "ecommerce", "checkout", "trust", "mobile", "analytics", "remediation"],
        "appendices": ["A1", "A2", "A8", "A10", "A11"],
    },
    "checkout_report": {
        "title": "Checkout Optimization Report",
        "audience": "Product and Engineering Teams",
        "domains": ["front", "checkout", "forms", "performance", "analytics", "remediation"],
        "appendices": ["A3", "A6", "A8", "A11", "A12"],
    },
    "analytics_funnel_report": {
        "title": "Analytics and Funnel Report",
        "audience": "Analytics Teams",
        "domains": ["front", "analytics", "remediation"],
        "appendices": ["A2", "A7", "A8", "A13", "A14"],
    },
    "mobile_cro_report": {
        "title": "Mobile CRO Report",
        "audience": "Product and Design Teams",
        "domains": ["front", "mobile", "accessibility", "performance", "remediation"],
        "appendices": ["A3", "A4", "A10", "A11"],
    },
    "remediation_pack": {
        "title": "Consolidated CRO Remediation Pack",
        "audience": "Developers and Implementation Teams",
        "domains": ["front", "remediation"],
        "appendices": ["A1", "A6", "A10", "A11", "A12"],
    },
    "experimentation_report": {
        "title": "CRO Experimentation Report",
        "audience": "Growth and Experimentation Teams",
        "domains": ["front", "analytics", "remediation"],
        "appendices": ["A8", "A9", "A13", "A14"],
    },
    "verification_report": {
        "title": "Independent CRO Verification Report",
        "audience": "Management and Reviewers",
        "domains": ["front", "remediation"],
        "appendices": ["A10", "A11", "A12", "A14"],
    },
    "evidence_appendix": {
        "title": "CRO Technical & Compliance Evidence Appendix",
        "audience": "Technical and Compliance Reviewers",
        "domains": ["front"],
        "appendices": ["*"],
    },
}
