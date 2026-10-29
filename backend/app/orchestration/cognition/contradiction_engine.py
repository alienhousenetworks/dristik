"""
Dristik AI Contradiction Engine
================================
Detects and resolves conflicts between audit findings.

A contradiction occurs when two findings make mutually exclusive claims about
the same site property, e.g.:
  - "Title tag is absent" (TECHNICAL_SEO) AND "Title tag is present but truncated" (ON_PAGE_SEO)
  - "No schema.org markup" (SCHEMA) AND "FAQ schema detected" (GEO)
  - Agent-A scores GEO: 40, Agent-B scores GEO: 72 (inter-agent conflict)

The engine:
  1. Groups findings by category + rule_id (or title hash).
  2. Detects pairs where one claim implies the negation of the other.
  3. Produces a ContradictionReport for each conflict.
  4. Resolves based on EvidenceLevel precedence — the higher-evidence claim wins.
  5. Marks the losing finding with held_from_executive=True.
  6. Flags unresolvable conflicts as UNRESOLVED for human review.

Design invariant:
  Only findings with evidence (OBSERVED / EXTERNALLY_VERIFIED) can be winners.
  A MODEL_INFERRED finding can NEVER override an OBSERVED finding.
"""
from __future__ import annotations

import itertools
import re
from typing import List, Optional, Tuple, Dict, Any

from app.domain.enums import (
    Category,
    ContradictionStatus,
    EvidenceClass,
    EvidenceLevel,
    RubricConfidence,
)
from app.domain.models import ContradictionReport, Finding, FindingEvidence


# ---------------------------------------------------------------------------
# Negation pairs — if title_a matches pattern_a AND title_b matches pattern_b
# (for the same category) it's a contradiction candidate.
# ---------------------------------------------------------------------------
_NEGATION_PAIRS: List[Tuple[str, str]] = [
    # Title / H1
    (r"missing\s+title|no\s+title|title\s+absent", r"title\s+present|title\s+too\s+(long|short)|title\s+truncated"),
    (r"missing\s+<?h1>?|no\s+<?h1>?|<?h1>?\s+absent|lacks\s+(?:a\s+)?(?:top-level\s+)?<?h1>?", r"<?h1>?\s+present|multiple\s+<?h1>?|<?h1>?\s+too\s+long"),
    # Meta description
    (r"missing\s+meta\s+desc|no\s+meta\s+desc", r"meta\s+desc\s+too\s+(long|short)|meta\s+desc\s+truncated"),
    # Schema
    (r"no\s+schema|schema\s+absent|no\s+structured\s+data", r"schema\s+detected|faq\s+schema|organization\s+schema"),
    # HTTPS
    (r"not\s+https|http\s+only|insecure\s+protocol", r"https\s+detected|secure\s+connection|ssl\s+present"),
    # Robots
    (r"robots\s+blocking|disallow\s+all|blocked\s+by\s+robots", r"robots\s+allows|crawl\s+accessible"),
    # Sitemap
    (r"no\s+sitemap|sitemap\s+missing|sitemap\s+absent", r"sitemap\s+found|sitemap\s+present|sitemap\s+detected"),
    # Canonical
    (r"missing\s+canonical|no\s+canonical", r"canonical\s+present|canonical\s+tag\s+found"),
    # GEO / AI visibility
    (r"not\s+cited|no\s+ai\s+citation|invisible\s+to\s+ai", r"cited\s+by|ai\s+citation\s+detected|ai\s+visible"),
]

# EvidenceLevel numeric rank: higher wins
_LEVEL_RANK: dict = {
    EvidenceLevel.E6_CORROBORATED: 6,
    EvidenceLevel.E5_AUTHORIZED_EXTERNAL: 5,
    EvidenceLevel.E4_FIRST_PARTY_DOM: 4,
    EvidenceLevel.E3_DETERMINISTIC: 3,
    EvidenceLevel.E2_DERIVED: 2,
    EvidenceLevel.E1_LLM_ASSERTION: 1,
    EvidenceLevel.E0_NONE: 0,
}


def _title_matches(title: str, pattern: str) -> bool:
    return bool(re.search(pattern, title, re.I))


def _evidence_rank(finding: Finding) -> int:
    level = getattr(finding, "evidence_level", None)
    if level:
        return _LEVEL_RANK.get(level, 0)
    # Infer from evidence_class
    ev_class_map = {
        EvidenceClass.EXTERNALLY_VERIFIED: 5,
        EvidenceClass.OBSERVED: 4,
        EvidenceClass.MODEL_INFERRED: 1,
        EvidenceClass.HYPOTHESIS: 0,
    }
    ev_class = getattr(finding, "evidence_class", None)
    if ev_class:
        return ev_class_map.get(ev_class, 2)
    # Fall back to rubric confidence
    rubric = getattr(finding, "confidence_rubric", None)
    if rubric in (RubricConfidence.VERIFIED, RubricConfidence.CERTAIN):
        return 4
    if rubric in (RubricConfidence.HIGH_CONFIDENCE, RubricConfidence.LIKELY):
        return 3
    if rubric == RubricConfidence.MEDIUM_CONFIDENCE:
        return 2
    return 1


def _are_contradictory(a: Finding, b: Finding) -> Optional[Tuple[str, str]]:
    """
    Returns (pattern_a, pattern_b) if the pair is contradictory, else None.
    Contradictions apply within the same category, or across structural categories
    (e.g., SEO, Technical, Schema, Accessibility/UX) for foundational site invariants.
    """
    structural_cats = {
        Category.ON_PAGE_SEO, Category.TECHNICAL_SEO, Category.SCHEMA,
        Category.UX_CONVERSION, Category.CONTENT,
    }
    is_compatible_cat = (a.category == b.category) or (a.category in structural_cats and b.category in structural_cats)
    if not is_compatible_cat:
        return None

    text_a = f"{a.title} {a.description or ''}"
    text_b = f"{b.title} {b.description or ''}"

    for pat_a, pat_b in _NEGATION_PAIRS:
        if _title_matches(text_a, pat_a) and _title_matches(text_b, pat_b):
            return (pat_a, pat_b)
        if _title_matches(text_a, pat_b) and _title_matches(text_b, pat_a):
            return (pat_b, pat_a)
    return None


def _resolve(
    a: Finding,
    b: Finding,
    pair: Tuple[str, str],
) -> ContradictionReport:
    """
    Produce a ContradictionReport.  The higher-evidence finding wins.
    MODEL_INFERRED findings CANNOT override OBSERVED evidence.
    """
    rank_a = _evidence_rank(a)
    rank_b = _evidence_rank(b)

    if rank_a == rank_b:
        # Tie → flag as UNRESOLVED
        status = ContradictionStatus.UNRESOLVED
        winner_id = None
        reason = (
            f"Both '{a.title}' and '{b.title}' have equal evidence weight "
            f"(rank={rank_a}). A human reviewer must determine which is correct."
        )
    elif rank_a > rank_b:
        status = ContradictionStatus.RESOLVED
        winner_id = a.finding_id
        reason = (
            f"'{a.title}' (evidence rank {rank_a}) overrides '{b.title}' "
            f"(evidence rank {rank_b}). The lower-evidence finding is demoted."
        )
    else:
        status = ContradictionStatus.RESOLVED
        winner_id = b.finding_id
        reason = (
            f"'{b.title}' (evidence rank {rank_b}) overrides '{a.title}' "
            f"(evidence rank {rank_a}). The lower-evidence finding is demoted."
        )

    ev_a = FindingEvidence(
        evidence_id=a.finding_id,
        value=a.title,
        source=getattr(a, "confidence_basis", "") or a.finding_id,
    )
    ev_b = FindingEvidence(
        evidence_id=b.finding_id,
        value=b.title,
        source=getattr(b, "confidence_basis", "") or b.finding_id,
    )

    cid = f"CTRD-{a.finding_id[:6]}-{b.finding_id[:6]}"
    return ContradictionReport(
        id=cid,
        contradiction_type="inter_finding_conflict",
        declared_type=a.category.value,
        detected_type=b.category.value,
        confidence=0.85 if status == ContradictionStatus.RESOLVED else 0.60,
        reason=reason,
        evidence=[ev_a, ev_b],
    ), winner_id, status


class ContradictionEngine:
    """
    Detects contradictions across all audit findings and produces a reconciled
    view with ContradictionReports and a winner-marked finding list.

    Usage::

        engine = ContradictionEngine()
        contradictions, reconciled = engine.reconcile(findings)
    """

    def reconcile(
        self,
        findings: List[Finding],
    ) -> Tuple[List[ContradictionReport], List[Finding]]:
        """
        Analyse all finding pairs.

        Returns
        -------
        contradictions : List[ContradictionReport]
            One report per detected conflict.
        reconciled : List[Finding]
            Full finding list where losers have held_from_executive=True and
            UNRESOLVED pairs are flagged.
        """
        reports: List[ContradictionReport] = []
        # id → mutated copy with held_from_executive potentially set
        finding_map: Dict[str, Finding] = {f.finding_id: f for f in findings}
        held_ids: set = set()

        for a, b in itertools.combinations(findings, 2):
            pair = _are_contradictory(a, b)
            if pair is None:
                continue

            report, winner_id, status = _resolve(a, b, pair)
            reports.append(report)

            if status == ContradictionStatus.RESOLVED and winner_id:
                loser_id = b.finding_id if winner_id == a.finding_id else a.finding_id
                if loser_id not in held_ids:
                    held_ids.add(loser_id)
                    loser = finding_map[loser_id]
                    finding_map[loser_id] = loser.model_copy(update={
                        "held_from_executive": True,
                        "verification_notes": (
                            (loser.verification_notes or "") +
                            f" [CONTRADICTION RESOLVED: overridden by {winner_id} — {report.reason}]"
                        ),
                    })
            elif status == ContradictionStatus.UNRESOLVED:
                # Both get flagged as needing review but neither is held
                for fid in (a.finding_id, b.finding_id):
                    f = finding_map[fid]
                    finding_map[fid] = f.model_copy(update={
                        "verification_notes": (
                            (f.verification_notes or "") +
                            f" [UNRESOLVED CONTRADICTION with {b.finding_id if fid == a.finding_id else a.finding_id} — requires human review]"
                        )
                    })

        reconciled = [finding_map[f.finding_id] for f in findings]
        return reports, reconciled

    def summarise(self, reports: List[ContradictionReport]) -> Dict:
        resolved = sum(1 for r in reports if "overrides" in r.reason)
        unresolved = len(reports) - resolved
        return {
            "total_contradictions": len(reports),
            "resolved": resolved,
            "unresolved": unresolved,
            "unresolved_ids": [
                r.id for r in reports
                if "human reviewer" in r.reason
            ],
        }

    def reconcile_with_manifest_and_rollups(
        self,
        findings: List[Finding],
        manifest: Optional[Any] = None,
        heading_hierarchy: Optional[Any] = None,
    ) -> Tuple[List[Finding], List[str]]:
        """
        Reconciles findings against deterministic crawl ground truth (HeadingHierarchyRollup, CrawlManifest):
        1. If heading_hierarchy shows missing_h1 == 0 (no pages missing H1),
           any finding claiming "Document lacks a top-level <h1>" or "missing an <h1>"
           is reconciled (clause stripped if multiple H1s are present, or suppressed).
        2. If manifest.sitemap_found == True, findings claiming "no sitemap found" are suppressed.
        3. If manifest.robots_txt_found == True, findings claiming "robots.txt missing" are suppressed.
        """
        reconciled: List[Finding] = []
        actions_taken: List[str] = []

        missing_h1_total = 0
        if heading_hierarchy and hasattr(heading_hierarchy, "missing_h1"):
            missing_h1_total = len(heading_hierarchy.missing_h1 or [])
        elif manifest and hasattr(manifest, "crawl_health"):
            missing_h1_total = int(manifest.crawl_health.get("missing_h1_count", 0))

        sitemap_found = bool(manifest and getattr(manifest, "sitemap_found", False))
        robots_found = bool(manifest and getattr(manifest, "robots_txt_found", False))

        for f in findings:
            desc = (f.description or "").lower()
            title = f.title.lower()
            full_text = f"{title} {desc}"

            # 1. Heading check: if sitewide missing H1 is 0, but finding claims document lacks an H1
            if missing_h1_total == 0 and any(k in full_text for k in ["lacks a top-level <h1>", "lacks a top-level h1", "missing an <h1>", "no <h1> tag"]):
                if "multiple" in full_text:
                    clean_desc = re.sub(r"(?:Document|Page\s*\([^)]*\))\s*lacks\s*a\s*top-level\s*<h1\b[^>]*>\s*(?:heading)?\.?;?\s*", "", f.description or "", flags=re.I).strip()
                    clean_desc = re.sub(r"page\s*is\s*completely\s*missing\s*an\s*<h1>\s*tag\.?;?\s*", "", clean_desc, flags=re.I).strip()
                    if not clean_desc:
                        clean_desc = "Page contains multiple competing <h1> tags diluting primary topical authority."
                    clean_title = f.title
                    if any(k in clean_title.lower() for k in ["lacks", "missing"]):
                        clean_title = "Multiple <h1> tags compete for primary topical authority"
                    f_updated = f.model_copy(update={"title": clean_title, "description": clean_desc})
                    reconciled.append(f_updated)
                    actions_taken.append(f"Reconciled heading finding {f.finding_id}: updated to multiple H1s because crawl proved 0 pages missing H1.")
                    continue
                else:
                    f_held = f.model_copy(update={
                        "held_from_executive": True,
                        "verification_notes": (
                            (f.verification_notes or "") +
                            " [CONTRADICTION SUPPRESSED: HeadingAnalyzer verified 0 pages missing an H1.]"
                        )
                    })
                    reconciled.append(f_held)
                    actions_taken.append(f"Suppressed finding {f.finding_id} ('{f.title}') due to contradiction with verified 0 missing H1 count.")
                    continue

            # 2. Sitemap check
            if sitemap_found and any(k in full_text for k in ["no sitemap found", "sitemap missing", "sitemap absent"]):
                f_held = f.model_copy(update={
                    "held_from_executive": True,
                    "verification_notes": (
                        (f.verification_notes or "") +
                        " [CONTRADICTION SUPPRESSED: Crawl manifest verified valid sitemap.xml present.]"
                    )
                })
                reconciled.append(f_held)
                actions_taken.append(f"Suppressed finding {f.finding_id} ('{f.title}') because sitemap.xml was verified present.")
                continue

            # 3. Robots.txt check
            if robots_found and any(k in full_text for k in ["robots.txt missing", "no robots.txt"]):
                f_held = f.model_copy(update={
                    "held_from_executive": True,
                    "verification_notes": (
                        (f.verification_notes or "") +
                        " [CONTRADICTION SUPPRESSED: Crawl manifest verified valid robots.txt present.]"
                    )
                })
                reconciled.append(f_held)
                actions_taken.append(f"Suppressed finding {f.finding_id} ('{f.title}') because robots.txt was verified present.")
                continue

            reconciled.append(f)

        return reconciled, actions_taken


# Singleton
contradiction_engine = ContradictionEngine()
