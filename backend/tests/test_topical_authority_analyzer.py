"""
Unit tests for Topical Authority & Content Quality Analyzer (Information Gain, unbacked claims, cannibalization)
"""
import pytest
from app.domain.models import PageEvidence
from app.seo.analyzers.topical_authority_analyzer import analyze_topical_authority


def test_topical_authority_high_information_gain():
    pages = [
        PageEvidence(
            url="https://analytics-corp.com/benchmarks",
            title="2026 SaaS Retention Benchmarks",
            h1=["2026 SaaS Retention & LTV Benchmark Study"],
            h2=["Key Findings from 1,200 SaaS Companies", "Churn Rate by Pricing Tier", "Methodology"],
            body_text=(
                "In our research analyzing 1,200 SaaS companies, our data shows average net revenue retention of 104%. "
                "Companies with annual billing experienced 32% lower churn compared to monthly billing tiers."
            ),
            content_authority={
                "url": "https://analytics-corp.com/benchmarks",
                "word_count": 850,
                "topical_entities": ["SaaS Retention", "Net Revenue Retention", "Churn Rate", "Annual Billing"],
                "information_gain_score": 85.0,
                "original_data_points": 8,
                "first_party_evidence_markers": ["our research", "our data shows"],
                "expert_signals": ["Dr. Jane Doe, Chief Data Scientist"],
                "unbacked_claims": [],
                "search_intent": "INFORMATIONAL",
                "data_tables_count": 2,
            },
            status_code=200,
        )
    ]

    report, findings = analyze_topical_authority(pages, "analytics-corp.com")
    assert report.status == "PASS"
    assert report.avg_information_gain >= 75.0
    assert report.total_original_data_points == 8
    assert report.unbacked_claims_total == 0
    assert len(report.cannibalization_clusters) == 0


def test_topical_authority_flags_unbacked_claims():
    pages = [
        PageEvidence(
            url="https://fluff-agency.com",
            title="World's Best Agency",
            h1=["The World's Best Marketing Agency"],
            body_text="We are the world's best marketing firm providing industry leading solutions with guaranteed results.",
            content_authority={
                "url": "https://fluff-agency.com",
                "word_count": 300,
                "topical_entities": ["Marketing Agency"],
                "information_gain_score": 25.0,
                "original_data_points": 0,
                "first_party_evidence_markers": [],
                "expert_signals": [],
                "unbacked_claims": ["world's best", "industry leading", "guaranteed results"],
                "search_intent": "INFORMATIONAL",
            },
            status_code=200,
        )
    ]

    report, findings = analyze_topical_authority(pages, "fluff-agency.com")
    assert report.status in ("THIN_COMMODITY", "NEEDS_IMPROVEMENT")
    assert report.unbacked_claims_total == 3

    unbacked_finding = next((f for f in findings if f.finding_id == "content_unbacked_superlative_claims"), None)
    assert unbacked_finding is not None


def test_topical_authority_detects_content_cannibalization():
    shared_text = (
        "Enterprise cloud cybersecurity services provide continuous vulnerability scanning, "
        "automated threat intelligence ingestion, zero trust architecture design, and SOC2 compliance monitoring."
    )
    pages = [
        PageEvidence(
            url="https://cyber.com/cloud-security",
            title="Cloud Cybersecurity Solutions",
            h1=["Enterprise Cloud Cybersecurity Services"],
            body_text=shared_text + " Learn how we protect your modern hybrid cloud infrastructure today.",
            status_code=200,
        ),
        PageEvidence(
            url="https://cyber.com/enterprise-cloud-security",
            title="Enterprise Cloud Security Platform",
            h1=["Enterprise Cloud Cybersecurity Services"],  # Identical H1!
            body_text=shared_text + " Discover our cutting-edge enterprise cloud protection platform.",
            status_code=200,
        ),
    ]

    report, findings = analyze_topical_authority(pages, "cyber.com")
    assert len(report.cannibalization_clusters) >= 1
    cluster = report.cannibalization_clusters[0]
    assert len(cluster.urls) == 2

    cannibal_finding = next((f for f in findings if f.finding_id == "content_cannibalization_clusters"), None)
    assert cannibal_finding is not None
    assert cannibal_finding.severity.value in ("HIGH", "CRITICAL")
