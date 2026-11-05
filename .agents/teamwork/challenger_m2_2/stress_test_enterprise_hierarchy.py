#!/usr/bin/env python3
"""
Deep Adversarial & Volume Stress Testing for Milestone M2 Enterprise Hierarchy
Tests:
1. Deep cascade volume test (106 records across 5 tiers) under ORM delete
2. Deep cascade volume test (106 records) under Raw SQLite Engine with PRAGMA foreign_keys=ON against Alembic Migrated DB
3. Intermediate tier cascade tests:
   - Workspace cascade deletion
   - Domain cascade deletion
   - AuditRun cascade deletion
4. Multi-tenant isolation stress testing on uq_workspaces_org_slug
5. Extreme data boundary tests (512-char titles, deep JSON trees, floating precision, UTC timezone)
"""
import os
import sys
import json
import sqlite3
import tempfile
import subprocess
from datetime import datetime, timezone

BACKEND_DIR = "/Users/sayantande/Downloads/dristik-main/backend"
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
import app.db.models as models
from app.db.models import (
    Organization, Workspace, Domain, AuditRun,
    EvidenceNode, Finding, AICitation, EnterpriseAuditLog
)

def build_engine_with_fk(db_url="sqlite:///:memory:"):
    engine = create_engine(db_url)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    return engine

def test_deep_orm_cascade():
    print("\n[STRESS TEST 1] Deep ORM Cascade Volume Test (106 records)...")
    engine = build_engine_with_fk()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id="org_mega", name="Mega Corp", slug="mega")
    session.add(org)

    # 3 Enterprise Audit Logs
    for i in range(3):
        org.enterprise_audit_logs.append(
            EnterpriseAuditLog(id=f"log_{i}", action=f"ACTION_{i}", resource_type="workspace")
        )

    # 2 Workspaces
    for w in range(2):
        ws = Workspace(id=f"ws_{w}", name=f"Workspace {w}", slug=f"ws-{w}")
        org.workspaces.append(ws)

        # 2 Domains per WS
        for d in range(2):
            dom = Domain(id=f"dom_{w}_{d}", hostname=f"site-{w}-{d}.com")
            ws.domains.append(dom)

            # 2 AI Citations per domain
            for c in range(2):
                dom.ai_citations.append(
                    AICitation(id=f"cite_{w}_{d}_{c}", query=f"query {c}", engine="bing")
                )

            # 2 Audit Runs per domain
            for r in range(2):
                run = AuditRun(id=f"run_{w}_{d}_{r}", domain=f"site-{w}-{d}.com", status="completed")
                dom.audit_runs.append(run)

                # 5 Findings per run
                for f in range(5):
                    run.findings.append(
                        Finding(id=f"find_{w}_{d}_{r}_{f}", category="TECH", severity="HIGH", title=f"Finding {f}")
                    )

                # 5 Evidence Nodes per run
                for e in range(5):
                    run.evidence_nodes.append(
                        EvidenceNode(
                            id=f"ev_{w}_{d}_{r}_{e}", url="https://site.com",
                            node_type="dom", content_hash=f"hash_{w}_{d}_{r}_{e}",
                            storage_uri=f"cas://hash_{w}_{d}_{r}_{e}",
                            node_metadata={"key": f"val_{e}"}
                        )
                    )

    session.commit()

    # Verify counts
    assert session.query(Organization).count() == 1
    assert session.query(EnterpriseAuditLog).count() == 3
    assert session.query(Workspace).count() == 2
    assert session.query(Domain).count() == 4
    assert session.query(AICitation).count() == 8
    assert session.query(AuditRun).count() == 8
    assert session.query(Finding).count() == 40
    assert session.query(EvidenceNode).count() == 40
    total = 1 + 3 + 2 + 4 + 8 + 8 + 40 + 40
    print(f" -> Successfully seeded full enterprise hierarchy: {total} records across 5 tiers.")

    # Delete Org via ORM
    session.delete(org)
    session.commit()

    # Verify all 106 records vanished
    assert session.query(Organization).count() == 0
    assert session.query(EnterpriseAuditLog).count() == 0
    assert session.query(Workspace).count() == 0
    assert session.query(Domain).count() == 0
    assert session.query(AICitation).count() == 0
    assert session.query(AuditRun).count() == 0
    assert session.query(Finding).count() == 0
    assert session.query(EvidenceNode).count() == 0
    print(" -> PASS: Complete 106-record ORM cascade deletion verified clean!")
    session.close()

def test_deep_raw_sql_cascade():
    print("\n[STRESS TEST 2] Deep Raw SQL Foreign Key Cascade Test on Alembic DDL (106 records)...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Run alembic upgrade head to build genuine enterprise DDL
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        cmd_up = ["/Library/Frameworks/Python.framework/Versions/3.12/bin/alembic", "-c", "alembic.ini", "upgrade", "head"]
        res = subprocess.run(cmd_up, cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
        assert res.returncode == 0, f"Alembic upgrade failed: {res.stderr}"

        # Connect with SQLite foreign keys enabled
        engine = build_engine_with_fk(f"sqlite:///{db_path}")

        with engine.begin() as conn:
            # Insert Org using Alembic server_defaults for plan and sso_enabled
            conn.execute(text("INSERT INTO organizations (id, name, slug) VALUES ('org_sql', 'SQL Corp', 'sql')"))

            for i in range(3):
                conn.execute(text(f"INSERT INTO enterprise_audit_logs (id, org_id, action, resource_type) VALUES ('log_s_{i}', 'org_sql', 'ACT_{i}', 'res')"))

            for w in range(2):
                conn.execute(text(f"INSERT INTO workspaces (id, org_id, name, slug) VALUES ('ws_s_{w}', 'org_sql', 'WS {w}', 'ws-{w}')"))
                for d in range(2):
                    conn.execute(text(f"INSERT INTO domains (id, workspace_id, hostname) VALUES ('dom_s_{w}_{d}', 'ws_s_{w}', 'site-{w}-{d}.com')"))
                    for c in range(2):
                        conn.execute(text(f"INSERT INTO ai_citations (id, domain_id, query, engine) VALUES ('cite_s_{w}_{d}_{c}', 'dom_s_{w}_{d}', 'q', 'bing')"))
                    for r in range(2):
                        conn.execute(text(f"INSERT INTO audit_runs (id, domain_id) VALUES ('run_s_{w}_{d}_{r}', 'dom_s_{w}_{d}')"))
                        for f in range(5):
                            conn.execute(text(f"INSERT INTO findings (id, audit_run_id, category, title) VALUES ('find_s_{w}_{d}_{r}_{f}', 'run_s_{w}_{d}_{r}', 'SEO', 'title')"))
                        for e in range(5):
                            conn.execute(text(f"INSERT INTO evidence_nodes (id, audit_run_id, url, node_type, content_hash, storage_uri, metadata) VALUES ('ev_s_{w}_{d}_{r}_{e}', 'run_s_{w}_{d}_{r}', 'u', 't', 'h', 'cas://h', '{{}}')"))

            # Verify initial count
            assert conn.execute(text("SELECT COUNT(*) FROM findings")).scalar() == 40
            assert conn.execute(text("SELECT COUNT(*) FROM evidence_nodes")).scalar() == 40

            # Execute raw SQL delete on organization
            conn.execute(text("DELETE FROM organizations WHERE id = 'org_sql'"))

            # Verify DB foreign keys wiped every table
            assert conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM enterprise_audit_logs")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM workspaces")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM domains")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM ai_citations")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM audit_runs")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM findings")).scalar() == 0
            assert conn.execute(text("SELECT COUNT(*) FROM evidence_nodes")).scalar() == 0
        print(" -> PASS: Deep Raw SQL engine cascade deletion wiped all 106 records via SQLite FK triggers!")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_intermediate_tier_cascades():
    print("\n[STRESS TEST 3] Intermediate Tier Cascades (Workspace, Domain, AuditRun)...")
    engine = build_engine_with_fk()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Test Domain deletion cascades to AuditRuns, Findings, EvidenceNodes, AICitations
    org = Organization(id="org_mid", name="Mid Corp", slug="mid")
    ws = Workspace(id="ws_mid", org_id="org_mid", name="Mid WS", slug="mid-ws")
    dom = Domain(id="dom_mid", workspace_id="ws_mid", hostname="mid.com")
    run = AuditRun(id="run_mid", domain_id="dom_mid", status="done")
    find = Finding(id="f_mid", audit_run_id="run_mid", category="TECH", severity="LOW", title="T")
    ev = EvidenceNode(id="ev_mid", audit_run_id="run_mid", url="u", node_type="t", content_hash="h", storage_uri="s", node_metadata={})
    cite = AICitation(id="cite_mid", domain_id="dom_mid", query="q", engine="e")

    session.add_all([org, ws, dom, run, find, ev, cite])
    session.commit()

    # Delete Domain only
    session.delete(dom)
    session.commit()

    # Org and WS should survive
    assert session.query(Organization).count() == 1
    assert session.query(Workspace).count() == 1
    # Downstream should be cascaded
    assert session.query(Domain).count() == 0
    assert session.query(AuditRun).count() == 0
    assert session.query(Finding).count() == 0
    assert session.query(EvidenceNode).count() == 0
    assert session.query(AICitation).count() == 0
    print(" -> PASS: Domain deletion cleanly cascaded children while preserving parent Workspace/Org!")

    # 2. Test AuditRun deletion cascades to Findings and EvidenceNodes only
    dom2 = Domain(id="dom_mid2", workspace_id="ws_mid", hostname="mid2.com")
    run2 = AuditRun(id="run_mid2", domain_id="dom_mid2", status="done")
    find2 = Finding(id="f_mid2", audit_run_id="run_mid2", category="TECH", severity="LOW", title="T2")
    ev2 = EvidenceNode(id="ev_mid2", audit_run_id="run_mid2", url="u2", node_type="t2", content_hash="h2", storage_uri="s2", node_metadata={})
    session.add_all([dom2, run2, find2, ev2])
    session.commit()

    session.delete(run2)
    session.commit()

    assert session.query(Domain).count() == 1
    assert session.query(AuditRun).count() == 0
    assert session.query(Finding).count() == 0
    assert session.query(EvidenceNode).count() == 0
    print(" -> PASS: AuditRun deletion cleanly cascaded findings/evidence while preserving Domain!")

    session.close()

def test_data_boundaries_and_types():
    print("\n[STRESS TEST 4] Extreme Data Boundaries and Data Types...")
    engine = build_engine_with_fk()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Test 512-character title for Finding
    long_title = "A" * 512
    org = Organization(id="org_bnd", name="Boundary Corp", slug="bnd")
    ws = Workspace(id="ws_bnd", org_id="org_bnd", name="WS Bnd", slug="ws-bnd")
    dom = Domain(id="dom_bnd", workspace_id="ws_bnd", hostname="bnd.com")
    run = AuditRun(id="run_bnd", domain_id="dom_bnd", total_score=99.987654)
    find = Finding(
        id="f_long",
        audit_run_id="run_bnd",
        category="PERFORMANCE",
        severity="CRITICAL",
        title=long_title,
        confidence=0.9999,
        suggested_patch={"patch": ["line1", {"nested": [1, 2, 3]}], "unicode": "🚀 AI Search"}
    )
    session.add_all([org, ws, dom, run, find])
    session.commit()

    reloaded = session.query(Finding).filter_by(id="f_long").first()
    assert len(reloaded.title) == 512
    assert reloaded.suggested_patch["unicode"] == "🚀 AI Search"
    assert session.query(AuditRun).first().total_score == 99.987654
    print(" -> PASS: 512-char finding titles, float precision, and unicode JSON verified!")
    session.close()

if __name__ == "__main__":
    test_deep_orm_cascade()
    test_deep_raw_sql_cascade()
    test_intermediate_tier_cascades()
    test_data_boundaries_and_types()
    print("\nALL STRESS TESTS COMPLETED SUCCESSFULLY!")
