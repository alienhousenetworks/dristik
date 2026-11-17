"""
Milestone 5 Verification Test Suite:
Enterprise Workflows, Governance & Multi-Industry Regression
Verifies 4 distinct industries (Perfora D2C, CloudOps SaaS, Smile Dental Clinic, AlienHouse IT)
and Enterprise Remediation / Retest History / Governance.
"""
import pytest
from datetime import datetime, timezone
from app.domain.enums import Category, Severity, BusinessIntent, EvidenceState
from app.domain.models import (
    BusinessProfile,
    Finding,
    FindingEvidence,
    CrawlManifest,
    PageEvidence,
    RemediationPatch,
)
from app.domain.scoring.engine import ScoringEngine
from app.geo.readiness import evaluate_geo_readiness
from app.geo.dynamic_sandbox import validate_questions_against_business_context


def test_industry_1_perfora_d2c_oral_care():
    """
    Industry 1: D2C Oral Hygiene (Perfora).
    Ecommerce intent, physical product catalog, multi-tier product pricing without false conflicts,
    Product schema, consumer taxonomy.
    """
    profile = BusinessProfile(
        business_name="Perfora",
        website_url="https://perforacare.com",
        primary_intent=BusinessIntent.ECOMMERCE,
        industry="Personal Care / D2C Oral Hygiene",
        niche="electric toothbrushes, probiotic mouthwash, smart dental accessories",
    )
    pages = [
        PageEvidence(
            url="https://perforacare.com/",
            title="Perfora Clean Oral Care",
            h1=["Clean Oral Care for India"],
            body_text="Smart Sonic Toothbrush at Rs 999. Probiotic Mouthwash at Rs 399.",
            schema_types=["Organization", "Product"],
            raw_schema=[{"@type": "Product", "name": "Toothbrush", "offers": {"price": "999"}}],
        )
    ]
    manifest = CrawlManifest(
        domain="perforacare.com",
        base_url="https://perforacare.com",
        total_pages_discovered=504,
        total_pages_crawled=5,
        robots_txt_found=True,
        sitemap_found=True,
    )

    scores = ScoringEngine().calculate_scores(
        findings=[],
        business_profile=profile,
        manifest=manifest,
        pages=pages,
    )
    assert scores.overall_score is not None
    assert scores.overall_score > 0

    geo = evaluate_geo_readiness(
        website_url="https://perforacare.com",
        pages=pages,
        manifest=manifest,
        profile=profile,
    )
    assert geo.extractability_score is not None
    # Must not have false pricing conflicts for Rs 399 vs Rs 999
    assert geo.questions_conflicting == 0


def test_industry_2_cloudops_b2b_saas():
    """
    Industry 2: B2B SaaS Cloud Infrastructure (Acme Cloud / CloudOps).
    Lead generation intent, SLA / SOC 2 / compliance proof, software features,
    SoftwareApplication / Organization schema.
    """
    profile = BusinessProfile(
        business_name="CloudOps Technologies",
        website_url="https://cloudops.io",
        primary_intent=BusinessIntent.LEAD_GENERATION,
        industry="Enterprise Software / B2B SaaS",
        niche="zero-trust cloud security, edge firewall, continuous deployment",
    )
    pages = [
        PageEvidence(
            url="https://cloudops.io/",
            title="CloudOps | Enterprise Zero Trust Edge Firewall",
            h1=["Next-Gen Cloud Security Platform"],
            body_text=(
                "CloudOps provides zero-trust edge protection for enterprise engineering teams. "
                "SOC 2 Type II certified and ISO 27001 compliant. Pricing starts at $49/month."
            ),
            schema_types=["Organization", "SoftwareApplication"],
            raw_schema=[{"@type": "SoftwareApplication", "name": "CloudOps Gateway"}],
        )
    ]
    manifest = CrawlManifest(
        domain="cloudops.io",
        base_url="https://cloudops.io",
        total_pages_discovered=120,
        total_pages_crawled=5,
        robots_txt_found=True,
        sitemap_found=True,
    )

    scores = ScoringEngine().calculate_scores(
        findings=[],
        business_profile=profile,
        manifest=manifest,
        pages=pages,
    )
    assert scores.overall_score is not None
    assert scores.category_scores[Category.TECHNICAL_SEO.value].score is not None

    geo = evaluate_geo_readiness(
        website_url="https://cloudops.io",
        pages=pages,
        manifest=manifest,
        profile=profile,
    )
    assert geo.extractability_score is not None


def test_industry_3_smile_dental_local_healthcare_clinic():
    """
    Industry 3: Local Healthcare Clinic (Smile Dental Clinic).
    Local appointment booking intent, LocalBusiness schema, Google Business Profile / NAP.
    """
    profile = BusinessProfile(
        business_name="Smile Dental Clinic",
        website_url="https://smiledentalclinic.com",
        primary_intent=BusinessIntent.LOCAL_BUSINESS,
        industry="Healthcare / Local Dental Practice",
        niche="general dentistry, orthodontics, teeth whitening, emergency dental care",
    )
    pages = [
        PageEvidence(
            url="https://smiledentalclinic.com/",
            title="Smile Dental Clinic | Delhi Dental Specialists",
            h1=["Smile Dental Clinic South Delhi"],
            body_text=(
                "Smile Dental Clinic is located at 42 Ring Road, Lajpat Nagar, New Delhi. "
                "Call +91-11-2983-4567 for dental appointments."
            ),
            schema_types=["LocalBusiness", "Dentist"],
            raw_schema=[{
                "@type": "Dentist",
                "name": "Smile Dental Clinic",
                "telephone": "+91-11-2983-4567",
                "address": {"streetAddress": "42 Ring Road", "addressLocality": "New Delhi"},
            }],
        )
    ]
    manifest = CrawlManifest(
        domain="smiledentalclinic.com",
        base_url="https://smiledentalclinic.com",
        total_pages_discovered=15,
        total_pages_crawled=5,
        robots_txt_found=True,
        sitemap_found=True,
    )

    scores = ScoringEngine().calculate_scores(
        findings=[],
        business_profile=profile,
        manifest=manifest,
        pages=pages,
    )
    assert scores.overall_score is not None


def test_industry_4_alienhouse_it_professional_services():
    """
    Industry 4: Professional IT Services & Consulting (AlienHouse Networks).
    Services intent, case studies, quote request CTA, Service / Organization schema.
    """
    profile = BusinessProfile(
        business_name="AlienHouse Networks",
        website_url="https://alienhousenetworks.com",
        primary_intent=BusinessIntent.LEAD_GENERATION,
        industry="IT Services / Cybersecurity Consulting",
        niche="penetration testing, cloud migration, enterprise network architecture",
    )
    pages = [
        PageEvidence(
            url="https://alienhousenetworks.com/",
            title="AlienHouse Networks | Strategic Cybersecurity & Cloud Architecture",
            h1=["Elite Cybersecurity Architecture & Network Defense"],
            body_text=(
                "AlienHouse Networks delivers bespoke penetration testing and secure cloud infrastructure. "
                "Trusted by financial institutions and high-growth technology enterprises."
            ),
            schema_types=["Organization", "ProfessionalService"],
            raw_schema=[{"@type": "ProfessionalService", "name": "AlienHouse Networks"}],
        )
    ]
    manifest = CrawlManifest(
        domain="alienhousenetworks.com",
        base_url="https://alienhousenetworks.com",
        total_pages_discovered=40,
        total_pages_crawled=5,
        robots_txt_found=True,
        sitemap_found=True,
    )

    scores = ScoringEngine().calculate_scores(
        findings=[],
        business_profile=profile,
        manifest=manifest,
        pages=pages,
    )
    assert scores.overall_score is not None


def test_enterprise_remediation_assignment_and_retest_history():
    """
    Enterprise Assurance: Findings and RemediationPatches track:
    - assigned_to (engineer / team role)
    - retest_history (timestamped validation outcomes)
    - verification status transitions
    """
    patch = RemediationPatch(
        patch_id="patch_hsts_001",
        finding_id="find_sec_01",
        category=Category.TECHNICAL_SEO,
        target_file="nginx.conf",
        title="Add Strict-Transport-Security header",
        explanation="Enforces HTTPS connections and disables cleartext downgrades.",
        after_snippet="add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;",
        assignee_id="devops-lead@perforacare.com",
        retest_history=[
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED",
                "notes": "HSTS header missing on staging re-test",
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "PASSED",
                "notes": "Verified max-age=31536000 on production curl test",
            },
        ],
    )

    assert patch.assigned_to == "devops-lead@perforacare.com"
    assert len(patch.retest_history) == 2
    assert patch.retest_history[1]["status"] == "PASSED"
