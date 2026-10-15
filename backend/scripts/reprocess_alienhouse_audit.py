"""
Reprocess AlienHouse Networks Audit (run_529ca7cc31)
Applies the upgraded Master SEO Audit Pipeline across all 15 phases:
- Establishes canonical CrawlInventory
- Computes comprehensive DiagnosticInventory
- Compiles PageLevelAssessments
- Reconciles across 12 dimensions with CrossChapterConsistencyEngine
- Enforces 10 publication Quality Gates with ValidationGate
- Renders publication-grade 20-chapter print book HTML and standalone report HTML
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audit.inventory_helper import get_canonical_crawl_inventory
from app.audit.diagnostic_inventory import DiagnosticInventoryEngine
from app.audit.page_analysis import PageLevelAnalysisEngine
from app.audit.consistency_engine import CrossChapterConsistencyEngine
from app.reports.validation_gate import ValidationGate
from app.reports.seo_print_report import seo_print_renderer
from app.reports.seo_report_generator import CompleteSeoReportGenerator
from app.domain.models import ExecutiveReport, CrawlManifest


def reprocess():
    db_path = Path(__file__).resolve().parent.parent / "data" / "dristik_audits.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT analysis_id, domain, raw_report_json FROM audits WHERE analysis_id = 'run_529ca7cc31'")
    row = cur.fetchone()
    if not row:
        print("ERROR: run_529ca7cc31 not found in database!")
        return

    print(f"Loaded audit record: {row['analysis_id']} for domain: {row['domain']}")
    raw_json = json.loads(row["raw_report_json"])

    # Instantiate ExecutiveReport and CrawlManifest
    report = ExecutiveReport.model_validate(raw_json)
    manifest = report.crawl_manifest
    if not manifest and "crawl_manifest" in raw_json:
        manifest = CrawlManifest.model_validate(raw_json["crawl_manifest"])
        report.crawl_manifest = manifest

    pages = getattr(manifest, "pages", []) or getattr(report, "page_reports", [])
    print(f"Audit initial state: Discovered={getattr(manifest, 'total_pages_discovered', None)}, Pages in manifest={len(pages)}")

    # Step 1: Establish authoritative CrawlInventory
    canonical_inv = get_canonical_crawl_inventory(manifest, report)
    print(f"Canonical Crawl Inventory: Discovered={canonical_inv.discovered_total}, Tested={canonical_inv.tested_pages}, Untested={canonical_inv.untested_total}, Coverage={canonical_inv.url_coverage_pct}% (Denominator: {canonical_inv.coverage_denominator})")

    # Step 2: Build Diagnostic Coverage Matrix across all 20 chapters
    report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    print(f"Diagnostic Coverage Matrix built: {report.diagnostic_inventory.total_diagnostics} diagnostics across {len(report.diagnostic_inventory.chapter_breakdown)} chapters.")

    # Step 3: Compile page-level dossiers separating syntax vs Google feature eligibility
    report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    print(f"Page Level Assessments compiled: {len(report.page_level_assessments)} URL dossiers.")

    # Step 4: 12-Dimension Cross-Chapter Reconciliation
    reconciled_report, consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    print(f"Cross-Chapter Consistency Audit: {consistency_report.checks_run} checks performed, {len(consistency_report.contradictions_detected)} contradictions identified and repaired.")
    for repair in consistency_report.reconciled_repairs:
        print(f"  [REPAIR] {repair.get('field')}: {repair.get('reason')}")

    # Step 5: Enforce 10 Publication Quality Gates
    certified_report, gate_result = ValidationGate.enforce_gate(reconciled_report, manifest)
    print(f"\nFinal Certification Status: {certified_report.certification_status}")
    print(f"Overall Score: {certified_report.scores.overall_score:.1f}/100 (Grade: {certified_report.scores.grade}, Label: {certified_report.scores.health_label})")

    qg = ValidationGate.evaluate_quality_gates(certified_report, manifest)
    print("\nQuality Gate Breakdown (Phase 11 10-Gate Evaluation):")
    for gate_name, gate_data in qg.get("gates", {}).items():
        status = gate_data.get("status")
        desc = gate_data.get("description", "")
        passed = gate_data.get("passed")
        print(f"  - [{gate_name.upper()}]: {'PASSED' if passed else status} - {desc}")

    print(f"\n{gate_result.summary()}")

    # Step 6: Persist updated audit to SQLite
    score_val = certified_report.scores.overall_score
    updated_json = certified_report.model_dump_json()
    cur.execute(
        "UPDATE audits SET raw_report_json = ?, score_overall = ? WHERE analysis_id = 'run_529ca7cc31'",
        (updated_json, score_val),
    )
    conn.commit()
    conn.close()
    print("\nPersisted updated audit to SQLite database.")

    # Step 7: Render Reports
    output_dir = Path(__file__).resolve().parent.parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nRendering 20-Chapter Book HTML...")
    book_html = seo_print_renderer.render(certified_report)
    book_path = output_dir / "alienhouse_networks_print_book.html"
    book_path.write_text(book_html, encoding="utf-8")
    print(f"Saved Print Book HTML to: {book_path} ({len(book_html)} bytes)")

    print("Rendering Standalone Interactive HTML Report...")
    generator = CompleteSeoReportGenerator()
    standalone_html = generator.render_html_report(certified_report)
    standalone_path = output_dir / "alienhouse_networks_master_seo_audit.html"
    standalone_path.write_text(standalone_html, encoding="utf-8")
    print(f"Saved Standalone HTML to: {standalone_path} ({len(standalone_html)} bytes)")

    # Also save to conversation artifacts directory
    for art_dir_str in [
        "/Users/sayantande/.gemini/antigravity-ide/brain/b2e34e7c-e4a5-44f1-8065-4c358b8bd3d5",
        "/Users/sayantande/.gemini/antigravity-ide/brain/027bb798-0011-4553-9b14-46ae251bd89b",
    ]:
        art_dir = Path(art_dir_str)
        if art_dir.exists():
            try:
                (art_dir / "alienhouse_networks_print_book.html").write_text(book_html, encoding="utf-8")
                (art_dir / "alienhouse_networks_master_seo_audit.html").write_text(standalone_html, encoding="utf-8")
                print(f"Mirrored reports to conversation artifacts directory: {art_dir}")
            except Exception as e:
                print(f"Notice: Could not write to artifact dir {art_dir}: {e}")

    return {
        "status": certified_report.certification_status,
        "score": certified_report.scores.overall_score,
        "book_path": str(book_path),
        "standalone_path": str(standalone_path),
        "gates": qg.get("gates", {}),
    }


if __name__ == "__main__":
    reprocess()
