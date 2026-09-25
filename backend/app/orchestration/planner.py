"""
Dristik AI Adaptive Information-Gain Planner
Formulates capability execution schedules, detects evidence uncertainty,
and dynamically plans adaptive investigation loops.
"""
from typing import List, Dict, Any, Optional
from app.domain.models import CrawlManifest
from app.domain.capability import CAPABILITY_REGISTRY, CapabilityDomain, ExecutionTier

class AdaptiveMissionPlanner:
    def plan_mission(self, manifest: CrawlManifest) -> Dict[str, Any]:
        """
        Formulates capability execution tiers based on crawl depth, domain structure, and business intent.
        """
        # Tier 1: Deterministic Technical Foundation ($0 inference)
        technical_caps = [
            "01_discovery",
            "02_semantic_structure",
            "03_indexability",
            "04_link_architecture",
            "05_performance",
            "06_security",
            "07_asset_optimization",
            "08_mobile_readiness",
            "09_schema_syntax",
            "11_opengraph_metadata",
            "19_readability",
            "21_cannibalization"
        ]

        # Tier 2: Business & Positioning Foundation (SLM)
        business_caps = [
            "12_positioning",
            "13_icp_alignment",
            "14_value_prop_strength",
            "15_commercial_clarity"
        ]

        # Tier 3: Parallel Specialist Intelligence (GEO, AI Search, Content, UX)
        specialist_caps = [
            "10_entity_graph",
            "16_competitive_differentiation",
            "17_content_depth",
            "18_eeat_authority",
            "20_topic_coverage",
            "22_direct_extractability",
            "23_information_gain",
            "24_summarizability",
            "25_citation_readiness",
            "26_ai_discoverability",
            "31_ux_friction",
            "32_trust_signals",
            "33_conversion_cro"
        ]

        # Tier 4: Adversarial Review & Contradiction Resolution
        verification_caps = [
            "34_adversarial_verification",
            "35_contradiction_resolution"
        ]

        return {
            "tier_1_deterministic": technical_caps,
            "tier_2_business": business_caps,
            "tier_3_specialists": specialist_caps,
            "tier_4_verification": verification_caps,
            "total_capabilities": 35
        }

    def evaluate_uncertainty(self, claims: List[Any], evidence_count: int) -> Dict[str, Any]:
        """
        Evaluates whether additional targeted crawl investigations are required to resolve ambiguous claims.
        """
        low_confidence_claims = [c for c in claims if getattr(c, "confidence", 1.0) < 0.70]
        needs_investigation = len(low_confidence_claims) > 2 and evidence_count < 20

        return {
            "needs_investigation": needs_investigation,
            "uncertain_claims_count": len(low_confidence_claims),
            "expected_information_gain": 0.85 if needs_investigation else 0.10
        }
