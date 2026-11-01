"""
Dristik AI Progressive Report Registry.
Maintains in-memory and disk-synchronized registry of all generated sub-phase and
consolidated phase reports, tracking statuses, hashes, and download endpoints.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.reporting.contracts.subphase_contract import (
    ExecutionStatus,
    PhaseReportContract,
    SubPhaseReportContract,
)
from app.reporting.engines.pdf_renderer import ProgressivePDFRenderer
from app.reporting.engines.phase_consolidator import PhaseConsolidator
from app.reporting.storage.report_storage import ReportStorage, get_report_storage

logger = logging.getLogger("dristik.reporting.registry")


class ReportRegistry:
    def __init__(self, storage: Optional[ReportStorage] = None):
        self.storage = storage or get_report_storage()
        # In-memory index: run_id -> dict of subphases / phases
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._subphases_cache: Dict[str, Dict[str, SubPhaseReportContract]] = {}

    def _init_run(self, run_id: str):
        if run_id not in self._registry:
            self._registry[run_id] = {
                "phases": {},
                "subphases": {},
            }
        if run_id not in self._subphases_cache:
            self._subphases_cache[run_id] = {}

    async def register_and_generate_subphase(
        self,
        contract: SubPhaseReportContract,
        filename_slug: str,
        generate_pdf_now: bool = True,
    ) -> Dict[str, Any]:
        """
        Rule: Persist First, Generate Second.
        1. Save JSON contract to disk atomically.
        2. In background or inline, render HTML and compile PDF.
        3. Register entry in registry.
        """
        run_id = contract.run_id
        phase_id = contract.phase_id
        subphase_id = contract.subphase_id
        self._init_run(run_id)

        # 1. Persist JSON source of truth
        json_path = self.storage.save_subphase_json(contract)
        self._subphases_cache[run_id][f"{phase_id}_{subphase_id}"] = contract

        entry = {
            "run_id": run_id,
            "phase_id": phase_id,
            "subphase_id": subphase_id,
            "title": contract.subphase_title,
            "status": contract.status.value,
            "confidence": contract.confidence.value,
            "findings_count": len(contract.findings),
            "content_hash": contract.content_hash,
            "json_path": str(json_path),
            "pdf_ready": False,
            "pdf_path": None,
            "download_url": f"/api/v1/analyses/{run_id}/phases/{phase_id}/subphases/{subphase_id}/pdf",
            "json_url": f"/api/v1/analyses/{run_id}/phases/{phase_id}/subphases/{subphase_id}/json",
        }
        self._registry[run_id]["subphases"][f"{phase_id}_{subphase_id}"] = entry

        # 2. Render PDF if requested
        if generate_pdf_now:
            try:
                html_content = ProgressivePDFRenderer.render_subphase_html(contract)
                pdf_bytes = await ProgressivePDFRenderer.render_pdf(html_content)
                if pdf_bytes:
                    pdf_path = self.storage.save_subphase_pdf(run_id, phase_id, subphase_id, pdf_bytes, filename_slug)
                    entry["pdf_ready"] = True
                    entry["pdf_path"] = str(pdf_path)
                else:
                    logger.warning(f"PDF rendering returned None for subphase {subphase_id}; JSON remains intact.")
            except Exception as e:
                logger.error(f"Failed to generate subphase PDF {subphase_id}: {e}", exc_info=True)

        return entry

    async def consolidate_and_generate_phase(
        self,
        run_id: str,
        phase_id: str,
        filename_slug: str,
        generate_pdf_now: bool = True,
    ) -> Optional[Dict[str, Any]]:
        self._init_run(run_id)
        # Collect all cached subphases for this phase
        prefix = f"{phase_id}_"
        sub_contracts = [
            contract
            for key, contract in self._subphases_cache.get(run_id, {}).items()
            if key.startswith(prefix)
        ]

        if not sub_contracts:
            # Try loading from disk
            phase_dir = self.storage.get_phase_dir(run_id, phase_id)
            for jf in (phase_dir / "outputs").glob("subphase_*.json"):
                try:
                    sub_id = jf.stem.replace("subphase_", "").replace("_", ".")
                    c = self.storage.load_subphase_json(run_id, phase_id, sub_id)
                    if c:
                        sub_contracts.append(c)
                except Exception:
                    pass

        if not sub_contracts:
            logger.warning(f"No subphases found to consolidate for phase {phase_id}")
            return None

        phase_contract = PhaseConsolidator.consolidate_phase(run_id, phase_id, sub_contracts)
        json_path = self.storage.save_phase_json(phase_contract)

        entry = {
            "run_id": run_id,
            "phase_id": phase_id,
            "phase_name": phase_contract.phase_name,
            "status": phase_contract.status.value,
            "subphase_count": len(sub_contracts),
            "reconciled_findings_count": len(phase_contract.reconciled_findings),
            "content_hash": phase_contract.content_hash,
            "json_path": str(json_path),
            "pdf_ready": False,
            "pdf_path": None,
            "download_url": f"/api/v1/analyses/{run_id}/phases/{phase_id}/pdf",
        }
        self._registry[run_id]["phases"][phase_id] = entry

        if generate_pdf_now:
            try:
                html_content = ProgressivePDFRenderer.render_phase_html(phase_contract)
                pdf_bytes = await ProgressivePDFRenderer.render_pdf(html_content)
                if pdf_bytes:
                    pdf_path = self.storage.save_phase_pdf(run_id, phase_id, pdf_bytes, filename_slug)
                    entry["pdf_ready"] = True
                    entry["pdf_path"] = str(pdf_path)
            except Exception as e:
                logger.error(f"Failed to generate consolidated phase PDF {phase_id}: {e}", exc_info=True)

        return entry

    def get_catalog(self, run_id: str) -> Dict[str, Any]:
        self._init_run(run_id)
        # Scan filesystem if registry is empty for this run
        if not self._registry[run_id]["subphases"]:
            self._scan_filesystem_for_run(run_id)

        subphases = list(self._registry[run_id]["subphases"].values())
        phases = list(self._registry[run_id]["phases"].values())

        return {
            "run_id": run_id,
            "total_subphase_reports": len(subphases),
            "ready_subphase_pdfs": sum(1 for s in subphases if s.get("pdf_ready")),
            "total_phase_reports": len(phases),
            "ready_phase_pdfs": sum(1 for p in phases if p.get("pdf_ready")),
            "phases": phases,
            "subphases": subphases,
        }

    def _scan_filesystem_for_run(self, run_id: str):
        run_dir = self.storage.get_run_dir(run_id)
        for phase_dir in run_dir.iterdir():
            if not phase_dir.is_dir() or not phase_dir.name.startswith("phase_"):
                continue
            phase_id = phase_dir.name
            outputs_dir = phase_dir / "outputs"
            reports_dir = phase_dir / "reports"

            if outputs_dir.exists():
                for jf in outputs_dir.glob("subphase_*.json"):
                    try:
                        clean_id = jf.stem.replace("subphase_", "").replace("_", ".")
                        pdf_matches = list(reports_dir.glob(f"subphase_{clean_id.replace('.', '_')}*.pdf")) if reports_dir.exists() else []
                        key = f"{phase_id}_{clean_id}"
                        self._registry[run_id]["subphases"][key] = {
                            "run_id": run_id,
                            "phase_id": phase_id,
                            "subphase_id": clean_id,
                            "title": clean_id,
                            "status": "COMPLETED",
                            "confidence": "VERIFIED",
                            "findings_count": 0,
                            "content_hash": "",
                            "json_path": str(jf),
                            "pdf_ready": len(pdf_matches) > 0,
                            "pdf_path": str(pdf_matches[0]) if pdf_matches else None,
                            "download_url": f"/api/v1/analyses/{run_id}/phases/{phase_id}/subphases/{clean_id}/pdf",
                            "json_url": f"/api/v1/analyses/{run_id}/phases/{phase_id}/subphases/{clean_id}/json",
                        }
                    except Exception:
                        pass


_global_report_registry: Optional[ReportRegistry] = None


def get_report_registry() -> ReportRegistry:
    global _global_report_registry
    if _global_report_registry is None:
        _global_report_registry = ReportRegistry()
    return _global_report_registry
