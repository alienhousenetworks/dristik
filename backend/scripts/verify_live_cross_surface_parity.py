#!/usr/bin/env python3
"""Live Cross-Surface Score Parity Verifier (API <-> UI model <-> All 5 PDFs <-> PPTX).

Usage:
  # Verify existing completed analysis IDs from a running Dristik API:
  python scripts/verify_live_cross_surface_parity.py --api-url http://localhost:8000 --token <JWT> --analysis-ids id1,id2,id3

  # Or verify saved report JSON files directly:
  python scripts/verify_live_cross_surface_parity.py --report-files report1.json,report2.json

Exits 0 if all checked surfaces have 0.0 drift, or 1 if any mismatch is detected.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.models import ExecutiveReport
from app.domain.scoring.canonical_scorecard import CanonicalScorecardEngine
from app.domain.scoring.displayed_score import displayed_composite
from app.reports.deck.math_engine import DeterministicMetricEngine
from app.reports.narrative_validator import build_scorecard_vars
from app.reports.snapshot_provenance import format_audit_execution_metadata


def _frontend_displayed_composite(payload: Dict[str, Any]) -> Optional[float]:
    """Mirrors frontend/src/lib/displayedAuditScore.ts canonical_scorecard path."""
    card = payload.get("canonical_scorecard")
    if isinstance(card, dict) and isinstance(card.get("pillars"), dict):
        val = card.get("composite_health_score")
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
    return None


def verify_report_parity(payload: Dict[str, Any], label: str) -> Dict[str, Any]:
    report = ExecutiveReport.model_validate(payload)
    card = CanonicalScorecardEngine.evaluate_from_report(report)
    serialized = report.model_dump(mode="json")

    expected = card.composite_health_score
    surfaces = {
        "canonical_scorecard": expected,
        "api_serialized": (serialized.get("canonical_scorecard") or {}).get("composite_health_score"),
        "frontend_displayed_score": _frontend_displayed_composite(serialized),
        "backend_displayed_composite": displayed_composite(report),
        "pdf_snapshot_provenance": format_audit_execution_metadata(report).composite_score,
        "pptx_deck_math": DeterministicMetricEngine().compute_bundle(report).overall_score if expected is not None else None,
    }
    sv = build_scorecard_vars(report)
    expected_str = f"{int(round(expected))}/100" if expected is not None else "NOT_MEASURED"
    narrative_ok = sv.get("score.overall") == expected_str

    mismatches: List[str] = []
    for name, val in surfaces.items():
        if expected is None and val is None:
            continue
        if expected is None or val is None or abs(float(val) - float(expected)) > 1e-6:
            mismatches.append(f"{name}={val} != canonical={expected}")
    if not narrative_ok:
        mismatches.append(f"narrative_vars={sv.get('score.overall')} != {expected_str}")

    return {
        "label": label,
        "domain": report.domain or report.website_url,
        "crawl_scope": f"{card.crawl_coverage.crawled_urls}/{card.crawl_coverage.discovered_urls}",
        "surfaces": surfaces,
        "passed": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def _fetch_report(api_url: str, token: str, analysis_id: str) -> Dict[str, Any]:
    import httpx

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{api_url.rstrip('/')}/api/v1/analyses/{analysis_id}/report"
    resp = httpx.get(url, headers=headers, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify cross-surface Dristik score parity.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--token", default="")
    parser.add_argument("--analysis-ids", default="", help="Comma-separated completed analysis IDs")
    parser.add_argument("--report-files", default="", help="Comma-separated ExecutiveReport JSON files")
    parser.add_argument("--out-json", default="", help="Optional path to write JSON parity report")
    args = parser.parse_args()

    results: List[Dict[str, Any]] = []
    for aid in [s.strip() for s in args.analysis_ids.split(",") if s.strip()]:
        payload = _fetch_report(args.api_url, args.token, aid)
        results.append(verify_report_parity(payload, label=aid))

    for fp in [s.strip() for s in args.report_files.split(",") if s.strip()]:
        payload = json.loads(Path(fp).read_text(encoding="utf-8"))
        results.append(verify_report_parity(payload, label=fp))

    if not results:
        print("Provide --analysis-ids or --report-files to verify.", file=sys.stderr)
        return 2

    print("| Target | Domain | Crawl Scope | Canonical | Status | Mismatches |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    all_passed = True
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        if not r["passed"]:
            all_passed = False
        canon = r["surfaces"]["canonical_scorecard"]
        mm = "; ".join(r["mismatches"]) or "None"
        print(f"| {r['label']} | {r['domain']} | {r['crawl_scope']} | {canon} | {status} | {mm} |")

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(results, indent=2), encoding="utf-8")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
