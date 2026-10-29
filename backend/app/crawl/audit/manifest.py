"""
Per-audit run manifest.

A third party can reconstruct why finding X was reported at severity Y on date Z
from this file plus the content-addressed snapshots it references.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.crawl.audit.snapshots import SnapshotStore, artifacts_root
from app.evidence.provenance import sha256_text


class EvidenceTokenPin(BaseModel):
    token: str
    content_sha256: str
    fetched_at: Optional[str] = None
    raw_snapshot_id: Optional[str] = None
    source_type: str
    analyzer: str = ""
    url: Optional[str] = None


class FindingPin(BaseModel):
    finding_id: str
    finding: str
    severity: str
    materiality: Optional[str] = None
    confidence_rubric: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)
    source_agreement: int = 0


class AgentCallPin(BaseModel):
    call_id: str
    agent_id: str
    capability: str
    model: str
    provider: str
    prompt_sha256: str
    prompt_template_sha256: str
    called_at: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None
    cost_basis: str = "unpriced"
    is_actual: bool = False
    actual_cost_usd: Optional[float] = None
    calculated_cost_usd: Optional[float] = None


class RunManifest(BaseModel):
    manifest_id: str
    report_id: str
    analysis_id: str
    website_url: str
    created_at: str
    sealed_at: Optional[str] = None
    app_name: str = "Dristik AI"
    app_version: str = ""
    policy_pack: str = "enterprise_web_intel_v4"
    evidence_graph_snapshot_id: Optional[str] = None
    evidence_tokens: List[EvidenceTokenPin] = Field(default_factory=list)
    api_snapshots: List[str] = Field(default_factory=list)
    agent_calls: List[AgentCallPin] = Field(default_factory=list)
    prompt_library: Dict[str, str] = Field(default_factory=dict)
    findings: List[FindingPin] = Field(default_factory=list)

    def path_for(self, root: Optional[Path] = None) -> Path:
        base = Path(root) if root else artifacts_root()
        return base / self.analysis_id / "manifest.json"


def hash_prompt_library() -> Dict[str, str]:
    prompts_dir = Path(__file__).resolve().parent.parent.parent / "core" / "inference" / "prompts"
    if not prompts_dir.exists():
        prompts_dir = Path(__file__).resolve().parent.parent / "inference" / "prompts"
    out: Dict[str, str] = {}
    if prompts_dir.exists():
        for path in sorted(prompts_dir.glob("*.txt")):
            out[path.name] = sha256_text(path.read_text(encoding="utf-8"))
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    constitution = repo_root / "prompts" / "constitution.md"
    if constitution.exists():
        out["constitution.md"] = sha256_text(constitution.read_text(encoding="utf-8"))
    return out



def build_run_manifest(
    *,
    analysis_id: str,
    website_url: str,
    report_id: Optional[str] = None,
    evidence_store,
    findings=None,
    telemetry=None,
    snapshots: Optional[SnapshotStore] = None,
    evidence_graph_snapshot_id: Optional[str] = None,
    app_version: str = "",
    policy_pack: str = "enterprise_web_intel_v4",
) -> RunManifest:
    report_uuid = report_id or str(uuid4())
    manifest_id = str(uuid4())
    tokens: List[EvidenceTokenPin] = []
    api_snaps: List[str] = []
    if evidence_store:
        for ev in evidence_store.get_all():
            fetched = None
            if ev.fetched_at:
                fetched = ev.fetched_at.isoformat() if hasattr(ev.fetched_at, "isoformat") else str(ev.fetched_at)
            elif ev.timestamp:
                fetched = ev.timestamp.isoformat() if hasattr(ev.timestamp, "isoformat") else str(ev.timestamp)
            tokens.append(EvidenceTokenPin(
                token=ev.id,
                content_sha256=ev.content_sha256 or ev.hash,
                fetched_at=fetched,
                raw_snapshot_id=ev.raw_snapshot_id,
                source_type=ev.source_type,
                analyzer=ev.analyzer or "",
                url=ev.url,
            ))
            if ev.raw_snapshot_id and (ev.id.startswith("ext_") or ev.source_type in {"external", "api"}):
                api_snaps.append(ev.raw_snapshot_id)
    if snapshots:
        for sid in snapshots.list_ids():
            rec = snapshots.get(sid)
            if rec and rec.source_type == "api" and sid not in api_snaps:
                api_snaps.append(sid)

    calls: List[AgentCallPin] = []
    if telemetry is not None:
        for rec in getattr(telemetry, "agent_calls", []) or []:
            calls.append(AgentCallPin(
                call_id=rec.call_id,
                agent_id=rec.agent_id or rec.capability,
                capability=rec.capability,
                model=rec.model,
                provider=rec.provider,
                prompt_sha256=rec.prompt_sha256,
                prompt_template_sha256=rec.prompt_template_sha256,
                called_at=rec.called_at,
                input_tokens=rec.input_tokens,
                output_tokens=rec.output_tokens,
                cost_usd=getattr(rec, "cost_usd", None),
                cost_basis=getattr(rec, "cost_basis", None) or "unpriced",
                is_actual=bool(getattr(rec, "is_actual", False)),
                actual_cost_usd=getattr(rec, "actual_cost_usd", None),
                calculated_cost_usd=getattr(rec, "calculated_cost_usd", None),
            ))

    finding_pins: List[FindingPin] = []
    for f in findings or []:
        finding_pins.append(FindingPin(
            finding_id=f.finding_id,
            finding=getattr(f, "finding", None) or f.title,
            severity=str(f.severity.value if hasattr(f.severity, "value") else f.severity),
            materiality=str(f.materiality.value) if getattr(f, "materiality", None) and hasattr(f.materiality, "value") else None,
            confidence_rubric=str(f.confidence_rubric.value) if getattr(f, "confidence_rubric", None) and hasattr(f.confidence_rubric, "value") else None,
            evidence_refs=list(f.evidence_refs or []),
            source_agreement=int(getattr(f, "source_agreement", 0) or 0),
        ))

    return RunManifest(
        manifest_id=manifest_id,
        report_id=report_uuid,
        analysis_id=analysis_id,
        website_url=website_url,
        created_at=datetime.now(timezone.utc).isoformat(),
        app_version=app_version,
        policy_pack=policy_pack,
        evidence_graph_snapshot_id=evidence_graph_snapshot_id,
        evidence_tokens=tokens,
        api_snapshots=api_snaps,
        agent_calls=calls,
        prompt_library=hash_prompt_library(),
        findings=finding_pins,
    )


def seal_manifest(manifest: RunManifest, snapshots: Optional[SnapshotStore] = None, root: Optional[Path] = None) -> Path:
    manifest.sealed_at = datetime.now(timezone.utc).isoformat()
    path = manifest.path_for(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    if snapshots is not None:
        snapshots.put(
            source="run_manifest",
            body=json.loads(manifest.model_dump_json()),
            source_type="manifest",
            media_type="application/json",
            token_id=manifest.manifest_id,
            fetched_at=manifest.sealed_at,
        )
    return path


def load_manifest(analysis_id: str, root: Optional[Path] = None) -> Optional[RunManifest]:
    base = Path(root) if root else artifacts_root()
    path = base / analysis_id / "manifest.json"
    if not path.exists():
        return None
    return RunManifest.model_validate_json(path.read_text(encoding="utf-8"))
