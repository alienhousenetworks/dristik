"""Tests for Phase 2: Enterprise Agentic Remediation Pack & Verification Sandbox."""
import io
import json
import zipfile

from app.domain.models import BusinessProfile, CodePatch, Finding
from app.domain.enums import Category, Severity
from app.remediation.patch_pack import build_patch_pack_files, generate_patch_pack_zip


def _sample_bp() -> BusinessProfile:
    return BusinessProfile(
        business_name="Acme Cloud",
        niche="Cloud Observability",
        target_audience="Platform Engineering Teams",
        value_proposition="Sub-second distributed tracing without sampling.",
        primary_cta="Start Free Trial",
    )


def _sample_findings():
    return [
        Finding(
            finding_id="f_001",
            title="Missing canonical tag on /pricing",
            category=Category.TECHNICAL_SEO,
            severity=Severity.CRITICAL,
            description="Canonical link tag is absent on /pricing.",
            why_it_matters="Search engines may split ranking signals across UTM variants.",
            recommendation="Add <link rel='canonical' href='https://acme.io/pricing' />.",
            affected_urls=["https://acme.io/pricing"],
            evidence_refs=["ev_012"],
        )
    ]


def _sample_code_patches():
    return [
        CodePatch(
            patch_id="p_001",
            title="Add canonical link to /pricing",
            category=Category.TECHNICAL_SEO,
            target_file="app/pricing/page.tsx",
            before_snippet="<head><title>Pricing</title></head>",
            after_snippet="<head><title>Pricing</title><link rel='canonical' href='https://acme.io/pricing' /></head>",
            explanation="Prevents duplicate URL indexing.",
        )
    ]


def test_patch_pack_includes_unified_diff_framework_adapter_backlog_and_verification():
    files = build_patch_pack_files(
        bp=_sample_bp(),
        website_url="https://acme.io",
        commercial_evals=[],
        findings=_sample_findings(),
        code_patches=_sample_code_patches(),
        tech_stack={"primary_framework": "nextjs"},
    )
    assert "patches/unified.diff" in files
    assert "--- a/app/pricing/page.tsx" in files["patches/unified.diff"]
    assert "+++ b/app/pricing/page.tsx" in files["patches/unified.diff"]
    assert "patches/nextjs_metadata_layout.tsx" in files
    assert "export const metadata: Metadata" in files["patches/nextjs_metadata_layout.tsx"]

    backlog = json.loads(files["exports/jira_linear_backlog.json"])
    assert backlog["total_tickets"] == 1
    assert backlog["tickets"][0]["priority"] == "P0"
    assert backlog["tickets"][0]["evidence_refs"] == ["ev_012"]

    verification = json.loads(files["VERIFICATION_REPORT.json"])
    assert verification["overall_status"] == "VERIFIED_SYNTAX_PASS"


def test_patch_pack_zip_contains_all_verified_artifacts():
    raw_zip = generate_patch_pack_zip(
        bp=_sample_bp(),
        website_url="https://acme.io",
        commercial_evals=[],
        findings=_sample_findings(),
        code_patches=_sample_code_patches(),
        tech_stack={"primary_framework": "wordpress"},
    )
    with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
        names = set(zf.namelist())
        assert "patches/unified.diff" in names
        assert "patches/wordpress_dristik_seo.php" in names
        assert "exports/jira_linear_backlog.json" in names
        assert "VERIFICATION_REPORT.json" in names
