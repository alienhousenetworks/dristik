"""
Unit tests for Dristik's Enterprise CRO & Conversion Intelligence Analyzer.
Tests:
1. CTA classification (HIGH_INTENT, EXPLORATORY, PASSIVE_GENERIC) & rewrite suggestions
2. 5-second hook & hero value proposition clarity
3. Social proof detection (testimonials, client logos, quantified ROI claims, trust badges)
4. Pricing psychology (tiers, billing toggle, risk reversal)
5. Grounded Finding generation in Category.UX_CONVERSION
"""
import pytest
from app.domain.models import PageEvidence, BusinessProfile
from app.domain.enums import Category, Severity
from app.analyzers.cro_analyzer import CroAnalyzer, analyze_cro
from app.agents.runtime.reasoners import CroExperienceReasonerAgent


def test_cro_analyzer_cta_classification_and_rewrites():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test App</title></head>
    <body>
        <div class="hero">
            <h1>Scale Your Enterprise Revenue With AI</h1>
            <button class="btn btn-primary">Start Free Trial</button>
            <a href="/pricing" class="btn btn-secondary">View Pricing</a>
        </div>
        <div class="contact">
            <button class="btn">Submit</button>
            <a href="/about" class="btn">Click Here</a>
        </div>
    </body>
    </html>
    """
    page = PageEvidence(
        url="https://example.com",
        title="Test App",
        h1=["Scale Your Enterprise Revenue With AI"],
        word_count=250,
        raw_html=html
    )

    report, findings = analyze_cro([page], raw_html_map={page.url: html})

    assert report.cta_analysis.total_ctas_detected >= 4
    assert report.cta_analysis.high_intent_count >= 1
    assert report.cta_analysis.exploratory_count >= 1
    assert report.cta_analysis.passive_generic_count >= 2
    assert report.cta_analysis.has_hero_cta is True

    # Check that passive CTAs have rewrite suggestions
    passive_items = [c for c in report.cta_analysis.ctas if c.is_passive_friction]
    assert len(passive_items) >= 2
    submit_item = next((c for c in passive_items if c.cta_text.lower() == "submit"), None)
    assert submit_item is not None
    assert submit_item.suggested_rewrite is not None


def test_cro_analyzer_social_proof_and_trust_badges():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>SaaS Product</title></head>
    <body>
        <h1>Enterprise Security Platform</h1>
        <div class="client-logos">
            <img src="/logo1.png" alt="Acme Corp logo" />
            <img src="/logo2.png" alt="Globex partner logo" />
        </div>
        <div class="testimonial">
            <blockquote>"Saved $120,000 in infrastructure costs with a 45% lift in deployment velocity." - Jane Doe, CTO</blockquote>
        </div>
        <footer>
            <p>SOC 2 Type II Certified | 30-Day Money-Back Guarantee</p>
            <a href="https://example.com/privacy">Privacy Policy</a>
            <a href="https://example.com/terms">Terms of Service</a>
        </footer>
    </body>
    </html>
    """
    page = PageEvidence(
        url="https://example.com",
        title="SaaS Product",
        h1=["Enterprise Security Platform"],
        word_count=300,
        raw_html=html
    )

    report, _ = analyze_cro([page], raw_html_map={page.url: html})

    assert report.social_proof.client_logos_detected >= 2
    assert report.social_proof.total_testimonials >= 1
    assert len(report.social_proof.quantified_proof_claims) >= 1
    assert any("45%" in q for q in report.social_proof.quantified_proof_claims)
    assert report.social_proof.has_privacy_policy is True
    assert report.social_proof.has_terms_of_service is True
    assert len(report.social_proof.trust_badges_detected) >= 2
    assert report.social_proof.trust_authority_score >= 70.0


def test_cro_analyzer_pricing_psychology_and_toggles():
    pricing_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Pricing - Test SaaS</title></head>
    <body>
        <h1>Simple, Transparent Pricing</h1>
        <div class="billing-cycle">
            <span class="toggle">Annual Billing (Save 20%)</span>
        </div>
        <div class="pricing-card">
            <h3>Starter</h3>
            <p>$29/mo</p>
        </div>
        <div class="pricing-card">
            <h3>Enterprise</h3>
            <p>Custom</p>
        </div>
        <p>No credit card required. Cancel anytime.</p>
    </body>
    </html>
    """
    home_page = PageEvidence(url="https://example.com", title="Home", h1=["Home"], word_count=100)
    pricing_page = PageEvidence(
        url="https://example.com/pricing",
        title="Pricing - Test SaaS",
        h1=["Simple, Transparent Pricing"],
        word_count=200,
        raw_html=pricing_html
    )

    report, _ = analyze_cro([home_page, pricing_page], raw_html_map={pricing_page.url: pricing_html})

    assert report.pricing_psychology.pricing_page_detected is True
    assert report.pricing_psychology.detected_tiers_count >= 2
    assert report.pricing_psychology.has_billing_toggle is True
    assert report.pricing_psychology.has_free_trial is True


def test_cro_analyzer_generates_grounded_findings():
    # Page with passive CTA and missing social proof
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Welcome to our generic service</h1>
        <button>Submit</button>
    </body>
    </html>
    """
    page = PageEvidence(
        url="https://example.com",
        title="Generic Service",
        h1=["Welcome to our generic service"],
        word_count=150,
        raw_html=html
    )

    report, findings = analyze_cro([page], raw_html_map={page.url: html})

    assert len(findings) >= 2
    ux_cats = [f.category for f in findings]
    assert all(cat == Category.UX_CONVERSION for cat in ux_cats)

    # Passive CTA finding
    passive_finding = next((f for f in findings if "Passive" in f.title), None)
    assert passive_finding is not None
    assert passive_finding.severity == Severity.MEDIUM
    assert len(passive_finding.evidence) > 0


@pytest.mark.asyncio
async def test_cro_experience_reasoner_passive_cta():
    reasoner = CroExperienceReasonerAgent()
    class _MockPage:
        def __init__(self):
            self.url = "https://example.com"
            self.viewport = "width=device-width"
            self.word_count = 200
            self.ctas = ["Submit", "Learn more"]
            self.forms = []

    findings = await reasoner.reason(manifest=None, pages=[_MockPage()])
    passive_f = next((f for f in findings if "Passive CTA Microcopy" in f.title), None)
    assert passive_f is not None
    assert passive_f.category == Category.UX_CONVERSION
