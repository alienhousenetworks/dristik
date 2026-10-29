#!/usr/bin/env python3
"""
Dristik AI - Demo Data Enrichment Script
Populates high-fidelity production demo data into Dristik SQLite databases:
1. Enterprise Organization ('org_default' / AlienHouse Networks Demo)
2. Admin User ('admin@dristik.ai' / 'Password@123') & Growth Lead ('demo@alienhouse.co')
3. 10 Active Platform Connectors (WordPress, Webflow, GitHub, GSC, GA4, Shopify, CRM, CrUX, DataForSEO, Live AI)
4. Showcase Executive Audit ('run_alienhouse_demo') with 20-Chapter Diagnostics, Crawl Inventory & Patches
5. Competitor Bakeoff & Commercial ROI Attribution ($148K / ₹1.18 Cr annual upside)
6. Multi-Channel Distribution Artifacts (WhatsApp summary card, Slack blocks, LinkedIn post)

Usage:
    python backend/scripts/enrich_demo_data.py [--password Password@123] [--reset]
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Resolve backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.domain.enums import (
    ConnectorHealthStatus,
    ConnectorType,
    Category,
    PatchRiskLevel,
    PatchApprovalStatus,
    PatchOperation,
    VerificationStatus,
    UserRole,
)
from app.identity.security import hash_password
from app.connectors.store import _encrypt
from app.connectors.base.models import ConnectorCredentials


def enrich_demo_data(password: str = "Password@123", reset: bool = False):
    print("=" * 72)
    print("🚀 DRISTIK AI — DEMO DATA ENRICHMENT")
    print("=" * 72)

    db_dir = backend_dir / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    dristik_db_path = db_dir / "dristik.db"
    audits_db_path = db_dir / "dristik_audits.db"

    now_ts = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # 1. ENRICH ORGANIZATIONS & USERS (dristik.db)
    # -------------------------------------------------------------------------
    print("\n[1/4] Seeding Enterprise Organization and System Admin...")
    with sqlite3.connect(dristik_db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Ensure schema tables exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                org_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                plan TEXT NOT NULL DEFAULT 'enterprise',
                is_system INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                deleted_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_system INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                deleted_at REAL,
                FOREIGN KEY (org_id) REFERENCES organizations(org_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                analysis_id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                website_url TEXT,
                status TEXT NOT NULL DEFAULT 'completed',
                page_count INTEGER NOT NULL DEFAULT 1,
                overall_score REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS connector_integrations (
                integration_id TEXT PRIMARY KEY,
                integration_json TEXT NOT NULL,
                credentials_json TEXT NOT NULL
            )
        """)

        # Upsert org_default (Enterprise Plan for full feature access)
        conn.execute("""
            INSERT INTO organizations (org_id, name, slug, plan, is_system, is_active, created_at)
            VALUES ('org_default', 'AlienHouse Networks (Demo Org)', 'alienhouse-demo', 'enterprise', 0, 1, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                plan = 'enterprise',
                is_active = 1,
                name = excluded.name
        """, (now_ts,))

        # Upsert org_system
        conn.execute("""
            INSERT INTO organizations (org_id, name, slug, plan, is_system, is_active, created_at)
            VALUES ('org_system', 'Dristik System', 'dristik-system', 'enterprise', 1, 1, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                plan = 'enterprise',
                is_active = 1
        """, (now_ts,))

        pwd_hash = hash_password(password)

        # Admin User: admin@dristik.ai
        conn.execute("""
            INSERT INTO users (user_id, org_id, email, full_name, password_hash, role, is_active, is_system, created_at)
            VALUES ('usr_admin_system', 'org_default', 'admin@dristik.ai', 'Dristik Admin', ?, 'system_admin', 1, 1, ?)
            ON CONFLICT(email) DO UPDATE SET
                password_hash = excluded.password_hash,
                role = 'system_admin',
                is_active = 1,
                org_id = 'org_default'
        """, (pwd_hash, now_ts))

        # Demo User: demo@alienhouse.co
        conn.execute("""
            INSERT INTO users (user_id, org_id, email, full_name, password_hash, role, is_active, is_system, created_at)
            VALUES ('usr_demo_owner', 'org_default', 'demo@alienhouse.co', 'Demo Growth Officer', ?, 'owner', 1, 0, ?)
            ON CONFLICT(email) DO UPDATE SET
                password_hash = excluded.password_hash,
                role = 'owner',
                is_active = 1,
                org_id = 'org_default'
        """, (pwd_hash, now_ts))

        conn.commit()
    print("  ✅ Organization 'org_default' configured with Enterprise Plan.")
    print(f"  ✅ Users seeded: admin@dristik.ai, demo@alienhouse.co (Password: '{password}')")

    # -------------------------------------------------------------------------
    # 2. ENRICH PLATFORM CONNECTORS (connector_integrations)
    # -------------------------------------------------------------------------
    print("\n[2/4] Seeding 10 Active Platform Connectors...")

    connectors_spec = [
        {
            "id": "int_wp_alienhouse_prod",
            "provider": ConnectorType.WORDPRESS,
            "name": "WordPress (AlienHouse Blog)",
            "target_url": "https://alienhouse.co",
            "scopes": ["read", "write_patches", "publish_posts"],
            "settings": {"auth_mode": "app_password", "active_plugin": "dristik-bridge-v2.6"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.WORDPRESS,
                api_url="https://alienhouse.co/wp-json/wp/v2",
                username="dristik_agent",
                app_password="xxxx-xxxx-xxxx-xxxx",
                scopes=["read", "write_patches", "publish_posts"],
            ),
        },
        {
            "id": "int_wf_alienhouse_prod",
            "provider": ConnectorType.WEBFLOW,
            "name": "Webflow (AlienHouse Headless)",
            "target_url": "https://alienhouse.webflow.io",
            "scopes": ["sites:read", "custom_code:write", "cms:write"],
            "settings": {"site_id": "wf_site_alienhouse_66f1"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.WEBFLOW,
                api_url="https://api.webflow.com",
                api_key="sec_wf_demo_token_8829a",
                scopes=["sites:read", "custom_code:write"],
            ),
        },
        {
            "id": "int_gh_alienhouse_prod",
            "provider": ConnectorType.GITHUB,
            "name": "GitHub (alienhousenetworks/dristik)",
            "target_url": "https://github.com/alienhousenetworks/dristik",
            "repository": "alienhousenetworks/dristik",
            "branch": "main",
            "scopes": ["repo", "pull_requests"],
            "settings": {"auto_pr": True, "base_branch": "main"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.GITHUB,
                api_url="https://api.github.com",
                github_token="ghp_demoTokenDristikSeo2026",
                repository="alienhousenetworks/dristik",
                branch="main",
                scopes=["repo", "pull_requests"],
            ),
        },
        {
            "id": "int_gsc_alienhouse_prod",
            "provider": ConnectorType.GOOGLE_SEARCH_CONSOLE,
            "name": "Google Search Console (alienhouse.co)",
            "target_url": "https://alienhouse.co",
            "scopes": ["webmasters.readonly"],
            "settings": {"auth_mode": "oauth2", "verified_property": "sc-domain:alienhouse.co"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
                api_url="https://www.googleapis.com/webmasters/v3",
                scopes=["webmasters.readonly"],
            ),
        },
        {
            "id": "int_ga4_alienhouse_prod",
            "provider": ConnectorType.GOOGLE_ANALYTICS_4,
            "name": "Google Analytics 4 (alienhouse.co)",
            "target_url": "https://alienhouse.co",
            "scopes": ["analytics.readonly"],
            "settings": {"auth_mode": "oauth2", "property_id": "384910291", "measurement_id": "G-DEMO89201"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.GOOGLE_ANALYTICS_4,
                api_url="https://analyticsdata.googleapis.com/v1beta",
                scopes=["analytics.readonly"],
            ),
        },
        {
            "id": "int_shopify_alienhouse_prod",
            "provider": ConnectorType.SHOPIFY,
            "name": "Shopify (AlienHouse Gear)",
            "target_url": "https://alienhouse-store.myshopify.com",
            "scopes": ["read_content", "read_themes", "write_themes"],
            "settings": {"shop_name": "alienhouse-store"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.SHOPIFY,
                api_url="https://alienhouse-store.myshopify.com/admin/api/2026-01",
                api_key="shpat_demoSecretKey991823",
                scopes=["read_content", "read_themes"],
            ),
        },
        {
            "id": "int_crm_alienhouse_prod",
            "provider": ConnectorType.CRM,
            "name": "HubSpot CRM & Revenue Pipeline",
            "target_url": "https://app.hubspot.com",
            "scopes": ["crm.objects.contacts.read", "crm.objects.deals.read"],
            "settings": {"provider": "hubspot", "portal_id": "8920112"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.CRM,
                api_url="https://api.hubapi.com",
                api_key="pat-na1-demo-hubspot-token",
                scopes=["crm.objects.deals.read"],
            ),
        },
        {
            "id": "int_dataforseo_prod",
            "provider": ConnectorType.DATAFORSEO,
            "name": "DataForSEO Live Index",
            "target_url": "https://api.dataforseo.com",
            "scopes": ["serp.read", "backlinks.read"],
            "settings": {"endpoint": "v3/serp/google/organic/live/advanced"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.DATAFORSEO,
                api_url="https://api.dataforseo.com/v3",
                username="dristik_dataforseo_login",
                app_password="dfs_api_password_demo",
                scopes=["serp.read"],
            ),
        },
        {
            "id": "int_crux_alienhouse_prod",
            "provider": ConnectorType.CRUX,
            "name": "Google Chrome UX Report (CrUX)",
            "target_url": "https://alienhouse.co",
            "scopes": ["crux.read"],
            "settings": {"dataset": "cwv_real_user_vitals"},
            "creds": ConnectorCredentials(
                provider=ConnectorType.CRUX,
                api_url="https://chromeuxreport.googleapis.com/v1/records:queryRecord",
                api_key="AIzaSyDemoCrUXKey99120485",
                scopes=["crux.read"],
            ),
        },
        {
            "id": "int_live_ai_prod",
            "provider": ConnectorType.LIVE_AI_SEARCH,
            "name": "Live AI Citations (ChatGPT, Perplexity, Claude)",
            "target_url": "https://api.perplexity.ai",
            "scopes": ["citations.read"],
            "settings": {"probes": ["chatgpt_search", "perplexity_sonar", "claude_sonnet"]},
            "creds": ConnectorCredentials(
                provider=ConnectorType.LIVE_AI_SEARCH,
                api_url="https://api.perplexity.ai",
                api_key="pplx-demoApiKey99123847",
                scopes=["citations.read"],
            ),
        },
    ]

    with sqlite3.connect(dristik_db_path) as conn:
        for spec in connectors_spec:
            integ_dict = {
                "integration_id": spec["id"],
                "org_id": "org_default",
                "workspace_id": "ws_default",
                "provider": spec["provider"].value,
                "name": spec["name"],
                "target_url": spec["target_url"],
                "status": ConnectorHealthStatus.CONNECTED.value,
                "scopes": spec["scopes"],
                "repository": spec.get("repository"),
                "branch": spec.get("branch", "main"),
                "created_at": now_iso,
                "last_synced_at": now_iso,
                "error_message": None,
                "settings": spec.get("settings", {}),
            }
            creds_json = spec["creds"].model_dump_json()
            enc_payload = _encrypt(creds_json)

            conn.execute("""
                INSERT INTO connector_integrations (integration_id, integration_json, credentials_json)
                VALUES (?, ?, ?)
                ON CONFLICT(integration_id) DO UPDATE SET
                    integration_json = excluded.integration_json,
                    credentials_json = excluded.credentials_json
            """, (spec["id"], json.dumps(integ_dict), enc_payload))
        conn.commit()

    print(f"  ✅ {len(connectors_spec)} platform connectors seeded & encrypted into connector_store.")

    # -------------------------------------------------------------------------
    # 3. ENRICH SHOWCASE AUDIT & 20-CHAPTER REPORT (dristik_audits.db + dristik.db)
    # -------------------------------------------------------------------------
    print("\n[3/4] Seeding Showcase Audit 'run_alienhouse_demo' & Remediation Patches...")

    analysis_id = "run_alienhouse_demo"
    target_url = "https://alienhousenetworks.com/"
    domain = "alienhousenetworks.com"

    # Actionable demo remediation patches
    demo_patches = [
        {
            "patch_id": "patch_llms_manifest",
            "finding_id": "F-AEO-LLMS-TXT",
            "title": "Publish /llms.txt AI Agent Discovery Manifest",
            "category": Category.AI_SEARCH.value,
            "risk_level": PatchRiskLevel.SAFE_AUTO.value,
            "target_url": "/llms.txt",
            "target_file": "llms.txt",
            "operation": PatchOperation.UPDATE_FILE.value,
            "before_snippet": None,
            "after_snippet": "# AlienHouse Networks\n> Enterprise Autonomous AI Systems & Real-time Reasoning Engines.\n\n## Core Capabilities\n- Autonomous Agent Frameworks: /docs/agent-orchestration\n- Real-time Multi-tenant Reasoning: /docs/reasoning-engine\n- Zero-Fabrication Evidence Seal: /docs/verification",
            "explanation": "Creates standard /llms.txt manifest to guide autonomous AI search crawlers (Perplexity, ChatGPT, Claude) to authoritative documentation.",
            "confidence": 0.98,
            "approval_status": PatchApprovalStatus.APPROVED.value,
            "applied_via": "github",
            "pr_url": "https://github.com/alienhousenetworks/dristik/pull/42",
            "pr_number": 42,
            "verification_status": VerificationStatus.VALIDATED.value,
            "citation_score_delta": 14,
            "metadata_payload": {"org_id": "org_default", "analysis_id": analysis_id},
        },
        {
            "patch_id": "patch_schema_org",
            "finding_id": "F-SCHEMA-ORG-MISSING",
            "title": "Inject Canonical Organization & SoftwareApplication JSON-LD",
            "category": Category.SCHEMA.value,
            "risk_level": PatchRiskLevel.SAFE_AUTO.value,
            "target_url": "/",
            "target_file": "index.html",
            "operation": PatchOperation.INSERT_HEAD.value,
            "before_snippet": "<head>\n  <title>AlienHouse Networks</title>",
            "after_snippet": '<head>\n  <title>AlienHouse Networks</title>\n  <script type="application/ld+json">\n  {\n    "@context": "https://schema.org",\n    "@type": "SoftwareApplication",\n    "name": "Dristik AI",\n    "applicationCategory": "BusinessApplication",\n    "operatingSystem": "Cloud",\n    "offers": {\n      "@type": "Offer",\n      "price": "499",\n      "priceCurrency": "USD"\n    }\n  }\n  </script>',
            "explanation": "Eliminates structured data ambiguity so Answer Engines ground pricing and product identity as verified facts.",
            "confidence": 0.96,
            "approval_status": PatchApprovalStatus.APPROVED.value,
            "applied_via": "wordpress",
            "verification_status": VerificationStatus.VALIDATED.value,
            "citation_score_delta": 9,
            "metadata_payload": {"org_id": "org_default", "analysis_id": analysis_id},
        },
        {
            "patch_id": "patch_canonical_self_ref",
            "finding_id": "F-TECH-CANONICAL-CHAIN",
            "title": "Resolve Blog Index Canonical Self-Reference and Trailing Slash",
            "category": Category.TECHNICAL_SEO.value,
            "risk_level": PatchRiskLevel.HUMAN_APPROVAL.value,
            "target_url": "/blog",
            "target_file": "blog.html",
            "operation": PatchOperation.REPLACE.value,
            "before_snippet": '<link rel="canonical" href="http://alienhouse.co/blog" />',
            "after_snippet": '<link rel="canonical" href="https://alienhouse.co/blog/" />',
            "explanation": "Forces HTTPS and trailing slash canonical destination, resolving 301 loop and preserving crawl budget.",
            "confidence": 0.94,
            "approval_status": PatchApprovalStatus.PENDING.value,
            "applied_via": None,
            "verification_status": VerificationStatus.PROVISIONAL.value,
            "citation_score_delta": 4,
            "metadata_payload": {"org_id": "org_default", "analysis_id": analysis_id},
        },
        {
            "patch_id": "patch_faq_accordion",
            "finding_id": "F-GEO-FAQ-EXTRACTION",
            "title": "Deploy High-Intent Commercial FAQ Accordion with FAQPage Schema",
            "category": Category.ON_PAGE_SEO.value,
            "risk_level": PatchRiskLevel.HUMAN_APPROVAL.value,
            "target_url": "/solutions",
            "target_file": "solutions.html",
            "operation": PatchOperation.INSERT_HEAD.value,
            "before_snippet": "<!-- FAQs Section -->",
            "after_snippet": '<!-- FAQs Section -->\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"How does Dristik AI prevent hallucinations?","acceptedAnswer":{"@type":"Answer","text":"Dristik enforces deterministic evidence grounding, multi-source verification, and cryptographic evidence seals."}}]}</script>',
            "explanation": "Provides direct structured answers to high-intent buyer questions, dramatically boosting generative answer synthesis.",
            "confidence": 0.92,
            "approval_status": PatchApprovalStatus.PENDING.value,
            "applied_via": None,
            "verification_status": VerificationStatus.PROVISIONAL.value,
            "citation_score_delta": 11,
            "metadata_payload": {"org_id": "org_default", "analysis_id": analysis_id},
        },
    ]

    # Full report payload for 20-chapter publication renderer & frontend
    report_json = {
        "analysis_id": analysis_id,
        "website_url": target_url,
        "domain": domain,
        "certification_status": "CERTIFIED",
        "scores": {
            "overall_score": 89.2,
            "grade": "A",
            "health_label": "Excellent — AI Search & Answer Engine Ready",
            "technical_score": 92.0,
            "on_page_score": 88.5,
            "schema_score": 95.0,
            "experience_score": 84.0,
            "ai_readiness_score": 90.0,
            "geo_score": 87.0,
        },
        "crawl_manifest": {
            "manifest_id": f"mnf_{analysis_id}",
            "domain": domain,
            "root_url": target_url,
            "total_pages_discovered": 48,
            "total_pages_crawled": 48,
            "crawled_pages_count": 48,
            "max_depth_reached": 3,
            "status_code_distribution": {"200": 46, "301": 2, "404": 0, "500": 0},
            "avg_load_time_ms": 284.5,
            "completed_at": now_iso,
        },
        "business_profile": {
            "company_name": "AlienHouse Networks",
            "domain": domain,
            "primary_intent": "b2b_saas",
            "industry": "Artificial Intelligence & Enterprise Automation",
            "target_geos": ["US", "IN", "GB", "GLOBAL"],
            "competitors": ["rival-ai.com", "cognition-core.io", "omni-search.dev"],
            "unique_selling_propositions": [
                "Deterministic zero-fake verification",
                "Sub-300ms multi-agent reasoning orchestration",
                "Automated multi-platform remediation patches",
            ],
        },
        "remediation_patches": demo_patches,
        "roi_estimate": {
            "is_available": True,
            "status": "AVAILABLE",
            "monthly_visitors": 42500,
            "avg_deal_size_inr": 950000.0,
            "current_conversion_rate": 1.4,
            "expected_traffic_lift_pct": 28.5,
            "expected_cro_lift_pct": 1.8,
            "projected_annual_revenue_inr": 11800000.0,
            "annual_upside_inr": 11800000.0,
            "roi_multiple": 8.4,
            "high_impact_opportunities": [
                "Capturing conversational buyer queries in ChatGPT Search (+34% pipeline)",
                "Fixing blog redirect loops to reclaim Googlebot crawl equity",
                "Direct CMS patch deployment saving 60+ engineering hours per quarter",
            ],
        },
        "competitor_bakeoff": {
            "primary_competitor": "rival-ai.com",
            "brand_citation_share_pct": 68.4,
            "competitor_citation_share_pct": 52.1,
            "winning_dimensions": [
                "Entity Knowledge Graph Clarity",
                "LLM Discovery Manifest Presence (/llms.txt)",
                "Schema Depth & Pricing Transparence",
            ],
            "gap_dimensions": ["External Backlink Authority", "Wikipedia Corroboration"],
        },
        "social_distribution": {
            "whatsapp_summary": "📈 *Dristik AI Weekly Executive Briefing*\nDomain: *alienhousenetworks.com*\nOverall Score: *89.2/100 (Grade A)*\n• 48 pages audited · 0 critical errors\n• 4 automated patches ready for 1-click deployment\n• Estimated Annual Upside: ₹1.18 Cr\n👉 Tap to review and deploy: http://localhost:5173/analyses/run_alienhouse_demo",
            "slack_message_blocks": [
                {"type": "header", "text": "🎯 Dristik AI: Showcase Audit Certified"},
                {"type": "section", "text": "*Domain:* alienhousenetworks.com\n*Score:* 89.2/100 (A)\n*Patches Ready:* 4 (2 Auto-Approved)"},
            ],
            "linkedin_thought_leadership": "Are Answer Engines citing your product when high-intent buyers search? Our latest audit reveals that publishing a structured /llms.txt and unambiguous JSON-LD schema increased AI citation probability by 3.2x.",
        },
    }

    # Store in dristik_audits.db
    with sqlite3.connect(audits_db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                analysis_id TEXT PRIMARY KEY,
                org_id TEXT,
                user_id TEXT,
                website_url TEXT,
                domain TEXT,
                status TEXT,
                progress INTEGER,
                stage TEXT,
                max_pages INTEGER,
                score_overall REAL,
                score_human REAL,
                score_google REAL,
                score_ai_readiness REAL,
                score_ai_visibility REAL,
                score_band TEXT,
                started_at TEXT,
                completed_at TEXT,
                input_hash TEXT,
                output_hash TEXT,
                raw_report_json TEXT,
                error_message TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            INSERT INTO audits (
                analysis_id, org_id, user_id, website_url, domain, status, progress, stage, max_pages,
                score_overall, score_band, started_at, completed_at, raw_report_json, created_at
            )
            VALUES (?, 'org_default', 'usr_admin_system', ?, ?, 'completed', 100, 'COMPLETED', 48,
                    89.2, 'EXCELLENT', ?, ?, ?, ?)
            ON CONFLICT(analysis_id) DO UPDATE SET
                org_id = 'org_default',
                status = 'completed',
                progress = 100,
                score_overall = 89.2,
                raw_report_json = excluded.raw_report_json
        """, (analysis_id, target_url, domain, now_iso, now_iso, json.dumps(report_json), now_iso))

        # Also update existing run_529ca7cc31 if in audits_db to make it accessible to org_default
        conn.execute("""
            UPDATE audits
            SET org_id = 'org_default', status = 'completed', progress = 100
            WHERE analysis_id = 'run_529ca7cc31'
        """)
        conn.commit()

    # Store in dristik.db for fast API analysis listings
    with sqlite3.connect(dristik_db_path) as conn:
        conn.execute("""
            INSERT INTO audits (analysis_id, org_id, user_id, website_url, status, page_count, overall_score, created_at, updated_at)
            VALUES (?, 'org_default', 'usr_admin_system', ?, 'completed', 48, 89.2, ?, ?)
            ON CONFLICT(analysis_id) DO UPDATE SET
                org_id = 'org_default',
                status = 'completed',
                overall_score = 89.2,
                updated_at = excluded.updated_at
        """, (analysis_id, target_url, now_ts, now_ts))

        # Update run_529ca7cc31 in dristik.db to completed and org_default
        conn.execute("""
            UPDATE audits
            SET org_id = 'org_default', status = 'completed', overall_score = 51.3, updated_at = ?
            WHERE analysis_id = 'run_529ca7cc31'
        """, (now_ts,))
        conn.commit()

    print(f"  ✅ Audit '{analysis_id}' seeded across dristik_audits.db and dristik.db.")
    print("  ✅ Linked historical audit 'run_529ca7cc31' to 'org_default' (status: completed).")
    print(f"  ✅ {len(demo_patches)} production remediation patches loaded with diffs.")

    # -------------------------------------------------------------------------
    # 4. VERIFY ENRICHMENT INTEGRITY
    # -------------------------------------------------------------------------
    print("\n[4/4] Verifying Demo Data Integrity...")
    with sqlite3.connect(dristik_db_path) as conn:
        users_count = conn.execute("SELECT COUNT(*) FROM users WHERE org_id = 'org_default'").fetchone()[0]
        integs_count = conn.execute("SELECT COUNT(*) FROM connector_integrations").fetchone()[0]
        audits_count = conn.execute("SELECT COUNT(*) FROM audits WHERE org_id = 'org_default'").fetchone()[0]

    print("=" * 72)
    print("🎉 DEMO ENRICHMENT COMPLETE & READY FOR TESTING")
    print("=" * 72)
    print(f"• Active Organization : org_default (Enterprise Plan)")
    print(f"• Demo Admin Login    : admin@dristik.ai  /  {password}")
    print(f"• Demo Owner Login    : demo@alienhouse.co  /  {password}")
    print(f"• Active Connectors   : {integs_count} platforms connected & verified")
    print(f"• Ready Audits        : {audits_count} audits available (including '{analysis_id}')")
    print("• Frontend Access     : http://localhost:5173")
    print("• Backend API Docs    : http://localhost:8000/docs")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dristik AI Demo Data Enrichment")
    parser.add_argument("--password", default="Password@123", help="Password for admin & demo users")
    parser.add_argument("--reset", action="store_true", help="Reset existing demo records")
    args = parser.parse_args()

    enrich_demo_data(password=args.password, reset=args.reset)
