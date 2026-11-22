#!/usr/bin/env python3
"""
Dristik Pre/Post-Phase Baseline Capture Harness.

Runs a reproducible benchmark across fixed multi-industry URLs and writes
immutable JSON snapshots + a rollup summary.json so every phase (1..7) can
be compared objectively against the baseline.

Usage:
  python3 scripts/capture_baseline.py --out baseline_pre_phase1 --max-pages 5 --crawl-only
  python3 scripts/capture_baseline.py --out baseline_live_phase0 --max-pages 5
  python3 scripts/capture_baseline.py --urls https://a.com https://b.com --out my_baseline
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 10 diverse industry benchmark sites (override with --urls or --urls-file)
DEFAULT_BENCHMARK_URLS: List[str] = [
    "https://linear.app",                 # B2B SaaS
    "https://stripe.com",                 # Enterprise Fintech / API
    "https://www.allbirds.com",           # D2C E-commerce
    "https://www.mayoclinic.org",         # Healthcare / Medical Info
    "https://docs.python.org/3/",         # Technical Documentation
    "https://www.hubspot.com",            # B2B Marketing SaaS
    "https://www.basecamp.com",           # SMB Product / SaaS
    "https://www.mckinsey.com",           # Professional Services / Consulting
    "https://www.shopify.com",            # E-commerce Platform
    "https://www.smashingmagazine.com",   # Content & Publishing
]

USD_TO_INR = 85.0


def _slug(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "") or "site"
    return "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in host)


async def _capture_crawl_only(url: str, max_pages: int) -> Dict[str, Any]:
    from app.crawl.crawler import CrawlerService
    from app.domain.evidence.store import EvidenceStore

    t0 = time.perf_counter()
    crawler = CrawlerService()
    store = EvidenceStore(run_id=f"baseline_{_slug(url)}")
    manifest = await crawler.crawl_site_and_analyze(
        target_url=url,
        evidence_store=store,
        max_pages=max_pages,
    )
    elapsed_s = round(time.perf_counter() - t0, 2)
    pages = manifest.pages or []
    return {
        "mode": "crawl_only",
        "url": url,
        "domain": manifest.domain,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed_s,
        "pages_discovered": manifest.total_pages_discovered,
        "pages_crawled": len(pages),
        "evidence_items_count": store.count(),
        "total_body_chars": sum(len(p.body_text or "") for p in pages),
        "total_sections": sum(len(getattr(p, "sections", None) or []) for p in pages),
        "total_forms": sum(len(getattr(p, "forms", None) or []) for p in pages),
        "total_ctas": sum(len(getattr(p, "ctas", None) or []) for p in pages),
        "pages_with_footer_info": sum(1 for p in pages if getattr(p, "footer_info", None)),
        "pages_with_nav_items": sum(1 for p in pages if getattr(p, "nav_items", None)),
        "render_modes": {
            mode: sum(1 for p in pages if getattr(p, "render_mode", None) == mode)
            for mode in sorted({getattr(p, "render_mode", "unknown") for p in pages})
        },
        "pages": [
            {
                "url": p.url,
                "status_code": p.status_code,
                "page_type": p.page_type,
                "word_count": p.word_count,
                "body_chars": len(p.body_text or ""),
                "h1_count": len(p.h1 or []),
                "h2_count": len(p.h2 or []),
                "sections_count": len(getattr(p, "sections", None) or []),
                "forms_count": len(getattr(p, "forms", None) or []),
                "ctas_count": len(getattr(p, "ctas", None) or []),
                "render_mode": getattr(p, "render_mode", None),
                "render_status": getattr(p, "render_status", None),
                "render_error": getattr(p, "render_error", None),
            }
            for p in pages
        ],
    }


async def _capture_full_audit(url: str, max_pages: int) -> Dict[str, Any]:
    from app.orchestration.orchestrator import AnalysisOrchestrator

    t0 = time.perf_counter()
    orch = AnalysisOrchestrator()
    run = orch.create_run(website_url=url, org_id="org_baseline_eval", workspace_id="ws_baseline_eval")
    await orch.execute_analysis_pipeline(analysis_id=run.analysis_id, website_url=url, max_pages=max_pages)
    elapsed_s = round(time.perf_counter() - t0, 2)

    final_run = orch.get_run(run.analysis_id)
    report = final_run.report if final_run else None
    telemetry = getattr(report, "telemetry", None) or (getattr(final_run, "telemetry", None) if final_run else None)
    bb = orch.blackboards.get(run.analysis_id)
    pages = (bb.pages if bb else []) or []

    cost_usd = float(getattr(telemetry, "estimated_cost_usd", 0.0) or 0.0)
    calls_count = int(getattr(telemetry, "model_calls_count", 0) or 0)
    per_page_usd = round(cost_usd / max(1, len(pages)), 4)
    findings = list(getattr(report, "findings", None) or [])
    evidence_linked = sum(1 for f in findings if getattr(f, "evidence_refs", None) or getattr(f, "evidence", None))
    aeo_evals = list(getattr(report, "dynamic_sandbox_evaluations", None) or [])
    aeo_answerable = sum(1 for e in aeo_evals if getattr(e, "is_answerable", False))
    avg_grounding = (
        round(sum(float(getattr(e, "grounding_ratio", 0.0) or 0.0) for e in aeo_evals) / len(aeo_evals), 3)
        if aeo_evals else 0.0
    )

    return {
        "mode": "full_audit",
        "url": url,
        "analysis_id": run.analysis_id,
        "status": str(getattr(final_run, "status", "unknown")),
        "certification_status": getattr(report, "certification_status", None) if report else None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed_s,
        "pages_crawled": len(pages),
        "total_sections": sum(len(getattr(p, "sections", None) or []) for p in pages),
        "total_forms": sum(len(getattr(p, "forms", None) or []) for p in pages),
        "findings_count": len(findings),
        "findings_with_evidence_pct": round((evidence_linked / max(1, len(findings))) * 100.0, 1) if findings else 100.0,
        "overall_score": getattr(getattr(report, "scores", None), "overall_score", None) if report else None,
        "business_name": getattr(getattr(report, "business_profile", None), "business_name", None) if report else None,
        "aeo_questions_count": len(aeo_evals),
        "aeo_answerable_count": aeo_answerable,
        "aeo_avg_grounding_ratio": avg_grounding,
        "agent_coverage": (bb.blackboard_state.get("execution_coverage") if bb else None),
        "model_calls_count": calls_count,
        "total_tokens": int(getattr(telemetry, "total_tokens", 0) or 0),
        "cost_usd": round(cost_usd, 4),
        "cost_inr_est": round(cost_usd * USD_TO_INR, 2),
        "cost_per_page_usd": per_page_usd,
        "cost_per_page_inr_est": round(per_page_usd * USD_TO_INR, 2),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Capture pre/post-phase audit baselines.")
    parser.add_argument("--out", default="data/baseline_pre_phase1", help="Output directory for JSON snapshots")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages per site")
    parser.add_argument("--crawl-only", action="store_true", help="Capture crawl + extraction baseline ($0 LLM)")
    parser.add_argument("--urls", nargs="*", help="Custom list of URLs to audit")
    args = parser.parse_args()

    urls = args.urls if args.urls else DEFAULT_BENCHMARK_URLS
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for idx, url in enumerate(urls, start=1):
        print(f"[{idx}/{len(urls)}] Capturing {url} (max_pages={args.max_pages}, crawl_only={args.crawl_only})...")
        try:
            snap = await (_capture_crawl_only(url, args.max_pages) if args.crawl_only else _capture_full_audit(url, args.max_pages))
        except Exception as exc:
            snap = {"url": url, "error": f"{type(exc).__name__}: {exc}", "captured_at": datetime.now(timezone.utc).isoformat()}
        results.append(snap)
        (out_dir / f"{idx:02d}_{_slug(url)}.json").write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")

    summary = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "mode": "crawl_only" if args.crawl_only else "full_audit",
        "max_pages": args.max_pages,
        "sites_total": len(urls),
        "sites_succeeded": sum(1 for r in results if "error" not in r),
        "sites_failed": sum(1 for r in results if "error" in r),
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"Baseline saved to {out_dir / 'summary.json'} ({summary['sites_succeeded']}/{summary['sites_total']} succeeded)")


if __name__ == "__main__":
    asyncio.run(main())
