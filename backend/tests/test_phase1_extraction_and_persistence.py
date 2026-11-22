"""Phase 0.5 (budget caps/flag) & Phase 1 (section extraction, vector metadata, DB persistence) tests."""
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup

from app.core.config import Settings, settings
from app.core.inference.model_router import ModelRouter
from app.core.inference.telemetry import TelemetryTracker
from app.crawl.analyzers.sections import (
    extract_footer_info,
    extract_forms_from_soup,
    extract_nav_items,
    extract_page_sections,
)
from app.crawl.crawler import CrawlerService
from app.crawl.vector_store import VectorStore
from app.db.repository import AuditRepository
from app.domain.enums import ProvenanceType
from app.domain.evidence.store import EvidenceStore
from app.domain.models import PageEvidence


SAMPLE_HTML = """
<!doctype html>
<html lang="en">
<head><title>Acme Cloud — Automated Database Backups</title></head>
<body>
  <header class="site-header">
    <nav id="desktop-nav">
      <a href="/features">Features</a>
      <a href="/pricing">Pricing</a>
      <a href="/demo" class="btn btn-primary">Book a Demo</a>
    </nav>
  </header>
  <main>
    <section id="hero" class="hero-banner">
      <h1>Zero-Downtime Encrypted Backups for Postgres</h1>
      <p>Automated point-in-time recovery across AWS and GCP with 15-second RPO.</p>
      <a href="/signup" class="cta-primary">Start Free Trial</a>
    </section>
    <section id="pricing" class="pricing-grid">
      <h2>Simple Transparent Pricing</h2>
      <table>
        <tr><th>Tier</th><th>Price</th></tr>
        <tr><td>Starter</td><td>$49/mo</td></tr>
        <tr><td>Scale</td><td>$199/mo</td></tr>
      </table>
      <ul>
        <li>Unlimited snapshots</li>
        <li>AES-256 encryption at rest</li>
      </ul>
    </section>
    <section id="faq">
      <h2>Frequently Asked Questions</h2>
      <p>How fast is recovery? Full cluster restores complete in under 4 minutes.</p>
    </section>
    <section id="contact-form">
      <h2>Talk to Engineering</h2>
      <form id="lead-form" action="/api/leads" method="post">
        <label for="email">Work Email</label>
        <input id="email" name="email" type="email" required />
        <input name="company" type="text" placeholder="Company" />
        <button type="submit">Request Architecture Review</button>
      </form>
    </section>
  </main>
  <footer>
    <p>© 2026 Acme Cloud Inc. All rights reserved. Contact hello@acmecloud.io or +1 (415) 555-0192.</p>
    <a href="https://github.com/acmecloud">GitHub</a>
    <a href="https://www.linkedin.com/company/acmecloud">LinkedIn</a>
    <a href="/privacy">Privacy Policy</a>
    <a href="/terms">Terms of Service</a>
  </footer>
</body>
</html>
"""


def test_phase0_5_budget_defaults_and_enforcement_flag(monkeypatch):
    cfg = Settings(_env_file=None)
    assert cfg.ANALYSIS_MAX_COST_USD == 2.50
    assert cfg.ANALYSIS_MAX_MODEL_CALLS == 150
    assert cfg.ENFORCE_HARD_BUDGET_CAP is True

    # Flag disabled -> implicit budget check does not block
    tracker = TelemetryTracker()
    tracker.telemetry.model_calls_count = 999
    router = ModelRouter(telemetry_tracker=tracker)
    monkeypatch.setattr(settings, "ENFORCE_HARD_BUDGET_CAP", False)
    assert router._is_budget_exhausted() is None

    # Explicit constructor override always enforces even if global flag is False
    strict_router = ModelRouter(telemetry_tracker=tracker, max_model_calls=10)
    assert strict_router._is_budget_exhausted() is not None


def test_phase1_structured_section_form_nav_footer_extraction():
    soup = BeautifulSoup(SAMPLE_HTML, "lxml")
    url = "https://acmecloud.io/"

    sections = extract_page_sections(soup, page_url=url)
    assert len(sections) == 4
    roles = [s.section_role for s in sections]
    assert roles[0] == "hero"
    assert "pricing" in roles
    assert "faq" in roles
    assert sections[0].heading_text == "Zero-Downtime Encrypted Backups for Postgres"
    assert "Start Free Trial" in sections[0].ctas
    assert len(sections[1].tables) == 1
    assert len(sections[1].list_items) == 2
    assert all(s.content_sha256 and len(s.content_sha256) == 64 for s in sections)

    forms = extract_forms_from_soup(soup, page_url=url)
    assert len(forms) == 1
    assert forms[0]["input_count"] == 2
    assert forms[0]["required_count"] == 1
    assert forms[0]["missing_label_count"] == 1
    assert "Request Architecture Review" in forms[0]["submit_ctas"]

    nav = extract_nav_items(soup, page_url=url)
    nav_labels = [n["label"] for n in nav]
    assert "Features" in nav_labels
    assert "Pricing" in nav_labels
    assert any(n["label"] == "Book a Demo" and n["is_cta"] is True for n in nav)

    footer = extract_footer_info(soup, page_url=url)
    assert "hello@acmecloud.io" in footer["emails"]
    assert len(footer["phones"]) >= 1
    assert "https://github.com/acmecloud" in footer["social_links"]
    assert "https://www.linkedin.com/company/acmecloud" in footer["social_links"]
    assert any(l["label"] == "Privacy Policy" for l in footer["legal_links"])
    assert "2026 Acme Cloud" in (footer["copyright"] or "")


def test_phase1_flat_dom_heading_fallback():
    flat_html = """
    <html><body><main>
      <h1>Main Platform Overview</h1>
      <p>We automate compliance audits for regulated startups.</p>
      <h2>Security Architecture</h2>
      <p>All customer payloads are encrypted with KMS keys.</p>
    </main></body></html>
    """
    sections = extract_page_sections(BeautifulSoup(flat_html, "lxml"), page_url="https://flat.example/")
    assert len(sections) == 2
    assert sections[0].heading_text == "Main Platform Overview"
    assert sections[1].heading_text == "Security Architecture"
    assert "KMS keys" in sections[1].body_text


def test_phase1_section_aware_chunking_and_vector_store_metadata():
    soup = BeautifulSoup(SAMPLE_HTML, "lxml")
    sections = extract_page_sections(soup, page_url="https://acmecloud.io/")
    page = PageEvidence(
        url="https://acmecloud.io/",
        title="Acme Cloud",
        sections=sections,
        body_text="fallback text",
    )
    chunks = CrawlerService()._chunk_page_sections(page)
    assert len(chunks) == len(sections)
    assert chunks[0]["section_id"] == sections[0].section_id
    assert chunks[0]["section_heading"] == sections[0].heading_text

    with tempfile.TemporaryDirectory() as tmp:
        vs = VectorStore(db_path=str(Path(tmp) / "vec.db"))
        vecs = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
        saved = vs.save_chunks(
            domain="acmecloud.io",
            url=page.url,
            page_type="homepage",
            chunks=[c["text"] for c in chunks],
            vectors=vecs,
            analysis_id="run_phase1",
            chunk_metadata=chunks,
        )
        assert saved == 4
        hits = vs.search_similar([0.0, 1.0, 0.0, 0.0], domain="acmecloud.io", analysis_id="run_phase1", top_k=1)
        assert len(hits) == 1
        assert hits[0]["section_id"] == sections[1].section_id
        assert hits[0]["section_heading"] == "Simple Transparent Pricing"


def test_phase1_evidence_store_section_raw_provenance():
    store = EvidenceStore(run_id="run_ev_p1")
    store.record_fetch("https://acmecloud.io/", SAMPLE_HTML, source="crawler", source_type="http")
    ev = store.add_evidence(
        source_type="page_section",
        analyzer="section_extractor",
        url="https://acmecloud.io/",
        selector="section#pricing",
        text="Simple Transparent Pricing\nStarter $49/mo",
        metadata={"section_id": "sec_02_pricing"},
    )
    assert ev.provenance_type == ProvenanceType.RAW
    assert ev.raw_snapshot_id is not None
    assert len(ev.content_sha256) == 64


def test_phase1_db_persist_and_reload_pages_with_sections_no_collision():
    soup = BeautifulSoup(SAMPLE_HTML, "lxml")
    url = "https://acmecloud.io/"
    page = PageEvidence(
        url=url,
        title="Acme Cloud",
        h1=["Zero-Downtime Encrypted Backups for Postgres"],
        h2=["Simple Transparent Pricing", "Frequently Asked Questions"],
        body_text="Full extracted body text.",
        ctas=["Start Free Trial", "Book a Demo"],
        forms=extract_forms_from_soup(soup, page_url=url),
        nav_items=extract_nav_items(soup, page_url=url),
        footer_info=extract_footer_info(soup, page_url=url),
        sections=extract_page_sections(soup, page_url=url),
        render_mode="playwright_js",
        render_status="playwright_ok",
    )

    with tempfile.TemporaryDirectory() as tmp:
        repo = AuditRepository(db_path=str(Path(tmp) / "audit.db"))
        repo.persist_crawl_pages("run_a", [page])
        repo.persist_crawl_pages("run_b", [page])

        loaded_a = repo.load_crawl_pages("run_a")
        loaded_b = repo.load_crawl_pages("run_b")
        assert len(loaded_a) == 1 and len(loaded_b) == 1
        reloaded = loaded_a[0]
        assert len(reloaded.sections) == 4
        assert len(reloaded.forms) == 1
        assert "Book a Demo" in reloaded.ctas
        assert reloaded.footer_info["emails"] == ["hello@acmecloud.io"]
        assert reloaded.render_status == "playwright_ok"
        assert reloaded.body_text == "Full extracted body text."
