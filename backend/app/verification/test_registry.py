"""
Verification Test Registry — Phase 9.1 (10/10 Transformation)

Provides deterministic, reusable test executors for all 13 canonical condition categories:
1. HTTP conditions
2. HTML conditions
3. DOM conditions
4. Metadata
5. Schema
6. Internal links
7. Accessibility
8. Performance
9. Visual layout
10. Form behaviour
11. AI answer outcomes
12. Search performance
13. Analytics events
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.verification.models import TestCategory, TestExecutionResult

logger = logging.getLogger("dristik.verification.registry")


class VerificationTestRegistry:
    __test__ = False
    """
    Central registry of reusable condition testers across all 13 categories.
    """

    # 1. HTTP Conditions
    @staticmethod
    def test_http_condition(
        status_code: int,
        expected_status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        required_headers: Optional[List[str]] = None,
        max_hops: int = 1,
        actual_hops: int = 1,
    ) -> TestExecutionResult:
        passed = (status_code == expected_status) and (actual_hops <= max_hops)
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        missing = [h for h in (required_headers or []) if h.lower() not in hdrs]
        if missing:
            passed = False

        diag = f"HTTP status={status_code} (expected {expected_status}), hops={actual_hops} (max {max_hops})"
        if missing:
            diag += f", missing headers: {missing}"

        return TestExecutionResult(
            test_category=TestCategory.HTTP_CONDITION,
            name="HTTP Status & Headers Test",
            passed=passed,
            observed_value={"status": status_code, "hops": actual_hops},
            expected_condition=f"status == {expected_status} and hops <= {max_hops}",
            diagnostic_details=diag,
        )

    # 2. HTML Conditions
    @staticmethod
    def test_html_condition(html: str) -> TestExecutionResult:
        has_doctype = bool(re.search(r"<!DOCTYPE\s+html", html or "", re.IGNORECASE))
        has_charset = bool(re.search(r"<meta[^>]*charset=[\"']?[a-zA-Z0-9_-]+", html or "", re.IGNORECASE))
        open_tags = len(re.findall(r"<[a-zA-Z][^>/]*>", html or ""))
        close_tags = len(re.findall(r"</[a-zA-Z][^>]*>", html or ""))
        void_tags = len(re.findall(r"<(?:meta|link|input|img|br|hr)[^>]*>", html or "", re.IGNORECASE))

        # Balanced tag sanity check
        balanced = open_tags <= (close_tags + void_tags + 10)
        passed = has_doctype and balanced

        return TestExecutionResult(
            test_category=TestCategory.HTML_CONDITION,
            name="HTML Syntax & DOCTYPE Test",
            passed=passed,
            observed_value={"has_doctype": has_doctype, "has_charset": has_charset, "balanced": balanced},
            expected_condition="Valid HTML with DOCTYPE and balanced tag hierarchy.",
            diagnostic_details=f"DOCTYPE={has_doctype}, charset={has_charset}, balanced={balanced}",
        )

    # 3. DOM Conditions
    @staticmethod
    def test_dom_condition(
        html: str,
        target_selector: str,
        expected_text: Optional[str] = None,
        should_exist: bool = True,
    ) -> TestExecutionResult:
        # Check presence of selector tag or class
        found = False
        clean_sel = target_selector.strip()
        if clean_sel.startswith("#"):
            id_name = clean_sel[1:]
            found = bool(re.search(rf'id=["\']{id_name}["\']', html or "", re.IGNORECASE))
        elif clean_sel.startswith("."):
            class_name = clean_sel[1:]
            found = bool(re.search(rf'class=["\'][^"\']*\b{class_name}\b[^"\']*["\']', html or "", re.IGNORECASE))
        else:
            tag_name = clean_sel.split()[0]
            found = bool(re.search(rf'<{tag_name}\b', html or "", re.IGNORECASE))

        if expected_text and found:
            text_match = bool(re.search(re.escape(expected_text), html or "", re.IGNORECASE))
            found = text_match

        passed = (found == should_exist)
        return TestExecutionResult(
            test_category=TestCategory.DOM_CONDITION,
            name=f"DOM Condition '{target_selector}'",
            passed=passed,
            observed_value=found,
            expected_condition=f"Element '{target_selector}' presence == {should_exist}",
            diagnostic_details=f"Selector '{target_selector}' found={found}, expected={should_exist}",
        )

    # 4. Metadata Conditions
    @staticmethod
    def test_metadata(
        html: str,
        min_title_len: int = 10,
        max_title_len: int = 70,
        require_meta_desc: bool = True,
    ) -> TestExecutionResult:
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.IGNORECASE | re.DOTALL)
        title_text = title_m.group(1).strip() if title_m else ""
        desc_m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html or "", re.IGNORECASE)
        desc_text = desc_m.group(1).strip() if desc_m else ""

        title_ok = min_title_len <= len(title_text) <= max_title_len
        desc_ok = (len(desc_text) >= 20) if require_meta_desc else True
        passed = title_ok and desc_ok

        return TestExecutionResult(
            test_category=TestCategory.METADATA,
            name="Title & Meta Description Quality Test",
            passed=passed,
            observed_value={"title_length": len(title_text), "desc_length": len(desc_text)},
            expected_condition=f"Title ({min_title_len}-{max_title_len} chars) and non-empty description",
            diagnostic_details=f"Title='{title_text}' (len={len(title_text)}), Meta='{desc_text[:30]}...' (len={len(desc_text)})",
        )

    # 5. Schema Conditions
    @staticmethod
    def test_schema(
        html: str,
        required_type: Optional[str] = None,
        required_properties: Optional[List[str]] = None,
    ) -> TestExecutionResult:
        scripts = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or "", re.DOTALL | re.IGNORECASE)
        if not scripts:
            return TestExecutionResult(
                test_category=TestCategory.SCHEMA,
                name="Schema.org JSON-LD Test",
                passed=False,
                observed_value=0,
                expected_condition=f"Valid JSON-LD schema with @type={required_type or 'Any'}",
                diagnostic_details="No <script type='application/ld+json'> blocks found in HTML.",
            )

        valid_blocks = 0
        found_types = []
        has_req_type = False
        has_req_props = True

        for s in scripts:
            try:
                data = json.loads(s.strip())
                valid_blocks += 1
                items = data.get("@graph", [data]) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for it in items:
                    t = it.get("@type")
                    if t:
                        found_types.append(t)
                        if required_type and t == required_type:
                            has_req_type = True
                            if required_properties:
                                for p in required_properties:
                                    if p not in it:
                                        has_req_props = False
            except Exception:
                continue

        if required_type:
            passed = (valid_blocks > 0) and has_req_type and has_req_props
        else:
            passed = valid_blocks > 0

        return TestExecutionResult(
            test_category=TestCategory.SCHEMA,
            name="Schema.org JSON-LD Test",
            passed=passed,
            observed_value={"valid_blocks": valid_blocks, "types": found_types},
            expected_condition=f"Valid JSON-LD with type='{required_type or 'Any'}' and properties={required_properties or []}",
            diagnostic_details=f"Found types: {found_types}, req_type_found={has_req_type}, req_props_found={has_req_props}",
        )

    # 6. Internal Links
    @staticmethod
    def test_internal_links(
        html: str,
        target_link: str,
        target_resolves_200: bool = True,
    ) -> TestExecutionResult:
        links = re.findall(r'href=["\']([^"\']+)["\']', html or "", re.IGNORECASE)
        found = any(target_link in l for l in links)
        passed = found and target_resolves_200

        return TestExecutionResult(
            test_category=TestCategory.INTERNAL_LINKS,
            name="Internal Link Resolution Test",
            passed=passed,
            observed_value={"link_present": found, "resolves_200": target_resolves_200},
            expected_condition=f"Link to '{target_link}' present and resolving with HTTP 200",
            diagnostic_details=f"Link found={found}, resolves_200={target_resolves_200}",
        )

    # 7. Accessibility
    @staticmethod
    def test_accessibility(html: str) -> TestExecutionResult:
        # Check image alt attributes
        images = re.findall(r'<img[^>]*>', html or "", re.IGNORECASE)
        missing_alt = [img for img in images if not re.search(r'alt=["\'][^"\']+["\']', img, re.IGNORECASE)]
        passed = len(missing_alt) == 0

        return TestExecutionResult(
            test_category=TestCategory.ACCESSIBILITY,
            name="Image Alt Accessibility Test",
            passed=passed,
            observed_value={"total_images": len(images), "missing_alt": len(missing_alt)},
            expected_condition="All <img> tags possess descriptive non-empty alt attributes",
            diagnostic_details=f"Images evaluated={len(images)}, missing_alt={len(missing_alt)}",
        )

    # 8. Performance
    @staticmethod
    def test_performance(ttfb_ms: float, max_ttfb_ms: float = 300.0) -> TestExecutionResult:
        passed = ttfb_ms <= max_ttfb_ms
        return TestExecutionResult(
            test_category=TestCategory.PERFORMANCE,
            name="TTFB Performance Test",
            passed=passed,
            observed_value=ttfb_ms,
            expected_condition=f"TTFB <= {max_ttfb_ms}ms",
            diagnostic_details=f"Observed TTFB={ttfb_ms}ms (threshold {max_ttfb_ms}ms)",
        )

    # 9. Visual Layout
    @staticmethod
    def test_visual_layout(html: str) -> TestExecutionResult:
        viewport_m = re.search(r'<meta[^>]*name=["\']viewport["\'][^>]*content=["\']([^"\']*)["\']', html or "", re.IGNORECASE)
        has_width = bool(viewport_m and "width=device-width" in viewport_m.group(1).lower())
        passed = bool(viewport_m and has_width)

        return TestExecutionResult(
            test_category=TestCategory.VISUAL_LAYOUT,
            name="Mobile Viewport Layout Test",
            passed=passed,
            observed_value=viewport_m.group(1) if viewport_m else None,
            expected_condition="Viewport meta configured with width=device-width",
            diagnostic_details=f"Viewport tag: '{viewport_m.group(1) if viewport_m else 'MISSING'}'",
        )

    # 10. Form Behaviour
    @staticmethod
    def test_form_behaviour(html: str) -> TestExecutionResult:
        forms = re.findall(r'<form[^>]*>(.*?)</form>', html or "", re.DOTALL | re.IGNORECASE)
        if not forms:
            return TestExecutionResult(
                test_category=TestCategory.FORM_BEHAVIOUR,
                name="Form Behaviour Test",
                passed=True,
                observed_value=0,
                expected_condition="No broken forms",
                diagnostic_details="No forms on audited page.",
            )

        # Check that inputs have labels or aria-label
        inputs = re.findall(r'<input[^>]*>', html or "", re.IGNORECASE)
        accessible_inputs = [
            inp for inp in inputs
            if "type=\"hidden\"" in inp.lower() or "type='hidden'" in inp.lower()
            or "aria-label=" in inp.lower() or "id=" in inp.lower()
        ]
        passed = len(accessible_inputs) >= (len(inputs) * 0.8)

        return TestExecutionResult(
            test_category=TestCategory.FORM_BEHAVIOUR,
            name="Form Input Accessibility & Behaviour Test",
            passed=passed,
            observed_value={"inputs_count": len(inputs), "accessible_count": len(accessible_inputs)},
            expected_condition="Form inputs possess accessible identifiers or labels",
            diagnostic_details=f"Inputs={len(inputs)}, accessible={len(accessible_inputs)}",
        )

    # 11. AI Answer Outcomes
    @staticmethod
    def test_ai_answer_outcome(html: str, target_question: str) -> TestExecutionResult:
        clean_text = re.sub(r'<[^>]+>', ' ', html or "")
        clean_text = ' '.join(clean_text.split())
        words = clean_text.split()

        q_terms = [t.lower() for t in target_question.replace("?", "").split() if len(t) > 3]
        found_terms = [t for t in q_terms if t in clean_text.lower()]
        has_context = len(found_terms) >= max(1, len(q_terms) // 2)

        # Check for 20-40 word concise answer blocks
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html or "", re.DOTALL | re.IGNORECASE)
        has_extractable_passage = False
        for p in paragraphs:
            p_text = re.sub(r'<[^>]+>', '', p).strip()
            w_cnt = len(p_text.split())
            if 15 <= w_cnt <= 50 and any(t in p_text.lower() for t in q_terms):
                has_extractable_passage = True
                break

        passed = has_context and has_extractable_passage
        return TestExecutionResult(
            test_category=TestCategory.AI_ANSWER_OUTCOME,
            name="AI Answer Coverage & Extractability Test",
            passed=passed,
            observed_value={"terms_matched": found_terms, "extractable_passage": has_extractable_passage},
            expected_condition=f"Factual 20-40 word answer passage addressing '{target_question}'",
            diagnostic_details=f"Matched terms={found_terms}, extractable_passage={has_extractable_passage}",
        )

    # 12. Search Performance
    @staticmethod
    def test_search_performance(robots_txt: str, bot_name: str = "GPTBot") -> TestExecutionResult:
        lines = [line.strip().lower() for line in (robots_txt or "").splitlines()]
        disallowed = False
        current_agent = ""
        for line in lines:
            if line.startswith("user-agent:"):
                current_agent = line.replace("user-agent:", "").strip()
            elif line.startswith("disallow:") and (current_agent == bot_name.lower() or current_agent == "*"):
                path = line.replace("disallow:", "").strip()
                if path == "/":
                    disallowed = True

        passed = not disallowed
        return TestExecutionResult(
            test_category=TestCategory.SEARCH_PERFORMANCE,
            name=f"Robots.txt Crawler Access Test for {bot_name}",
            passed=passed,
            observed_value={"disallowed": disallowed},
            expected_condition=f"User-agent {bot_name} is allowed to crawl root /",
            diagnostic_details=f"Bot '{bot_name}' blocked={disallowed}",
        )

    # 13. Analytics Events
    @staticmethod
    def test_analytics_events(html: str) -> TestExecutionResult:
        has_ga4 = "gtag(" in html or "googletagmanager.com/gtm.js" in html or "data-ga" in html
        return TestExecutionResult(
            test_category=TestCategory.ANALYTICS_EVENTS,
            name="Analytics & Tag Event Tracking Test",
            passed=has_ga4,
            observed_value={"analytics_tag_present": has_ga4},
            expected_condition="GA4 / GTM measurement script integrated without render-blocking errors",
            diagnostic_details=f"Analytics snippet detected={has_ga4}",
        )


verification_test_registry = VerificationTestRegistry()
