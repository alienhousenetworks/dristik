"""
Dristik Standalone CLI with CI/CD Score Gating & Agent JSON Schema (Phase 6).

Usage:
  python -m app.cli audit <url> [--json] [--min-score <n>]
  python -m app.cli check "<prompt>" --brand <name> [--country US] [--engine ...] [--json] [--min-score <n>]
  python -m app.cli sro <url> --keyword "<kw>" [--country US] [--json]
  python -m app.cli help --json

Exit codes:
  0 = success (and score >= --min-score if provided)
  1 = runtime error
  2 = invalid arguments
  3 = score below --min-score (CI/CD gate failed)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

CLI_SPEC: Dict[str, Any] = {
    "name": "dristik",
    "version": "2.0.0",
    "exit_codes": {"0": "ok", "1": "error", "2": "usage", "3": "below_min_score"},
    "commands": {
        "audit": {
            "description": "Fast single-page AEO/GEO readiness check (robots.txt, llms.txt, llms-full.txt, schema, definition). Free, zero API keys.",
            "args": ["url"],
            "flags": ["--json", "--min-score"],
        },
        "check": {
            "description": "Query configured live AI engines for brand mentions and citations.",
            "args": ["prompt"],
            "flags": ["--brand", "--website", "--country", "--engine", "--json", "--min-score"],
        },
        "sro": {
            "description": "Run Selection Rate Optimization (Gemini groundingSupports + cross-platform citations).",
            "args": ["url"],
            "flags": ["--keyword", "--country", "--json"],
        },
    },
}


async def _cmd_audit(url: str) -> Dict[str, Any]:
    import httpx
    from urllib.parse import urlparse
    from app.core.security.ssrf import is_safe_url
    from app.domain.models import CrawlManifest, PageEvidence
    from app.geo.agent_readiness import evaluate_agent_readiness

    target = url if "://" in url else f"https://{url}"
    safe, reason = is_safe_url(target)
    if not safe:
        raise ValueError(f"Blocked URL: {reason}")

    parsed = urlparse(target)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_txt = ""
    robots_found = False
    html = ""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        page_res = await client.get(target, headers={"User-Agent": "Dristik-CLI/2.0"})
        html = page_res.text[:500_000]
        r_res = await client.get(f"{origin}/robots.txt", headers={"User-Agent": "Dristik-CLI/2.0"})
        if r_res.status_code == 200:
            robots_found = True
            robots_txt = r_res.text

    import re
    schema_types = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
    plain = re.sub(r"<[^>]+>", " ", re.sub(r"<(?:script|style)[\s\S]*?</(?:script|style)>", " ", html, flags=re.I))
    plain = re.sub(r"\s+", " ", plain).strip()
    page = PageEvidence(
        url=target,
        status_code=200,
        schema_types=list(dict.fromkeys(schema_types)),
        body_text=plain,
        word_count=len(plain.split()),
    )
    manifest = CrawlManifest(website_url=origin, robots_txt_found=robots_found, robots_txt_content=robots_txt)
    rep = await evaluate_agent_readiness(target, [page], manifest)
    return {
        "url": target,
        "score": rep.score,
        "summary": rep.summary,
        "signals": [s.model_dump() for s in rep.signals],
    }


async def _cmd_check(
    prompt: str,
    brand: str,
    website: str = "",
    country: str = "US",
    engines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from app.geo.adapters.registry import get_adapter, get_available_adapters

    adapters = [get_adapter(e) for e in (engines or [])] if engines else get_available_adapters()
    adapters = [a for a in adapters if a and a.is_configured()]
    if not adapters:
        return {
            "prompt": prompt,
            "brand": brand,
            "country": country.upper(),
            "status": "NOT_CONFIGURED",
            "average_score": None,
            "results": [],
        }

    brand_low = brand.strip().lower()
    site_host = website.lower().replace("https://", "").replace("http://", "").split("/")[0].removeprefix("www.")

    async def _one(ad: Any) -> Dict[str, Any]:
        res = await ad.execute_prompt({"prompt": prompt, "market": country.upper(), "enable_search": True})
        mentioned = bool(brand_low and brand_low in (res.raw_content or "").lower())
        cited = bool(site_host and any(site_host in c.lower() for c in (res.citations or [])))
        score = (50 if mentioned else 0) + (50 if cited else 0) if res.is_live else None
        return {
            "engine": ad.engine_id,
            "is_live": res.is_live,
            "testing_mode": res.testing_mode.value if hasattr(res.testing_mode, "value") else str(res.testing_mode),
            "mentioned": mentioned,
            "website_cited": cited,
            "score": score,
            "citations_count": len(res.citations or []),
            "error": res.error,
        }

    results = list(await asyncio.gather(*[_one(a) for a in adapters]))
    live_scores = [r["score"] for r in results if isinstance(r["score"], (int, float))]
    avg = round(sum(live_scores) / len(live_scores), 1) if live_scores else None
    return {
        "prompt": prompt,
        "brand": brand,
        "country": country.upper(),
        "status": "MEASURED" if live_scores else "ERROR",
        "average_score": avg,
        "results": results,
    }


async def _cmd_sro(url: str, keyword: str, country: str = "US") -> Dict[str, Any]:
    from app.geo.sro import sro_engine
    res = await sro_engine.analyze(target_url=url, keyword=keyword, country=country.upper())
    return res.model_dump(mode="json")


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="dristik", description="Dristik GEO/AEO CLI with CI score gating.")
    sub = parser.add_subparsers(dest="command")

    p_help = sub.add_parser("help", help="Show CLI specification")
    p_help.add_argument("--json", action="store_true", dest="as_json")

    p_audit = sub.add_parser("audit", help="Run zero-key single-page AEO/GEO readiness audit")
    p_audit.add_argument("url")
    p_audit.add_argument("--json", action="store_true", dest="as_json")
    p_audit.add_argument("--min-score", type=float, default=None)

    p_check = sub.add_parser("check", help="Check brand visibility across configured AI engines")
    p_check.add_argument("prompt")
    p_check.add_argument("--brand", required=True)
    p_check.add_argument("--website", default="")
    p_check.add_argument("--country", default="US")
    p_check.add_argument("--engine", action="append", default=None)
    p_check.add_argument("--json", action="store_true", dest="as_json")
    p_check.add_argument("--min-score", type=float, default=None)

    p_sro = sub.add_parser("sro", help="Run Selection Rate Optimization analysis")
    p_sro.add_argument("url")
    p_sro.add_argument("--keyword", required=True)
    p_sro.add_argument("--country", default="US")
    p_sro.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2

    if args.command == "help":
        if getattr(args, "as_json", False):
            print(json.dumps(CLI_SPEC, indent=2))
        else:
            parser.print_help()
        return 0

    as_json = bool(getattr(args, "as_json", False))
    try:
        if args.command == "audit":
            out = asyncio.run(_cmd_audit(args.url))
            score = out.get("score")
        elif args.command == "check":
            out = asyncio.run(_cmd_check(args.prompt, args.brand, args.website, args.country, args.engine))
            score = out.get("average_score")
        elif args.command == "sro":
            out = asyncio.run(_cmd_sro(args.url, args.keyword, args.country))
            score = out.get("overall_score")
        else:
            return 2

        if as_json:
            print(json.dumps(out, indent=2))
        else:
            print(f"{args.command.upper()} score={score} | {out.get('summary') or out.get('status')}")

        min_score = getattr(args, "min_score", None)
        if min_score is not None:
            if score is None or float(score) < float(min_score):
                return 3
        return 0
    except Exception as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
