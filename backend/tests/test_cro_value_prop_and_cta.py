"""
Tests for Phase 6.3 & 6.4: Value Proposition Intelligence & CTA Intelligence.
"""
import pytest
from app.domain.models import PageEvidence
from app.cro.value_prop_analyzer import ValuePropAnalyzer
from app.cro.analyzer import CroAnalyzer


def test_value_prop_evaluates_all_6_buyer_questions():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Apex Software | Enterprise AI</title></head>
    <body>
        <div class="hero">
            <h1>Automate Enterprise Revenue with AI Software Platform</h1>
            <p>Designed specifically for engineering teams to eliminate deployment friction.</p>
            <button class="btn btn-primary">Start Free Trial</button>
        </div>
        <div class="proof">
            <p>SOC 2 Type II Certified · 45% deployment lift for 5,000 users</p>
        </div>
    </body>
    </html>
    """
    p = PageEvidence(
        url="https://example.com/",
        title="Apex Software",
        h1=["Automate Enterprise Revenue with AI Software Platform"],
        word_count=150,
        raw_html=html,
    )
    res = ValuePropAnalyzer.analyze([p], raw_html_map={p.url: html})

    assert len(res.buyer_questions) == 6
    assert len(res.dimensions) == 10

    # Check that Q1 (What is being sold) and Q2 (Who is it for) are answered
    q1 = next(q for q in res.buyer_questions if q.question_number == 1)
    q2 = next(q for q in res.buyer_questions if q.question_number == 2)
    q3 = next(q for q in res.buyer_questions if q.question_number == 3)
    q5 = next(q for q in res.buyer_questions if q.question_number == 5)
    q6 = next(q for q in res.buyer_questions if q.question_number == 6)

    assert q1.answered is True
    assert q2.answered is True
    assert q3.answered is True
    assert q5.answered is True
    assert q6.answered is True
    assert res.overall_value_prop_score >= 70.0


def test_cta_intelligence_detects_contrast_and_intent():
    html = """
    <html><body>
      <div class="hero">
        <h1>Transform Your Growth</h1>
        <button class="btn btn-primary">Get Started Now</button>
      </div>
      <a href="/docs" class="btn">Learn more</a>
    </body></html>
    """
    p = PageEvidence(url="https://example.com/", title="Test", word_count=50, raw_html=html)
    rep, findings = CroAnalyzer.analyze_cro([p], raw_html_map={p.url: html})

    assert rep.cta_analysis.total_ctas_detected >= 2
    assert rep.cta_analysis.high_intent_count >= 1
    assert rep.cta_analysis.passive_generic_count >= 1
    assert rep.cta_analysis.has_hero_cta is True
    assert rep.intelligence["value_prop_intelligence"] is not None
    assert rep.intelligence["journey_graph"] is not None
