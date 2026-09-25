"""
Comprehensive Test Suite for Phase 1: High-Density AI Extractability Engine (Layer 1).
Tests:
1.1 Cross-Page Entity Consistency & Semantic Fragmentation Detector
1.2 Claim & Triple Extraction Pipeline
1.3 Scaled 50-Question Answerability Engine
1.4 Citation-Ready Passage Detector & Rewriter
1.5 Schema ↔ Visible Content Consistency Engine
Integration with evaluate_geo_readiness.
"""
import pytest
from app.domain.models import BusinessProfile, CrawlManifest, PageEvidence
from app.intelligence.geo.entity_consistency import entity_consistency_analyzer, GeoEntityConsistencyAnalyzer
from app.intelligence.geo.claim_extractor import claim_extractor, GeoClaimExtractor
from app.intelligence.geo.question_graph import question_graph_engine, GeoQuestionGraphEngine
from app.intelligence.geo.citation_passages import passage_analyzer, CitationPassageAnalyzer
from app.intelligence.geo.schema_crosscheck import schema_crosschecker, SchemaContentCrosschecker
from app.intelligence.geo.readiness import evaluate_geo_readiness


def test_entity_consistency_fragmentation_detection():
    """
    Tests detection of semantic identity fragmentation when different surface areas
    use conflicting category and brand definitions.
    """
    pages = [
        # Surface 1: Homepage
        PageEvidence(
            url="https://alienhouse.ai/",
            title="AlienHouse Networks | AI Development Company",
            h1=["AlienHouse Networks builds enterprise AI solutions"],
            body_text="AlienHouse Networks is an AI and GenAI development company headquartered in India.",
        ),
        # Surface 2: About page
        PageEvidence(
            url="https://alienhouse.ai/about",
            title="About AlienHouse Solutions",
            h1=["About AlienHouse Solutions"],
            body_text="AlienHouse Solutions is a general software development and IT staffing consultancy.",
        ),
        # Surface 3: Structured Data
        PageEvidence(
            url="https://alienhouse.ai/",
            title="AlienHouse",
            raw_schema=[{
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "AlienHouse IT Agency",
                "description": "Digital marketing and performance advertising agency.",
            }],
        ),
    ]

    analyzer = GeoEntityConsistencyAnalyzer(target_domain="alienhouse.ai")
    res = analyzer.analyze(pages, website_url="https://alienhouse.ai/")

    assert res.surfaces_analyzed_count >= 3
    assert len(res.discrepancies) >= 1
    # Check that fragmentation was detected
    assert res.fragmentation_risk in ["MODERATE", "SEVERE"]
    assert any("brand_name" in d.field or "primary_category" in d.field for d in res.discrepancies)


def test_claims_and_triples_extraction():
    """
    Tests extracting structured triples, distinguishing concrete technical claims
    from marketing fluff, and computing specificity/verifiability scores.
    """
    pages = [
        PageEvidence(
            url="https://alienhouse.ai/services",
            title="Services",
            h1=["Our Core Engineering Deliverables"],
            body_text=(
                "AlienHouse provides FastAPI and PyTorch machine learning applications for Series A startups. "
                "We empower organizations to unlock revolutionary unprecedented growth through cutting-edge synergy. "
                "AlienHouse guarantees 99.99% uptime and maintains SOC 2 Type II compliance. "
                "Plans start at $499/month billed annually."
            ),
        )
    ]

    extractor = GeoClaimExtractor(canonical_brand="AlienHouse")
    res = extractor.extract_claims(pages, brand_name="AlienHouse")

    assert res.total_claims_extracted >= 3
    assert res.citable_claims_count >= 1
    assert res.fluff_claims_count >= 1

    # Check triple extraction
    citable_claim = next((c for c in res.claims if "fastapi" in c.evidence_passage.lower()), None)
    assert citable_claim is not None
    assert citable_claim.machine_citable is True
    assert citable_claim.specificity_score >= 0.70
    assert citable_claim.subject == "AlienHouse"

    # Check fluff claim
    fluff_claim = next((c for c in res.claims if "unprecedented" in c.evidence_passage.lower()), None)
    assert fluff_claim is not None
    assert fluff_claim.is_fluff is True
    assert "unprecedented" in fluff_claim.fluff_terms


def test_scaled_50_question_graph():
    """
    Tests automated generation and evaluation of the 50-question buyer intent graph across 8 categories.
    """
    pages = [
        PageEvidence(
            url="https://alienhouse.ai/",
            title="AlienHouse | Enterprise GenAI Backend Engineering",
            h1=["AlienHouse develops production-ready AI applications"],
            h2=["What We Do", "Target Customers", "Pricing", "Security & Compliance"],
            body_text=(
                "AlienHouse is an AI development company founded by engineering leaders in 2023. "
                "We provide custom REST APIs, FastAPI backends, and LangChain agents. "
                "AlienHouse is built for enterprise engineering teams and VC-backed startups. "
                "Pricing starts at $1,500/month with transparent billing and a 14-day free proof of concept. "
                "AlienHouse is SOC 2 compliant, ISO 27001 certified, and encrypts all customer data with AES-256. "
                "Unlike traditional agencies that take months, AlienHouse deploys in under 2 weeks with a dedicated Slack channel."
            ),
        )
    ]

    engine = GeoQuestionGraphEngine(brand_name="AlienHouse")
    res = engine.evaluate_graph(pages, brand_name="AlienHouse", website_url="https://alienhouse.ai/")

    assert res.total_questions == 50
    assert res.supported_count >= 10
    assert res.answerability_score > 0
    assert "high-intent buyer questions" in res.headline
    assert len(res.category_scores) == 8

    # Verify key categories are represented
    assert "Entity Identity" in res.category_scores
    assert "Core Capabilities & Services" in res.category_scores
    assert "Pricing & Commercial Terms" in res.category_scores
    assert "Security, Trust & Compliance" in res.category_scores
    assert "Comparative & Differentiators" in res.category_scores


def test_citation_passage_detection_and_rewriter():
    """
    Tests detection of citation-ready narrative passages and synthesis of drop-in rewrites.
    """
    pages = [
        PageEvidence(
            url="https://alienhouse.ai/about",
            title="About Us",
            body_text=(
                "AlienHouse Networks develops production-grade FastAPI and PyTorch software solutions for enterprise SaaS companies. "
                "Our engineering team delivers real-time LLM inference pipelines with sub-100ms latency and 99.99% availability.\n\n"
                "We provide cutting-edge revolutionary solutions to empower businesses to seamlessly scale into the future."
            ),
        )
    ]

    analyzer = CitationPassageAnalyzer(brand_name="AlienHouse Networks")
    res = analyzer.analyze(pages, brand_name="AlienHouse Networks")

    assert res.total_passages_scanned >= 1
    assert len(res.passages) >= 1

    # Check that a rewrite was recommended for the fluff passage
    assert len(res.rewrite_recommendations) >= 1
    rewrite = res.rewrite_recommendations[0]
    assert "AlienHouse" in rewrite.recommended_rewrite
    assert len(rewrite.why) > 10


def test_schema_content_crosschecker():
    """
    Tests Schema.org JSON-LD ↔ visible HTML cross-verification.
    """
    pages = [
        PageEvidence(
            url="https://alienhouse.ai/",
            title="AlienHouse Networks",
            h1=["AlienHouse Networks"],
            body_text="AlienHouse Networks offers AI software. Connect on Twitter and LinkedIn. Pricing: $49/mo.",
            external_links=["https://twitter.com/alienhouse", "https://linkedin.com/company/alienhouse"],
            raw_schema=[
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "AlienHouse Networks",
                    "sameAs": [
                        "https://twitter.com/alienhouse",
                        "https://github.com/alienhouse-unlinked"  # Unlinked, should be detected as unmatched
                    ],
                },
                {
                    "@context": "https://schema.org",
                    "@type": "Service",
                    "name": "AI Software",
                }
            ],
            schema_types=["Organization", "Service"],
        )
    ]

    checker = SchemaContentCrosschecker()
    res = checker.crosscheck(pages, brand_name="AlienHouse Networks")

    assert res.total_properties_checked >= 3
    assert res.verified_count >= 2
    # The unlinked github URL should trigger an unmatched check and discrepancy
    assert res.unmatched_count >= 1
    assert any("github.com/alienhouse-unlinked" in d for d in res.discrepancies)
    assert res.grounding_score > 0


def test_full_geo_readiness_integration():
    """
    Tests evaluate_geo_readiness produces full Layer 1 Extractability results.
    """
    pages = [
        PageEvidence(
            url="https://alienhouse.ai/",
            title="AlienHouse CRM | Enterprise Sales Intelligence",
            h1=["AlienHouse CRM provides real-time sales pipelines"],
            h2=["What is AlienHouse", "Pricing Plans", "Security Standards"],
            body_text=(
                "AlienHouse CRM is an AI-powered sales platform for B2B enterprises. "
                "Plans start at $99/month. We comply with SOC 2 Type II and GDPR."
            ),
            schema_types=["Organization", "SoftwareApplication"],
            raw_schema=[{
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "AlienHouse CRM",
            }]
        )
    ]

    report = evaluate_geo_readiness(
        website_url="https://alienhouse.ai/",
        pages=pages,
        manifest=CrawlManifest(
            domain="alienhouse.ai",
            base_url="https://alienhouse.ai",
            pages=pages,
            robots_txt_found=True,
            sitemap_found=True,
        ),
        profile=BusinessProfile(business_name="AlienHouse CRM", industry="CRM software"),
    )

    # Standard backwards compatibility
    assert report.questions_total == 6
    assert report.questions_supported >= 2

    # Layer 1 Extractability Additions
    assert report.extractability_score is not None
    assert 0.0 <= report.extractability_score <= 100.0
    assert report.entity_consistency is not None
    assert report.claims_analysis is not None
    assert report.question_graph_50 is not None
    assert report.question_graph_50["total_questions"] == 50
    assert report.citation_passages is not None
    assert report.schema_crosscheck is not None
