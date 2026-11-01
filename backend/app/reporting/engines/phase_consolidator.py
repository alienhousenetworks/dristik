"""
Dristik AI Phase Consolidation Engine.
Aggregates and reconciles completed sub-phase reports into a unified PhaseReportContract,
computing cross-phase hashes and verifying terminal states.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from app.reporting.contracts.subphase_contract import (
    ExecutionStatus,
    PhaseReportContract,
    ReportFinding,
    SubPhaseReportContract,
)

logger = logging.getLogger("dristik.reporting.consolidator")


class PhaseConsolidator:
    """Aggregates subphase reports into a consolidated phase dossier."""

    PHASE_METADATA: Dict[str, Dict[str, str]] = {
        "phase_01_ingestion": {
            "name": "Phase 1: Ingestion & Multi-Page Crawl",
            "summary": "Establishes technical crawlability, SSRF boundary containment, DOM AST extraction, and CAS snapshot integrity.",
        },
        "phase_02_business": {
            "name": "Phase 2: Business Understanding & Entity Grounding",
            "summary": "Synthesizes canonical corporate identity, target ICP buyer personas, search intent taxonomy, and arbitrated commercial profile.",
        },
        "phase_03_pillars": {
            "name": "Phase 3: Four Strategic Pillars (SEO, GEO, AEO, CRO)",
            "summary": "Evaluates technical search engine health, generative AI knowledge footprint, answer engine citability, and UX conversion friction.",
        },
        "phase_04_copywriting": {
            "name": "Phase 4: Copywriting & Page Intelligence",
            "summary": "Audits editorial copy clarity, SERP meta tags, FAQ schema copy, and character-safe hero headlines across key strategic pages.",
        },
        "phase_05_remediation": {
            "name": "Phase 5: Engineering Remediation & Action Roadmaps",
            "summary": "Deduplicates findings into causal root problems, generates drop-in code patch packs, and designs 7/30/90-day execution roadmaps.",
        },
        "phase_06_reporting": {
            "name": "Phase 6: Reporting, Verification & Cryptographic Sealing",
            "summary": "Adversarial cross-examination of specialist findings, honest multi-pillar scoring, C-suite executive briefing, and tamper-evident sealing.",
        },
    }

    @classmethod
    def consolidate_phase(
        cls,
        run_id: str,
        phase_id: str,
        subphase_reports: List[SubPhaseReportContract],
    ) -> PhaseReportContract:
        meta = cls.PHASE_METADATA.get(
            phase_id,
            {"name": phase_id.replace("_", " ").title(), "summary": "Consolidated execution results."},
        )

        subphase_ids = []
        subphase_summaries = {}
        subphase_hashes = {}
        reconciled_findings: List[ReportFinding] = []
        seen_finding_ids = set()
        critical_blockers = []
        unresolved = []
        total_duration = 0

        any_failed = False
        for sub in subphase_reports:
            subphase_ids.append(sub.subphase_id)
            subphase_summaries[f"Sub-Phase {sub.subphase_id}: {sub.subphase_title}"] = f"Status: {sub.status.value} | Findings: {len(sub.findings)}"
            subphase_hashes[sub.subphase_id] = sub.content_hash or sub.compute_hash()
            total_duration += sub.duration_ms

            if sub.status == ExecutionStatus.FAILED:
                any_failed = True

            for f in sub.findings:
                if f.finding_id not in seen_finding_ids:
                    seen_finding_ids.add(f.finding_id)
                    reconciled_findings.append(f)
                    if f.severity.lower() == "critical":
                        critical_blockers.append(f.title)

            for u in sub.unresolved_issues:
                if u not in unresolved:
                    unresolved.append(u)

        phase_contract = PhaseReportContract(
            run_id=run_id,
            phase_id=phase_id,
            phase_name=meta["name"],
            status=ExecutionStatus.FAILED if any_failed else ExecutionStatus.COMPLETED,
            duration_ms=total_duration,
            summary=meta["summary"],
            subphase_ids=subphase_ids,
            subphase_summaries=subphase_summaries,
            reconciled_findings=reconciled_findings,
            critical_blockers=critical_blockers,
            unresolved_conflicts=unresolved,
            passed_to_next_phase={"subphases_count": len(subphase_reports)},
            subphase_hashes=subphase_hashes,
        )
        return phase_contract.seal()
