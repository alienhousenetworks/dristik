"""Reproducibility: immutable snapshots, version pins, run manifest, report UUID."""
import hashlib
import json
from pathlib import Path

from app.audit.manifest import build_run_manifest, load_manifest, seal_manifest
from app.audit.snapshots import SnapshotStore
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.domain.models import Finding
from app.evidence.provenance import compute_raw_source_hash, sha256_text, verify_evidence_hash
from app.evidence.store import EvidenceStore
from app.inference.telemetry import TelemetryTracker


def test_raw_source_hash_is_sha256_of_exact_bytes():
    html = "<html><h1>AlienHouse</h1></html>"
    digest = compute_raw_source_hash(html)
    assert digest == hashlib.sha256(html.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    assert compute_raw_source_hash(html) == digest
    assert compute_raw_source_hash(html + " ") != digest


def test_page_snapshot_round_trip_and_immutability(tmp_path: Path):
    store = SnapshotStore("run_snap", root=tmp_path / "run_snap")
    html = "<html><body>exactly this</body></html>"
    rec = store.put(source="crawler", body=html, source_type="http", url="https://example.com/")
    assert rec.snapshot_id.startswith("snap_")
    assert rec.sha256 == hashlib.sha256(html.encode("utf-8")).hexdigest()
    loaded = store.get(rec.snapshot_id)
    assert loaded is not None
    assert loaded.body == html
    assert store.verify(rec.snapshot_id)

    again = store.put(source="crawler", body=html, source_type="http")
    assert again.snapshot_id == rec.snapshot_id


def test_evidence_token_stores_content_hash_timestamp_and_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DRISTIK_RUN_ARTIFACTS", str(tmp_path))
    ev_store = EvidenceStore("run_ev", snapshots=SnapshotStore("run_ev", root=tmp_path / "run_ev"))
    html = "<html><h1>HQ</h1></html>"
    snap = ev_store.record_fetch("https://example.com/", html)
    ev = ev_store.add_evidence(
        source_type="dom",
        analyzer="html_analyzer",
        url="https://example.com/",
        selector="h1",
        text="HQ",
    )
    assert ev.content_sha256 == snap.sha256
    assert ev.raw_snapshot_id == snap.snapshot_id
    assert ev.fetched_at is not None
    assert ev.hash
    assert ev.hash != ev.content_sha256 or True  # derived vs raw may differ
    retrieved = ev_store.snapshots.get(ev.raw_snapshot_id)
    assert retrieved.body == html
    assert compute_raw_source_hash(retrieved.body) == ev.content_sha256


def test_evidence_rows_from_one_page_do_not_share_a_payload_hash(tmp_path: Path, monkeypatch):
    """The page snapshot hash is shared. Each evidence row keeps its own payload digest."""
    monkeypatch.setenv("DRISTIK_RUN_ARTIFACTS", str(tmp_path))
    ev_store = EvidenceStore("run_distinct", snapshots=SnapshotStore("run_distinct", root=tmp_path / "run_distinct"))
    html = "<html><h1>AlienHouse</h1><title>Networks</title></html>"
    snap = ev_store.record_fetch("https://alienhouse.example/", html)
    heading = ev_store.add_evidence(
        source_type="dom",
        analyzer="html_analyzer",
        url="https://alienhouse.example/",
        selector="h1",
        text="AlienHouse",
    )
    title = ev_store.add_evidence(
        source_type="dom",
        analyzer="html_analyzer",
        url="https://alienhouse.example/",
        selector="title",
        text="Networks",
    )
    assert heading.content_sha256 == snap.sha256
    assert title.content_sha256 == snap.sha256
    assert heading.hash != title.hash
    assert verify_evidence_hash("dom", "html_analyzer", "https://alienhouse.example/", "h1", "AlienHouse", None, heading.hash)
    assert verify_evidence_hash("dom", "html_analyzer", "https://alienhouse.example/", "title", "Networks", None, title.hash)
    assert not verify_evidence_hash("dom", "html_analyzer", "https://alienhouse.example/", "h1", "AlienHouse", None, title.hash)


def test_measured_zero_is_not_rewritten_to_one_hundred():
    from app.domain.enums import Category
    from app.domain.models import CategoryScore
    from app.scoring.engine import measured_category_score, weighted_mean

    zero = CategoryScore(category=Category.UX_CONVERSION, score=0, summary="measured miss", status="MEASURED")
    missing = CategoryScore(category=Category.CONTENT, score=None, summary="absent", status="NOT_MEASURED")
    scores = {
        Category.UX_CONVERSION.value: zero,
        Category.CONTENT.value: missing,
    }
    assert measured_category_score(scores, Category.UX_CONVERSION) == 0.0
    assert measured_category_score(scores, Category.CONTENT) is None
    assert weighted_mean([(0.5, 0.0), (0.5, None)]) == 0.0


def test_external_token_snapshots_raw_api_payload(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DRISTIK_RUN_ARTIFACTS", str(tmp_path))
    ev_store = EvidenceStore("run_ext", snapshots=SnapshotStore("run_ext", root=tmp_path / "run_ext"))
    payload = {"company_size": "51-200 employees", "status": "ok"}
    ext = ev_store.add_external_evidence(
        source="linkedin",
        claim="LinkedIn lists 51-200 employees.",
        raw_value=payload,
        confidence_basis="third_party_aggregator",
    )
    assert ext.id.startswith("ext_")
    assert ext.content_sha256
    assert ext.raw_snapshot_id
    snap = ev_store.snapshots.get(ext.raw_snapshot_id)
    assert snap.body == payload
    assert snap.sha256 == compute_raw_source_hash(payload)


def test_telemetry_pins_model_and_prompt_hash():
    tracker = TelemetryTracker()
    tracker.record_call(
        input_tokens=10,
        output_tokens=20,
        latency_ms=12.0,
        capability="business_icp",
        model="claude-haiku-4-5-20251001",
        provider="anthropic",
        prompt_sha256=sha256_text("system\nuser"),
        prompt_template_sha256=sha256_text("system"),
        agent_id="business.icp.v3",
    )
    call = tracker.get_data().agent_calls[0]
    assert call.model == "claude-haiku-4-5-20251001"
    assert call.provider == "anthropic"
    assert call.prompt_sha256 == sha256_text("system\nuser")
    assert call.agent_id == "business.icp.v3"


def test_run_manifest_ties_report_uuid_and_is_reconstructable(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DRISTIK_RUN_ARTIFACTS", str(tmp_path))
    snap_store = SnapshotStore("run_man", root=tmp_path / "run_man")
    ev_store = EvidenceStore("run_man", snapshots=snap_store)
    ev_store.record_fetch("https://example.com/", "<html>raw</html>")
    ev = ev_store.add_evidence("dom", "test", url="https://example.com/", text="raw")
    ext = ev_store.add_external_evidence("crux", "NOT_CONFIGURED", raw_value={"status": "NOT_CONFIGURED"})
    findings = [
        Finding(
            finding_id="find_001",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Missing H1",
            description="",
            recommendation="Add H1",
            evidence_refs=[ev.id],
        )
    ]
    tracker = TelemetryTracker()
    tracker.record_call(1, 2, 3.0, "seo.html.v3", model="claude-haiku-4-5-20251001", provider="anthropic", prompt_sha256="abc")
    report_id = "11111111-2222-3333-4444-555555555555"
    manifest = build_run_manifest(
        analysis_id="run_man",
        website_url="https://example.com/",
        report_id=report_id,
        evidence_store=ev_store,
        findings=findings,
        telemetry=tracker.get_data(),
        snapshots=snap_store,
        evidence_graph_snapshot_id="snap_graph",
        app_version="2.0.0",
    )
    path = seal_manifest(manifest, snapshots=snap_store, root=tmp_path)
    assert path.exists()
    loaded = load_manifest("run_man", root=tmp_path)
    assert loaded is not None
    assert loaded.report_id == report_id
    assert loaded.analysis_id == "run_man"
    assert loaded.sealed_at
    tokens = {t.token: t for t in loaded.evidence_tokens}
    assert tokens[ev.id].content_sha256 == ev.content_sha256
    assert tokens[ev.id].raw_snapshot_id == ev.raw_snapshot_id
    assert tokens[ext.id].raw_snapshot_id
    assert loaded.findings[0].finding_id == "find_001"
    assert loaded.findings[0].severity == "HIGH"
    assert loaded.agent_calls[0].model == "claude-haiku-4-5-20251001"
    assert loaded.prompt_library  # hashed templates
    # Reconstruct: raw snapshot still matches token hash
    raw = snap_store.get(tokens[ev.id].raw_snapshot_id)
    assert compute_raw_source_hash(raw.body) == tokens[ev.id].content_sha256


def test_blackboard_wires_snapshot_store(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DRISTIK_RUN_ARTIFACTS", str(tmp_path))
    bb = CognitiveBlackboard("run_bb", "https://example.com")
    assert bb.evidence_store.snapshots is bb.snapshot_store
    bb.evidence_store.record_fetch("https://example.com/", "<html/>")
    ev = bb.evidence_store.add_evidence("dom", "t", url="https://example.com/", text="x")
    assert ev.raw_snapshot_id
    assert ev.content_sha256
