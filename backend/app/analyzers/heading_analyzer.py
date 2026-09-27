"""
Dristik AI Heading & Outline Hierarchy Analyzer
Evaluates H1-H6 tags per page and sitewide:
- Detects missing_h1, multiple_h1, short_h1 (<10 chars), long_h1 (>70 chars), duplicate_h1 collisions
- Evaluates H1 -> H2 -> H3 outline tree hierarchy to detect broken structures
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.domain.models import PageEvidence, HeadingIssueItem, HeadingHierarchyRollup


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
            h1s = [h.strip() for h in (p.h1 or []) if h.strip()]
            h2s = [h.strip() for h in (p.h2 or []) if h.strip()]
            h3s = [h.strip() for h in (p.h3 or []) if h.strip()]

            # 1. Missing H1
            if len(h1s) == 0:
                missing_h1.append(HeadingIssueItem(
                    url=p.url,
                    headings=[],
                    issue_type="missing_h1",
                    detail="Page is completely missing an <h1> tag."
                ))
            # 2. Multiple H1s
            elif len(h1s) > 1:
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

            # 5. Broken hierarchy check (H3 present without H2, or H2/H3 present without H1)
            violations_on_page = []
            if len(h1s) == 0 and (len(h2s) > 0 or len(h3s) > 0):
                violations_on_page.append("Subheadings (H2/H3) exist without an H1 parent.")
            if len(h2s) == 0 and len(h3s) > 0:
                violations_on_page.append("H3 subheadings exist with no preceding H2 parent heading.")

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


def analyze_heading_hierarchy(pages: List[PageEvidence]) -> HeadingHierarchyRollup:
    return HeadingAnalyzer.analyze(pages)
