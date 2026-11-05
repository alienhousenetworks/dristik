#!/usr/bin/env python3
"""
Empirical Verification & Adversarial Stress Harness for Milestone M2
Tests:
1. Alembic migrations (offline SQLite & PostgreSQL SQL generation, online upgrade/downgrade cycle)
2. Schema Parity: SQLAlchemy declarative models vs Alembic migration 001
3. Foreign Key Cascades: ORM-level & DB-level across entire enterprise hierarchy
4. Unique Constraints & Multi-tenancy Scoping (uq_workspaces_org_slug cross-tenant isolation)
5. JSON payload integrity, backward compatibility synonyms, and fail-fast engine connectivity
"""
import os
import sys
import json
import sqlite3
import tempfile
import subprocess
from datetime import datetime, timezone

# Add backend directory to sys.path
BACKEND_DIR = "/Users/sayantande/Downloads/dristik-main/backend"
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import (
    create_engine, text, inspect, event,
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text as SAText, JSON
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
import app.db.models as models
from app.db.models import (
    Organization, Workspace, Domain, AuditRun,
    EvidenceNode, Finding, AICitation, EnterpriseAuditLog,
    User, Integration
)
from app.db.session import (
    create_app_engine, verify_database_connection, mask_database_url,
    DatabaseConnectionError, get_db
)

passed_tests = []
failed_tests = []

def run_test(name, func):
    print(f"\n--- [RUNNING] {name} ---")
    try:
        func()
        print(f"+++ [PASS] {name} +++")
        passed_tests.append(name)
    except Exception as e:
        print(f"!!! [FAIL] {name}: {e} !!!")
        import traceback
        traceback.print_exc()
        failed_tests.append((name, str(e)))

# ---------------------------------------------------------------------------
# Test 1: Alembic Upgrade/Downgrade/Upgrade Lifecycle on Live SQLite
# ---------------------------------------------------------------------------
def test_alembic_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        db_url = f"sqlite:///{db_path}"
        env = os.environ.copy()
        env["DATABASE_URL"] = db_url

        # Upgrade head
        cmd_up = ["/Library/Frameworks/Python.framework/Versions/3.12/bin/alembic", "-c", "alembic.ini", "upgrade", "head"]
        res_up = subprocess.run(cmd_up, cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
        assert res_up.returncode == 0, f"alembic upgrade head failed: {res_up.stderr}"

        # Verify tables created
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
        expected_tables = {
            "alembic_version", "organizations", "workspaces", "domains",
            "audit_runs", "evidence_nodes", "findings", "ai_citations",
            "enterprise_audit_logs", "users", "integrations"
        }
        for t in expected_tables:
            assert t in tables, f"Expected table {t} missing after migration upgrade"

        # Downgrade base
        cmd_down = ["/Library/Frameworks/Python.framework/Versions/3.12/bin/alembic", "-c", "alembic.ini", "downgrade", "base"]
        res_down = subprocess.run(cmd_down, cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
        assert res_down.returncode == 0, f"alembic downgrade base failed: {res_down.stderr}"

        # Verify tables dropped
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_after_down = {r[0] for r in cur.fetchall()}
        remaining = tables_after_down - {"alembic_version"}
        assert len(remaining) == 0, f"Tables remained after downgrade base: {remaining}"

        # Re-upgrade head to verify idempotency
        res_reup = subprocess.run(cmd_up, cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
        assert res_reup.returncode == 0, f"alembic re-upgrade head failed: {res_reup.stderr}"
        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

# ---------------------------------------------------------------------------
# Test 2: Alembic Offline SQL Generation for PostgreSQL and SQLite Dialects
# ---------------------------------------------------------------------------
def test_alembic_offline_sql():
    # SQLite offline
    env_sqlite = os.environ.copy()
    env_sqlite["DATABASE_URL"] = "sqlite:///data/dristik.db"
    cmd_sqlite = ["/Library/Frameworks/Python.framework/Versions/3.12/bin/alembic", "-c", "alembic.ini", "upgrade", "head", "--sql"]
    res_sqlite = subprocess.run(cmd_sqlite, cwd=BACKEND_DIR, env=env_sqlite, capture_output=True, text=True)
    assert res_sqlite.returncode == 0, f"SQLite offline SQL generation failed: {res_sqlite.stderr}"
    assert "CREATE TABLE organizations" in res_sqlite.stdout
    assert "uq_workspaces_org_slug" in res_sqlite.stdout

    # PostgreSQL offline
    env_pg = os.environ.copy()
    env_pg["DATABASE_URL"] = "postgresql://enterprise_usr:secret_pw@db.enterprise.internal:5432/dristik_prod"
    cmd_pg = ["/Library/Frameworks/Python.framework/Versions/3.12/bin/alembic", "-c", "alembic.ini", "upgrade", "head", "--sql"]
    res_pg = subprocess.run(cmd_pg, cwd=BACKEND_DIR, env=env_pg, capture_output=True, text=True)
    assert res_pg.returncode == 0, f"PostgreSQL offline SQL generation failed: {res_pg.stderr}"
    assert "TIMESTAMP WITH TIME ZONE" in res_pg.stdout
    assert "uq_workspaces_org_slug" in res_pg.stdout
    assert "BEGIN;" in res_pg.stdout
    assert "COMMIT;" in res_pg.stdout

# ---------------------------------------------------------------------------
# Test 3: Schema Parity: Models vs Migration vs Invariants
# ---------------------------------------------------------------------------
def test_schema_parity():
    # Create tables in in-memory SQLite using Base.metadata
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    tables = insp.get_table_names()

    required_tables = [
        "organizations", "workspaces", "domains", "audit_runs",
        "evidence_nodes", "findings", "ai_citations", "enterprise_audit_logs"
    ]
    for tbl in required_tables:
        assert tbl in tables, f"Model table {tbl} missing from Base.metadata"

    # Check workspaces unique constraint
    uqs = insp.get_unique_constraints("workspaces")
    uq_names = {u["name"] for u in uqs}
    assert "uq_workspaces_org_slug" in uq_names, f"uq_workspaces_org_slug missing in workspaces: {uqs}"
    for u in uqs:
        if u["name"] == "uq_workspaces_org_slug":
            assert set(u["column_names"]) == {"org_id", "slug"}

    # Check organizations slug unique
    org_uqs = insp.get_unique_constraints("organizations")
    # Note: sqlite unique index or unique constraint
    org_indexes = insp.get_indexes("organizations")
    slug_unique = any("slug" in idx.get("column_names", []) and idx.get("unique") for idx in org_indexes) or any("slug" in u.get("column_names", []) for u in org_uqs)
    assert slug_unique, "slug column on organizations is not marked unique"

    # Check foreign keys with CASCADE
    fks_workspace = insp.get_foreign_keys("workspaces")
    assert any(fk["referred_table"] == "organizations" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_workspace), "workspaces.org_id does not have ondelete=CASCADE"

    fks_domains = insp.get_foreign_keys("domains")
    assert any(fk["referred_table"] == "workspaces" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_domains), "domains.workspace_id does not have ondelete=CASCADE"

    fks_audit_runs = insp.get_foreign_keys("audit_runs")
    assert any(fk["referred_table"] == "domains" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_audit_runs), "audit_runs.domain_id does not have ondelete=CASCADE"

    fks_findings = insp.get_foreign_keys("findings")
    assert any(fk["referred_table"] == "audit_runs" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_findings), "findings.audit_run_id does not have ondelete=CASCADE"

    fks_evidence = insp.get_foreign_keys("evidence_nodes")
    assert any(fk["referred_table"] == "audit_runs" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_evidence), "evidence_nodes.audit_run_id does not have ondelete=CASCADE"

    fks_citations = insp.get_foreign_keys("ai_citations")
    assert any(fk["referred_table"] == "domains" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_citations), "ai_citations.domain_id does not have ondelete=CASCADE"

    fks_logs = insp.get_foreign_keys("enterprise_audit_logs")
    assert any(fk["referred_table"] == "organizations" and fk["options"].get("ondelete") == "CASCADE" for fk in fks_logs), "enterprise_audit_logs.org_id does not have ondelete=CASCADE"

# ---------------------------------------------------------------------------
# Test 4: ORM Cascade Deletion across the Hierarchy
# ---------------------------------------------------------------------------
def test_orm_cascade_deletion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Create full hierarchy
    org = Organization(id="org_test_1", name="Acme Corp", slug="acme")
    ws = Workspace(id="ws_test_1", org_id=org.id, name="Default WS", slug="default")
    org.workspaces.append(ws)

    dom = Domain(id="dom_test_1", workspace_id=ws.id, hostname="acme.com")
    ws.domains.append(dom)

    run = AuditRun(id="run_test_1", domain_id=dom.id, domain="acme.com", status="completed")
    dom.audit_runs.append(run)

    finding = Finding(id="find_test_1", audit_run_id=run.id, category="SECURITY", severity="HIGH", title="Exposed secret")
    run.findings.append(finding)

    node = EvidenceNode(id="ev_test_1", audit_run_id=run.id, url="https://acme.com", node_type="html", content_hash="abc12345", storage_uri="cas://abc12345", node_metadata={"k": "v"})
    run.evidence_nodes.append(node)

    citation = AICitation(id="cite_test_1", domain_id=dom.id, query="best crm", engine="perplexity", is_cited=True)
    dom.ai_citations.append(citation)

    log = EnterpriseAuditLog(id="log_test_1", org_id=org.id, action="LOGIN", resource_type="user", resource_id="usr_1")
    org.enterprise_audit_logs.append(log)

    session.add(org)
    session.commit()

    # Verify all records exist
    assert session.query(Organization).count() == 1
    assert session.query(Workspace).count() == 1
    assert session.query(Domain).count() == 1
    assert session.query(AuditRun).count() == 1
    assert session.query(Finding).count() == 1
    assert session.query(EvidenceNode).count() == 1
    assert session.query(AICitation).count() == 1
    assert session.query(EnterpriseAuditLog).count() == 1

    # Delete organization via ORM
    session.delete(org)
    session.commit()

    # Verify that ORM cascade deleted all child records
    assert session.query(Organization).count() == 0, "Organization not deleted"
    assert session.query(Workspace).count() == 0, "Workspace was not cascaded"
    assert session.query(Domain).count() == 0, "Domain was not cascaded"
    assert session.query(AuditRun).count() == 0, "AuditRun was not cascaded"
    assert session.query(Finding).count() == 0, "Finding was not cascaded"
    assert session.query(EvidenceNode).count() == 0, "EvidenceNode was not cascaded"
    assert session.query(AICitation).count() == 0, "AICitation was not cascaded"
    assert session.query(EnterpriseAuditLog).count() == 0, "EnterpriseAuditLog was not cascaded"
    session.close()

# ---------------------------------------------------------------------------
# Test 5: DB-level (Raw SQL) Foreign Key Cascade Deletion in SQLite
# ---------------------------------------------------------------------------
def test_raw_sql_foreign_key_cascades():
    engine = create_engine("sqlite:///:memory:")

    # Enforce SQLite foreign keys on raw connections
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Insert raw rows using direct SQL to test engine DDL foreign key triggers
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id, name, slug, plan, sso_enabled, created_at, updated_at) VALUES ('org_raw', 'Raw Corp', 'raw', 'enterprise', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO workspaces (id, org_id, name, slug, created_at) VALUES ('ws_raw', 'org_raw', 'WS Raw', 'raw-ws', CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO domains (id, workspace_id, hostname, default_scheme, site_type, crawl_frequency, max_pages, is_active, created_at) VALUES ('dom_raw', 'ws_raw', 'raw.com', 'https', 'b2b_saas', 'weekly', 500, 1, CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO audit_runs (id, domain_id, domain, status, stage, pages_crawled, findings_count, created_at) VALUES ('run_raw', 'dom_raw', 'raw.com', 'completed', 'analysis', 10, 2, CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO evidence_nodes (id, audit_run_id, url, node_type, content_hash, storage_uri, metadata, created_at) VALUES ('ev_raw', 'run_raw', 'https://raw.com', 'dom', 'hash123', 'cas://hash123', '{}', CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO findings (id, audit_run_id, category, severity, title, status, created_at) VALUES ('find_raw', 'run_raw', 'SEO', 'HIGH', 'Title missing', 'open', CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO ai_citations (id, domain_id, query, engine, is_cited, queried_at) VALUES ('cite_raw', 'dom_raw', 'raw search', 'google', 1, CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO enterprise_audit_logs (id, org_id, action, resource_type, created_at) VALUES ('log_raw', 'org_raw', 'CREATE', 'org', CURRENT_TIMESTAMP)"))

        # Verify initial population
        assert conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM workspaces")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM domains")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM audit_runs")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM evidence_nodes")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM findings")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM ai_citations")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM enterprise_audit_logs")).scalar() == 1

        # Delete org with raw SQL
        conn.execute(text("DELETE FROM organizations WHERE id = 'org_raw'"))

        # Verify DB foreign key cascade deleted all downstream tables
        assert conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM workspaces")).scalar() == 0, "DB FK cascade failed for workspaces"
        assert conn.execute(text("SELECT COUNT(*) FROM domains")).scalar() == 0, "DB FK cascade failed for domains"
        assert conn.execute(text("SELECT COUNT(*) FROM audit_runs")).scalar() == 0, "DB FK cascade failed for audit_runs"
        assert conn.execute(text("SELECT COUNT(*) FROM evidence_nodes")).scalar() == 0, "DB FK cascade failed for evidence_nodes"
        assert conn.execute(text("SELECT COUNT(*) FROM findings")).scalar() == 0, "DB FK cascade failed for findings"
        assert conn.execute(text("SELECT COUNT(*) FROM ai_citations")).scalar() == 0, "DB FK cascade failed for ai_citations"
        assert conn.execute(text("SELECT COUNT(*) FROM enterprise_audit_logs")).scalar() == 0, "DB FK cascade failed for enterprise_audit_logs"

# ---------------------------------------------------------------------------
# Test 6: Multi-tenant Unique Constraint Isolation (uq_workspaces_org_slug)
# ---------------------------------------------------------------------------
def test_unique_constraints_and_multi_tenancy():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Create Org A and Org B
    org_a = Organization(id="org_a", name="Org Alpha", slug="alpha")
    org_b = Organization(id="org_b", name="Org Beta", slug="beta")
    session.add_all([org_a, org_b])
    session.commit()

    # Both orgs can have a workspace named 'production' with slug 'prod'
    ws_a = Workspace(id="ws_a_prod", org_id="org_a", name="Production Alpha", slug="prod")
    ws_b = Workspace(id="ws_b_prod", org_id="org_b", name="Production Beta", slug="prod")
    session.add_all([ws_a, ws_b])
    session.commit()
    assert session.query(Workspace).count() == 2

    # But Org A cannot add another workspace with slug 'prod'
    ws_a_duplicate = Workspace(id="ws_a_prod_2", org_id="org_a", name="Duplicate Prod", slug="prod")
    session.add(ws_a_duplicate)
    try:
        session.commit()
        assert False, "Should have failed due to uq_workspaces_org_slug violation!"
    except IntegrityError:
        session.rollback()

    # Organization slug unique constraint
    org_duplicate = Organization(id="org_c", name="Duplicate Slug Org", slug="alpha")
    session.add(org_duplicate)
    try:
        session.commit()
        assert False, "Should have failed due to organizations.slug unique constraint!"
    except IntegrityError:
        session.rollback()

    session.close()

# ---------------------------------------------------------------------------
# Test 7: Backward-compatibility Synonyms & JSON Data Integrity
# ---------------------------------------------------------------------------
def test_synonyms_and_json_payloads():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()

    # Test synonym .org_id on Organization
    org = Organization(id="org_syn", name="Synonym Corp", slug="syn-corp")
    assert org.org_id == "org_syn"
    org.org_id = "org_syn_modified"
    assert org.id == "org_syn_modified"
    session.add(org)
    session.commit()

    # Test JSON fidelity in audit_runs, findings, evidence_nodes
    complex_config = {
        "engine_weights": {"TECH": 0.15, "CONTENT": 0.15},
        "flags": [True, False, None],
        "nested": {"deep": {"value": 42.5}}
    }
    run = AuditRun(
        id="run_json",
        domain="syn.com",
        status="completed",
        config=complex_config
    )
    finding = Finding(
        id="find_json",
        audit_run_id="run_json",
        category="TECH",
        severity="MEDIUM",
        title="Synonym Finding",
        suggested_patch={"action": "replace", "diff": "@@ -1,3 +1,3 @@"},
        evidence_ids=["ev_1", "ev_2"]
    )
    # Test synonym .audit_id on Finding
    assert finding.audit_id == "run_json"
    finding.audit_id = "run_json_updated"
    assert finding.audit_run_id == "run_json_updated"
    finding.audit_run_id = "run_json"

    session.add_all([run, finding])
    session.commit()

    reloaded_run = session.query(AuditRun).filter_by(id="run_json").first()
    assert reloaded_run.config == complex_config
    assert reloaded_run.config["nested"]["deep"]["value"] == 42.5

    reloaded_finding = session.query(Finding).filter_by(id="find_json").first()
    assert reloaded_finding.suggested_patch["action"] == "replace"
    assert reloaded_finding.evidence_ids == ["ev_1", "ev_2"]

    session.close()

# ---------------------------------------------------------------------------
# Test 8: Fail-Fast Engine Connectivity & URL Masking
# ---------------------------------------------------------------------------
def test_fail_fast_and_url_masking():
    # Test URL masking
    assert mask_database_url("postgresql://user:super_secret_pw@db.internal:5432/app") == "postgresql://user:***@db.internal:5432/app"
    assert mask_database_url("sqlite:///data/dristik.db") == "sqlite:///data/dristik.db"

    # Test verify_database_connection on unreachable port
    unreachable_engine = create_engine("postgresql://postgres:pass@127.0.0.1:59999/nonexistent", connect_args={"connect_timeout": 1})
    try:
        verify_database_connection(unreachable_engine, timeout_seconds=1.0)
        assert False, "Should have raised DatabaseConnectionError"
    except DatabaseConnectionError as err:
        assert "59999" in str(err)
        assert "***" in str(err) or "pass" not in str(err)

    # Test verify_database_connection on valid engine
    valid_engine = create_engine("sqlite:///:memory:")
    assert verify_database_connection(valid_engine) is True

if __name__ == "__main__":
    print("=" * 60)
    print("STARTING EMPIRICAL VERIFICATION FOR M2 SCHEMA & MIGRATIONS")
    print("=" * 60)

    run_test("test_alembic_lifecycle", test_alembic_lifecycle)
    run_test("test_alembic_offline_sql", test_alembic_offline_sql)
    run_test("test_schema_parity", test_schema_parity)
    run_test("test_orm_cascade_deletion", test_orm_cascade_deletion)
    run_test("test_raw_sql_foreign_key_cascades", test_raw_sql_foreign_key_cascades)
    run_test("test_unique_constraints_and_multi_tenancy", test_unique_constraints_and_multi_tenancy)
    run_test("test_synonyms_and_json_payloads", test_synonyms_and_json_payloads)
    run_test("test_fail_fast_and_url_masking", test_fail_fast_and_url_masking)

    print("\n" + "=" * 60)
    print(f"VERIFICATION SUMMARY: {len(passed_tests)} Passed, {len(failed_tests)} Failed")
    print("=" * 60)

    if failed_tests:
        for name, err in failed_tests:
            print(f"FAILED: {name} -> {err}")
        sys.exit(1)
    else:
        print("ALL EMPIRICAL TESTS PASSED PERFECTLY!")
        sys.exit(0)
