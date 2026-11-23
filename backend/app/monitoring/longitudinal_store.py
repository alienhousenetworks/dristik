"""
Immutable Historical Snapshot Store & Comparable Longitudinal Intelligence Engine.

Preserves across every audit comparison:
- Original crawl scope & comparable URL-set intersection
- Scoring methodology version
- Connector availability delta
- Confidence and coverage changes (e.g., 5 pages -> 500 pages explicitly disclosed)
- Finding lifecycle diffs (NEW, FIXED, REOPENED, RECURRING)
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

from app.db.verification_historical_schema import connect_verification_history_db
from app.governance.data_reliability import utc_now_iso
from app.scoring.canonical_scorecard import CanonicalEnterpriseScorecard


class LongitudinalComparisonReport(BaseModel):
    org_id: str
    domain: str
    baseline_audit_run_id: str
    current_audit_run_id: str
    is_directly_comparable: bool
    comparability_warnings: List[str] = Field(default_factory=list)
    comparable_url_overlap_count: int = 0
    methodology_changed: bool = False
    coverage_changed: bool = False
    connectors_added: List[str] = Field(default_factory=list)
    connectors_removed: List[str] = Field(default_factory=list)
    pillar_deltas: Dict[str, Dict[str, Optional[float]]] = Field(default_factory=dict)
    finding_lifecycle: Dict[str, List[str]] = Field(default_factory=dict)


class LongitudinalSnapshotStore:
    """Persists immutable audit snapshots and computes comparability-guarded deltas."""

    @classmethod
    def save_snapshot(
        cls,
        *,
        org_id: str,
        scorecard: CanonicalEnterpriseScorecard,
        crawled_urls: Sequence[str],
        connectors_available: Sequence[str],
        findings: Sequence[Dict[str, Any]] = (),
        db_path: Optional[str] = None,
    ) -> str:
        snap_id = f"snap_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        cc = scorecard.crawl_coverage
        conn = connect_verification_history_db(db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_run_snapshots (
                    snapshot_id, org_id, domain, audit_run_id, methodology_version,
                    discovered_urls, crawled_urls, rendered_urls, inspected_urls, tested_urls,
                    crawled_url_set_json, connectors_available_json,
                    capability_completeness, evidence_coverage, optimization_effectiveness,
                    scorecard_sha256, captured_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snap_id, org_id, scorecard.domain, scorecard.audit_run_id, scorecard.methodology_version,
                    cc.discovered_urls, cc.crawled_urls, cc.rendered_urls, cc.inspected_urls, cc.tested_urls,
                    json.dumps(sorted(set(crawled_urls))), json.dumps(sorted(set(connectors_available))),
                    scorecard.capability_completeness_score, scorecard.evidence_coverage_score,
                    scorecard.optimization_effectiveness_score, scorecard.scorecard_sha256, now,
                ),
            )
            for p_name, p_score in scorecard.pillars.items():
                conn.execute(
                    """
                    INSERT INTO audit_score_history (
                        id, org_id, domain, audit_run_id, pillar,
                        capability_completeness, evidence_coverage, measured_health_score,
                        methodology_version, captured_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ash_{uuid.uuid4().hex[:12]}", org_id, scorecard.domain, scorecard.audit_run_id,
                        p_name, p_score.capability_completeness_score, p_score.evidence_coverage_score,
                        p_score.measured_health_score, scorecard.methodology_version, now,
                    ),
                )
            for f in findings:
                sig = str(f.get("signature") or f.get("finding_id") or f.get("title") or "")
                if not sig:
                    continue
                conn.execute(
                    """
                    INSERT INTO finding_history (
                        id, org_id, domain, audit_run_id, finding_signature, finding_id,
                        pillar, severity, lifecycle_status, captured_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"fh_{uuid.uuid4().hex[:12]}", org_id, scorecard.domain, scorecard.audit_run_id,
                        sig, str(f.get("finding_id") or sig), str(f.get("pillar") or "SEO"),
                        str(f.get("severity") or "MEDIUM"), str(f.get("status") or "OPEN"), now,
                    ),
                )
            conn.commit()
            return snap_id
        finally:
            conn.close()

    @classmethod
    def compare_runs(
        cls,
        *,
        org_id: str,
        baseline_audit_run_id: str,
        current_audit_run_id: str,
        db_path: Optional[str] = None,
    ) -> LongitudinalComparisonReport:
        conn = connect_verification_history_db(db_path)
        try:
            b = conn.execute(
                "SELECT * FROM audit_run_snapshots WHERE org_id = ? AND audit_run_id = ?",
                (org_id, baseline_audit_run_id),
            ).fetchone()
            c = conn.execute(
                "SELECT * FROM audit_run_snapshots WHERE org_id = ? AND audit_run_id = ?",
                (org_id, current_audit_run_id),
            ).fetchone()
            if not b or not c:
                raise KeyError("Both baseline and current audit run snapshots must exist for comparison.")

            warnings: List[str] = []
            meth_changed = b["methodology_version"] != c["methodology_version"]
            if meth_changed:
                warnings.append(
                    f"Methodology changed from {b['methodology_version']} to {c['methodology_version']}."
                )

            b_urls = set(json.loads(b["crawled_url_set_json"] or "[]"))
            c_urls = set(json.loads(c["crawled_url_set_json"] or "[]"))
            overlap = len(b_urls & c_urls)
            b_cnt, c_cnt = max(int(b["crawled_urls"]), 1), max(int(c["crawled_urls"]), 1)
            cov_changed = abs(c_cnt - b_cnt) / float(b_cnt) >= 0.25
            if cov_changed:
                warnings.append(
                    f"Crawl scope changed significantly ({b['crawled_urls']} -> {c['crawled_urls']} URLs; {overlap} overlapping URLs). "
                    "Do not interpret raw score changes without accounting for changed coverage."
                )

            b_conns = set(json.loads(b["connectors_available_json"] or "[]"))
            c_conns = set(json.loads(c["connectors_available_json"] or "[]"))
            added_conns = sorted(c_conns - b_conns)
            removed_conns = sorted(b_conns - c_conns)
            if added_conns or removed_conns:
                warnings.append(f"Connector availability changed (added={added_conns}, removed={removed_conns}).")

            # Pillar deltas
            b_scores = {
                r["pillar"]: r
                for r in conn.execute("SELECT * FROM audit_score_history WHERE org_id = ? AND audit_run_id = ?", (org_id, baseline_audit_run_id)).fetchall()
            }
            c_scores = {
                r["pillar"]: r
                for r in conn.execute("SELECT * FROM audit_score_history WHERE org_id = ? AND audit_run_id = ?", (org_id, current_audit_run_id)).fetchall()
            }
            pillar_deltas: Dict[str, Dict[str, Optional[float]]] = {}
            for p in ("SEO", "GEO", "AEO", "CRO"):
                bs = b_scores.get(p)
                cs = c_scores.get(p)
                bh = bs["measured_health_score"] if bs else None
                ch = cs["measured_health_score"] if cs else None
                pillar_deltas[p] = {
                    "baseline_health": bh,
                    "current_health": ch,
                    "delta": round(ch - bh, 1) if (bh is not None and ch is not None) else None,
                }

            # Finding lifecycle: new, fixed, recurring
            b_f = {r["finding_signature"] for r in conn.execute("SELECT finding_signature FROM finding_history WHERE org_id = ? AND audit_run_id = ?", (org_id, baseline_audit_run_id)).fetchall()}
            c_f = {r["finding_signature"] for r in conn.execute("SELECT finding_signature FROM finding_history WHERE org_id = ? AND audit_run_id = ?", (org_id, current_audit_run_id)).fetchall()}

            return LongitudinalComparisonReport(
                org_id=org_id,
                domain=c["domain"],
                baseline_audit_run_id=baseline_audit_run_id,
                current_audit_run_id=current_audit_run_id,
                is_directly_comparable=(not meth_changed and not cov_changed),
                comparability_warnings=warnings,
                comparable_url_overlap_count=overlap,
                methodology_changed=meth_changed,
                coverage_changed=cov_changed,
                connectors_added=added_conns,
                connectors_removed=removed_conns,
                pillar_deltas=pillar_deltas,
                finding_lifecycle={
                    "new": sorted(c_f - b_f),
                    "fixed": sorted(b_f - c_f),
                    "recurring": sorted(b_f & c_f),
                },
            )
        finally:
            conn.close()
