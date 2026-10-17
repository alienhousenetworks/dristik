"""
Dristik AI Pre-Seal Report Critic & Scope Consistency Reconciler.
Inspects findings, crawl ground truth, and multi-plane scoring metrics before report sealing:
1. Reconciles finding scopes: prevents single-page defects from reading as global sitewide deficits.
2. Enforces ground-truth alignment with CrawlManifest and HeadingHierarchyRollup.
3. Synthesizes explanatory bridges when distinct perspectives (e.g. Crawl Integrity vs Category SEO) diverge.
4. Returns reconciled findings and auditable critic actions.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.models import ExecutiveReport, Finding
from app.domain.enums import Severity

logger = logging.getLogger(__name__)


class ReportCritic:
    """
    Adversarial Critic that enforces internal report consistency, scope precision,
    and ground-truth harmonization before sealing.
    """

    @classmethod
    def reconcile_report(
        cls,
        report: ExecutiveReport,
        manifest: Optional[Any] = None,
        heading_hierarchy: Optional[Any] = None,
    ) -> Tuple[ExecutiveReport, List[str]]:
        actions: List[str] = []

        # -------------------------------------------------------------
        # 1. Heading Scope & Ground-Truth Reconciliation
        # -------------------------------------------------------------
        missing_h1_total = 0
        multiple_h1_total = 0
        if heading_hierarchy and hasattr(heading_hierarchy, "missing_h1"):
            missing_h1_total = len(heading_hierarchy.missing_h1 or [])
            multiple_h1_total = len(getattr(heading_hierarchy, "multiple_h1", []) or [])
        elif report.heading_hierarchy and hasattr(report.heading_hierarchy, "missing_h1"):
            missing_h1_total = len(report.heading_hierarchy.missing_h1 or [])
            multiple_h1_total = len(getattr(report.heading_hierarchy, "multiple_h1", []) or [])
        elif manifest and hasattr(manifest, "crawl_health") and isinstance(manifest.crawl_health, dict):
            missing_h1_total = int(manifest.crawl_health.get("missing_h1_count", 0))
            multiple_h1_total = int(manifest.crawl_health.get("multiple_h1_count", 0))
        elif report.crawl_summary and isinstance(report.crawl_summary, dict):
            missing_h1_total = int(report.crawl_summary.get("missing_h1_count", 0))
            multiple_h1_total = int(report.crawl_summary.get("multiple_h1_count", 0))

        reconciled_findings: List[Finding] = []

        for f in report.findings:
            desc = f.description or ""
            title = f.title or ""
            full_text = f"{title} {desc}".lower()

            # Check for H1 contradiction: Crawl verifies 0 pages missing H1, but finding claims document lacks H1
            if missing_h1_total == 0 and any(
                k in full_text for k in [
                    "lacks a top-level <h1>",
                    "lacks a top-level h1",
                    "lacks a top level h1",
                    "lacks an <h1>",
                    "lacks an h1",
                    "missing an <h1>",
                    "missing an h1 tag",
                    "no <h1> tag",
                    "no h1 tag",
                    "no <h1> heading",
                    "no h1 heading",
                    "document lacks a top-level",
                    "page lacks a top-level",
                    "lacks a top-level",
                ]
            ):
                # If finding also mentions multiple H1s, it's a multiple H1 issue where one clause said lacks H1
                if "multiple" in full_text:
                    clean_desc = re.sub(
                        r"(?:Document|Page\s*\([^)]*\))\s*lacks\s*a\s*top-level\s*<h1\b[^>]*>\s*(?:heading)?\.?;?\s*",
                        "",
                        desc,
                        flags=re.I
                    ).strip()
                    clean_desc = re.sub(
                        r"page\s*is\s*completely\s*missing\s*an\s*<h1>\s*tag\.?;?\s*",
                        "",
                        clean_desc,
                        flags=re.I
                    ).strip()
                    if not clean_desc:
                        clean_desc = "Page contains multiple competing <h1> tags diluting primary topical authority."
                    clean_title = f.title
                    if any(k in clean_title.lower() for k in ["lacks", "missing"]):
                        clean_title = "Multiple <h1> tags compete for primary topical authority"
                    f_updated = f.model_copy(update={"title": clean_title, "description": clean_desc})
                    reconciled_findings.append(f_updated)
                    actions.append(
                        f"Critic reconciled finding {f.finding_id}: updated to multiple H1s because crawl proved 0 pages missing H1."
                    )
                    continue

                # If finding has a specific subpage URL in evidence or description, qualify the scope explicitly
                subpage_match = re.search(r"https?://[^\s,;:)]+", desc)
                if subpage_match and subpage_match.group(0):
                    target_url = subpage_match.group(0)
                    qualified_desc = re.sub(
                        r"Document\s+lacks\s+a\s+top-level\s*<h1\b[^>]*>\s*(?:heading)?",
                        f"Subpage ({target_url}) lacks a top-level <h1> heading (homepage verified present)",
                        desc,
                        flags=re.I
                    )
                    clean_title = f.title.replace("Document lacks", "Subpage lacks")
                    if "lacks" in clean_title and "subpage" not in clean_title.lower():
                        clean_title = f"Subpage lacks top-level <h1> heading: {target_url}"
                    f_updated = f.model_copy(update={
                        "title": clean_title,
                        "description": qualified_desc
                    })
                    reconciled_findings.append(f_updated)
                    actions.append(
                        f"Critic qualified finding {f.finding_id} scope to specific subpage URL: {target_url}."
                    )
                    continue

                # If multiple H1s are present on the site, convert the defect to multiple H1s
                if multiple_h1_total > 0:
                    f_updated = f.model_copy(update={
                        "title": "Multiple competing <h1> tags detected",
                        "description": "Evaluated pages contain multiple competing <h1> tags diluting primary topical authority. Crawl verified 0 pages missing an <h1>.",
                        "recommendation": "Consolidate heading hierarchy to a single top-level <h1> per page."
                    })
                    reconciled_findings.append(f_updated)
                    actions.append(
                        f"Critic converted finding {f.finding_id} from 'lacks H1' to 'multiple H1s' matching crawl ground truth."
                    )
                    continue

                # Otherwise, suppress finding because deterministic crawl verified 0 missing H1 pages
                f_suppressed = f.model_copy(update={
                    "held_from_executive": True,
                    "verification_notes": (
                        (f.verification_notes or "") +
                        " [CRITIC SUPPRESSED: HeadingAnalyzer and Crawl Ground Truth verified 0 pages missing an H1.]"
                    )
                })
                reconciled_findings.append(f_suppressed)
                actions.append(
                    f"Critic suppressed finding {f.finding_id} ('{f.title}') due to conflict with verified 0 missing H1 crawl ground truth."
                )
                continue

            # Check sitemap contradiction
            sitemap_found = bool(manifest and getattr(manifest, "sitemap_found", False))
            if sitemap_found and any(k in full_text for k in ["no sitemap found", "sitemap.xml is missing", "sitemap missing"]):
                f_suppressed = f.model_copy(update={
                    "held_from_executive": True,
                    "verification_notes": (
                        (f.verification_notes or "") +
                        " [CRITIC SUPPRESSED: CrawlManifest verified sitemap was successfully discovered.]"
                    )
                })
                reconciled_findings.append(f_suppressed)
                actions.append(
                    f"Critic suppressed finding {f.finding_id} ('{f.title}') because sitemap was discovered at {getattr(manifest, 'sitemap_url', 'target')}"
                )
                continue

            # Check robots.txt contradiction
            robots_found = bool(manifest and getattr(manifest, "robots_txt_found", False))
            if robots_found and any(k in full_text for k in ["robots.txt missing", "robots.txt not found", "no robots.txt"]):
                f_suppressed = f.model_copy(update={
                    "held_from_executive": True,
                    "verification_notes": (
                        (f.verification_notes or "") +
                        " [CRITIC SUPPRESSED: CrawlManifest verified robots.txt is present.]"
                    )
                })
                reconciled_findings.append(f_suppressed)
                actions.append(
                    f"Critic suppressed finding {f.finding_id} ('{f.title}') because robots.txt is present."
                )
                continue

            reconciled_findings.append(f)

        # Retain only unheld findings for the executive report
        report.findings = [f for f in reconciled_findings if not getattr(f, "held_from_executive", False)]

        # -------------------------------------------------------------
        # 2. Score Perspective & Harmony Alignment
        # -------------------------------------------------------------
        # Synthesize explanatory bridges between Honest Scores and Category/Pillar scores
        if report.scores:
            scores = report.scores
            cat_scores = scores.category_scores or {}
            honest = getattr(report, "honest_scores", None)

            bridges = []
            # Traditional Search Crawl vs Category SEO
            if honest and honest.google_score is not None:
                seo_cat = cat_scores.get("TECHNICAL_SEO") or cat_scores.get("technical_seo")
                seo_cat_val = getattr(seo_cat, "score", None) if seo_cat else None
                if seo_cat_val is not None and abs(honest.google_score - seo_cat_val) >= 15:
                    bridges.append(
                        f"Search Intelligence Perspective: Traditional Search Crawl baseline ({honest.google_score:.0f}/100) "
                        f"reflects compound unweighted crawl friction across technical headers, content formatting, and entity schema, "
                        f"whereas Technical SEO Pillar ({seo_cat_val:.0f}/100) measures isolated on-page indexing compliance."
                    )

            # Live AI Citations vs On-page GEO Readiness
            if honest and honest.ai_visibility_score is not None and honest.ai_readiness_score is not None:
                if honest.ai_visibility_score == 0 and honest.ai_readiness_score > 40:
                    bridges.append(
                        f"AI Answer Engine Perspective: On-page GEO Readiness is {honest.ai_readiness_score:.0f}/100 "
                        f"(extractable facts present in DOM), but Live AI Citation Visibility is currently "
                        f"{honest.ai_visibility_score:.0f}/100 across live engines. "
                        "The site provides extractable data, but generative models have not yet grounded citations on the brand."
                    )

            # Overall Score vs Component Distribution Bridge
            if scores.overall_score is not None:
                bridges.append(
                    f"Scoring Synthesis: Overall Composite Score ({scores.overall_score:.0f}/100) reflects the multi-pillar weighted average of evaluated on-page systems. "
                    "Unmeasured or external outcome planes (such as live AI citations or third-party authority) do not penalize on-page architectural readiness."
                )

            current_exp = getattr(report, "scoring_explanation", None) or ""
            if bridges:
                new_explanation = " · ".join(bridges)
                if not current_exp:
                    report.scoring_explanation = new_explanation
                elif not any(b[:30] in current_exp for b in bridges):
                    report.scoring_explanation = f"{current_exp} · {new_explanation}"
                actions.append("Critic synthesized score harmony explanatory bridges.")

        return report, actions

        return report, actions


critic = ReportCritic()
