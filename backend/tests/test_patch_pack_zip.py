"""
Tests for Developer Patch Pack ZIP, Character-Safe Copy, and Notion Block Generator
"""
import io
import zipfile
from app.domain.models import BusinessProfile, CommercialQueryEvaluation
from app.remediation.patch_pack import (
    build_patch_pack_files,
    generate_patch_pack_zip,
    generate_notion_block,
    generate_character_safe_copy,
    generate_whatsapp_summary
)

def test_developer_patch_pack_generation():
    bp = BusinessProfile(
        business_name="FastPay",
        niche="Fintech Infrastructure",
        value_proposition="Low-latency unified payments orchestration for high-volume cross-border platforms.",
        target_audience="Fintech CTOs and payment engineering leads",
        primary_cta="Start Sandbox Integration"
    )
    evals = [
        CommercialQueryEvaluation(
            question_key="identity",
            question_title="Identity & Category",
            buyer_query="What does FastPay do?",
            before_score=6,
            before_answer="FastPay is a payment orchestration gateway.",
            before_evidence_status="VERIFIED",
            after_score=9,
            after_answer="FastPay provides unified payments orchestration with 99.99% uptime."
        )
    ]

    files = build_patch_pack_files(bp, "https://fastpay.io", evals)
    assert "schema.jsonld" in files
    assert "metadata.html" in files
    assert "faq.html" in files
    assert "llms.txt" in files
    assert "robots.txt" in files
    assert "README_DEV_INSTALL.md" in files

    # Verify zip archive creation
    zip_bytes = generate_patch_pack_zip(bp, "https://fastpay.io", evals)
    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "schema.jsonld" in namelist
        assert "llms.txt" in namelist
        assert "robots.txt" in namelist

    # Observed profile text only. A character band is not a grade.
    copy = generate_character_safe_copy(bp, "https://fastpay.io")
    assert copy.title_status == "unjudged"
    assert "FastPay" in copy.title
    assert "Fintech Infrastructure" in copy.title
    assert copy.meta_description.startswith("Low-latency")
    assert "guaranteed" not in (copy.hero_subhead or "").lower()
    assert copy.primary_cta == "Start Sandbox Integration"

    # Verify Notion block
    notion_md = generate_notion_block(bp, "https://fastpay.io", evals)
    assert "FastPay" in notion_md
    assert "metadata.html" in notion_md

    # Verify WhatsApp summary
    wa_summary = generate_whatsapp_summary("fastpay.io", None, "Do not redesign blog footer.", "Pricing opacity", ["Add Schema", "Deploy llms.txt"])
    assert "FASTPAY.IO" in wa_summary
    assert "WHAT TO IGNORE" in wa_summary
