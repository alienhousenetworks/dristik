"""Phase 12.6: Enterprise Regression Benchmark Library.

Permanent calibration benchmark suite covering 10 diverse website archetypes:
1. Known-Good Architecture
2. Known-Defect Failure Cases
3. WordPress / WooCommerce
4. Shopify E-commerce Catalog
5. Webflow SaaS Platform
6. Professional Service Firm
7. Large-Scale Enterprise Site (>100k pages)
8. JavaScript-Heavy Hydrated SPA
9. Multilingual Regional Site (hreflang)
10. Unusual API/Headless Architecture

Tracks false positives, false negatives, and guarantees 10/10 deterministic replay parity.
"""
from __future__ import annotations

from typing import Any, Optional

from app.governance.models import BenchmarkSiteProfile


class RegressionBenchmarkLibrary:
    """Manages gold-standard benchmark site profiles and deterministic calibration suites."""

    def __init__(self):
        self._profiles: dict[str, BenchmarkSiteProfile] = {}
        self._bootstrap_10_archetypes()

    def _bootstrap_10_archetypes(self) -> None:
        archetypes = [
            BenchmarkSiteProfile(
                profile_id="ARCH_01_KNOWN_GOOD",
                archetype_name="Known-Good Enterprise Site",
                site_type="SAAS",
                cms="CUSTOM_STATIC",
                expected_score_ranges={"TECHNICAL_HEALTH": (88.0, 100.0), "CONTENT_READINESS": (85.0, 100.0)},
                known_defects=[],
                sample_evidence={"canonical_valid": True, "ttfb_ms": 140, "broken_links": 0},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_02_KNOWN_DEFECT",
                archetype_name="Known-Defect Failure Site",
                site_type="BLOG",
                cms="LEGACY_PHP",
                expected_score_ranges={"TECHNICAL_HEALTH": (0.0, 50.0), "CONTENT_READINESS": (0.0, 45.0)},
                known_defects=["REDIRECT_LOOP", "NOINDEX_INJECTION", "BROKEN_LINKS"],
                sample_evidence={"redirect_loop": True, "noindex_present": True, "broken_links": 28},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_03_WORDPRESS",
                archetype_name="WordPress / WooCommerce Store",
                site_type="ECOMMERCE",
                cms="WORDPRESS",
                expected_score_ranges={"TECHNICAL_HEALTH": (65.0, 85.0), "USER_EXPERIENCE": (70.0, 90.0)},
                known_defects=["MISSING_H1_ON_CATEGORY"],
                sample_evidence={"taxonomy_pages": 45, "woocommerce_active": True},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_04_SHOPIFY",
                archetype_name="Shopify E-Commerce Catalog",
                site_type="ECOMMERCE",
                cms="SHOPIFY",
                expected_score_ranges={"TECHNICAL_HEALTH": (75.0, 92.0), "BUSINESS_PERFORMANCE": (80.0, 98.0)},
                known_defects=["DUPLICATE_COLLECTION_URLS"],
                sample_evidence={"variants_count": 120, "checkout_flow_active": True},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_05_WEBFLOW",
                archetype_name="Webflow B2B SaaS Platform",
                site_type="SAAS",
                cms="WEBFLOW",
                expected_score_ranges={"TECHNICAL_HEALTH": (80.0, 95.0), "USER_EXPERIENCE": (85.0, 98.0)},
                known_defects=[],
                sample_evidence={"clean_semantic_dom": True, "cms_collections": 6},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_06_SERVICES",
                archetype_name="High-Ticket Professional Services",
                site_type="SERVICES",
                cms="CUSTOM_REACT",
                expected_score_ranges={"TECHNICAL_HEALTH": (70.0, 90.0), "USER_EXPERIENCE": (60.0, 85.0)},
                known_defects=["HIGH_FORM_FRICTION"],
                sample_evidence={"inquiry_form_fields": 8},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_07_LARGE_SCALE",
                archetype_name="Large-Scale Enterprise (>100k URLs)",
                site_type="MEDIA_PUBLISHER",
                cms="ENTERPRISE_CUSTOM",
                expected_score_ranges={"TECHNICAL_HEALTH": (60.0, 80.0), "CONTENT_READINESS": (65.0, 85.0)},
                known_defects=["PAGINATION_ORPHANS"],
                sample_evidence={"urls_crawled": 120000, "pagination_depth": 24},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_08_JS_SPA",
                archetype_name="JavaScript Hydrated Next.js App",
                site_type="WEB_APPLICATION",
                cms="NEXTJS",
                expected_score_ranges={"TECHNICAL_HEALTH": (70.0, 90.0), "CONTENT_READINESS": (60.0, 80.0)},
                known_defects=["CLIENT_SIDE_RENDER_DELAY"],
                sample_evidence={"hydration_time_ms": 650, "ssr_enabled": True},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_09_MULTILINGUAL",
                archetype_name="Multilingual Regional Portal",
                site_type="INTERNATIONAL",
                cms="DRUPAL",
                expected_score_ranges={"TECHNICAL_HEALTH": (70.0, 90.0), "CONTENT_READINESS": (75.0, 92.0)},
                known_defects=["MISSING_RETURN_HREFLANG"],
                sample_evidence={"locales": ["en-US", "es-ES", "de-DE", "ja-JP"]},
            ),
            BenchmarkSiteProfile(
                profile_id="ARCH_10_UNUSUAL",
                archetype_name="Unusual Headless / Multi-Origin Architecture",
                site_type="HEADLESS_PORTAL",
                cms="CUSTOM_GRAPHQL",
                expected_score_ranges={"TECHNICAL_HEALTH": (65.0, 88.0), "OBSERVED_VISIBILITY": (60.0, 85.0)},
                known_defects=["CROSS_ORIGIN_CANONICAL_MISMATCH"],
                sample_evidence={"api_gateway": "https://api.example.com", "frontend_origin": "https://example.com"},
            ),
        ]

        for a in archetypes:
            self._profiles[a.profile_id] = a

    def get_profile(self, profile_id: str) -> Optional[BenchmarkSiteProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[BenchmarkSiteProfile]:
        return list(self._profiles.values())

    def evaluate_benchmark(
        self,
        profile_id: str,
        measured_scores: dict[str, float],
        detected_defects: list[str],
    ) -> dict[str, Any]:
        """Evaluates engine performance against benchmark archetype truth."""
        profile = self._profiles.get(profile_id)
        if not profile:
            raise ValueError(f"Unknown benchmark site profile '{profile_id}'.")

        # 1. Score boundary checks
        score_failures = []
        for cat, (low, high) in profile.expected_score_ranges.items():
            actual = measured_scores.get(cat)
            if actual is not None and not (low <= actual <= high):
                score_failures.append(
                    f"{cat} score {actual:.1f} out of expected range [{low:.1f}, {high:.1f}]."
                )

        # 2. False Positives & False Negatives tracking
        expected_defects = set(profile.known_defects)
        actual_defects = set(detected_defects)

        false_positives = sorted(list(actual_defects - expected_defects))
        false_negatives = sorted(list(expected_defects - actual_defects))

        passed = len(score_failures) == 0 and len(false_negatives) == 0

        return {
            "profile_id": profile_id,
            "passed": passed,
            "score_failures": score_failures,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "measured_scores": measured_scores,
        }

    @staticmethod
    def verify_deterministic_replay(run_a: dict[str, Any], run_b: dict[str, Any]) -> bool:
        """10/10 Acceptance: Two executions against identical immutable evidence must yield identical measurements.

        Verifies that correlation R = 1.0 and zero score drift occurs across executions.
        """
        # Compare scores
        scores_a = run_a.get("scores", {})
        scores_b = run_b.get("scores", {})
        if scores_a != scores_b:
            return False

        # Compare finding identities and severities
        f_a = sorted([(f.get("finding_id"), f.get("severity")) for f in run_a.get("findings", [])])
        f_b = sorted([(f.get("finding_id"), f.get("severity")) for f in run_b.get("findings", [])])
        if f_a != f_b:
            return False

        return True
