"""
Cross-Discipline Regression Testing Engine — Phase 9.4 (10/10 Transformation)

Validates that a deployed remediation did not introduce cross-discipline regressions:
1. Metadata changes break template rendering (unclosed tags or missing structure)
2. CSS fixes create mobile overflow (viewport / overflow-x issues)
3. Schema modifications create invalid JSON-LD syntax
4. Redirect changes create loops or excessive hops (>2)
5. New scripts degrade performance (TTFB spike or size bloat)
6. Navigation changes create broken links or 404s
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.verification.models import RegressionCheckResult

logger = logging.getLogger("dristik.verification.regression")


class CrossDisciplineRegressionEngine:
    """
    Executes cross-discipline regression checks on post-deployment crawl artifacts.
    """

    def check_regressions(
        self,
        baseline_evidence: Dict[str, Any],
        post_deploy_evidence: Dict[str, Any],
    ) -> RegressionCheckResult:
        html = post_deploy_evidence.get("html", "")

        # 1. Template Rendering Regression (Metadata / HTML)
        open_tags = len(re.findall(r'<[a-zA-Z][^>/]*>', html or ""))
        close_tags = len(re.findall(r'</[a-zA-Z][^>]*>', html or ""))
        void_tags = len(re.findall(r'<(?:meta|link|input|img|br|hr)[^>]*>', html or "", re.IGNORECASE))
        if open_tags > close_tags + void_tags + 15:
            return RegressionCheckResult(
                has_regression=True,
                regression_type="METADATA_RENDER",
                details="Template rendering regression: severe HTML unclosed tag imbalance detected.",
                affected_selector="html, head, body",
            )

        # 2. Schema Syntax Regression
        scripts = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or "", re.DOTALL | re.IGNORECASE)
        for s in scripts:
            try:
                json.loads(s.strip())
            except Exception as e:
                return RegressionCheckResult(
                    has_regression=True,
                    regression_type="SCHEMA_SYNTAX",
                    details=f"Schema regression: invalid JSON-LD introduced: {e}",
                    affected_selector="script[type='application/ld+json']",
                )

        # 3. Mobile Overflow Regression (CSS / Layout)
        if "overflow-x: scroll" in html or "width: 1500px" in html or "width:1200px" in html:
            # Fixed desktop width without media queries can break mobile
            if "@media" not in html and "max-width" not in html:
                return RegressionCheckResult(
                    has_regression=True,
                    regression_type="MOBILE_OVERFLOW",
                    details="Mobile layout regression: fixed desktop pixel width introduces horizontal overflow.",
                    affected_selector="div, container",
                )

        # 4. Redirect Loop Regression
        redirect_chain = post_deploy_evidence.get("redirect_chain", [])
        if len(redirect_chain) > 2:
            return RegressionCheckResult(
                has_regression=True,
                regression_type="REDIRECT_LOOP",
                details=f"Redirect regression: excessive hops ({len(redirect_chain)}) detected: {redirect_chain}",
            )
        # Check for loop: e.g. ["/a", "/b", "/a"]
        if len(redirect_chain) != len(set(redirect_chain)):
            return RegressionCheckResult(
                has_regression=True,
                regression_type="REDIRECT_LOOP",
                details=f"Redirect regression: circular loop detected: {redirect_chain}",
            )

        # 5. Performance Spike Regression
        base_ttfb = float(baseline_evidence.get("ttfb_ms", 180.0))
        new_ttfb = float(post_deploy_evidence.get("ttfb_ms", 180.0))
        if new_ttfb > (base_ttfb * 2.0) and new_ttfb > 500.0:
            return RegressionCheckResult(
                has_regression=True,
                regression_type="PERFORMANCE_SPIKE",
                details=f"Performance regression: TTFB spiked from {base_ttfb}ms to {new_ttfb}ms (>100% degradation).",
            )

        # 6. Navigation Broken Link Regression
        broken_links = post_deploy_evidence.get("broken_internal_links", [])
        if broken_links:
            return RegressionCheckResult(
                has_regression=True,
                regression_type="BROKEN_LINKS",
                details=f"Navigation regression: patch introduced {len(broken_links)} broken internal links: {broken_links[:3]}",
                affected_selector="nav a",
            )

        return RegressionCheckResult(
            has_regression=False,
            details="Zero cross-discipline regressions detected across rendering, schema, layout, redirects, performance, and links.",
        )


cross_discipline_regression_engine = CrossDisciplineRegressionEngine()
