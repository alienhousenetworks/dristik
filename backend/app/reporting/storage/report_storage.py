"""
Dristik AI Progressive Report Storage Engine.
Handles deterministic filesystem storage of sub-phase outputs, JSON contracts,
and immutable rendered PDFs under `data/runs/{run_id}/`.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from app.reporting.contracts.subphase_contract import (
    PhaseReportContract,
    SubPhaseReportContract,
)

logger = logging.getLogger("dristik.reporting.storage")


class ReportStorage:
    def __init__(self, base_dir: str = "data/runs"):
        self.base_dir = Path(base_dir)

    def get_run_dir(self, run_id: str) -> Path:
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def get_phase_dir(self, run_id: str, phase_id: str) -> Path:
        phase_dir = self.get_run_dir(run_id) / phase_id
        phase_dir.mkdir(parents=True, exist_ok=True)
        (phase_dir / "outputs").mkdir(parents=True, exist_ok=True)
        (phase_dir / "reports").mkdir(parents=True, exist_ok=True)
        return phase_dir

    def save_subphase_json(self, contract: SubPhaseReportContract) -> Path:
        """Saves sealed JSON contract atomically."""
        contract.seal()
        phase_dir = self.get_phase_dir(contract.run_id, contract.phase_id)
        clean_sub_id = contract.subphase_id.replace(".", "_")
        target_path = phase_dir / "outputs" / f"subphase_{clean_sub_id}.json"

        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(contract.model_dump(mode="json"), f, indent=2)
        temp_path.replace(target_path)
        logger.info(f"Saved subphase JSON: {target_path} (hash: {contract.content_hash[:8]})")
        return target_path

    def load_subphase_json(self, run_id: str, phase_id: str, subphase_id: str) -> Optional[SubPhaseReportContract]:
        clean_sub_id = subphase_id.replace(".", "_")
        target_path = self.get_phase_dir(run_id, phase_id) / "outputs" / f"subphase_{clean_sub_id}.json"
        if not target_path.exists():
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SubPhaseReportContract(**data)

    def save_subphase_pdf(self, run_id: str, phase_id: str, subphase_id: str, pdf_bytes: bytes, filename_slug: str) -> Path:
        phase_dir = self.get_phase_dir(run_id, phase_id)
        clean_sub_id = subphase_id.replace(".", "_")
        target_path = phase_dir / "reports" / f"subphase_{clean_sub_id}_{filename_slug}.pdf"

        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)
        temp_path.replace(target_path)
        logger.info(f"Saved subphase PDF: {target_path} ({len(pdf_bytes)} bytes)")
        return target_path

    def get_subphase_pdf_path(self, run_id: str, phase_id: str, subphase_id: str) -> Optional[Path]:
        phase_dir = self.get_phase_dir(run_id, phase_id)
        clean_sub_id = subphase_id.replace(".", "_")
        pattern = f"subphase_{clean_sub_id}*.pdf"
        matches = list((phase_dir / "reports").glob(pattern))
        return matches[0] if matches else None

    def save_phase_json(self, contract: PhaseReportContract) -> Path:
        contract.seal()
        phase_dir = self.get_phase_dir(contract.run_id, contract.phase_id)
        target_path = phase_dir / "outputs" / f"{contract.phase_id}_consolidated.json"

        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(contract.model_dump(mode="json"), f, indent=2)
        temp_path.replace(target_path)
        logger.info(f"Saved consolidated phase JSON: {target_path}")
        return target_path

    def load_phase_json(self, run_id: str, phase_id: str) -> Optional[PhaseReportContract]:
        target_path = self.get_phase_dir(run_id, phase_id) / "outputs" / f"{phase_id}_consolidated.json"
        if not target_path.exists():
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PhaseReportContract(**data)

    def save_phase_pdf(self, run_id: str, phase_id: str, pdf_bytes: bytes, filename_slug: str) -> Path:
        phase_dir = self.get_phase_dir(run_id, phase_id)
        target_path = phase_dir / "reports" / f"{phase_id}_{filename_slug}.pdf"

        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)
        temp_path.replace(target_path)
        logger.info(f"Saved consolidated phase PDF: {target_path} ({len(pdf_bytes)} bytes)")
        return target_path

    def get_phase_pdf_path(self, run_id: str, phase_id: str) -> Optional[Path]:
        phase_dir = self.get_phase_dir(run_id, phase_id)
        matches = list((phase_dir / "reports").glob(f"{phase_id}*.pdf"))
        return matches[0] if matches else None


_global_report_storage: Optional[ReportStorage] = None


def get_report_storage() -> ReportStorage:
    global _global_report_storage
    if _global_report_storage is None:
        _global_report_storage = ReportStorage()
    return _global_report_storage
