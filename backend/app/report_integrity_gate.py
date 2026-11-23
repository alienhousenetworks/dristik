"""Final deterministic integrity gate for customer-facing audit reports.

This gate runs after report assembly and the existing validation gate, but before
the run manifest is sealed or the report is persisted. It distinguishes blocking
integrity failures from evidence gaps that must be disclosed to the customer.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


def _value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _normalized_title(value: Any) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).split())


def validate_final_report(report: Any, manifest: Any | None = None) -> dict[str, Any]:
    """Validate report identity, scores, finding uniqueness, evidence links and manifest parity.

    Raises ValueError for structural failures that make the report unsafe to persist.
    Missing evidence is not converted into a positive claim: it prevents certification
    and is surfaced as a warning, while dangling references and invalid scores block.
    """
    blockers: list[str] = []
    warnings: list[str] = []
    findings = list(getattr(report, "findings", None) or [])
    evidence_ledger = getattr(report, "evidence_ledger", None) or {}
    evidence_ids = set(evidence_ledger.keys()) if isinstance(evidence_ledger, dict) else set()

    for item in findings:
        embedded = getattr(item, "evidence", None) or []
        for evidence in embedded:
            evidence_id = getattr(evidence, "evidence_id", None)
            if evidence_id:
                evidence_ids.add(str(evidence_id))

    finding_ids: set[str] = set()
    semantic_keys: Counter[tuple[str, str]] = Counter()
    unsupported_findings: list[str] = []
    dangling_refs: list[str] = []

    for index, finding in enumerate(findings):
        finding_id = str(getattr(finding, "finding_id", "") or "").strip()
        if not finding_id:
            blockers.append(f"finding at index {index} has no finding_id")
        elif finding_id in finding_ids:
            blockers.append(f"duplicate finding_id: {finding_id}")
        finding_ids.add(finding_id)

        title = _normalized_title(getattr(finding, "title", None) or getattr(finding, "finding", None))
        category = str(_value(getattr(finding, "category", "")) or "").casefold()
        if title:
            semantic_keys[(category, title)] += 1

        refs: set[str] = set()
        for field in ("evidence_refs", "evidence_ids", "evidence_references"):
            raw = getattr(finding, field, None) or []
            if isinstance(raw, (list, tuple, set)):
                refs.update(str(ref) for ref in raw if ref)
        for evidence in (getattr(finding, "evidence", None) or []):
            ref = getattr(evidence, "evidence_id", None)
            if ref:
                refs.add(str(ref))

        if not refs:
            unsupported_findings.append(finding_id or f"index:{index}")
        else:
            missing = sorted(refs - evidence_ids)
            if missing:
                dangling_refs.append(f"{finding_id or index}: {', '.join(missing)}")

    duplicate_titles = [
        f"{category}:{title}" for (category, title), count in semantic_keys.items() if count > 1
    ]
    if duplicate_titles:
        blockers.append("duplicate finding root-cause keys: " + "; ".join(duplicate_titles[:20]))
        if len(duplicate_titles) > 20:
            warnings.append(f"{len(duplicate_titles) - 20} additional duplicate finding keys omitted")

    if dangling_refs:
        blockers.append("dangling evidence references: " + "; ".join(dangling_refs[:20]))
        if len(dangling_refs) > 20:
            warnings.append(f"{len(dangling_refs) - 20} additional dangling references omitted")

    synthetic_hashes: list[str] = []

    def _note_hash(owner: str, value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            return
        lowered = text.lower()
        if lowered.startswith(("sha_", "hash_")) or not re.fullmatch(r"[0-9a-fA-F]{64}", text):
            synthetic_hashes.append(f"{owner}: {text[:24]}")

    ledger_items = evidence_ledger.values() if isinstance(evidence_ledger, dict) else []
    for item in ledger_items:
        if not isinstance(item, dict):
            item = getattr(item, "__dict__", {}) if not isinstance(item, dict) else item
        owner = str(item.get("id") or "ledger")
        _note_hash(owner, item.get("content_sha256"))
        digest = str(item.get("hash") or "")
        if digest.lower().startswith(("sha_", "hash_")):
            synthetic_hashes.append(f"{owner}: {digest[:24]}")
    for finding in findings:
        for evidence in (getattr(finding, "evidence", None) or []):
            owner = str(getattr(evidence, "evidence_id", None) or getattr(finding, "finding_id", "finding"))
            _note_hash(owner, getattr(evidence, "content_sha256", None))
            digest = str(getattr(evidence, "hash", "") or "")
            if digest.lower().startswith(("sha_", "hash_")):
                synthetic_hashes.append(f"{owner}: {digest[:24]}")
    if synthetic_hashes:
        blockers.append(
            "evidence hash is not a SHA-256 of a fetched body: " + "; ".join(synthetic_hashes[:20])
        )

    scores = getattr(report, "scores", None)
    overall = getattr(scores, "overall_score", None)
    if isinstance(overall, bool) or not isinstance(overall, (int, float)) or not math.isfinite(float(overall)) or not 0 <= float(overall) <= 100:
        blockers.append("overall score is missing, non-finite, or outside 0..100")

    category_scores = getattr(scores, "category_scores", None) or {}
    active_category_weights: list[float] = []
    if isinstance(category_scores, dict):
        for key, item in category_scores.items():
            raw_score = getattr(item, "score", item if isinstance(item, (int, float)) else None)
            status = str(_value(getattr(item, "status", "MEASURED")) or "MEASURED").upper()
            raw_weight = getattr(item, "weight", None)
            raw_weighted = getattr(item, "weighted_score", None)
            weight = None
            if raw_weight is not None:
                if (
                    isinstance(raw_weight, bool)
                    or not isinstance(raw_weight, (int, float))
                    or not math.isfinite(float(raw_weight))
                    or not 0 <= float(raw_weight) <= 1
                ):
                    blockers.append(f"category weight {key} is invalid")
                else:
                    weight = float(raw_weight)
                    if status in {"MEASURED", "PARTIAL"} and weight > 0:
                        active_category_weights.append(weight)

            if raw_score is not None and (
                isinstance(raw_score, bool)
                or not isinstance(raw_score, (int, float))
                or not math.isfinite(float(raw_score))
                or not 0 <= float(raw_score) <= 100
            ):
                blockers.append(f"category score {key} is invalid")
                continue

            if status == "NOT_MEASURED" and raw_score is not None:
                blockers.append(f"category {key} is marked NOT_MEASURED but has a numeric score")
            if raw_score is None and weight is not None and weight > 0:
                blockers.append(f"category {key} has positive weight but no measured score")

            if raw_score is not None and weight is not None and raw_weighted is not None:
                if (
                    isinstance(raw_weighted, bool)
                    or not isinstance(raw_weighted, (int, float))
                    or not math.isfinite(float(raw_weighted))
                    or not 0 <= float(raw_weighted) <= 100
                ):
                    blockers.append(f"category weighted score {key} is invalid")
                elif weight > 0 and abs(float(raw_weighted) - float(raw_score) * weight) > 0.05:
                    blockers.append(f"category weighted score {key} does not reconcile with score × weight")

        if active_category_weights and abs(sum(active_category_weights) - 1.0) > 0.01:
            blockers.append("measured category weights do not sum to 1.0")

    if manifest is not None:
        if getattr(manifest, "analysis_id", None) != getattr(report, "analysis_id", None):
            blockers.append("report and manifest analysis_id do not match")
        if getattr(manifest, "report_id", None) != getattr(report, "report_id", None):
            blockers.append("report and manifest report_id do not match")
        pinned_ids = {str(getattr(pin, "finding_id", "")) for pin in (getattr(manifest, "findings", None) or [])}
        if hasattr(manifest, "findings") and pinned_ids != finding_ids:
            blockers.append("manifest finding pins do not match final report findings")

    if unsupported_findings:
        warnings.append(
            f"{len(unsupported_findings)} finding(s) have no linked evidence and must not be represented as verified."
        )
    if warnings:
        pass

    if blockers:
        raise ValueError("Final report integrity gate failed: " + " | ".join(blockers))

    fully_supported = not unsupported_findings
    return {
        "status": "PASS" if fully_supported else "PASS_WITH_EVIDENCE_GAPS",
        "certified": fully_supported,
        "finding_count": len(findings),
        "evidence_id_count": len(evidence_ids),
        "unsupported_finding_ids": unsupported_findings,
        "warnings": warnings,
        "blockers": [],
        "checked_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "gate_version": "final-report-integrity-v1",
    }


_FORBIDDEN_PDF_TOKENS = (
    ("chapter_ref_leak", re.compile(r"\[\[chapter_ref:[^\]]*\]\]", re.IGNORECASE)),
    ("placeholder_domain", re.compile(r"\byourdomain\.com\b", re.IGNORECASE)),
    ("placeholder_brand", re.compile(r"\bVerified Brand Name\b", re.IGNORECASE)),
    ("epistemic_unknown", re.compile(r"Epistemic Basis:\s*UNKNOWN\b", re.IGNORECASE)),
    ("empty_citation_brackets", re.compile(r"\[\s*\]")),
)

_FIVE_POINT_MARKERS = (
    "1. Finding:",
    "2. Algorithm Analysis",
    "3. AI Understanding:",
    "4. AI Analysis:",
    "5. Fix Plan (Prompt):",
    "Fix resolves issue:",
)


def validate_pdf_release_gates(
    pdf_artifacts: dict[str, dict[str, Any]],
    *,
    max_master_pages: int = 22,
) -> dict[str, Any]:
    """Enforce Phase 5 release gates across all rendered PDF publications (Master + 5 pillars).

    Each value in `pdf_artifacts` is a dict with:
      - composite_score: float | None
      - finding_count: int
      - html: str (rendered HTML/text of the PDF)
      - page_count: int | None (optional; checked against max_master_pages for 'master')
      - chapters: list[dict] (optional; [{chapter_id, owned_finding_count, html}])
    """
    blockers: list[str] = []
    if not pdf_artifacts:
        raise ValueError("PDF release gate failed: no PDF artifacts supplied")

    scores = {
        name: round(float(meta["composite_score"]), 1)
        for name, meta in pdf_artifacts.items()
        if meta.get("composite_score") is not None
    }
    if len(set(scores.values())) > 1:
        blockers.append(f"composite score mismatch across PDFs: {scores}")

    counts = {
        name: int(meta["finding_count"])
        for name, meta in pdf_artifacts.items()
        if meta.get("finding_count") is not None
    }
    if len(set(counts.values())) > 1:
        blockers.append(f"finding count mismatch across PDFs: {counts}")

    for name, meta in pdf_artifacts.items():
        body = str(meta.get("html") or "")
        for tok_name, pattern in _FORBIDDEN_PDF_TOKENS:
            if pattern.search(body):
                blockers.append(f"{name}: leaked/placeholder token detected ({tok_name})")

        # Verify every 5-point finding card contains all 5 blocks + connector verdict
        if "five-point-finding-card" in body:
            for marker in _FIVE_POINT_MARKERS:
                if marker not in body:
                    blockers.append(f"{name}: missing 5-point card block '{marker}'")

        # Verify no chapter claims 'no defects' while owning findings
        for ch in (meta.get("chapters") or []):
            owned_cnt = int(ch.get("owned_finding_count") or 0)
            ch_html = str(ch.get("html") or "")
            if owned_cnt > 0 and re.search(r"\b(?:no defects|0 defects|zero defects)\b", ch_html, re.IGNORECASE):
                blockers.append(
                    f"{name}/{ch.get('chapter_id', 'chapter')}: claims no defects while owning {owned_cnt} finding(s)"
                )

        if name == "master" and meta.get("page_count") is not None:
            pg = int(meta["page_count"])
            if pg > max_master_pages:
                blockers.append(f"master PDF page count {pg} exceeds budget of {max_master_pages} pages")

    if blockers:
        raise ValueError("PDF release gates failed: " + " | ".join(blockers))

    return {
        "status": "PASS",
        "pdfs_checked": sorted(pdf_artifacts.keys()),
        "composite_score": next(iter(scores.values()), None),
        "finding_count": next(iter(counts.values()), None),
        "blockers": [],
    }
