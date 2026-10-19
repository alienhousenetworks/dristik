"""HTML appendix for the enterprise SEO assessment.

The appendix is generated from the assessment. It does not fill missing
metrics, and it does not assign page numbers ahead of the renderer.
"""

from __future__ import annotations

import html
from typing import Any

from app.seo.enterprise.assess import build_enterprise_seo
from app.seo.enterprise.contracts import EnterpriseSeoAssessment

_LABELS = {
    "ISSUE_VERIFIED": "Issue verified",
    "NO_ISSUE": "No issue in the checked sample",
    "MEASURED": "Measured",
    "INFERRED": "Inferred",
    "DATA_UNAVAILABLE": "Data unavailable",
    "NOT_TESTED": "Not tested",
    "NOT_APPLICABLE": "Not applicable",
}


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_enterprise_appendix(report: Any) -> str:
    try:
        assessment = build_enterprise_seo(report)
    except Exception as exc:
        return (
            "<section class=\"chapter-start\" id=\"enterprise-seo\">"
            "<h2>Enterprise SEO assessment</h2>"
            f"<p>The enterprise assessment could not be built ({_esc(type(exc).__name__)}). "
            "The indexed chapters above still use the sealed report.</p>"
            "</section>"
        )
    return _render(assessment)


def _render(assessment: EnterpriseSeoAssessment) -> str:
    score_rows = []
    for score in assessment.scores:
        shown = "Not scored" if score.score is None else f"{score.score:g}"
        score_rows.append(
            "<tr>"
            f"<td>{_esc(score.category)}</td>"
            f"<td>{_esc(shown)}</td>"
            f"<td>{_esc(score.status)}</td>"
            f"<td>{_esc(score.note)}</td>"
            "</tr>"
        )
    chapter_rows = []
    for chapter in assessment.chapters:
        chapter_rows.append(
            "<tr>"
            f"<td>{chapter.chapter:02d}</td>"
            f"<td>{_esc(chapter.title)}</td>"
            f"<td>{_esc(_LABELS.get(chapter.status, chapter.status))}</td>"
            f"<td>{len(chapter.finding_ids)}</td>"
            "</tr>"
        )
    finding_blocks = []
    cards = {card.finding_id: card for card in assessment.cards}
    for finding in assessment.findings:
        card = cards.get(finding.finding_id)
        sections = ""
        if card:
            sections = "".join(
                f"<h4>{section.number}. {_esc(section.heading)}</h4><p>{_esc(section.body)}</p>"
                for section in card.sections
            )
        finding_blocks.append(
            "<article class=\"card\">"
            f"<h3>{_esc(finding.title)}</h3>"
            f"<p>Finding {_esc(finding.finding_id)} · {_esc(finding.evaluation_state)} · {_esc(finding.severity)} · "
            f"{_esc(finding.scope)} · {_esc(finding.verification_status)}</p>"
            f"{sections}"
            "</article>"
        )
    if not finding_blocks:
        finding_blocks.append("<p>No validated finding was published from the stored evidence.</p>")
    limitations = "".join(f"<li>{_esc(item)}</li>" for item in assessment.limitations)
    return f"""
    <section class="chapter-start" id="enterprise-seo">
        <h2>Enterprise SEO assessment</h2>
        <p>{_esc(assessment.coverage.statement)}</p>
        <p>Report stage: {_esc(assessment.report_stage)}. Schema {_esc(assessment.schema_version)}.
        This appendix does not replace the indexed chapters, and it does not calculate a new score.</p>
        <p>{_esc(assessment.diagnostic_summary)}</p>
        <p>Not executed in this phase: {_esc(", ".join(assessment.deferred_modules) or "none recorded")}.</p>
        <table>
            <thead><tr><th>Category</th><th>Score</th><th>Status</th><th>Note</th></tr></thead>
            <tbody>{''.join(score_rows)}</tbody>
        </table>
        <h3>Chapters</h3>
        <table>
            <thead><tr><th>Chapter</th><th>Title</th><th>Status</th><th>Findings</th></tr></thead>
            <tbody>{''.join(chapter_rows)}</tbody>
        </table>
        <h3>Findings</h3>
        {''.join(finding_blocks)}
        <h3>Limitations</h3>
        <ul>{limitations}</ul>
    </section>
    """
