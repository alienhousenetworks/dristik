"""
Integration & Regression Test Suite for Claude SEO Assets & Dristik Integration.
Tests prompts, skills, reference data, specialist agent registry, topological waves,
task cards, ValidationGate deprecation & INP enforcement, and drift analysis.
"""
import pytest
from app.domain.models import ExecutiveReport, Finding, FindingEvidence, CodePatch, CategoryScore, OverallScoreResult
from app.domain.enums import Severity, Category
from app.agents.runtime.registry import SPECIALIST_AGENTS_V3, get_agent_definition
from app.agents.runtime.task_cards import task_card_for, TASK_CARDS
from app.orchestration.agent_pool import topological_waves, AgentPool
from app.reports.validation_gate import ValidationGate
from app.seo.prompts import list_prompts, get_prompt_text
from app.seo.skills import list_skills, get_skill_manifest
from app.seo.reference_data import get_google_updates, get_schema_templates, list_references
from app.seo.audit.drift_analyzer import SeoDriftAnalyzer
from app.seo.audit.schema_validator import validate_jsonld, validate_schema_object


def test_prompts_loaded():
    """Verify all 19 prompt files are accessible and non-empty."""
    prompts = list_prompts()
    assert len(prompts) >= 19
    expected = [
        "seo-technical", "seo-content", "seo-schema", "seo-performance",
        "seo-geo", "seo-agentic", "seo-drift", "seo-ecommerce",
        "seo-sxo", "seo-cluster", "seo-maps", "seo-backlinks"
    ]
    for exp in expected:
        assert exp in prompts or f"{exp}.md" in prompts, f"Missing prompt: {exp}"
        text = get_prompt_text(exp)
        assert text is not None and len(text) > 100, f"Prompt {exp} empty or too short"


def test_skills_loaded():
    """Verify all 26 skills can be discovered and have valid SKILL.md manifests."""
    skills = list_skills()
    assert len(skills) >= 26
    expected_skills = [
        "seo", "seo-agentic", "seo-audit", "seo-cluster", "seo-content",
        "seo-drift", "seo-ecommerce", "seo-geo", "seo-maps", "seo-schema", "seo-sxo"
    ]
    for sk in expected_skills:
        assert sk in skills, f"Missing skill: {sk}"
        manifest = get_skill_manifest(sk)
        assert manifest is not None and len(manifest) > 50, f"Skill {sk} manifest missing or empty"


def test_reference_data_loaded():
    """Verify Google updates and schema reference documents are loaded."""
    updates = get_google_updates()
    assert isinstance(updates, list) and len(updates) > 0
    templates = get_schema_templates()
    assert isinstance(templates, dict)
    refs = list_references()
    assert len(refs) >= 100


def test_specialist_agents_registered():
    """Verify the 6 new Claude SEO agents are properly registered in SPECIALIST_AGENTS_V3."""
    new_agents = [
        "seo.drift.v3",
        "seo.ecommerce.v3",
        "seo.cluster.v3",
        "seo.agentic_readiness.v3",
        "seo.maps_intelligence.v3",
        "seo.sxo.v3",
    ]
    for aid in new_agents:
        assert aid in SPECIALIST_AGENTS_V3, f"Agent {aid} not registered"
        defn = get_agent_definition(aid)
        assert defn.agent_id == aid
        assert defn.domain in ["TECHNICAL_SEO", "STRUCTURED_DATA", "CONTENT", "GEO", "EXPERIENCE"]
        assert len(defn.capabilities) > 0


def test_topological_waves_no_cycles():
    """Verify the Kahn topological sort resolves all agents into waves without cycles."""
    waves = topological_waves(SPECIALIST_AGENTS_V3)
    assert len(waves) >= 4
    all_scheduled = [aid for w in waves for aid in w]
    assert len(all_scheduled) == len(SPECIALIST_AGENTS_V3)
    # Check that dependencies precede children
    scheduled_indices = {aid: idx for idx, aid in enumerate(all_scheduled)}
    for aid, defn in SPECIALIST_AGENTS_V3.items():
        for dep in defn.dependencies:
            if dep in scheduled_indices:
                assert scheduled_indices[dep] < scheduled_indices[aid], f"{dep} must precede {aid}"


def test_task_cards_present():
    """Verify each new agent has a distinct task card with mission details."""
    new_agents = [
        "seo.drift.v3",
        "seo.ecommerce.v3",
        "seo.cluster.v3",
        "seo.agentic_readiness.v3",
        "seo.maps_intelligence.v3",
        "seo.sxo.v3",
    ]
    for aid in new_agents:
        card = task_card_for(aid)
        assert len(card) > 100
        assert aid in card or "TASK CONTRACT" in card


from tests.test_validation_gate import create_sample_report


def test_validation_gate_schema_deprecation_rejection():
    """Verify ValidationGate catches deprecated schema types and unreplaced placeholders."""
    report = create_sample_report()
    report.code_patches = [
        CodePatch(
            patch_id="patch_01",
            title="HowTo schema patch",
            category=Category.SCHEMA,
            target_file="index.html",
            explanation="Add schema",
            after_snippet='<script type="application/ld+json">{"@context":"https://schema.org","@type":"HowTo","name":"How to buy"}</script>'
        )
    ]
    result = ValidationGate.validate_report(report)
    assert not result.is_valid
    assert "schema_no_deprecated_types_or_placeholders" in result.failed_checks


def test_validation_gate_inp_exclusivity():
    """Verify ValidationGate rejects legacy FID and enforces INP exclusively."""
    report = create_sample_report()
    report.story_summary = "Enterprise Platform scores 80/100 (grade A). Audit revealed that First Input Delay (FID) was 320ms on mobile devices."
    report.findings = [
        Finding(
            finding_id="f_fid_01",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Poor FID metric observed",
            description="The page exhibits high FID above 300ms.",
            evidence=[FindingEvidence(url="https://example.com", evidence_type="CWV", description="FID=320ms")]
        )
    ]
    result = ValidationGate.validate_report(report)
    assert not result.is_valid
    assert "inp_exclusive_no_legacy_fid" in result.failed_checks

    # Verify auto-repair replaces FID with INP
    repaired, repairs = ValidationGate.repair_report(report)
    assert any("FID" in r for r in repairs)
    assert "FID" not in repaired.story_summary
    assert "INP" in repaired.story_summary


def test_seo_drift_analyzer():
    """Verify SeoDriftAnalyzer detects schema removal, canonical drift, and INP degradation."""
    baseline = {
        "schema": [{"@context": "https://schema.org", "@type": "Organization", "name": "Acme"}],
        "canonical": "https://acme.org/",
        "robots": "index, follow",
        "h1": "Welcome to Acme Solutions",
        "title": "Acme Solutions - Enterprise Software",
        "inp": 120,
    }
    current = {
        "schema": [],
        "canonical": None,
        "robots": "noindex, follow",
        "h1": [],
        "title": "",
        "inp": 340,
    }
    findings = SeoDriftAnalyzer.compare_page("https://acme.org/", baseline, current)
    assert len(findings) >= 4
    rule_titles = [f.title for f in findings]
    assert any("Structured Data" in t for t in rule_titles)
    assert any("Canonical" in t for t in rule_titles)
    assert any("noindex" in t for t in rule_titles)
    assert any("Interaction to Next Paint" in t for t in rule_titles)


def test_schema_validator_jsonld():
    """Verify schema validator detects deprecated types in raw JSON-LD markup."""
    bad_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "SpecialAnnouncement",
          "name": "Notice"
        }
        </script>
      </head>
    </html>
    """
    errors = validate_jsonld(bad_html)
    assert any("deprecated" in e.lower() for e in errors)
