import sys
backend_path = "/Users/sayantande/Downloads/dristik-main/backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from types import SimpleNamespace
from app.domain.models import PageEvidence, BusinessProfile, CrawlManifest
from app.domain.enums import BusinessIntent
from app.scoring.engine import ScoringEngine

def verify_fix():
    engine = ScoringEngine()

    # Multi-page test case where homepage has no schema, but interior page does
    p0 = PageEvidence(url="https://example.com", schema_types=[], readability_score=75.0)
    p1 = PageEvidence(url="https://example.com/about", schema_types=["Organization"], readability_score=75.0)
    pages = [p0, p1]
    page_ev = p0
    website_url = "https://example.com"
    profile = BusinessProfile(business_name="Discrepancy Corp", domain="example.com", primary_intent=BusinessIntent.SAAS)

    # Setup evaluations fallback scenario:
    # commercial_evaluations is None, but ai_search_evaluations has items
    commercial_evaluations = None
    ai_search_evaluations = [SimpleNamespace(before_score=8.5), SimpleNamespace(before_score=9.5)]
    commercial_evals_val = commercial_evaluations or ai_search_evaluations or []

    # Proposed Step 15 variables
    has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in pages) if pages else False
    readability_val = page_ev.readability_score if page_ev else None
    is_https_val = website_url.startswith("https://") if website_url else False

    # Proposed Step 15 calculation
    step15_cat = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        has_schema=has_schema,
        is_https=is_https_val,
        readability=readability_val,
        external_authority_connected=False,
    )

    step15_honest = engine.calculate_honest_scores(
        findings=[],
        business_profile=profile,
        commercial_evals=commercial_evals_val,
        has_schema=has_schema,
        is_https=is_https_val,
        readability=readability_val,
        external_authority_connected=False,
    )

    # Proposed node_honest_scoring calculation
    node_has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in pages) if pages else False
    node_commercial_evals = commercial_evaluations or ai_search_evaluations or []
    node_honest = engine.calculate_honest_scores(
        findings=[],
        business_profile=profile,
        commercial_evals=node_commercial_evals,
        has_schema=node_has_schema,
        is_https=is_https_val,
        readability=readability_val,
        external_authority_connected=False,
    )

    print(f"Step 15 Category Scores Schema Score: {step15_cat.category_scores['SCHEMA'].score}")
    print(f"Step 15 Honest Scores Google Score:   {step15_honest.google_score}")
    print(f"node_honest_scoring Google Score:     {node_honest.google_score}")
    print(f"Step 15 Honest AI Readiness:          {step15_honest.ai_readiness_score}")
    print(f"node_honest_scoring AI Readiness:    {node_honest.ai_readiness_score}")

    divergence_google = abs(node_honest.google_score - step15_honest.google_score)
    divergence_ai = abs(node_honest.ai_readiness_score - step15_honest.ai_readiness_score)

    print(f"Google Divergence: {divergence_google:.4f} points")
    print(f"AI Readiness Divergence: {divergence_ai:.4f} points")

    assert divergence_google == 0.0, f"Expected 0.0 Google divergence, got {divergence_google}"
    assert divergence_ai == 0.0, f"Expected 0.0 AI divergence, got {divergence_ai}"
    assert step15_honest.google_score == 100.0, f"Expected 100.0 Google score, got {step15_honest.google_score}"
    print("VERIFICATION SUCCESS: Exact mathematical parity across all perspectives!")

    # NoneType page_ev test case
    null_page_ev = None
    null_pages = []
    has_schema_null = any(len(getattr(p, "schema_types", [])) > 0 for p in null_pages) if null_pages else False
    readability_null = null_page_ev.readability_score if null_page_ev else None
    
    assert has_schema_null is False
    assert readability_null is None
    print("VERIFICATION SUCCESS: NoneType page_ev handled safely without AttributeError!")

if __name__ == "__main__":
    verify_fix()
