"""
Central SEO Audit Orchestrator & Multi-Agent Workflow Engine (2026 Master Standard).

Coordinates:
- 40 specialist roles across 10 departments + 6 core pipeline stages in topological waves
- 4 operating modes: QUICK (incl. 5-page sample), STANDARD, DEEP, CONTINUOUS
- Real deterministic SEO analyzers (meta, headings, HTTP, canonicals, media, schema,
  link graph, international, local, ecommerce, rendering parity, enterprise assessment)
- Durable persistence across the 26 relational SEO tables + checkpoint resume
- 9-dimension MathematicalScoreEngine, stack-detected PostAuditRemediationEngine,
  and 10-gate fail-closed SeoQaValidator
- Real-time canonical SSE event streaming
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.connectors.seo_connector_manager import ConnectorManager, seo_connector_manager
from app.db.seo_orchestrator_schema import default_seo_db_path, init_seo_orchestrator_schema
from app.domain.models import CrawlInventory
from app.seo.audit.internal_links.link_graph_engine import build_internal_link_graph
from app.seo.audit.orchestration.dag import AuditDAG, DAGNode, DAGStage
from app.seo.audit.orchestration.event_store import EventStore
from app.seo.audit.orchestration.execution_state import (
    AuditConfiguration,
    AuditMode,
    FailurePolicy,
    NodeState,
    TaskCheckpoint,
    WorkflowBudget,
    WorkflowExecutionState,
    WorkflowStatus,
)
from app.seo.audit.orchestration.task_executor import TaskExecutor
from app.seo.audit.qa.seo_qa_validator import QaCertificationReport, SeoQaValidator
from app.seo.audit.remediation.post_audit_remediation_engine import PostAuditRemediationEngine, RemediationTask
from app.seo.audit.scoring.mathematical_score_engine import MathematicalScoreEngine, SeoScorecardReport
from app.seo.enterprise.assess import build_enterprise_seo

logger = logging.getLogger("dristik.seo.orchestrator")


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:32]


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class SEOAuditOrchestrator:
    """
    Central Coordinator for the Dristik SEO Multi-Agent Workforce.
    """

    def __init__(
        self,
        audit_id: str,
        domain: str,
        config: Optional[AuditConfiguration] = None,
        db_path: Optional[str] = None,
        source_report: Optional[Any] = None,
        seed_pages: Optional[List[Dict[str, Any]]] = None,
        connector_manager: Optional[ConnectorManager] = None,
    ):
        self.audit_id = audit_id
        self.domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        self.db_path = db_path or default_seo_db_path()
        self.config = config or AuditConfiguration(
            target_url=f"https://{self.domain}/",
            mode=AuditMode.STANDARD,
        )
        self.budget = WorkflowBudget.from_mode(self.config.mode)
        if self.config.max_pages:
            self.budget.max_pages = int(self.config.max_pages)
        self.dag = AuditDAG(mode=self.config.mode)
        self.events = EventStore(audit_id=self.audit_id)
        self.state = WorkflowExecutionState(
            audit_id=self.audit_id,
            mode=self.config.mode,
            status=WorkflowStatus.QUEUED,
        )
        self.executor = TaskExecutor()
        self.connectors = connector_manager or ConnectorManager(db_path=self.db_path)
        self.source_report = source_report
        self._seed_pages = list(seed_pages or [])

        # Shared run artifacts populated deterministically across stages
        self._crawl_manifest: Dict[str, Any] = {}
        self._pages: List[Dict[str, Any]] = []
        self._evidence_records: List[Dict[str, Any]] = []
        self._raw_findings: List[Dict[str, Any]] = []
        self._deduped_findings: List[Dict[str, Any]] = []
        self._specialist_applicable: Dict[str, bool] = {"local": False, "international": False, "ecommerce": False}
        self._detected_headers: Dict[str, str] = {}
        self._detected_dom_sample: str = ""
        self._analyzer_results: Dict[str, Any] = {}

        # Sealed canonical outputs
        self.canonical_assessment: Optional[Dict[str, Any]] = None
        self.scorecard: Optional[SeoScorecardReport] = None
        self.remediation_tasks: List[RemediationTask] = []
        self.qa_report: Optional[QaCertificationReport] = None
        self.link_graph: Optional[Dict[str, Any]] = None

        init_seo_orchestrator_schema(self.db_path)
        self._register_all_agent_runners()
        self._persist_initial_state()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _persist_initial_state(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_audit_runs (
                    id, org_id, workspace_id, domain, mode, status, current_stage,
                    execution_budget_sec, total_tasks, idempotency_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.audit_id,
                    self.config.org_id,
                    self.config.workspace_id,
                    self.domain,
                    self.config.mode.value,
                    self.state.status.value,
                    self.state.current_stage,
                    int(self.budget.max_execution_sec),
                    len(self.dag.nodes),
                    self.config.idempotency_key,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_audit_configurations (
                    id, audit_id, org_id, workspace_id, target_url, mode,
                    max_pages, max_concurrency, requests_per_second,
                    respect_robots_txt, render_javascript, connectors_enabled, excluded_paths
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"cfg_{self.audit_id}",
                    self.audit_id,
                    self.config.org_id,
                    self.config.workspace_id,
                    self.config.target_url,
                    self.config.mode.value,
                    self.budget.max_pages,
                    self.budget.max_concurrency,
                    self.budget.requests_per_second,
                    self.config.respect_robots_txt,
                    1 if self.config.render_javascript else 0,
                    json.dumps(self.config.connectors_enabled),
                    json.dumps(self.config.excluded_paths),
                ),
            )
            for node in self.dag.nodes.values():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_agent_registry (
                        agent_id, name, group_name, department, version, mode,
                        timeout_sec, retry_limit, required_connector, is_active
                    ) VALUES (?, ?, ?, ?, 'v2', ?, ?, ?, ?, 1)
                    """,
                    (
                        node.agent_id,
                        node.agent_name,
                        node.stage.value,
                        node.department,
                        node.execution_mode,
                        int(node.timeout_sec),
                        node.retry_limit,
                        node.required_connector,
                    ),
                )
                task_pk = f"{self.audit_id}:{node.agent_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_workflow_tasks (
                        id, audit_id, workspace_id, task_name, stage, status
                    ) VALUES (?, ?, ?, ?, ?, 'PENDING')
                    """,
                    (task_pk, self.audit_id, self.config.workspace_id, node.agent_id, node.stage.value),
                )
                for dep in node.dependencies:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO seo_workflow_dependencies (task_id, depends_on_task_id, audit_id)
                        VALUES (?, ?, ?)
                        """,
                        (task_pk, f"{self.audit_id}:{dep}", self.audit_id),
                    )
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_methodology_versions (version_tag, formula_spec, released_at, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (
                    MathematicalScoreEngine.METHODOLOGY_VERSION,
                    json.dumps(MathematicalScoreEngine.DIMENSION_WEIGHTS),
                    now,
                ),
            )
            conn.commit()

    def _add_evidence(
        self,
        *,
        url: Optional[str],
        check_id: str,
        source_type: str,
        source_location: str,
        observed_value: Any,
        expected_value: Any,
        result: str,
        agent_id: str,
        snapshot_id: Optional[str] = None,
        content_sha256: Optional[str] = None,
    ) -> str:
        ev_id = f"SEO_EV_{len(self._evidence_records) + 1:06d}"
        now = datetime.now(timezone.utc).isoformat()
        digest = content_sha256 or _sha256(json.dumps({
            "url": url, "check_id": check_id, "observed": observed_value,
        }, sort_keys=True, default=str))
        rec = {
            "evidence_id": ev_id,
            "audit_id": self.audit_id,
            "url": url,
            "check_id": check_id,
            "source_type": source_type,
            "source_location": source_location,
            "observed_value": observed_value,
            "expected_value": expected_value,
            "result": result,
            "evidence_status": "verified",
            "observed_at": now,
            "snapshot_id": snapshot_id or f"SNAP_{self.audit_id}_{len(self._evidence_records) + 1:04d}",
            "content_sha256": digest,
            "content_hash": digest,
            "agent_id": agent_id,
            "methodology_version": MathematicalScoreEngine.METHODOLOGY_VERSION,
        }
        self._evidence_records.append(rec)
        return ev_id

    def _add_finding(
        self,
        *,
        rule_id: str,
        category: str,
        severity: str,
        title: str,
        description: str,
        recommendation: str,
        affected_urls: List[str],
        evidence_ids: List[str],
        agent_id: str,
        root_cause_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        rc_seed = f"{rule_id}:{root_cause_key or self._infer_template(affected_urls)}"
        rc_id = f"SEO-RC-{hashlib.sha256(rc_seed.encode()).hexdigest()[:8].upper()}"
        finding_id = f"SEO-F-{len(self._raw_findings) + 1:03d}"
        finding = {
            "finding_id": finding_id,
            "id": finding_id,
            "rule_id": rule_id,
            "root_cause_id": rc_id,
            "category": category,
            "severity": severity.upper(),
            "status": "VERIFIED",
            "verification_status": "VERIFIED",
            "title": title,
            "description": description,
            "observed_condition": description,
            "recommendation": recommendation,
            "affected_urls": list(dict.fromkeys(affected_urls)),
            "affected_url_count": len(set(affected_urls)),
            "evidence_ids": list(evidence_ids),
            "evidence_refs": list(evidence_ids),
            "agent_id": agent_id,
            "verification_required": True,
            "business_impact": {
                "type": category.lower(),
                "confidence": "high" if evidence_ids else "low",
                "quantified": False,
            },
        }
        self._raw_findings.append(finding)
        return finding

    @staticmethod
    def _infer_template(urls: List[str]) -> str:
        if not urls:
            return "sitewide"
        path = urlparse(urls[0]).path.strip("/")
        if not path:
            return "homepage"
        return f"/{path.split('/')[0]}/*"

    def _fetched_pages(self) -> List[Dict[str, Any]]:
        return [page for page in self._pages if page.get("crawl_source") != "unfetched_seed"]

    def _stamp_page_template(self) -> None:
        from app.crawl.template_discovery import build_page_template_intelligence

        discovered = list(self._crawl_manifest.get("discovered_urls") or [])
        self._crawl_manifest["page_template"] = build_page_template_intelligence(
            self._fetched_pages(),
            discovered,
        )
        self._crawl_manifest.setdefault("mobile_validation", {
            "verification_status": "NOT_TESTED",
            "physical_device": False,
            "measurement_method": "not_run",
            "reason": "No emulated browser viewport was executed. A viewport meta tag is not a mobile UX audit.",
            "runs": [],
        })

    def _coverage_numbers(self) -> Dict[str, int]:
        intel = self._crawl_manifest.get("page_template") or {}
        fetched = self._fetched_pages()
        rendered_fallback = sum(
            1 for page in fetched
            if page.get("rendered_html") or str(page.get("render_mode") or "") in {"playwright_js", "firecrawl_js"}
        )
        discovered = int(intel.get("urls_discovered") or self._crawl_manifest.get("total_pages_discovered") or len(fetched))
        crawled = int(intel["urls_crawled"]) if "urls_crawled" in intel else len(fetched)
        rendered = int(intel["urls_rendered"]) if "urls_rendered" in intel else rendered_fallback
        deep = int(intel["urls_deeply_analyzed"]) if "urls_deeply_analyzed" in intel else rendered
        return {"discovered": discovered, "crawled": crawled, "rendered": rendered, "deep": deep}

    async def _run_mobile_emulation(self) -> None:
        from app.seo.audit.crawlers.playwright_client import measure_emulated_devices

        intel = self._crawl_manifest.get("page_template") or {}
        urls: List[str] = []
        for template in intel.get("templates") or []:
            sample = template.get("sample_url")
            if sample and sample not in urls:
                urls.append(sample)
        if not urls:
            urls = [str(page.get("url")) for page in self._fetched_pages() if page.get("url")]
        # shortcut: three template samples, not every discovered URL
        runs = []
        for url in urls[:3]:
            runs.append(await measure_emulated_devices(url))
        measured = any(run.get("verification_status") == "VERIFIED" for run in runs)
        unavailable = any(run.get("verification_status") == "DATA_UNAVAILABLE" for run in runs)
        self._crawl_manifest["mobile_validation"] = {
            "verification_status": "VERIFIED" if measured else ("DATA_UNAVAILABLE" if unavailable else "NOT_TESTED"),
            "physical_device": False,
            "measurement_method": "emulated_browser" if measured else "not_run",
            "label": "Browser-emulated device. Not a physical phone. Menus, forms, and checkout were not clicked.",
            "runs": runs,
        }
        for run in runs:
            for device in run.get("devices") or []:
                if not device.get("layout_measured"):
                    continue
                label = device.get("device_label") or device.get("device_id") or "viewport"
                url = str(run.get("url") or device.get("url") or "")
                if device.get("has_horizontal_overflow"):
                    evidence_id = self._add_evidence(
                        url=url,
                        check_id="seo.mobile.overflow",
                        source_type="rendered_dom",
                        source_location=f"emulated:{label}",
                        observed_value=device.get("overflow_elements") or True,
                        expected_value="No horizontal overflow",
                        result="failed",
                        agent_id="mobile_rendering",
                    )
                    self._add_finding(
                        rule_id="seo.mobile.overflow",
                        category="TECHNICAL_SEO",
                        severity="MEDIUM",
                        title=f"Horizontal overflow on emulated {label} viewport",
                        description=(
                            f"The emulated {label} browser viewport overflowed on {url}. "
                            "This is an emulated browser, not a physical phone."
                        ),
                        recommendation="Constrain the overflowing element to the viewport width and re-run the same emulated viewport.",
                        affected_urls=[url] if url else [],
                        evidence_ids=[evidence_id],
                        agent_id="mobile_rendering",
                    )
                failed_targets = device.get("failed_touch_targets") or []
                if failed_targets:
                    evidence_id = self._add_evidence(
                        url=url,
                        check_id="seo.mobile.touch_target",
                        source_type="rendered_dom",
                        source_location=f"emulated:{label}",
                        observed_value=len(failed_targets),
                        expected_value="Interactive targets at least 48x48px",
                        result="failed",
                        agent_id="mobile_rendering",
                    )
                    self._add_finding(
                        rule_id="seo.mobile.touch_target",
                        category="TECHNICAL_SEO",
                        severity="MEDIUM",
                        title=f"Undersized touch targets on emulated {label} viewport",
                        description=(
                            f"{len(failed_targets)} interactive element(s) were under 40px on the emulated {label} viewport of {url}. "
                            "This is an emulated browser, not a physical phone."
                        ),
                        recommendation="Increase the tap target to at least 48x48px and re-run the same emulated viewport.",
                        affected_urls=[url] if url else [],
                        evidence_ids=[evidence_id],
                        agent_id="mobile_rendering",
                    )

    def _hydrate_pages_from_source(self) -> List[Dict[str, Any]]:
        if self._seed_pages:
            return [dict(p) for p in self._seed_pages]
        if self.source_report is not None:
            rep = self.source_report
            manifest = rep.get("crawl_manifest") if isinstance(rep, dict) else getattr(rep, "crawl_manifest", None)
            raw_pages = (
                (manifest.get("pages") if isinstance(manifest, dict) else getattr(manifest, "pages", None))
                or (rep.get("page_reports") if isinstance(rep, dict) else getattr(rep, "page_reports", None))
                or []
            )
            out: List[Dict[str, Any]] = []
            for p in raw_pages:
                if hasattr(p, "model_dump"):
                    out.append(p.model_dump())
                elif isinstance(p, dict):
                    out.append(dict(p))
            return out
        return []

    def _register_all_agent_runners(self) -> None:
        """Registers executable runners for ALL 46 DAG nodes (40 specialist roles + 6 pipeline stages)."""

        # --- Stage 1 & 2: Dept A — Discovery & Crawling (4 specialists) ---
        async def run_discovery_sitemap(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.events.emit("crawl.discovering", {"domain": self.domain, "mode": self.config.mode.value})
            pages = self._hydrate_pages_from_source()
            if not pages and self.config.live_crawl:
                try:
                    from app.crawl.crawler import CrawlerService
                    crawler = CrawlerService()
                    manifest_obj = await crawler.crawl_site(
                        self.config.target_url,
                        max_pages=min(self.budget.max_pages, 25 if self.config.mode == AuditMode.QUICK else self.budget.max_pages),
                    )
                    if hasattr(manifest_obj, "model_dump"):
                        self._crawl_manifest = manifest_obj.model_dump()
                    elif isinstance(manifest_obj, dict):
                        self._crawl_manifest = manifest_obj
                    pages = list(self._crawl_manifest.get("pages") or [])
                except Exception as exc:
                    logger.warning("Live crawl failed for %s: %s", self.domain, exc)

            if pages:
                self._pages = pages
                if not self._crawl_manifest:
                    disc_urls = list(dict.fromkeys(
                        [str(p.get("url")) for p in pages if p.get("url")]
                        + list(self.config.custom_seed_urls or [])
                    ))
                    self._crawl_manifest = {
                        "domain": self.domain,
                        "total_pages_discovered": max(len(disc_urls), len(pages)),
                        "total_pages_crawled": len(pages),
                        "discovered_urls": disc_urls,
                        "pages": pages,
                        "robots_txt_found": bool(self._crawl_manifest.get("robots_txt_found")),
                        "sitemap_found": bool(self._crawl_manifest.get("sitemap_urls")),
                        "sampling_status": "SAMPLED_AUDIT" if len(disc_urls) > len(pages) else "FULL_CRAWL",
                    }
            else:
                root_url = self.config.target_url.rstrip("/") + "/"
                seed_urls = list(dict.fromkeys([root_url] + list(self.config.custom_seed_urls or [])))
                self._pages = []
                self._crawl_manifest = {
                    "domain": self.domain,
                    "total_pages_discovered": len(seed_urls),
                    "total_pages_crawled": 0,
                    "discovered_urls": seed_urls,
                    "pages": [],
                    "robots_txt_found": False,
                    "sitemap_found": False,
                    "sampling_status": "SAMPLED_AUDIT",
                }

            self._stamp_page_template()
            if self.config.live_crawl and self._fetched_pages() and os.environ.get("DRISTIK_MOBILE_EMULATION", "1") != "0":
                try:
                    await self._run_mobile_emulation()
                except Exception as exc:
                    logger.warning("Emulated mobile validation failed for %s: %s", self.domain, exc)
                    self._crawl_manifest["mobile_validation"] = {
                        "verification_status": "DATA_UNAVAILABLE",
                        "physical_device": False,
                        "measurement_method": "emulated_browser",
                        "error": f"{type(exc).__name__}: {exc}",
                        "runs": [],
                    }

            self.state.crawled_pages = list(self._pages)
            self.state.discovered_urls = list(self._crawl_manifest.get("discovered_urls") or [p.get("url") for p in self._pages])
            return {
                "domain": self.domain,
                "discovered_urls_count": len(self.state.discovered_urls),
                "robots_txt_found": bool(self._crawl_manifest.get("robots_txt_found")),
                "sitemap_found": bool(self._crawl_manifest.get("sitemap_found")),
            }

        async def run_sitemap_validator(ctx: Dict[str, Any]) -> Dict[str, Any]:
            sitemap_urls = list(self._crawl_manifest.get("sitemap_urls") or [])
            sitemap_found = bool(self._crawl_manifest.get("sitemap_found"))
            findings = []
            if not sitemap_found:
                ev_id = self._add_evidence(
                    url=self.config.target_url,
                    check_id="seo.sitemap.missing",
                    source_type="http",
                    source_location="/sitemap.xml",
                    observed_value=None,
                    expected_value="Valid XML sitemap with HTTP 200",
                    result="failed",
                    agent_id="agent_sitemap_validator",
                )
                findings.append(self._add_finding(
                    rule_id="seo.sitemap.missing",
                    category="TECHNICAL_SEO",
                    severity="MEDIUM",
                    title="XML Sitemap Not Detected",
                    description="No valid XML sitemap was discovered via robots.txt or standard sitemap endpoints.",
                    recommendation="Publish an XML sitemap listing all canonical indexable URLs and declare it in robots.txt.",
                    affected_urls=[self.config.target_url],
                    evidence_ids=[ev_id],
                    agent_id="agent_sitemap_validator",
                ))
            return {"sitemap_found": sitemap_found, "sitemap_url_count": len(sitemap_urls), "findings": findings}

        async def run_url_inventory(ctx: Dict[str, Any]) -> Dict[str, Any]:
            numbers = self._coverage_numbers()
            discovered = numbers["discovered"]
            crawled = numbers["crawled"]
            return {
                "urls_discovered": discovered,
                "urls_crawled": crawled,
                "urls_rendered": numbers["rendered"],
                "urls_deeply_inspected": numbers["deep"],
                "full_site_audit": bool((self._crawl_manifest.get("page_template") or {}).get("full_site_audit")),
                "sampling_status": "SAMPLED_AUDIT" if discovered > crawled or self.config.mode == AuditMode.QUICK else "FULL_CRAWL",
            }

        async def run_crawl_strategy(ctx: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "mode": self.config.mode.value,
                "budget_max_pages": self.budget.max_pages,
                "prioritized_urls": [p.get("url") for p in self._pages[:20]],
            }

        async def run_crawler_engine(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.events.emit("crawl.progress", {
                "urls_discovered": len(self.state.discovered_urls),
                "urls_crawled": len(self._pages),
            })
            # Extract real headers & DOM sample for stack detection (never guess)
            for p in self._pages:
                hdrs = p.get("response_headers") or p.get("headers") or {}
                if isinstance(hdrs, dict) and hdrs:
                    self._detected_headers.update({str(k): str(v) for k, v in hdrs.items()})
                raw = str(p.get("raw_html") or p.get("rendered_html") or "")
                if raw and not self._detected_dom_sample:
                    self._detected_dom_sample = raw[:16000]
            return {
                "pages_crawled": len(self._pages),
                "headers_captured": len(self._detected_headers),
            }

        async def run_evidence_extractor(ctx: Dict[str, Any]) -> Dict[str, Any]:
            for idx, p in enumerate(self._pages):
                url = str(p.get("url") or self.config.target_url)
                raw_html = str(p.get("raw_html") or "")
                rendered_html = str(p.get("rendered_html") or raw_html)
                self._add_evidence(
                    url=url,
                    check_id="seo.page.snapshot",
                    source_type="rendered_dom" if p.get("rendered_html") else "http",
                    source_location="document",
                    observed_value={
                        "status_code": p.get("status_code"),
                        "title": p.get("title"),
                        "word_count": p.get("word_count"),
                    },
                    expected_value="HTTP 200 with parseable DOM",
                    result="passed" if 200 <= int(p.get("status_code") or 0) < 300 else "failed",
                    agent_id="evidence_extractor",
                    snapshot_id=f"SNAP_{self.audit_id}_{idx + 1:04d}",
                    content_sha256=_sha256(rendered_html or url),
                )
            intel = self._crawl_manifest.get("page_template") or {}
            for defect in intel.get("template_defects") or []:
                affected = [url for url in (defect.get("affected_urls") or []) if url]
                if not affected:
                    continue
                names = ", ".join(defect.get("defects") or []) or "shared markup"
                remaining = len(intel.get("expansion_urls") or [])
                evidence_id = self._add_evidence(
                    url=affected[0],
                    check_id="seo.template.shared_defect",
                    source_type="http",
                    source_location=str(defect.get("template_id") or "template"),
                    observed_value=names,
                    expected_value="Fetched pages in this template do not share the same defect",
                    result="failed",
                    agent_id="page_template",
                )
                self._add_finding(
                    rule_id="seo.template.shared_defect",
                    category="TECHNICAL_SEO",
                    severity="HIGH" if "canonical" in names else "MEDIUM",
                    title=f"Shared template defect: {names}",
                    description=(
                        f"The same {names} pattern was read from HTML on {len(affected)} fetched URL(s) "
                        f"in {defect.get('template_name') or 'one template'}. "
                        + (
                            f"{remaining} same-prefix URL(s) were not fetched and are not counted as broken."
                            if remaining else
                            "No unfetched same-prefix URL remained."
                        )
                    ),
                    recommendation="Fix the shared template, then fetch every affected URL again before calling the template clean.",
                    affected_urls=affected,
                    evidence_ids=[evidence_id],
                    agent_id="page_template",
                )
            self.events.emit("evidence.persisted", {"evidence_count": len(self._evidence_records)})
            return {"evidence_count": len(self._evidence_records)}

        # --- Helper for connector-gated agents ---
        _CONNECTOR_TO_AUTHORITY_PROVIDERS: Dict[str, List[str]] = {
            "google_search_console": ["google_search_console"],
            "google_analytics_4": ["google_analytics_4"],
            "backlink_provider": ["ahrefs", "semrush", "majestic", "moz", "commoncrawl", "dataforseo"],
            "keyword_serp_provider": ["dataforseo", "serpapi"],
            "google_business_profile": ["google_business_profile"],
            "bing_webmaster": ["bing_webmaster"],
            "pagespeed_crux": ["pagespeed_crux"],
        }
        _CONNECTOR_CATEGORY: Dict[str, str] = {
            "google_search_console": "SEARCH_PERFORMANCE",
            "google_analytics_4": "SEARCH_PERFORMANCE",
            "backlink_provider": "AUTHORITY_BACKLINKS",
            "keyword_serp_provider": "SEARCH_PERFORMANCE",
            "google_business_profile": "LOCAL_SEO",
            "bing_webmaster": "SEARCH_PERFORMANCE",
            "pagespeed_crux": "CORE_WEB_VITALS",
        }

        def make_connector_runner(agent_id: str, connector_id: str, summary_label: str):
            async def _runner(ctx: Dict[str, Any]) -> Dict[str, Any]:
                status = self.connectors.get_connector_status(connector_id, workspace_id=self.config.workspace_id)
                provider_ids = _CONNECTOR_TO_AUTHORITY_PROVIDERS.get(connector_id, [connector_id])
                category = _CONNECTOR_CATEGORY.get(connector_id, "TECHNICAL_SEO")

                # Inspect ExternalAuthorityService for measured snapshots & findings across matching providers
                ea_connected = False
                ea_data_state = "NOT_CONNECTED"
                ea_metrics: Dict[str, Any] = {}
                ea_findings: List[Dict[str, Any]] = []
                records_count = 0
                matched_provider: Optional[str] = None

                try:
                    from app.connectors.authority.service import get_service

                    svc = get_service()
                    candidate_projects = [
                        p for p in dict.fromkeys([self.config.org_id, self.config.workspace_id, "default"]) if p
                    ]
                    for proj_id in candidate_projects:
                        conn_rows = {r.get("provider"): r for r in svc.store.public_connections(proj_id)}
                        for pid in provider_ids:
                            snap = svc.store.latest_snapshot(proj_id, pid, self.domain, 28)
                            crow = conn_rows.get(pid)
                            if (crow and crow.get("status") == "CONNECTED") or snap is not None:
                                ea_connected = True
                                matched_provider = pid
                                if snap:
                                    ea_data_state = str(snap.get("data_state") or "MEASURED")
                                    summary = snap.get("summary") or {}
                                    if isinstance(summary, dict) and isinstance(summary.get("totals"), dict):
                                        ea_metrics.update(summary["totals"])
                                    recs = svc.store.records_for_snapshot(snap["snapshot_id"])
                                    records_count += len(recs)
                                    # Build provider-scoped report findings deterministically from stored records
                                    rep = svc.report(proj_id, self.domain, 28)
                                    for rf in rep.get("findings") or []:
                                        src_prov = str(rf.get("source_provider") or rf.get("provider") or "").lower()
                                        if src_prov and src_prov not in provider_ids:
                                            continue
                                        if rf.get("data_state") not in (None, "MEASURED", "PARTIALLY_MEASURED"):
                                            continue
                                        sev_raw = str(rf.get("severity") or "MEDIUM").upper()
                                        sev = sev_raw if sev_raw in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "MEDIUM"
                                        affected = [str(u) for u in (rf.get("affected_urls") or [self.config.target_url]) if u]
                                        ev_id = self._add_evidence(
                                            url=affected[0],
                                            check_id=str(rf.get("rule_id") or f"seo.connector.{connector_id}"),
                                            source_type=f"connector:{pid}",
                                            source_location=f"{pid}.snapshot",
                                            observed_value=rf.get("observed_value", rf.get("metric_value", ea_metrics)),
                                            expected_value=rf.get("expected_value"),
                                            result="failed",
                                            agent_id=agent_id,
                                        )
                                        ea_findings.append(
                                            self._add_finding(
                                                rule_id=str(rf.get("rule_id") or f"seo.connector.{connector_id}"),
                                                category=category,
                                                severity=sev,
                                                title=str(rf.get("title") or f"{summary_label} Finding"),
                                                description=str(rf.get("description") or rf.get("summary") or ""),
                                                recommendation=str(rf.get("recommendation") or "Review live connector telemetry and remediate affected URLs."),
                                                affected_urls=affected,
                                                evidence_ids=[ev_id],
                                                agent_id=agent_id,
                                            )
                                        )
                                    # Deterministic record-level checks when snapshot has metrics but analyzer emitted 0 findings
                                    if connector_id == "google_search_console" and not ea_findings:
                                        for r in recs:
                                            if r.get("metric") == "sitemap" and int((r.get("metadata") or {}).get("errors") or 0) > 0:
                                                sm_url = str(r.get("url") or self.config.target_url)
                                                err_cnt = int((r.get("metadata") or {}).get("errors") or 0)
                                                ev_id = self._add_evidence(
                                                    url=sm_url,
                                                    check_id="seo.gsc.sitemap_errors",
                                                    source_type="connector:google_search_console",
                                                    source_location="webmasters.sitemaps.list",
                                                    observed_value=err_cnt,
                                                    expected_value=0,
                                                    result="failed",
                                                    agent_id=agent_id,
                                                )
                                                ea_findings.append(
                                                    self._add_finding(
                                                        rule_id="seo.gsc.sitemap_errors",
                                                        category="SEARCH_PERFORMANCE",
                                                        severity="HIGH",
                                                        title=f"Google Search Console Reports {err_cnt} Sitemap Error(s)",
                                                        description=f"GSC reports {err_cnt} error(s) in submitted sitemap {sm_url}.",
                                                        recommendation="Fix malformed or unreachable URLs in the XML sitemap and resubmit in Google Search Console.",
                                                        affected_urls=[sm_url],
                                                        evidence_ids=[ev_id],
                                                        agent_id=agent_id,
                                                    )
                                                )
                                    break
                        if ea_connected:
                            break
                except Exception as exc:
                    logger.debug("ExternalAuthority lookup skipped for %s: %s", connector_id, exc)

                # PageSpeed / CrUX LCP subpart analysis when connector is connected with CrUX/PSI metrics
                if connector_id == "pagespeed_crux" and status.status == "CONNECTED":
                    creds = self.connectors.get_decrypted_credentials(connector_id, workspace_id=self.config.workspace_id) or {}
                    crux_lcp = creds.get("lcp_subparts") or creds.get("crux_metrics")
                    if isinstance(crux_lcp, dict) and crux_lcp.get("lcp_ms"):
                        from app.seo.analyzers.lcp_subparts import analyze_lcp_subparts
                        lcp_diag = analyze_lcp_subparts(
                            lcp_ms=float(crux_lcp.get("lcp_ms")),
                            ttfb_ms=crux_lcp.get("ttfb_ms"),
                            resource_load_delay_ms=crux_lcp.get("resource_load_delay_ms"),
                            resource_load_duration_ms=crux_lcp.get("resource_load_duration_ms"),
                            element_render_delay_ms=crux_lcp.get("element_render_delay_ms"),
                        )
                        ea_metrics["lcp_subparts"] = lcp_diag
                        ea_data_state = "MEASURED"
                        if lcp_diag.get("status") in ("needs_improvement", "poor"):
                            ev_id = self._add_evidence(
                                url=self.config.target_url,
                                check_id="seo.cwv.lcp_subpart_bottleneck",
                                source_type="connector:pagespeed_crux",
                                source_location="crux.lcp_subparts",
                                observed_value=lcp_diag,
                                expected_value={"lcp_ms": "<= 2500"},
                                result="failed",
                                agent_id=agent_id,
                            )
                            ea_findings.append(
                                self._add_finding(
                                    rule_id="seo.cwv.lcp_subpart_bottleneck",
                                    category="CORE_WEB_VITALS",
                                    severity="HIGH" if lcp_diag.get("status") == "poor" else "MEDIUM",
                                    title=f"CrUX LCP Bottleneck: {lcp_diag.get('primary_bottleneck')}",
                                    description=f"Field LCP is {lcp_diag.get('lcp_ms')}ms; dominant subpart is {lcp_diag.get('primary_bottleneck')}.",
                                    recommendation=str(lcp_diag.get("recommendation") or "Optimize the primary LCP subpart bottleneck."),
                                    affected_urls=[self.config.target_url],
                                    evidence_ids=[ev_id],
                                    agent_id=agent_id,
                                )
                            )

                is_connected = (status.status == "CONNECTED") or ea_connected
                if not is_connected:
                    return {
                        "node_status": "DATA_UNAVAILABLE",
                        "connector": connector_id,
                        "status": "NOT_CONFIGURED",
                        "data_state": "NOT_CONNECTED",
                        "message": f"{summary_label} unavailable: {connector_id} is not connected.",
                        "findings": [],
                    }

                effective_state = ea_data_state if ea_data_state != "NOT_CONNECTED" else "CONNECTED_AWAITING_SYNC"
                return {
                    "connector": connector_id,
                    "provider_matched": matched_provider or connector_id,
                    "status": "CONNECTED",
                    "data_state": effective_state,
                    "last_sync": status.last_sync_timestamp,
                    "records_count": records_count,
                    "metrics": ea_metrics,
                    "findings": ea_findings,
                }
            return _runner

        # --- Dept B: Technical SEO (6 specialists) ---
        async def run_technical_http(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            bad_pages = [p for p in self._pages if int(p.get("status_code") or 200) >= 400]
            for p in bad_pages:
                u = str(p.get("url"))
                sc = int(p.get("status_code"))
                ev_id = self._add_evidence(
                    url=u, check_id="seo.http.error_status", source_type="http",
                    source_location="http.status_code", observed_value=sc, expected_value=200,
                    result="failed", agent_id="agent_technical_http",
                )
                findings.append(self._add_finding(
                    rule_id="seo.http.error_status", category="TECHNICAL_SEO",
                    severity="CRITICAL" if sc >= 500 else "HIGH",
                    title=f"HTTP {sc} Error Response on Crawled URL",
                    description=f"URL {u} returned HTTP status {sc}.",
                    recommendation="Restore a 200 OK response or configure a single permanent 301 redirect to a valid target.",
                    affected_urls=[u], evidence_ids=[ev_id], agent_id="agent_technical_http",
                ))
            return {"checked_pages": len(self._pages), "error_pages": len(bad_pages), "findings": findings}

        async def run_technical_indexability(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            noindexed = [
                p for p in self._pages
                if "noindex" in str(p.get("robots_meta") or "").lower()
                or "noindex" in str((p.get("response_headers") or {}).get("x-robots-tag", "")).lower()
            ]
            if noindexed:
                urls = [str(p.get("url")) for p in noindexed]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.indexability.noindex", source_type="rendered_dom",
                    source_location="head.meta[name=robots]", observed_value="noindex",
                    expected_value="index, follow (for eligible commercial pages)",
                    result="failed", agent_id="agent_technical_indexability",
                )
                findings.append(self._add_finding(
                    rule_id="seo.indexability.noindex", category="TECHNICAL_SEO", severity="HIGH",
                    title="Indexable Pages Blocked by Noindex Directive",
                    description=f"{len(urls)} crawled URL(s) emit a noindex directive.",
                    recommendation="Remove unintended noindex directives from production pages meant to rank.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_technical_indexability",
                ))
            return {"noindexed_count": len(noindexed), "findings": findings}

        async def run_technical_canonical(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            missing = [p for p in self._pages if not str(p.get("canonical_url") or "").strip()]
            if missing:
                urls = [str(p.get("url")) for p in missing]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.canonical.missing", source_type="rendered_dom",
                    source_location="head.link[rel=canonical]", observed_value=None,
                    expected_value="Absolute self-referencing canonical URL",
                    result="failed", agent_id="agent_technical_canonical",
                )
                findings.append(self._add_finding(
                    rule_id="seo.canonical.missing", category="TECHNICAL_SEO", severity="HIGH",
                    title="Missing Rel=Canonical Link Element",
                    description=f"{len(urls)} crawled URL(s) lack a rel=canonical link tag.",
                    recommendation="Add an absolute self-referencing canonical link element in the shared document head.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_technical_canonical",
                ))
            # Check relative or cross-domain canonical conflicts
            bad_canon = []
            for p in self._pages:
                can = str(p.get("canonical_url") or "").strip()
                if not can:
                    continue
                if not can.startswith(("http://", "https://")):
                    bad_canon.append((str(p.get("url")), can, "relative canonical"))
                else:
                    can_host = urlparse(can).netloc.lower().replace("www.", "")
                    url_host = urlparse(str(p.get("final_url") or p.get("url") or "")).netloc.lower().replace("www.", "")
                    if can_host and url_host and can_host != url_host:
                        bad_canon.append((str(p.get("url")), can, f"cross-domain canonical ({can_host} != {url_host})"))
            if bad_canon:
                urls = [u for u, _, _ in bad_canon]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.canonical.conflict", source_type="rendered_dom",
                    source_location="head.link[rel=canonical]", observed_value=bad_canon[0][1],
                    expected_value="Absolute same-domain canonical URL",
                    result="failed", agent_id="agent_technical_canonical",
                )
                findings.append(self._add_finding(
                    rule_id="seo.canonical.conflict", category="TECHNICAL_SEO", severity="HIGH",
                    title="Invalid or Cross-Domain Canonical URL Detected",
                    description=f"{len(urls)} URL(s) declare relative or cross-domain canonical targets ({bad_canon[0][2]}).",
                    recommendation="Use absolute same-host canonical URLs matching the final 200 OK destination.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_technical_canonical",
                ))
            return {"missing_canonical_count": len(missing), "conflict_canonical_count": len(bad_canon), "findings": findings}

        async def run_technical_rendering(ctx: Dict[str, Any]) -> Dict[str, Any]:
            from app.seo.analyzers.rendering_disparity import analyze_rendering_disparity
            findings = []
            disparity_urls = []
            for p in self._pages[:8]:
                raw, rend = p.get("raw_html"), p.get("rendered_html")
                if raw and rend and raw != rend:
                    disp, _ = analyze_rendering_disparity(str(raw), str(rend), str(p.get("url") or ""))
                    if disp.get("has_disparity") or disp.get("has_discrepancy"):
                        disparity_urls.append(str(p.get("url")))
            if disparity_urls:
                ev_id = self._add_evidence(
                    url=disparity_urls[0], check_id="seo.rendering.js_disparity", source_type="rendered_dom",
                    source_location="raw_vs_rendered_dom", observed_value="client_js_dependency",
                    expected_value="Core content & metadata present in raw HTML",
                    result="failed", agent_id="agent_technical_rendering",
                )
                findings.append(self._add_finding(
                    rule_id="seo.rendering.js_disparity", category="TECHNICAL_SEO", severity="HIGH",
                    title="Raw HTML vs. Rendered DOM Parity Discrepancy",
                    description=f"{len(disparity_urls)} URL(s) rely on client-side JS injection for critical SEO markup.",
                    recommendation="Use SSR or static prerendering so primary headings, content, and canonicals exist in raw HTML.",
                    affected_urls=disparity_urls, evidence_ids=[ev_id], agent_id="agent_technical_rendering",
                ))
            return {"disparity_urls": disparity_urls, "findings": findings}

        async def run_technical_cwv(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            slow = [p for p in self._pages if isinstance(p.get("ttfb_ms"), (int, float)) and float(p["ttfb_ms"]) > 800.0]
            if slow:
                urls = [str(p.get("url")) for p in slow]
                worst = max(float(p["ttfb_ms"]) for p in slow)
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.performance.slow_ttfb", source_type="http",
                    source_location="http.ttfb_ms", observed_value=worst, expected_value="<= 800ms",
                    result="failed", agent_id="agent_technical_cwv",
                )
                findings.append(self._add_finding(
                    rule_id="seo.performance.slow_ttfb", category="PERFORMANCE", severity="MEDIUM",
                    title="Elevated Server Response Time (TTFB > 800ms)",
                    description=f"{len(urls)} URL(s) exceeded 800ms TTFB (worst: {worst:.0f}ms, lab measurement).",
                    recommendation="Enable edge/CDN caching, compress responses, and optimize backend query latency.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_technical_cwv",
                ))
            return {"slow_ttfb_pages": len(slow), "measurement_type": "lab", "findings": findings}

        async def run_technical_mobile(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            no_vp = [p for p in self._pages if p.get("has_viewport") is False or p.get("mobile_viewport") is False]
            if no_vp:
                urls = [str(p.get("url")) for p in no_vp]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.mobile.missing_viewport", source_type="rendered_dom",
                    source_location="head.meta[name=viewport]", observed_value=None,
                    expected_value="width=device-width, initial-scale=1",
                    result="failed", agent_id="agent_technical_mobile",
                )
                findings.append(self._add_finding(
                    rule_id="seo.mobile.missing_viewport", category="TECHNICAL_SEO", severity="HIGH",
                    title="Missing Responsive Viewport Meta Tag",
                    description=f"{len(urls)} page(s) lack a mobile viewport meta tag.",
                    recommendation="Add <meta name='viewport' content='width=device-width, initial-scale=1'>.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_technical_mobile",
                ))
            return {"missing_viewport_count": len(no_vp), "findings": findings}

        # --- Dept C: On-Page SEO (5 specialists) ---
        async def run_onpage_metadata(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            no_title = [p for p in self._pages if not str(p.get("title") or "").strip()]
            if no_title:
                urls = [str(p.get("url")) for p in no_title]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.title.missing", source_type="rendered_dom",
                    source_location="head.title", observed_value=None,
                    expected_value="Descriptive unique page title",
                    result="failed", agent_id="agent_onpage_metadata",
                )
                findings.append(self._add_finding(
                    rule_id="seo.title.missing", category="ON_PAGE_SEO", severity="HIGH",
                    title="Missing Primary Title Tag",
                    description=f"{len(urls)} page(s) lack a populated <title> tag in rendered DOM.",
                    recommendation="Add unique, descriptive page titles in the shared page metadata template.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_onpage_metadata",
                ))
            no_desc = [p for p in self._pages if not str(p.get("meta_description") or "").strip()]
            if no_desc:
                urls = [str(p.get("url")) for p in no_desc]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.meta_description.missing", source_type="rendered_dom",
                    source_location="head.meta[name=description]", observed_value=None,
                    expected_value="Descriptive unique meta description",
                    result="failed", agent_id="agent_onpage_metadata",
                )
                findings.append(self._add_finding(
                    rule_id="seo.meta_description.missing", category="ON_PAGE_SEO", severity="MEDIUM",
                    title="Missing Meta Description",
                    description=f"{len(urls)} page(s) have no meta description tag.",
                    recommendation="Populate unique meta descriptions summarizing page intent.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_onpage_metadata",
                ))
            return {"missing_titles": len(no_title), "missing_descriptions": len(no_desc), "findings": findings}

        async def run_onpage_headings(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            no_h1 = [
                p for p in self._pages
                if not (p.get("h1") if isinstance(p.get("h1"), list) else ([p.get("h1")] if p.get("h1") else []))
            ]
            if no_h1:
                urls = [str(p.get("url")) for p in no_h1]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.h1.missing", source_type="rendered_dom",
                    source_location="body.h1", observed_value=0, expected_value=1,
                    result="failed", agent_id="agent_onpage_headings",
                )
                findings.append(self._add_finding(
                    rule_id="seo.h1.missing", category="ON_PAGE_SEO", severity="MEDIUM",
                    title="Missing Primary H1 Heading",
                    description=f"{len(urls)} inspected URL(s) contain no <h1> element in rendered DOM.",
                    recommendation="Add one visible, descriptive <h1> heading per page template.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_onpage_headings",
                ))
            return {"missing_h1_count": len(no_h1), "findings": findings}

        async def run_onpage_media(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            alt_gaps = [p for p in self._pages if int(p.get("images_without_alt") or 0) > 0]
            if alt_gaps:
                urls = [str(p.get("url")) for p in alt_gaps]
                total_missing = sum(int(p.get("images_without_alt") or 0) for p in alt_gaps)
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.images.missing_alt", source_type="rendered_dom",
                    source_location="img[alt]", observed_value=total_missing, expected_value=0,
                    result="failed", agent_id="agent_onpage_media",
                )
                findings.append(self._add_finding(
                    rule_id="seo.images.missing_alt", category="ON_PAGE_SEO", severity="LOW",
                    title="Images Missing Descriptive Alt Attributes",
                    description=f"{total_missing} image(s) across {len(urls)} URL(s) lack alt text.",
                    recommendation="Add concise descriptive alt attributes to informative images and empty alt='' to decorative ones.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_onpage_media",
                ))
            return {"pages_with_alt_gaps": len(alt_gaps), "findings": findings}

        async def run_onpage_linking(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.link_graph = build_internal_link_graph(self._pages, domain=self.domain)
            summary = self.link_graph.get("summary", {})
            findings = []
            if summary.get("orphan_count", 0) > 0:
                orphans = [n["url"] for n in self.link_graph["nodes"] if n["status"] == "orphan"]
                ev_id = self._add_evidence(
                    url=orphans[0], check_id="seo.links.orphan_pages", source_type="rendered_dom",
                    source_location="link_graph.in_degree", observed_value=0, expected_value=">= 1",
                    result="failed", agent_id="agent_onpage_linking",
                )
                findings.append(self._add_finding(
                    rule_id="seo.links.orphan_pages", category="TECHNICAL_SEO", severity="MEDIUM",
                    title="Orphan Pages Detected in Crawled Link Graph",
                    description=f"{len(orphans)} crawled URL(s) have 0 incoming internal links in the measured crawl sample.",
                    recommendation="Link orphan URLs contextually from relevant hub or category pages.",
                    affected_urls=orphans, evidence_ids=[ev_id], agent_id="agent_onpage_linking",
                ))
            return {"summary": summary, "findings": findings}

        async def run_onpage_url_opt(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            param_urls = [str(p.get("url")) for p in self._pages if "?" in str(p.get("url") or "")]
            if param_urls:
                ev_id = self._add_evidence(
                    url=param_urls[0], check_id="seo.url.query_parameters", source_type="http",
                    source_location="url.query", observed_value=len(param_urls), expected_value=0,
                    result="failed", agent_id="agent_onpage_url_optimization",
                )
                findings.append(self._add_finding(
                    rule_id="seo.url.query_parameters", category="ON_PAGE_SEO", severity="LOW",
                    title="Parameterized URLs Observed in Crawled Inventory",
                    description=f"{len(param_urls)} crawled URL(s) include query parameters that may cause duplicate crawling.",
                    recommendation="Canonicalize parameterized URLs to their clean parent path or manage crawl rules.",
                    affected_urls=param_urls, evidence_ids=[ev_id], agent_id="agent_onpage_url_optimization",
                ))
            return {"parameterized_urls": len(param_urls), "findings": findings}

        # --- Dept D: Content & Semantic Intelligence (5 specialists) ---
        async def run_content_quality(ctx: Dict[str, Any]) -> Dict[str, Any]:
            findings = []
            thin = [p for p in self._pages if int(p.get("word_count") or 0) < 200 and p.get("crawl_source") != "unfetched_seed"]
            if thin:
                urls = [str(p.get("url")) for p in thin]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.content.thin_pages", source_type="rendered_dom",
                    source_location="body.word_count", observed_value=int(thin[0].get("word_count") or 0),
                    expected_value=">= 200 substantive words", result="failed", agent_id="agent_content_quality",
                )
                findings.append(self._add_finding(
                    rule_id="seo.content.thin_pages", category="CONTENT", severity="MEDIUM",
                    title="Low Extracted Word Count / Thin Content Candidate",
                    description=f"{len(urls)} page(s) had fewer than 200 extracted words.",
                    recommendation="Expand primary editorial copy with substantive answers and product/service detail.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_content_quality",
                ))
            return {"thin_pages": len(thin), "findings": findings}

        async def run_content_intent(ctx: Dict[str, Any]) -> Dict[str, Any]:
            classified = []
            for p in self._pages:
                path = urlparse(str(p.get("url") or "")).path.lower()
                if any(k in path for k in ("pricing", "buy", "checkout", "cart", "product")):
                    intent = "transactional"
                elif any(k in path for k in ("compare", "vs", "review", "service", "solution")):
                    intent = "commercial"
                elif any(k in path for k in ("blog", "guide", "learn", "docs", "faq")):
                    intent = "informational"
                elif any(k in path for k in ("contact", "location", "store")):
                    intent = "local"
                else:
                    intent = "navigational"
                classified.append({"url": p.get("url"), "intent": intent})
            return {"classified_pages": len(classified), "intents": classified, "findings": []}

        async def run_content_semantic(ctx: Dict[str, Any]) -> Dict[str, Any]:
            headings = []
            for p in self._pages:
                for h in (p.get("h1") or []) + (p.get("h2") or []):
                    if isinstance(h, str) and h.strip():
                        headings.append(h.strip())
            return {"extracted_concepts": list(dict.fromkeys(headings))[:30], "findings": []}

        async def run_content_topical_authority(ctx: Dict[str, Any]) -> Dict[str, Any]:
            title_groups: Dict[str, List[str]] = {}
            for p in self._pages:
                t = str(p.get("title") or "").strip().lower()
                if t:
                    title_groups.setdefault(t, []).append(str(p.get("url")))
            cannibal_groups = {t: urls for t, urls in title_groups.items() if len(urls) > 1}
            findings = []
            for dup_title, urls in cannibal_groups.items():
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.content.cannibalization_title_overlap", source_type="rendered_dom",
                    source_location="head.title", observed_value=dup_title, expected_value="Distinct primary topic per URL",
                    result="failed", agent_id="agent_content_topical_authority",
                )
                findings.append(self._add_finding(
                    rule_id="seo.content.cannibalization_title_overlap", category="CONTENT", severity="MEDIUM",
                    title=f"Duplicate Title / Potential Keyword Cannibalization ({dup_title[:60]})",
                    description=f"{len(urls)} URLs share identical title '{dup_title}'.",
                    recommendation="Differentiate target search intent and titles or consolidate overlapping pages.",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_content_topical_authority",
                ))
            return {"cannibalization_clusters": len(cannibal_groups), "findings": findings}

        async def run_content_gap(ctx: Dict[str, Any]) -> Dict[str, Any]:
            return {"evaluated_pages": len(self._pages), "competitor_source_connected": False, "findings": []}

        # --- Dept E: Structured Data & Entities (4 specialists) ---
        async def run_schema_detection(ctx: Dict[str, Any]) -> Dict[str, Any]:
            detected_types = sorted({str(s) for p in self._pages for s in (p.get("schema_types") or []) if s})
            return {"detected_schema_types": detected_types, "pages_with_schema": sum(1 for p in self._pages if p.get("schema_types")), "findings": []}

        async def run_schema_validator(ctx: Dict[str, Any]) -> Dict[str, Any]:
            from app.seo.analyzers.schema_validator import analyze_schema_rich_results
            from app.domain.models import PageEvidence
            findings = []
            no_schema = [p for p in self._pages if not (p.get("schema_types") or [])]
            if no_schema and len(no_schema) == len(self._pages):
                urls = [str(p.get("url")) for p in no_schema]
                ev_id = self._add_evidence(
                    url=urls[0], check_id="seo.schema.missing", source_type="rendered_dom",
                    source_location="script[type='application/ld+json']", observed_value=[],
                    expected_value="Valid Organization/WebSite or page-appropriate JSON-LD",
                    result="failed", agent_id="agent_schema_validator",
                )
                findings.append(self._add_finding(
                    rule_id="seo.schema.missing", category="STRUCTURED_DATA", severity="MEDIUM",
                    title="No Structured Data (JSON-LD) Detected on Inspected Pages",
                    description=f"0 JSON-LD/Microdata schema blocks detected across {len(urls)} inspected URL(s).",
                    recommendation="Implement valid Schema.org JSON-LD (Organization, WebSite, BreadcrumbList, and page-type schema).",
                    affected_urls=urls, evidence_ids=[ev_id], agent_id="agent_schema_validator",
                ))
            else:
                schema_pages = [p for p in self._pages if p.get("raw_schema")]
                if schema_pages:
                    pe_list = [
                        PageEvidence(
                            url=str(p.get("url") or self.config.target_url),
                            status_code=int(p.get("status_code") or 200),
                            title=p.get("title"),
                            schema_types=list(p.get("schema_types") or []),
                            raw_schema=list(p.get("raw_schema") or []),
                        )
                        for p in schema_pages
                    ]
                    val_rep = analyze_schema_rich_results(pe_list)
                    invalid_issues = [
                        iss for iss in (getattr(val_rep, "issues", None) or [])
                        if str(getattr(iss, "severity", "")).upper() in ("ERROR", "CRITICAL", "HIGH")
                    ]
                    if invalid_issues:
                        affected = sorted({str(getattr(iss, "url", self.config.target_url)) for iss in invalid_issues})
                        ev_id = self._add_evidence(
                            url=affected[0], check_id="seo.schema.validation_errors", source_type="rendered_dom",
                            source_location="script[type='application/ld+json']",
                            observed_value=getattr(invalid_issues[0], "message", "Schema validation error"),
                            expected_value="Schema.org compliant JSON-LD with required fields",
                            result="failed", agent_id="agent_schema_validator",
                        )
                        findings.append(self._add_finding(
                            rule_id="seo.schema.validation_errors", category="STRUCTURED_DATA", severity="MEDIUM",
                            title=f"Structured Data Validation Errors ({len(invalid_issues)} issue(s))",
                            description=f"Schema validator found {len(invalid_issues)} error(s): {getattr(invalid_issues[0], 'message', '')}",
                            recommendation="Fix missing required Schema.org properties and deprecated types in JSON-LD blocks.",
                            affected_urls=affected, evidence_ids=[ev_id], agent_id="agent_schema_validator",
                        ))
            status_str = "MISSING" if (no_schema and len(no_schema) == len(self._pages)) else ("ERRORS" if findings else "VALID")
            return {"schema_validity_status": status_str, "findings": findings}

        async def run_entity_graph(ctx: Dict[str, Any]) -> Dict[str, Any]:
            types = sorted({str(s) for p in self._pages for s in (p.get("schema_types") or [])})
            return {"entity_types": types, "organization_linked": "Organization" in types, "findings": []}

        async def run_rich_results(ctx: Dict[str, Any]) -> Dict[str, Any]:
            types = {str(s) for p in self._pages for s in (p.get("schema_types") or [])}
            eligible = sorted(types.intersection({"Product", "Article", "BreadcrumbList", "FAQPage", "LocalBusiness", "Review"}))
            return {
                "schema_validity_status": "VALID" if types else "NONE_DETECTED",
                "rich_result_eligibility_status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
                "observed_serp_appearance_status": "UNMEASURED_WITHOUT_GSC",
                "eligible_types": eligible,
                "findings": [],
            }

        # --- Dept F: Authority & Trust (4 specialists) ---
        async def run_authority_eeat(ctx: Dict[str, Any]) -> Dict[str, Any]:
            urls_lower = [str(p.get("url") or "").lower() for p in self._pages]
            has_about = any("about" in u for u in urls_lower)
            has_contact = any("contact" in u for u in urls_lower)
            return {
                "observable_signals": {"about_page": has_about, "contact_page": has_contact},
                "note": "Observable trust signals only; not a fabricated Google ranking score.",
                "findings": [],
            }

        async def run_authority_trust(ctx: Dict[str, Any]) -> Dict[str, Any]:
            non_https = [str(p.get("url")) for p in self._pages if str(p.get("url") or "").startswith("http://")]
            findings = []
            if non_https:
                ev_id = self._add_evidence(
                    url=non_https[0], check_id="seo.security.non_https", source_type="http",
                    source_location="url.scheme", observed_value="http", expected_value="https",
                    result="failed", agent_id="agent_authority_trust",
                )
                findings.append(self._add_finding(
                    rule_id="seo.security.non_https", category="TECHNICAL_SEO", severity="HIGH",
                    title="Non-HTTPS URL Served in Crawled Sample",
                    description=f"{len(non_https)} URL(s) served over unencrypted HTTP.",
                    recommendation="Enforce HTTPS with 301 redirects and HSTS header.",
                    affected_urls=non_https, evidence_ids=[ev_id], agent_id="agent_authority_trust",
                ))
            return {"non_https_count": len(non_https), "findings": findings}

        # --- Dept G & H: Local, International, Ecommerce (Conditional) ---
        async def run_specialist_local(ctx: Dict[str, Any]) -> Dict[str, Any]:
            has_local = any("LocalBusiness" in (p.get("schema_types") or []) or "/location" in str(p.get("url") or "").lower() for p in self._pages)
            self._specialist_applicable["local"] = has_local
            return {"node_status": "COMPLETED" if has_local else "NOT_APPLICABLE", "applicable": has_local, "findings": []}

        async def run_specialist_international(ctx: Dict[str, Any]) -> Dict[str, Any]:
            has_intl = any(bool(p.get("hreflang_tags") or p.get("hreflang")) for p in self._pages)
            self._specialist_applicable["international"] = has_intl
            return {"node_status": "COMPLETED" if has_intl else "NOT_APPLICABLE", "applicable": has_intl, "findings": []}

        async def run_international_hreflang(ctx: Dict[str, Any]) -> Dict[str, Any]:
            has_intl = self._specialist_applicable["international"]
            return {"node_status": "COMPLETED" if has_intl else "NOT_APPLICABLE", "applicable": has_intl, "findings": []}

        async def run_ecommerce_check(ctx: Dict[str, Any]) -> Dict[str, Any]:
            has_ecom = any(
                "Product" in (p.get("schema_types") or [])
                or any(k in str(p.get("url") or "").lower() for k in ("/product", "/shop", "/collection", "/cart"))
                for p in self._pages
            )
            self._specialist_applicable["ecommerce"] = has_ecom
            return {"node_status": "COMPLETED" if has_ecom else "NOT_APPLICABLE", "applicable": has_ecom, "findings": []}

        # --- Stages 6–11: Normalization, Deduplication, Scoring, Dept J (Roles 39–40), Publisher ---
        async def run_output_normalizer(ctx: Dict[str, Any]) -> Dict[str, Any]:
            return {"raw_findings": len(self._raw_findings), "evidence_records": len(self._evidence_records)}

        async def run_finding_deduplicator(ctx: Dict[str, Any]) -> Dict[str, Any]:
            by_key: Dict[str, Dict[str, Any]] = {}
            for f in self._raw_findings:
                key = f"{f['rule_id']}::{f['root_cause_id']}"
                if key not in by_key:
                    by_key[key] = dict(f)
                else:
                    existing = by_key[key]
                    merged_urls = list(dict.fromkeys(existing["affected_urls"] + f["affected_urls"]))
                    merged_ev = list(dict.fromkeys(existing["evidence_ids"] + f["evidence_ids"]))
                    existing["affected_urls"] = merged_urls
                    existing["affected_url_count"] = len(merged_urls)
                    existing["evidence_ids"] = merged_ev
                    existing["evidence_refs"] = merged_ev
            self._deduped_findings = list(by_key.values())
            self.events.emit("findings.validated", {"findings_count": len(self._deduped_findings)})
            return {"deduplicated_findings": len(self._deduped_findings)}

        async def run_scoring_engine(ctx: Dict[str, Any]) -> Dict[str, Any]:
            engine = MathematicalScoreEngine()
            conn_statuses = [c.model_dump() for c in self.connectors.list_all_connectors(workspace_id=self.config.workspace_id)]
            discovered = int(self._crawl_manifest.get("total_pages_discovered") or len(self._pages))
            crawled = len(self._pages)
            sampling_status = "SAMPLED_AUDIT" if discovered > crawled or self.config.mode == AuditMode.QUICK else "FULL_CRAWL"
            self.scorecard = engine.build_scorecard_from_observations(
                pages=self._pages,
                findings=self._deduped_findings,
                evidence_records=self._evidence_records,
                discovered_count=discovered,
                crawled_count=crawled,
                sampling_status=sampling_status,
                connector_statuses=conn_statuses,
                specialist_applicable=self._specialist_applicable,
            )
            self.events.emit("scoring.completed", {
                "overall_score": self.scorecard.overall_health_score,
                "score_status": self.scorecard.score_status,
                "methodology_version": self.scorecard.methodology_version,
            })
            return {"overall_score": self.scorecard.overall_health_score, "score_status": self.scorecard.score_status}

        async def run_remediation_planner(ctx: Dict[str, Any]) -> Dict[str, Any]:
            if ctx.get("is_unified_pipeline", False) or getattr(self.config, "defer_remediation", False):
                self.remediation_tasks = []
                self.events.emit("remediation.deferred", {"message": "SEO remediation deferred to Unified Cross-Pillar Remediation Pack"})
                return {"tasks_count": 0, "status": "DEFERRED_TO_UNIFIED_PACK"}

            remed_engine = PostAuditRemediationEngine()
            self.remediation_tasks = remed_engine.synthesize_remediation_plan(
                self._deduped_findings,
                server_headers=self._detected_headers,
                dom_sample=self._detected_dom_sample,
            )
            self.events.emit("remediation.generated", {"tasks_count": len(self.remediation_tasks)})
            return {"tasks_count": len(self.remediation_tasks)}

        async def run_validation_gate(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.events.emit("qa.started", {"audit_id": self.audit_id})
            validator = SeoQaValidator()
            discovered = int(self._crawl_manifest.get("total_pages_discovered") or len(self._pages))
            crawled = len(self._pages)
            sampling = "SAMPLED_AUDIT" if discovered > crawled or self.config.mode == AuditMode.QUICK else "FULL_CRAWL"
            assessment_proxy = {
                "audit_run_id": self.audit_id,
                "schema_version": "seo.enterprise.v1",
                "findings": self._deduped_findings,
                "evidence": self._evidence_records,
                "coverage": {
                    "urls_discovered": discovered,
                    "urls_crawled": crawled,
                    "sampling_status": sampling,
                },
                "mathematical_scorecard": self.scorecard.model_dump() if self.scorecard else None,
            }
            report_proxy = {
                "analysis_id": self.audit_id,
                "crawl_manifest": self._crawl_manifest,
                "findings": self._deduped_findings,
                "evidence": self._evidence_records,
                "mathematical_scorecard": self.scorecard.model_dump() if self.scorecard else None,
                "methodology_version": MathematicalScoreEngine.METHODOLOGY_VERSION,
                "executive_summary_finding_count": len(self._deduped_findings),
                "failed_agents_count": len(self.state.failed_tasks),
            }
            self.qa_report = validator.validate(assessment_proxy, report_proxy)
            self.events.emit("qa.completed", {
                "is_certified": self.qa_report.is_certified,
                "status": self.qa_report.status,
                "blockers_count": self.qa_report.blockers_count,
            })
            return self.qa_report.model_dump()

        async def run_canonical_publisher(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.canonical_assessment = self.publish_canonical_result()
            return {"published": True, "findings_count": len(self._deduped_findings)}

        # Register ALL 46 runners explicitly (zero missing runners!)
        runner_map = {
            "discovery_sitemap": run_discovery_sitemap,
            "agent_sitemap_validator": run_sitemap_validator,
            "url_inventory": run_url_inventory,
            "agent_crawl_strategy": run_crawl_strategy,
            "crawler_engine": run_crawler_engine,
            "evidence_extractor": run_evidence_extractor,
            "agent_technical_http": run_technical_http,
            "agent_technical_indexability": run_technical_indexability,
            "agent_technical_canonical": run_technical_canonical,
            "agent_technical_rendering": run_technical_rendering,
            "agent_technical_cwv": run_technical_cwv,
            "agent_technical_mobile": run_technical_mobile,
            "agent_onpage_metadata": run_onpage_metadata,
            "agent_onpage_headings": run_onpage_headings,
            "agent_onpage_media": run_onpage_media,
            "agent_onpage_linking": run_onpage_linking,
            "agent_onpage_url_optimization": run_onpage_url_opt,
            "agent_content_quality": run_content_quality,
            "agent_content_intent": run_content_intent,
            "agent_content_semantic": run_content_semantic,
            "agent_content_topical_authority": run_content_topical_authority,
            "agent_content_gap": run_content_gap,
            "agent_schema_detection": run_schema_detection,
            "agent_schema_validator": run_schema_validator,
            "agent_entity_graph": run_entity_graph,
            "agent_rich_results": run_rich_results,
            "agent_authority_backlinks": make_connector_runner("agent_authority_backlinks", "backlink_provider", "Backlink Intelligence"),
            "agent_authority_referring_domains": make_connector_runner("agent_authority_referring_domains", "backlink_provider", "Referring Domains"),
            "agent_authority_eeat": run_authority_eeat,
            "agent_authority_trust": run_authority_trust,
            "agent_specialist_local": run_specialist_local,
            "agent_local_gbp": make_connector_runner("agent_local_gbp", "google_business_profile", "Google Business Profile"),
            "agent_specialist_international": run_specialist_international,
            "agent_international_hreflang": run_international_hreflang,
            "agent_ecommerce_product": run_ecommerce_check,
            "agent_ecommerce_category": run_ecommerce_check,
            "agent_specialist_ecommerce": run_ecommerce_check,
            "agent_search_console": make_connector_runner("agent_search_console", "google_search_console", "Google Search Console"),
            "agent_ga4_analytics": make_connector_runner("agent_ga4_analytics", "google_analytics_4", "Google Analytics 4"),
            "agent_competitor_seo": make_connector_runner("agent_competitor_seo", "keyword_serp_provider", "Competitor SERP Intelligence"),
            "output_normalizer": run_output_normalizer,
            "finding_deduplicator": run_finding_deduplicator,
            "scoring_engine": run_scoring_engine,
            "remediation_planner": run_remediation_planner,
            "validation_gate": run_validation_gate,
            "canonical_publisher": run_canonical_publisher,
        }
        for agent_id, fn in runner_map.items():
            self.executor.register_runner(agent_id, fn)

    def cancel(self) -> None:
        self.state.cancellation_requested = True
        self.state.status = WorkflowStatus.CANCELLED
        self.events.emit("audit.cancelled", {"reason": "User requested cancellation"})

    def pause(self) -> None:
        self.state.status = WorkflowStatus.PAUSED
        self.events.emit("audit.paused", {"completed_tasks": list(self.state.completed_tasks)})

    def _load_checkpoints_from_db(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM seo_agent_executions WHERE audit_id = ? AND status IN ('COMPLETED', 'SKIPPED')",
                (self.audit_id,),
            ).fetchall()
        for r in rows:
            aid = r["agent_id"]
            if aid not in self.state.completed_tasks:
                st = NodeState.SKIPPED if r["status"] == "SKIPPED" else NodeState.COMPLETED
                self.state.checkpoints[aid] = TaskCheckpoint(
                    task_id=aid,
                    agent_id=aid,
                    status=st,
                    inputs_hash=r["inputs_hash"],
                    execution_time_sec=float(r["execution_time_sec"] or 0.0),
                    token_usage=int(r["token_usage"] or 0),
                    estimated_cost_usd=float(r["estimated_cost_usd"] or 0.0),
                    completed_at=r["completed_at"],
                )
                if st == NodeState.SKIPPED:
                    self.state.skipped_tasks.add(aid)
                else:
                    self.state.completed_tasks.add(aid)

    async def resume(self) -> Dict[str, Any]:
        if self.state.status == WorkflowStatus.CANCELLED:
            raise RuntimeError("Cannot resume a cancelled audit run")
        self._load_checkpoints_from_db()
        self.events.emit("audit.resumed", {"completed_checkpoints": len(self.state.checkpoints)})
        return await self.run()

    async def run(self) -> Dict[str, Any]:
        self.state.status = WorkflowStatus.RUNNING
        self.state.start_time = time.monotonic()

        if self.state.cancellation_requested:
            self.state.status = WorkflowStatus.CANCELLED
            self.state.elapsed_time_sec = round(time.monotonic() - self.state.start_time, 3)
            self._persist_final_state()
            return {
                "audit_id": self.audit_id,
                "domain": self.domain,
                "mode": self.config.mode.value,
                "status": "CANCELLED",
                "total_agents": len(self.dag.nodes),
                "specialist_agents_count": len(self.dag.specialist_nodes),
                "executed_agents": 0,
                "failed_agents": 0,
                "execution_time_sec": self.state.elapsed_time_sec,
                "overall_score": None,
                "canonical_assessment": None,
            }

        self.events.emit("audit.started", {
            "mode": self.config.mode.value,
            "target_url": self.config.target_url,
            "total_nodes": len(self.dag.nodes),
            "specialist_roles": len(self.dag.specialist_nodes),
            "budget_seconds": self.budget.max_execution_sec,
        })

        waves = self.dag.get_waves()
        try:
            for wave_idx, wave in enumerate(waves, 1):
                if self.state.cancellation_requested:
                    self.state.status = WorkflowStatus.CANCELLED
                    break

                self.state.current_stage = wave[0].stage.value
                pending_nodes = [
                    node for node in wave
                    if node.agent_id not in self.state.completed_tasks
                    and node.agent_id not in self.state.skipped_tasks
                ]
                if not pending_nodes:
                    continue

                tasks = [self._execute_single_node(node) for node in pending_nodes]
                results: List[TaskCheckpoint] = await asyncio.gather(*tasks, return_exceptions=False)

                for res in results:
                    self.state.checkpoints[res.agent_id] = res
                    self.state.total_tokens += res.token_usage
                    self.state.total_cost_usd = round(self.state.total_cost_usd + res.estimated_cost_usd, 6)
                    self._persist_node_checkpoint(res)

                    if res.status == NodeState.COMPLETED:
                        self.state.completed_tasks.add(res.agent_id)
                        self.events.emit("agent.completed", {
                            "agent_id": res.agent_id,
                            "findings_count": res.findings_count,
                            "elapsed_sec": res.execution_time_sec,
                        })
                    elif res.status == NodeState.SKIPPED:
                        self.state.skipped_tasks.add(res.agent_id)
                        self.state.completed_tasks.add(res.agent_id)
                        self.events.emit("agent.completed", {
                            "agent_id": res.agent_id,
                            "status": "SKIPPED",
                            "elapsed_sec": res.execution_time_sec,
                        })
                    else:
                        self.state.failed_tasks.add(res.agent_id)
                        self.events.emit("agent.failed", {
                            "agent_id": res.agent_id,
                            "error": res.error_message,
                        })
                        if self.config.failure_policy == FailurePolicy.FAIL_FAST:
                            self.state.status = WorkflowStatus.FAILED
                            raise RuntimeError(f"Workflow failed at node '{res.agent_id}': {res.error_message}")

            if not self.state.cancellation_requested and self.state.status != WorkflowStatus.FAILED:
                self.state.status = WorkflowStatus.PARTIAL if self.state.failed_tasks else WorkflowStatus.COMPLETED

        except Exception as exc:
            self.state.status = WorkflowStatus.FAILED
            self.events.emit("audit.failed", {"error": str(exc)})
            raise
        finally:
            self.state.elapsed_time_sec = round(time.monotonic() - (self.state.start_time or time.monotonic()), 3)
            self._persist_final_state()

        if self.canonical_assessment is None:
            self.canonical_assessment = self.publish_canonical_result()
            self._persist_final_state()

        terminal_event = "audit.partial" if self.state.status == WorkflowStatus.PARTIAL else "audit.completed"
        self.events.emit(terminal_event, {
            "status": self.state.status.value,
            "findings_count": len(self._deduped_findings),
            "overall_score": self.scorecard.overall_health_score if self.scorecard else None,
            "qa_status": self.qa_report.status if self.qa_report else "PENDING",
        })

        return {
            "audit_id": self.audit_id,
            "domain": self.domain,
            "mode": self.config.mode.value,
            "status": self.state.status.value,
            "total_agents": len(self.dag.nodes),
            "specialist_agents_count": len(self.dag.specialist_nodes),
            "executed_agents": len(self.state.completed_tasks),
            "failed_agents": len(self.state.failed_tasks),
            "execution_time_sec": self.state.elapsed_time_sec,
            "total_tokens": self.state.total_tokens,
            "total_cost_usd": self.state.total_cost_usd,
            "overall_score": self.scorecard.overall_health_score if self.scorecard else None,
            "qa_status": self.qa_report.status if self.qa_report else "PENDING",
            "canonical_assessment": self.canonical_assessment,
        }

    async def _execute_single_node(self, node: DAGNode) -> TaskCheckpoint:
        self.state.active_tasks.add(node.agent_id)
        self.events.emit("agent.started", {
            "agent_id": node.agent_id,
            "agent_name": node.agent_name,
            "department": node.department,
        })
        context = {
            "audit_id": self.audit_id,
            "domain": self.domain,
            "target_url": self.config.target_url,
            "mode": self.config.mode.value,
            "completed_checkpoints": self.state.checkpoints,
            "enable_cache": True,
        }

        def on_retry(agent_id: str, attempt: int, exc: Exception):
            self.events.emit("agent.progress", {"agent_id": agent_id, "retry_attempt": attempt, "error": str(exc)})

        checkpoint = await self.executor.execute_task(node, context, on_retry=on_retry)
        self.state.active_tasks.discard(node.agent_id)
        return checkpoint

    def publish_canonical_result(self) -> Dict[str, Any]:
        """Builds, seals, and persists the single-source-of-truth canonical SEO audit dataset."""
        numbers = self._coverage_numbers()
        discovered = numbers["discovered"]
        crawled = numbers["crawled"]
        rendered = numbers["rendered"]
        deep = numbers["deep"]
        sampling = "SAMPLED_AUDIT" if discovered > crawled or self.config.mode == AuditMode.QUICK else "FULL_CRAWL"
        defect_urls = {u for f in self._deduped_findings for u in (f.get("affected_urls") or []) if u}

        report_payload: Dict[str, Any] = {
            "analysis_id": self.audit_id,
            "report_id": f"rep_{self.audit_id}",
            "domain": self.domain,
            "target_url": self.config.target_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "crawl_manifest": {
                **self._crawl_manifest,
                "domain": self.domain,
                "total_pages_discovered": discovered,
                "total_pages_crawled": crawled,
                "sampling_status": sampling,
                "pages": self._pages,
            },
            "findings": self._deduped_findings,
            "scores": {
                "technical_score": self.scorecard.overall_health_score if self.scorecard else None,
            },
        }

        enterprise_obj = build_enterprise_seo(report_payload)
        result_dict = enterprise_obj.model_dump()
        result_dict["coverage"]["urls_discovered"] = discovered
        result_dict["coverage"]["urls_crawled"] = crawled
        result_dict["coverage"]["urls_rendered"] = rendered
        result_dict["coverage"]["urls_deeply_inspected"] = deep
        result_dict["coverage"]["full_site_audit"] = bool((self._crawl_manifest.get("page_template") or {}).get("full_site_audit"))
        template_statement = (self._crawl_manifest.get("page_template") or {}).get("statement")
        if template_statement:
            result_dict["coverage"]["statement"] = template_statement
        result_dict["coverage"]["urls_with_verified_findings"] = len(defect_urls)
        result_dict["coverage"]["sampling_status"] = sampling
        result_dict["coverage"]["urls_tested_by_specialist"] = {
            "technical_seo": crawled,
            "on_page_seo": crawled,
            "structured_data": crawled,
            "internal_linking": crawled,
        }
        result_dict["findings"] = self._deduped_findings
        result_dict["evidence"] = self._evidence_records
        result_dict["canonical_findings"] = self._deduped_findings
        result_dict["canonical_evidence"] = self._evidence_records
        result_dict["mathematical_scorecard"] = self.scorecard.model_dump(mode="json") if self.scorecard else None
        result_dict["remediation_tasks"] = [t.model_dump() for t in self.remediation_tasks]
        result_dict["qa_certification"] = self.qa_report.model_dump() if self.qa_report else None
        result_dict["internal_link_graph"] = self.link_graph
        result_dict["connectors"] = [
            c.model_dump() for c in self.connectors.list_all_connectors(workspace_id=self.config.workspace_id)
        ]
        result_dict["agent_executions"] = [
            {
                "agent_id": n.agent_id,
                "agent_name": n.agent_name,
                "department": n.department,
                "execution_mode": n.execution_mode,
                "status": self.state.checkpoints[n.agent_id].status.value if n.agent_id in self.state.checkpoints else "PENDING",
                "runtime_ms": round((self.state.checkpoints[n.agent_id].execution_time_sec if n.agent_id in self.state.checkpoints else 0.0) * 1000, 1),
                "findings_count": self.state.checkpoints[n.agent_id].findings_count if n.agent_id in self.state.checkpoints else 0,
            }
            for n in self.dag.specialist_nodes
        ]
        self._persist_canonical_entities(result_dict)
        return result_dict

    def _persist_node_checkpoint(self, cp: TaskCheckpoint) -> None:
        now = datetime.now(timezone.utc).isoformat()
        exec_id = f"exec_{self.audit_id}_{cp.agent_id}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_agent_executions (
                    id, audit_id, org_id, workspace_id, agent_id, status,
                    inputs_hash, execution_time_sec, token_usage, estimated_cost_usd,
                    error_message, completed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exec_id, self.audit_id, self.config.org_id, self.config.workspace_id,
                    cp.agent_id, cp.status.value, cp.inputs_hash, cp.execution_time_sec,
                    cp.token_usage, cp.estimated_cost_usd, cp.error_message, cp.completed_at or now, now,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_agent_outputs (
                    id, execution_id, audit_id, workspace_id, agent_id, findings_count, output_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"out_{exec_id}", exec_id, self.audit_id, self.config.workspace_id,
                    cp.agent_id, cp.findings_count, json.dumps(cp.output_summary, default=str),
                ),
            )
            conn.execute(
                "UPDATE seo_workflow_tasks SET status = ?, completed_at = ? WHERE id = ?",
                (cp.status.value, cp.completed_at or now, f"{self.audit_id}:{cp.agent_id}"),
            )
            conn.commit()

    def _persist_canonical_entities(self, result_dict: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        session_id = f"sess_{self.audit_id}"
        cov = result_dict.get("coverage", {})
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_crawl_sessions (
                    id, audit_id, org_id, workspace_id, pages_discovered, pages_crawled,
                    pages_rendered, pages_deeply_inspected, pages_with_verified_findings,
                    sampling_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, self.audit_id, self.config.org_id, self.config.workspace_id,
                    int(cov.get("urls_discovered") or 0), int(cov.get("urls_crawled") or 0),
                    int(cov.get("urls_rendered") or 0), int(cov.get("urls_deeply_inspected") or 0),
                    int(cov.get("urls_with_verified_findings") or 0), str(cov.get("sampling_status") or "SAMPLED_AUDIT"),
                ),
            )
            seen_urls = set()
            inventory_rows = list(self._pages)
            known = {str(p.get("url") or "") for p in self._pages}
            for url in list(self._crawl_manifest.get("discovered_urls") or []):
                if url and url not in known:
                    inventory_rows.append({"url": url, "crawl_source": "discovered_only"})
                    known.add(url)
            for idx, p in enumerate(inventory_rows):
                url = str(p.get("url") or "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                uh = _url_hash(url)
                html = str(p.get("raw_html") or p.get("html") or "")
                rendered_html = str(p.get("rendered_html") or "")
                raw_h = _sha256(html)
                rend_h = _sha256(rendered_html or html)
                if p.get("crawl_source") == "discovered_only":
                    tier = "DISCOVERED"
                    status_code = None
                    indexable = None
                elif rendered_html or str(p.get("render_mode") or "") in {"playwright_js", "firecrawl_js"}:
                    tier = "DEEP_INSPECTED"
                    status_code = int(p["status_code"]) if isinstance(p.get("status_code"), int) else None
                    indexable = 0 if "noindex" in f"{p.get('robots_meta') or ''} {p.get('x_robots_tag') or ''}".lower() else 1
                elif html:
                    tier = "CRAWLED"
                    status_code = int(p["status_code"]) if isinstance(p.get("status_code"), int) else None
                    indexable = 0 if "noindex" in f"{p.get('robots_meta') or ''} {p.get('x_robots_tag') or ''}".lower() else 1
                else:
                    tier = "DISCOVERED"
                    status_code = int(p["status_code"]) if isinstance(p.get("status_code"), int) else None
                    indexable = None
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_url_inventory (
                        id, audit_id, org_id, workspace_id, url, url_hash, discovery_source,
                        classification_tier, status_code, click_depth, is_indexable, canonical_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"uinv_{self.audit_id}_{idx}", self.audit_id, self.config.org_id, self.config.workspace_id,
                        url, uh, "crawl" if tier != "DISCOVERED" else "discovered", tier, status_code,
                        int(p.get("click_depth") or 0), indexable, p.get("canonical_url"),
                    ),
                )
                if tier == "DISCOVERED" or status_code is None:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_crawl_pages (
                        id, session_id, audit_id, workspace_id, url, url_hash,
                        status_code, ttfb_ms, page_payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"cpg_{self.audit_id}_{idx}", session_id, self.audit_id, self.config.workspace_id,
                        url, uh, status_code, p.get("ttfb_ms"), json.dumps(p, default=str),
                    ),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_page_snapshots (
                        id, audit_id, workspace_id, url, url_hash, raw_html_hash, rendered_dom_hash, storage_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"snap_{self.audit_id}_{idx}", self.audit_id, self.config.workspace_id,
                        url, uh, raw_h, rend_h, f"cas://{self.audit_id}/{uh}",
                    ),
                )
                hdrs = p.get("response_headers") or {}
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_http_observations (
                        id, audit_id, workspace_id, url_hash, protocol, server_header, x_robots_tag, headers_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"http_{self.audit_id}_{idx}", self.audit_id, self.config.workspace_id, uh,
                        "https" if url.startswith("https://") else "http",
                        hdrs.get("server") if isinstance(hdrs, dict) else None,
                        hdrs.get("x-robots-tag") if isinstance(hdrs, dict) else None,
                        json.dumps(hdrs, default=str),
                    ),
                )
                h1s = p.get("h1") if isinstance(p.get("h1"), list) else ([p.get("h1")] if p.get("h1") else [])
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_dom_observations (
                        id, audit_id, workspace_id, url_hash, title, meta_description, h1_count,
                        canonical_tag, robots_meta, missing_alt_count, internal_links_count,
                        word_count, schema_types_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"dom_{self.audit_id}_{idx}", self.audit_id, self.config.workspace_id, uh,
                        p.get("title"), p.get("meta_description"), len(h1s), p.get("canonical_url"),
                        p.get("robots_meta"), int(p.get("images_without_alt") or 0),
                        int(p.get("internal_links_count") or len(p.get("internal_links") or [])),
                        int(p.get("word_count") or 0), json.dumps(p.get("schema_types") or []),
                    ),
                )

            for f in self._deduped_findings:
                fid = f"{self.audit_id}:{f['finding_id']}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_findings (
                        id, audit_id, org_id, workspace_id, rule_id, root_cause_id,
                        category, severity, title, description, recommendation,
                        affected_urls_json, affected_urls_count, evidence_ids_json,
                        business_impact_json, status, verification_required, status_history_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        fid, self.audit_id, self.config.org_id, self.config.workspace_id,
                        f["rule_id"], f.get("root_cause_id"), f["category"], f["severity"],
                        f["title"], f.get("description"), f.get("recommendation"),
                        json.dumps(f.get("affected_urls") or []), int(f.get("affected_url_count") or 0),
                        json.dumps(f.get("evidence_ids") or []), json.dumps(f.get("business_impact") or {}),
                        f.get("status") or "VERIFIED",
                        json.dumps([{"status": f.get("status") or "VERIFIED", "at": now}]),
                        now,
                    ),
                )

            for ev in self._evidence_records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_finding_evidence (
                        id, finding_id, audit_id, workspace_id, url, url_hash, evidence_id,
                        check_id, source_type, source_location, observed_value, expected_value,
                        result, evidence_status, snapshot_id, content_sha256, agent_id,
                        methodology_version, observed_at
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{self.audit_id}:{ev['evidence_id']}", self.audit_id, self.config.workspace_id,
                        ev.get("url"), _url_hash(str(ev.get("url") or "")), ev["evidence_id"],
                        ev.get("check_id"), ev.get("source_type"), ev.get("source_location"),
                        json.dumps(ev.get("observed_value"), default=str),
                        json.dumps(ev.get("expected_value"), default=str),
                        ev.get("result"), ev.get("evidence_status"), ev.get("snapshot_id"),
                        ev.get("content_sha256"), ev.get("agent_id"), ev.get("methodology_version"),
                        ev.get("observed_at") or now,
                    ),
                )

            for t in self.remediation_tasks:
                tid = f"{self.audit_id}:{t.task_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_remediation_tasks (
                        id, recommendation_id, finding_id, audit_id, org_id, workspace_id,
                        title, fix_type, priority, status, approval_status, assigned_owner,
                        department, effort, acceptance_criteria, verification_protocol,
                        dependencies_json, implementation_json, affected_scope_json,
                        before_evidence_json, after_evidence_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tid, t.task_id, t.finding_id, self.audit_id, self.config.org_id, self.config.workspace_id,
                        t.problem, t.fix_type.value, t.priority, t.status, t.approval_status,
                        t.owner, t.department, t.effort, t.acceptance_criteria, t.verification_protocol,
                        json.dumps(t.dependencies), t.implementation.model_dump_json(),
                        json.dumps(t.affected_scope), json.dumps(t.before_evidence),
                        json.dumps(t.after_evidence), now,
                    ),
                )

            if self.scorecard:
                sc = self.scorecard
                dim_map = {d.dimension_id: d.score for d in sc.dimensions}
                sc_id = f"sc_{self.audit_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO seo_scorecards (
                        id, audit_id, org_id, workspace_id, overall_score, score_status,
                        overall_interpretation, technical_score, indexation_score, content_score,
                        onpage_score, internal_linking_score, schema_score, performance_score,
                        specialist_score, authority_score, active_weight_sum,
                        measured_dimensions_count, excluded_dimensions_count,
                        audit_coverage_pct, evidence_confidence_pct, data_freshness_hours,
                        connector_completeness_pct, sampling_status, disclosures_json,
                        raw_json, methodology_version, sealed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sc_id, self.audit_id, self.config.org_id, self.config.workspace_id,
                        sc.overall_health_score, sc.score_status, sc.overall_interpretation.value,
                        dim_map.get("technical_crawlability"), dim_map.get("indexation_canonicalization"),
                        dim_map.get("content_quality_intent"), dim_map.get("on_page_seo"),
                        dim_map.get("internal_linking_architecture"), dim_map.get("structured_data_entities"),
                        dim_map.get("performance_mobile"), dim_map.get("specialist_applicability"),
                        dim_map.get("trust_authority_signals"), sc.active_weight_sum,
                        sc.measured_dimensions_count, sc.excluded_dimensions_count,
                        sc.confidence_vectors.audit_coverage_pct, sc.confidence_vectors.evidence_confidence_pct,
                        sc.confidence_vectors.data_freshness_hours, sc.confidence_vectors.connector_completeness_pct,
                        sc.confidence_vectors.sampling_status, json.dumps(sc.disclosures),
                        sc.model_dump_json(), sc.methodology_version, sc.sealed_at,
                    ),
                )
                for d in sc.dimensions:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO seo_score_components (
                            id, scorecard_id, audit_id, workspace_id, component_name,
                            weight, effective_weight, is_applicable, is_measured,
                            raw_score, passed_checks, executed_checks
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{sc_id}:{d.dimension_id}", sc_id, self.audit_id, self.config.workspace_id,
                            d.dimension_id, d.configured_weight, d.effective_weight,
                            1 if d.is_applicable else 0, 1 if d.is_measured else 0,
                            d.score, d.passed_checks_count, d.executed_checks_count,
                        ),
                    )
            conn.commit()

    def _persist_final_state(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE seo_audit_runs SET
                    status = ?,
                    current_stage = ?,
                    elapsed_time_sec = ?,
                    completed_tasks = ?,
                    failed_tasks = ?,
                    overall_score = ?,
                    qa_status = ?,
                    canonical_assessment_json = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    self.state.status.value,
                    self.state.current_stage,
                    self.state.elapsed_time_sec,
                    len(self.state.completed_tasks),
                    len(self.state.failed_tasks),
                    self.scorecard.overall_health_score if self.scorecard else None,
                    self.qa_report.status if self.qa_report else "PENDING",
                    json.dumps(self.canonical_assessment, default=str) if self.canonical_assessment else None,
                    now,
                    now,
                    self.audit_id,
                ),
            )
            conn.commit()


SeoAuditOrchestrator = SEOAuditOrchestrator
