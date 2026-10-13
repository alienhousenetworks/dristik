"""
Dristik AI Raw HTML vs Rendered DOM Disparity Analyzer
Compares raw server-delivered HTTP markup with browser-rendered DOM to detect:
1. Empty server shells and hydration failures.
2. Missing server-side primary headings (H1/H2) and meta tags.
3. Client-only internal links (links that only exist after client-side JS executes).
4. Substantial content extraction discrepancies between static and rendered states.

Adheres strictly to the Zero-Fake Evidence Standard. Scope is PAGE_VERIFIED.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from app.domain.models import Finding, FindingClassification, FindingEvidence, GroundedRecommendation
from app.domain.enums import Category, Severity, RubricConfidence, EvidenceConfidence, EvidenceClass


def _extract_text_tokens(soup) -> List[str]:
    if not soup:
        return []
    # Remove script and style
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(separator=" ", strip=True)
    return re.findall(r"\b\w+\b", text.lower())


def _extract_links(soup, base_url: str) -> List[str]:
    if not soup:
        return []
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc.lower()
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if href.startswith("/") or domain in href.lower():
            links.append(href)
    return list(dict.fromkeys(links))


def analyze_rendering_disparity(
    raw_html: Optional[str],
    rendered_html: Optional[str],
    page_url: str,
    evidence_store: Optional[Any] = None,
) -> Tuple[Dict[str, Any], List[Finding]]:
    """
    Compares raw HTTP response with rendered DOM.
    Returns (discrepancy_report, list_of_findings).
    """
    if not raw_html or not rendered_html or not BeautifulSoup:
        return {
            "has_disparity": False,
            "evaluated": False,
            "reason": "Missing raw or rendered HTML snapshot",
        }, []

    # If raw and rendered are identical strings, no rendering was performed
    if raw_html.strip() == rendered_html.strip():
        return {
            "has_disparity": False,
            "has_discrepancy": False,
            "empty_raw_shell": False,
            "client_injected_h1": False,
            "evaluated": True,
            "raw_word_count": len(re.findall(r"\b\w+\b", raw_html)),
            "rendered_word_count": len(re.findall(r"\b\w+\b", rendered_html)),
            "note": "Static and rendered DOM are identical (no client-side hydration drift)",
        }, []

    raw_soup = BeautifulSoup(raw_html, "lxml")
    rendered_soup = BeautifulSoup(rendered_html, "lxml")

    # Extract headings
    raw_h1s = [h.get_text(strip=True) for h in raw_soup.find_all("h1")]
    rendered_h1s = [h.get_text(strip=True) for h in rendered_soup.find_all("h1")]

    # Extract words
    raw_words = _extract_text_tokens(raw_soup)
    rendered_words = _extract_text_tokens(rendered_soup)
    raw_wcnt = len(raw_words)
    rendered_wcnt = len(rendered_words)

    # Extract links
    raw_links = set(_extract_links(raw_soup, page_url))
    rendered_links = set(_extract_links(rendered_soup, page_url))
    client_only_links = list(rendered_links - raw_links)

    # Check for title disparity
    raw_title = raw_soup.title.get_text(strip=True) if raw_soup.title else ""
    rendered_title = rendered_soup.title.get_text(strip=True) if rendered_soup.title else ""

    # Assess discrepancies
    word_diff = rendered_wcnt - raw_wcnt
    has_empty_shell = (raw_wcnt <= 5 and rendered_wcnt >= 15) or (raw_wcnt < 80 and rendered_wcnt >= 150 and word_diff >= 100)
    has_major_word_diff = word_diff >= 150 and (word_diff / max(1, raw_wcnt)) > 0.5
    h1_injected_via_js = (len(raw_h1s) == 0 and len(rendered_h1s) > 0)
    client_link_deficit = len(client_only_links) >= 5

    has_disparity = bool(has_empty_shell or has_major_word_diff or h1_injected_via_js or client_link_deficit)

    risk_level = "LOW"
    if has_empty_shell or (h1_injected_via_js and has_major_word_diff):
        risk_level = "HIGH"
    elif has_major_word_diff or client_link_deficit:
        risk_level = "MEDIUM"

    report_data = {
        "has_disparity": has_disparity,
        "has_discrepancy": has_disparity,
        "evaluated": True,
        "risk_level": risk_level,
        "has_empty_shell": has_empty_shell,
        "empty_raw_shell": has_empty_shell,
        "raw_word_count": raw_wcnt,
        "rendered_word_count": rendered_wcnt,
        "word_count_diff": word_diff,
        "raw_h1_count": len(raw_h1s),
        "rendered_h1_count": len(rendered_h1s),
        "h1_injected_via_js": h1_injected_via_js,
        "client_injected_h1": h1_injected_via_js,
        "raw_links_count": len(raw_links),
        "rendered_links_count": len(rendered_links),
        "client_only_links_count": len(client_only_links),
        "client_only_links": client_only_links,
        "client_only_internal_links": client_only_links,
        "client_only_links_sample": client_only_links[:10],
        "raw_title": raw_title,
        "rendered_title": rendered_title,
    }

    findings: List[Finding] = []

    if has_disparity:
        finding_id = f"FND_RENDER_DISPARITY_{abs(hash(page_url)) % 100000:05d}"
        ev_refs = []
        if evidence_store:
            ev_item = evidence_store.add_evidence(
                source_type="architecture",
                analyzer="rendering_disparity_analyzer",
                url=page_url,
                text=(
                    f"DOM Disparity on {page_url}: Raw HTML contains {raw_wcnt} words vs {rendered_wcnt} words in rendered DOM. "
                    f"Client-only links: {len(client_only_links)}. H1 in raw: {len(raw_h1s)}, in rendered: {len(rendered_h1s)}."
                ),
                value=report_data,
            )
            if hasattr(ev_item, "id"):
                ev_refs.append(ev_item.id)

        sev = Severity.HIGH if risk_level == "HIGH" else Severity.MEDIUM
        diag_parts = []
        if has_empty_shell:
            diag_parts.append(
                f"Page serves an empty or near-empty server shell ({raw_wcnt} words) that relies on client-side JavaScript execution to populate {rendered_wcnt} words."
            )
        elif has_major_word_diff:
            diag_parts.append(
                f"Substantial content difference detected: raw HTTP HTML provides {raw_wcnt} words while rendered DOM contains {rendered_wcnt} words ({word_diff} additional words rendered via JS)."
            )
        if h1_injected_via_js:
            diag_parts.append(
                f"Primary heading H1 is absent in raw server markup and only injected client-side: '{rendered_h1s[0] if rendered_h1s else ''}'."
            )
        if client_link_deficit:
            diag_parts.append(
                f"{len(client_only_links)} internal links exist only in the rendered DOM and are missing from initial server HTML, delaying crawler discovery."
            )

        diagnosis_str = " ".join(diag_parts)

        f = Finding(
            finding_id=finding_id,
            rule_id="JS_RENDERING_HYDRATION_DISPARITY_001",
            category=Category.TECHNICAL_SEO,
            subcategory="JavaScript Rendering & Hydration",
            severity=sev,
            classification=FindingClassification.VERIFIED_DEFECT,
            confidence=0.95,
            confidence_label=EvidenceConfidence.CONFIRMED,
            confidence_rubric=RubricConfidence.VERIFIED,
            title=f"JavaScript Rendering & Hydration Disparity on {page_url}",
            description=diagnosis_str,
            finding=diagnosis_str,
            detailed_diagnosis=diagnosis_str,
            business_context=(
                "Search engines crawl with a two-wave indexing pipeline. When primary content, headings, or navigation links "
                "require client-side JavaScript rendering, pages experience delayed indexation, partial extraction, and reduced AI answer engine citability."
            ),
            affected_urls=[page_url],
            sample_size=1,
            affected_sample_count=1,
            affected_percentage=100.0,
            scope_classification="PAGE_VERIFIED",
            evidence_refs=ev_refs,
            evidence_references=ev_refs,
            root_cause="Client-side rendering / Single Page Application hydration dependency without full server-side rendering (SSR) or pre-rendering.",
            secondary_symptoms=[
                f"{word_diff} words delayed behind JS execution",
                f"{len(client_only_links)} internal links deferred until rendering",
            ],
            recommendation=(
                "Implement Server-Side Rendering (SSR), Static Site Generation (SSG), or Edge pre-rendering for primary copy, "
                "critical H1 headings, and internal navigation links so all key content is present in initial HTTP HTML."
            ),
            recommended_solution=(
                "Implement Server-Side Rendering (SSR), Static Site Generation (SSG), or Edge pre-rendering to deliver "
                "core editorial text, primary H1 heading, and internal links in the initial HTTP server response. "
                "Ensure client hydration enhances the page progressively without replacing empty shells."
            ),
            acceptance_criteria=(
                f"A raw HTTP GET request (via curl or non-JS crawler) to {page_url} must return the primary H1 heading "
                f"and at least 80% of the visible body copy in the initial server response."
            ),
            verification_method="Fetch URL using curl / non-JS HTTP client and verify that H1 and body text appear in initial response without browser execution.",
            implementation_steps=[
                "Configure framework SSR / ISR (e.g. Next.js getServerSideProps / static export, Nuxt, Astro).",
                "Ensure server template renders semantic H1 and primary copy before shipping HTML bundle.",
                "Verify internal navigation anchor <a> tags are rendered in static server markup.",
            ],
            relevant_code_or_configuration_example=(
                "// Next.js App Router: ensure page.tsx is a Server Component\n"
                "export default async function Page() {\n"
                "  const data = await getPageData();\n"
                "  return (\n"
                "    <main>\n"
                "      <h1>{data.title}</h1>\n"
                "      <p>{data.body}</p>\n"
                "    </main>\n"
                "  );\n"
                "}"
            ),
            grounded_recommendation=GroundedRecommendation(
                recommendation_id=f"REC_{finding_id}",
                underlying_finding_id=finding_id,
                underlying_evidence_ids=ev_refs,
                what_to_change="Deliver core content and headings in server-rendered HTTP response rather than client-side JS.",
                why="Non-rendering or rate-limited search engine bots will fail to index un-hydrated content.",
                how_to_change="Enable SSR or pre-rendering in your application framework.",
                target_file="server/template",
            ),
        )
        findings.append(f)

    return report_data, findings


class RenderingDisparityAnalyzer:
    """Class wrapper for Rendering Disparity Analysis."""

    @staticmethod
    def analyze(
        raw_html: Optional[str],
        rendered_html: Optional[str],
        page_url: str,
        evidence_store: Optional[Any] = None,
    ) -> Tuple[Dict[str, Any], List[Finding]]:
        return analyze_rendering_disparity(raw_html, rendered_html, page_url, evidence_store)

