"""
Dristik AI Heading & Outline Hierarchy Analyzer
Evaluates H1-H6 tags per page and sitewide:
- Detects missing_h1, multiple_h1, short_h1 (<10 chars), long_h1 (>70 chars), duplicate_h1 collisions
- Evaluates H1 -> H2 -> H3 outline tree hierarchy to detect broken structures
"""
import hashlib
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.domain.models import PageEvidence, HeadingIssueItem, HeadingHierarchyRollup, Finding, FindingEvidence
from app.domain.enums import Category, Severity


class HeadingAnalyzer:
    @staticmethod
    def analyze(pages: List[PageEvidence]) -> HeadingHierarchyRollup:
        total = len(pages)
        if total == 0:
            return HeadingHierarchyRollup(
                total_pages_evaluated=0,
                total_heading_issues=0,
                h1_health_score=100.0
            )

        missing_h1: List[HeadingIssueItem] = []
        multiple_h1: List[HeadingIssueItem] = []
        short_h1: List[HeadingIssueItem] = []
        long_h1: List[HeadingIssueItem] = []
        duplicate_h1: List[HeadingIssueItem] = []
        hierarchy_violations: List[Dict[str, Any]] = []
        outline_samples: List[Dict[str, Any]] = []

        # Track sitewide H1 occurrences for duplicate detection
        h1_url_map: Dict[str, List[str]] = defaultdict(list)
        for p in pages:
            for h in (p.h1 or []):
                cleaned = h.strip()
                if cleaned:
                    h1_url_map[cleaned.lower()].append(p.url)

        for p in pages:
            raw_h1s = p.h1 or []
            h1s = [h.strip() for h in raw_h1s if h.strip()]
            h2s = [h.strip() for h in (p.h2 or []) if h.strip()]
            h3s = [h.strip() for h in (p.h3 or []) if h.strip()]

            # 1. Missing H1 or Empty H1
            if len(h1s) == 0:
                missing_h1.append(HeadingIssueItem(
                    url=p.url,
                    headings=[],
                    issue_type="missing_h1",
                    detail="Page is completely missing a semantic <h1> tag."
                ))
            elif any(not raw.strip() for raw in raw_h1s):
                missing_h1.append(HeadingIssueItem(
                    url=p.url,
                    headings=[],
                    issue_type="empty_h1",
                    detail="Page contains an empty or whitespace-only <h1> tag."
                ))

            # 2. Multiple H1s
            if len(h1s) > 1:
                multiple_h1.append(HeadingIssueItem(
                    url=p.url,
                    headings=h1s,
                    issue_type="multiple_h1",
                    detail=f"Page has {len(h1s)} distinct <h1> tags, diluting primary topical authority."
                ))

            # 3. Short & Long H1 checks
            for h in h1s:
                if len(h) < 10:
                    short_h1.append(HeadingIssueItem(
                        url=p.url,
                        headings=[h],
                        issue_type="short_h1",
                        detail=f"<h1> is too short ({len(h)} chars): '{h}'."
                    ))
                elif len(h) > 70:
                    long_h1.append(HeadingIssueItem(
                        url=p.url,
                        headings=[h],
                        issue_type="long_h1",
                        detail=f"<h1> exceeds recommended length ({len(h)} chars): '{h[:60]}...'."
                    ))

            # 4. Duplicate H1 collision
            for h in h1s:
                if len(h1_url_map[h.lower()]) > 1:
                    duplicate_h1.append(HeadingIssueItem(
                        url=p.url,
                        headings=[h],
                        issue_type="duplicate_h1",
                        detail=f"H1 '{h}' is reused across {len(h1_url_map[h.lower()])} distinct URLs."
                    ))

            # 5. Broken hierarchy check
            violations_on_page = []
            if len(h1s) == 0 and (len(h2s) > 0 or len(h3s) > 0):
                violations_on_page.append("Subheadings (H2/H3) exist without an H1 parent.")
            if len(h2s) == 0 and len(h3s) > 0:
                violations_on_page.append("H3 subheadings exist with no preceding H2 parent heading.")
            if getattr(p, "word_count", 0) > 500 and len(h2s) == 0:
                violations_on_page.append("Long-form content (> 500 words) lacks H2 section headings.")

            if violations_on_page:
                hierarchy_violations.append({
                    "url": p.url,
                    "violations": violations_on_page,
                    "h1_count": len(h1s),
                    "h2_count": len(h2s),
                    "h3_count": len(h3s)
                })

            # 6. Outline sample
            if len(outline_samples) < 5:
                outline_samples.append({
                    "url": p.url,
                    "h1": h1s[:2],
                    "h2_sample": h2s[:4],
                    "h3_sample": h3s[:4],
                })

        total_issues = (
            len(missing_h1)
            + len(multiple_h1)
            + len(short_h1)
            + len(long_h1)
            + len(duplicate_h1)
            + len(hierarchy_violations)
        )

        penalty = min(90.0, (total_issues / max(1, total)) * 25.0)
        health_score = round(max(10.0, 100.0 - penalty), 1)

        return HeadingHierarchyRollup(
            total_pages_evaluated=total,
            missing_h1=missing_h1,
            multiple_h1=multiple_h1,
            short_h1=short_h1,
            long_h1=long_h1,
            duplicate_h1=duplicate_h1,
            hierarchy_violations=hierarchy_violations,
            outline_tree_sample=outline_samples,
            total_heading_issues=total_issues,
            h1_health_score=health_score
        )

    @staticmethod
    def generate_findings(rollup: HeadingHierarchyRollup) -> List[Finding]:
        findings: List[Finding] = []

        if rollup.missing_h1:
            ev_list = []
            for item in rollup.missing_h1[:8]:
                ev_id = f"EV-HDG-MISS-{hashlib.sha256(item.url.encode()).hexdigest()[:8]}"
                ev_list.append(FindingEvidence(
                    evidence_id=ev_id,
                    url=item.url,
                    element="h1",
                    value=item.detail or "Missing <h1> tag",
                    observed_value="Zero <h1> elements found on page",
                    expected_condition="Page must define exactly one primary <h1> heading summarizing its topic",
                    snippet=f"No <h1> found in HTML body of {item.url}",
                    test_method="crawl_html_headings",
                    source="crawl",
                ))

            aff_urls = [item.url for item in rollup.missing_h1]
            routes_preview = ", ".join(aff_urls[:3]) + ("..." if len(aff_urls) > 3 else "")
            findings.append(Finding(
                finding_id="finding_heading_missing_h1",
                category=Category.ON_PAGE_SEO,
                severity=Severity.HIGH,
                title=f"{len(rollup.missing_h1)} Page(s) Missing Semantic <h1> Heading",
                description=(
                    f"Identified {len(rollup.missing_h1)} crawled page(s) lacking an <h1> heading tag. "
                    "H1 tags are primary semantic anchors used by search engines and answer engines to interpret page intent."
                ),
                recommendation=f"Insert a single, concise <h1> heading above the primary hero section on each affected page ({routes_preview}).",
                why_it_matters="Search engines give heavy weight to H1 content when determining topical relevance for keyword rankings.",
                validation_criteria="Every indexable page must contain exactly one non-empty <h1> element.",
                evidence=ev_list,
                evidence_refs=[ev.evidence_id for ev in ev_list if ev.evidence_id] or ["heading_audit"],
                evidence_ids=[ev.evidence_id for ev in ev_list if ev.evidence_id],
                affected_urls=aff_urls,
                affected_sample_count=len(aff_urls),
                scope_classification="PAGE_VERIFIED" if len(aff_urls) <= 3 else "SAMPLE_VERIFIED",
                impact=7,
                effort=2,
                priority=7
            ))

        if rollup.multiple_h1:
            ev_list = []
            for item in rollup.multiple_h1[:8]:
                ev_id = f"EV-HDG-MULT-{hashlib.sha256(item.url.encode()).hexdigest()[:8]}"
                ev_list.append(FindingEvidence(
                    evidence_id=ev_id,
                    url=item.url,
                    element="h1",
                    value=item.detail or "Multiple <h1> tags",
                    observed_value=item.detail,
                    expected_condition="Page should define only one top-level <h1> heading",
                    snippet=f"Multiple <h1> instances found: {item.detail}",
                    test_method="crawl_html_headings",
                    source="crawl",
                ))

            aff_urls = [item.url for item in rollup.multiple_h1]
            routes_preview = ", ".join(aff_urls[:3]) + ("..." if len(aff_urls) > 3 else "")
            findings.append(Finding(
                finding_id="finding_heading_multiple_h1",
                category=Category.ON_PAGE_SEO,
                severity=Severity.MEDIUM,
                title=f"{len(rollup.multiple_h1)} Page(s) Contain Multiple <h1> Headings",
                description=(
                    f"Discovered {len(rollup.multiple_h1)} page(s) containing two or more <h1> tags. "
                    "Multiple top-level headings fracture document outline authority."
                ),
                recommendation=f"Preserve one primary <h1> representing page topic, and demote secondary section headings to <h2> on affected routes ({routes_preview}).",
                why_it_matters="Google recommends a single clear H1 per document to maintain an unambiguous semantic outline.",
                validation_criteria="Every indexable page must contain exactly one <h1> heading.",
                owner="Content Editor",
                responsible_role="Content Editor",
                estimated_effort="Low (< 2 hours)",
                dependencies=["CMS template or page editor access"],
                priority_rationale="Medium Priority: Dilutes semantic document outline and clarity of primary topical focus.",
                verification_command=f"curl -s '{aff_urls[0]}' | grep -i '<h1'",
                evidence=ev_list,
                evidence_refs=[ev.evidence_id for ev in ev_list if ev.evidence_id] or ["heading_audit"],
                evidence_ids=[ev.evidence_id for ev in ev_list if ev.evidence_id],
                affected_urls=aff_urls,
                affected_sample_count=len(aff_urls),
                scope_classification="PAGE_VERIFIED" if len(aff_urls) <= 3 else "SAMPLE_VERIFIED",
                impact=5,
                effort=2,
                priority=5
            ))

        if rollup.hierarchy_violations:
            ev_list = []
            for v in rollup.hierarchy_violations[:8]:
                v_str = ", ".join(v.get("violations", []))
                url_str = v.get("url", "")
                ev_id = f"EV-HDG-SKIP-{hashlib.sha256(f'{url_str}:{v_str}'.encode()).hexdigest()[:8]}"
                ev_list.append(FindingEvidence(
                    evidence_id=ev_id,
                    url=v.get("url", ""),
                    element="h2/h3",
                    value=v_str,
                    observed_value=v_str,
                    expected_condition="Heading structure must not skip parent levels (e.g. H1 -> H2 -> H3)",
                    snippet=f"Heading hierarchy violation on {v.get('url')}: {v_str}",
                    test_method="crawl_html_headings",
                    source="crawl",
                ))

            aff_urls = [v.get("url") for v in rollup.hierarchy_violations if v.get("url")]
            routes_preview = ", ".join(aff_urls[:3]) + ("..." if len(aff_urls) > 3 else "")
            findings.append(Finding(
                finding_id="finding_heading_hierarchy_skips",
                category=Category.ON_PAGE_SEO,
                severity=Severity.MEDIUM,
                title=f"{len(rollup.hierarchy_violations)} Page(s) Have Broken Heading Hierarchy",
                description=(
                    f"{len(rollup.hierarchy_violations)} page(s) exhibit heading hierarchy skips (e.g. H3 tags without an H2 parent, "
                    "or long-form articles without subheadings)."
                ),
                recommendation=f"Structure headings sequentially: H1 -> H2 -> H3 without skipping levels on affected routes ({routes_preview}).",
                why_it_matters="Logical document hierarchy aids screen readers (WCAG 2.2) and assists search engine passage indexing.",
                validation_criteria="All heading tags must follow logical parent-child levels without level skipping.",
                owner="Content Editor",
                responsible_role="Content Editor",
                estimated_effort="Low (< 2 hours)",
                dependencies=["Page content formatting privileges"],
                priority_rationale="Medium Priority: Improves screen reader accessibility and search engine passage extraction.",
                verification_command=f"curl -s '{aff_urls[0]}' | grep -E '<h[1-6]'",
                evidence=ev_list,
                evidence_refs=[ev.evidence_id for ev in ev_list if ev.evidence_id] or ["heading_audit"],
                evidence_ids=[ev.evidence_id for ev in ev_list if ev.evidence_id],
                affected_urls=aff_urls,
                affected_sample_count=len(aff_urls),
                scope_classification="PAGE_VERIFIED" if len(aff_urls) <= 3 else "SAMPLE_VERIFIED",
                impact=4,
                effort=2,
                priority=4
            ))

        return findings


def analyze_heading_hierarchy(pages: List[PageEvidence]) -> HeadingHierarchyRollup:
    return HeadingAnalyzer.analyze(pages)

