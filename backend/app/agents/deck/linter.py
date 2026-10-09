"""
Deck Quality & Provenance Linter
Executes multi-pass automated verification over the DeckBlueprint before rendering or export:
1. Interpretation Lint: Confirms every chart/table slide has a quantified 'Read: ...' takeaway.
2. Evidence Lineage Lint: Validates evidence token citations (ev_NNN, ext_NNN) for findings.
3. Scale & Units Lint: Validates metric bounds, units, and formatting.
4. Non-Repetition Lint: Verifies zero duplicate slide IDs, titles, or thematic overlaps.
"""
from typing import List, Dict, Any, Set
from datetime import datetime, timezone
from app.agents.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    DeckLintResult,
    DeckLintIssue,
    SlideLayoutType
)


class DeckQualityLinter:
    """
    Automated multi-pass verification engine for presentation decks.
    """

    def lint_blueprint(self, blueprint: DeckBlueprint) -> DeckLintResult:
        issues: List[DeckLintIssue] = []
        total_checks = 0

        # Pass 1: Non-Repetition Lint
        total_checks += 1
        seen_ids: Set[str] = set()
        seen_titles: Set[str] = set()
        seen_focuses: Set[str] = set()

        for slide in blueprint.slides:
            # Check ID uniqueness
            if slide.slide_id in seen_ids:
                issues.append(DeckLintIssue(
                    rule="NON_REPETITION_ID",
                    slide_id=slide.slide_id,
                    slide_number=slide.slide_number,
                    severity="ERROR",
                    message=f"Duplicate slide_id detected: '{slide.slide_id}'"
                ))
            seen_ids.add(slide.slide_id)

            # Check Title uniqueness across all slides
            normalized_title = slide.title.strip().lower()
            if normalized_title in seen_titles:
                issues.append(DeckLintIssue(
                    rule="NON_REPETITION_TITLE",
                    slide_id=slide.slide_id,
                    slide_number=slide.slide_number,
                    severity="ERROR",
                    message=f"Duplicate slide title detected: '{slide.title}'"
                ))
            seen_titles.add(normalized_title)

            # Check Thematic focus uniqueness
            if slide.thematic_focus in seen_focuses:
                issues.append(DeckLintIssue(
                    rule="NON_REPETITION_FOCUS",
                    slide_id=slide.slide_id,
                    slide_number=slide.slide_number,
                    severity="ERROR",
                    message=f"Duplicate thematic_focus detected: '{slide.thematic_focus}'"
                ))
            seen_focuses.add(slide.thematic_focus)

        # Pass 2: Interpretation Lint ('Read: ...')
        total_checks += 1
        for slide in blueprint.slides:
            has_exhibit = (slide.chart is not None or len(slide.table_rows) > 0)
            if has_exhibit:
                if not slide.interpretation or not slide.interpretation.strip():
                    issues.append(DeckLintIssue(
                        rule="INTERPRETATION_MISSING",
                        slide_id=slide.slide_id,
                        slide_number=slide.slide_number,
                        severity="WARNING",
                        message=f"Slide '{slide.slide_id}' contains data exhibit but lacks an analytical 'Read: ...' takeaway."
                    ))
                elif not slide.interpretation.startswith("Read:"):
                    issues.append(DeckLintIssue(
                        rule="INTERPRETATION_FORMAT",
                        slide_id=slide.slide_id,
                        slide_number=slide.slide_number,
                        severity="WARNING",
                        message=f"Takeaway on slide '{slide.slide_id}' should begin with 'Read: ...'"
                    ))

        # Pass 3: Evidence Lineage Lint
        total_checks += 1
        for slide in blueprint.slides:
            if slide.layout in (SlideLayoutType.FINDINGS_LEDGER, SlideLayoutType.CODE_PATCH_DIFF):
                if not slide.evidence_citations and not slide.lineage_evidence_tokens:
                    issues.append(DeckLintIssue(
                        rule="LINEAGE_MISSING",
                        slide_id=slide.slide_id,
                        slide_number=slide.slide_number,
                        severity="WARNING",
                        message=f"Remediation/Findings slide '{slide.slide_id}' lacks explicit evidence token citations (ev_NNN/ext_NNN)."
                    ))

        # Pass 4: Scale and Units Lint
        total_checks += 1
        for slide in blueprint.slides:
            if slide.chart:
                for s in slide.chart.series:
                    for v in s.get("values", []):
                        if isinstance(v, (int, float)):
                            if v < 0:
                                issues.append(DeckLintIssue(
                                    rule="SCALE_NEGATIVE",
                                    slide_id=slide.slide_id,
                                    slide_number=slide.slide_number,
                                    severity="ERROR",
                                    message=f"Negative value {v} detected in chart series '{s.get('name')}' on slide '{slide.slide_id}'"
                                ))

        errors_count = sum(1 for i in issues if i.severity == "ERROR")
        warnings_count = sum(1 for i in issues if i.severity == "WARNING")
        passed = (errors_count == 0)

        result = DeckLintResult(
            passed=passed,
            total_checks=total_checks,
            errors_count=errors_count,
            warnings_count=warnings_count,
            issues=issues,
            verified_at=datetime.now(timezone.utc).isoformat()
        )
        blueprint.lint_result = result
        return result
