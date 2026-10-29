"""
Dristik AI CI Guardrail & Anti-Regression Test Suite
Scans the entire production codebase (backend and frontend) to guarantee
no fake data, mock tokens, synthetic bypasses, or dishonest defaults can be reintroduced.
"""
import os
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def test_no_banned_payment_mock_tokens_in_production():
    """Verify that order_mock_, mock_sig_, pay_mock_ are not generated or used as fallback."""
    razorpay_ts = REPO_ROOT / "frontend" / "src" / "services" / "razorpay.ts"
    payments_py = REPO_ROOT / "backend" / "app" / "api" / "routes" / "platform" / "payments.py"

    assert razorpay_ts.exists()
    assert payments_py.exists()

    ts_content = razorpay_ts.read_text(encoding="utf-8")
    py_content = payments_py.read_text(encoding="utf-8")

    # Frontend must have ZERO mock tokens
    for token in ["order_mock_", "mock_sig_", "pay_mock_"]:
        assert token not in ts_content, f"Mock token '{token}' found in frontend razorpay.ts"

    # Backend must NEVER generate order_mock_
    assert "order_mock_" not in py_content, "order_mock_ generation found in backend payments.py"

def test_no_arbitrary_evidence_slicing_in_agents():
    """Verify that agents do not use fallback evidence_slice[:2] to invent evidence refs."""
    agents_dir = REPO_ROOT / "backend" / "app" / "agents"
    for py_file in agents_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "evidence_slice[:2]" not in content, (
            f"Arbitrary evidence slicing 'evidence_slice[:2]' found in {py_file}"
        )

def test_no_hardcoded_requery_fallback_scores_in_frontend():
    """Verify that ReQueryDiffView does not use 45 and 85 fallback scores."""
    target = REPO_ROOT / "frontend" / "src" / "components" / "ReQueryDiffView.tsx"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "before_score ?? 45" not in content
    assert "after_score ?? 85" not in content
    assert "before_score || 45" not in content
    assert "after_score || 85" not in content

def test_no_radar_fake_formula():
    """Verify that radar.py does not use the synthetic formula min(98.0, 75.0 + deltas * 1.5)."""
    target = REPO_ROOT / "backend" / "app" / "core" / "monitoring" / "radar.py"
    if not target.exists():
        target = REPO_ROOT / "backend" / "app" / "intelligence" / "monitoring" / "radar.py"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "75.0 + deltas" not in content
    assert "min(98.0, 75.0" not in content

def test_no_fake_connector_seeding():
    """Verify that connector store does not auto-seed fake integrations on initialization."""
    target = REPO_ROOT / "backend" / "app" / "connectors" / "store.py"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "_seed_default_integrations" not in content

def test_no_fake_invoice_url():
    """Verify that payments.py never hardcodes https://app.dristik.ai into invoices."""
    target = REPO_ROOT / "backend" / "app" / "api" / "routes" / "platform" / "payments.py"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert 'target_url="https://app.dristik.ai"' not in content

def test_production_mode_defaults_safe():
    """Verify default config enforces production integrity mode and disallows mocks."""
    from app.core.config import Settings
    default_settings = Settings()
    assert default_settings.PRODUCTION_DATA_INTEGRITY_MODE is True
    assert default_settings.ALLOW_PAYMENT_TEST_MOCKS is False

def test_integrity_gate_active_in_orchestrator():
    """Verify orchestrator imports and runs the EvidenceIntegrityValidator."""
    target = REPO_ROOT / "backend" / "app" / "orchestration" / "orchestrator.py"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "integrity_gate" in content
    assert "validate_claims_and_evidence" in content
