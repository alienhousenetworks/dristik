"""
Dristik Agentic Tool Bus — Sandboxed, Evidence-Grounded Tools for Specialists & Copilot.

Eliminates the 60-item evidence blind spot and single-shot LLM limitation by giving
specialists deterministic tools to search the entire evidence store, inspect page DOMs,
compare raw vs rendered HTML, validate JSON-LD, and query verified business context.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


_SCHEMA_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "Organization": ["name", "url"],
    "WebSite": ["name", "url"],
    "Product": ["name"],
    "Service": ["name", "provider"],
    "FAQPage": ["mainEntity"],
    "Article": ["headline", "author"],
    "BlogPosting": ["headline", "author"],
    "BreadcrumbList": ["itemListElement"],
}


class AgentToolBus:
    """Deterministic tool execution bus scoped to a single CognitiveBlackboard."""

    def __init__(self, blackboard: Any):
        self.bb = blackboard
        self.call_log: List[Dict[str, Any]] = []

    def available_tools_spec(self) -> str:
        """Concise tool schema specification injected into multi-turn specialist prompts."""
        return (
            "AVAILABLE TOOLS (invoke by returning JSON {\"tool_calls\": [{\"tool\": \"...\", \"args\": {...}}]}):\n"
            "1. search_evidence(query: str, limit: int = 20) -> Search ALL crawl & external evidence items beyond your initial slice.\n"
            "2. inspect_page_dom(url: str) -> Inspect full PageEvidence (title, meta, headings, canonical, JSON-LD, links, status) for a URL.\n"
            "3. compare_raw_vs_rendered(url: str) -> Check raw HTML vs JS-rendered DOM differences for a URL.\n"
            "4. validate_json_ld(json_ld_str: str) -> Validate JSON-LD syntax and Schema.org required fields.\n"
            "5. get_business_context() -> Retrieve verified BusinessProfile, ICP, tech stack, and prior agent findings.\n"
        )

    def execute(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        dispatch = {
            "search_evidence": self.search_evidence,
            "inspect_page_dom": self.inspect_page_dom,
            "compare_raw_vs_rendered": self.compare_raw_vs_rendered,
            "validate_json_ld": self.validate_json_ld,
            "get_business_context": self.get_business_context,
            "detect_tech_stack": self.detect_tech_stack,
        }
        fn = dispatch.get(tool_name)
        if fn is None:
            res = {"error": f"Unknown tool: {tool_name}"}
        else:
            try:
                res = fn(**args)
            except TypeError as exc:
                res = {"error": f"Invalid arguments for {tool_name}: {exc}"}
            except Exception as exc:
                res = {"error": f"Tool {tool_name} failed: {exc}"}

        self.call_log.append({"tool": tool_name, "args": args, "ok": "error" not in res})
        return res

    def search_evidence(self, query: str = "", category: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Hybrid keyword search across ALL ev_NNN and ext_NNN items in the blackboard."""
        tokens = [t.lower() for t in re.split(r"\W+", query or "") if len(t) >= 2]
        cap = max(1, min(int(limit or 20), 50))

        all_items: List[Any] = []
        if getattr(self.bb, "evidence_store", None) is not None:
            all_items.extend(self.bb.evidence_store.get_all() or [])
        ext_items = (getattr(self.bb, "blackboard_state", {}) or {}).get("external_evidence", []) or []
        all_items.extend(ext_items)

        scored: List[tuple] = []
        for ev in all_items:
            ev_id = str(getattr(ev, "id", "") or "")
            selector = str(getattr(ev, "selector", "") or "")
            text = str(getattr(ev, "text", "") or "")
            val = str(getattr(ev, "value", "") or "")
            url = str(getattr(ev, "url", "") or "")
            ev_cat = str(getattr(ev, "category", "") or getattr(ev, "source_type", "") or "")

            if category and category.lower() not in ev_cat.lower():
                continue

            blob = f"{ev_id} {selector} {text} {val} {url} {ev_cat}".lower()
            if not tokens:
                score = 1
            else:
                score = sum(1 for t in tokens if t in blob)
                if score == 0:
                    continue
            scored.append((score, ev_id, {
                "id": ev_id,
                "url": url,
                "selector": selector,
                "text": text[:300],
                "value": val[:300] if isinstance(getattr(ev, "value", None), (str, dict, list)) else str(val)[:200],
                "source_type": getattr(ev, "source_type", None),
            }))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return {
            "total_store_items": len(all_items),
            "matched_count": len(scored),
            "results": [item for _, _, item in scored[:cap]],
        }

    def inspect_page_dom(self, url: str = "") -> Dict[str, Any]:
        """Inspect full stored PageEvidence for a target URL (or homepage if omitted)."""
        pages = list(getattr(self.bb, "pages", []) or [])
        if not pages:
            return {"error": "No crawled pages available in blackboard."}

        target = None
        norm_req = (url or "").strip().rstrip("/").lower()
        for p in pages:
            p_url = str(getattr(p, "url", "") or "").strip().rstrip("/").lower()
            if not norm_req or p_url == norm_req or norm_req in p_url:
                target = p
                break
        if target is None:
            return {"error": f"URL not found in crawled pages: {url}", "available_urls": [getattr(p, "url", "") for p in pages[:15]]}

        return {
            "url": getattr(target, "url", ""),
            "status_code": getattr(target, "status_code", None),
            "title": getattr(target, "title", None),
            "meta_description": getattr(target, "meta_description", None),
            "canonical_url": getattr(target, "canonical_url", None),
            "robots_meta": getattr(target, "robots_meta", None),
            "h1": getattr(target, "h1", []) or [],
            "h2": (getattr(target, "h2", []) or [])[:15],
            "word_count": getattr(target, "word_count", None),
            "ttfb_ms": getattr(target, "ttfb_ms", None),
            "schema_types": getattr(target, "schema_types", []) or [],
            "json_ld_count": len(getattr(target, "json_ld", []) or []),
            "internal_links_count": len(getattr(target, "internal_links", []) or []),
            "external_links_count": len(getattr(target, "external_links", []) or []),
            "images_missing_alt": getattr(target, "images_missing_alt", None),
            "visible_text_excerpt": str(getattr(target, "visible_text", "") or "")[:600],
        }

    def compare_raw_vs_rendered(self, url: str = "") -> Dict[str, Any]:
        """Compare raw HTTP HTML vs Playwright-rendered DOM when both are captured."""
        pages = list(getattr(self.bb, "pages", []) or [])
        norm_req = (url or "").strip().rstrip("/").lower()
        target = next(
            (p for p in pages if not norm_req or str(getattr(p, "url", "")).strip().rstrip("/").lower() == norm_req),
            None,
        )
        if target is None:
            return {"error": f"URL not in crawled set: {url}"}

        raw_html = getattr(target, "raw_html", None) or ""
        rendered_html = getattr(target, "rendered_html", None) or getattr(target, "html", None) or ""
        rendered_used = bool(getattr(target, "js_rendered", False) or getattr(target, "rendered_html", None))

        if not raw_html and not rendered_html:
            return {"url": getattr(target, "url", ""), "status": "HTML_UNAVAILABLE"}

        raw_words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", raw_html))) if raw_html else 0
        ren_words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", rendered_html))) if rendered_html else raw_words
        return {
            "url": getattr(target, "url", ""),
            "js_rendered": rendered_used,
            "raw_word_count_est": raw_words,
            "rendered_word_count_est": ren_words,
            "hydration_word_delta": ren_words - raw_words,
            "spa_shell_risk": raw_words < 80 and ren_words > 200,
        }

    def validate_json_ld(self, json_ld_str: str = "") -> Dict[str, Any]:
        """Validate JSON-LD syntax and Schema.org required fields."""
        try:
            data = json.loads(json_ld_str)
        except Exception as exc:
            return {"valid": False, "error": f"Invalid JSON: {exc}"}

        nodes = data.get("@graph", [data]) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        issues: List[str] = []
        types_found: List[str] = []

        if isinstance(data, dict) and "@context" not in data:
            issues.append("Missing @context (expected https://schema.org)")

        for idx, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            ntype = node.get("@type")
            if not ntype:
                issues.append(f"Node {idx} missing @type")
                continue
            tlist = [ntype] if isinstance(ntype, str) else list(ntype)
            types_found.extend(tlist)
            for t in tlist:
                for req in _SCHEMA_REQUIRED_FIELDS.get(t, []):
                    if not node.get(req):
                        issues.append(f"{t} missing required property '{req}'")

        return {"valid": len(issues) == 0, "types_found": types_found, "issues": issues}

    def get_business_context(self) -> Dict[str, Any]:
        """Return verified BusinessProfile, ICP, tech stack, and prior specialist summaries."""
        bp = getattr(self.bb, "business_profile", None)
        bp_dict = {}
        if bp is not None:
            bp_dict = {
                "business_name": getattr(bp, "business_name", None),
                "niche": getattr(bp, "niche", None),
                "target_audience": getattr(bp, "target_audience", None),
                "value_proposition": getattr(bp, "value_proposition", None),
                "primary_cta": getattr(bp, "primary_cta", None),
                "business_model": getattr(bp, "business_model", None),
            }
        tech = self.detect_tech_stack()
        prior_results = (getattr(self.bb, "blackboard_state", {}) or {}).get("agent_results", {}) or {}
        biz_claims = []
        for aid, res in prior_results.items():
            if aid.startswith("business.") and isinstance(res, dict):
                for c in (res.get("claims") or [])[:3]:
                    biz_claims.append(c.get("statement") if isinstance(c, dict) else getattr(c, "statement", ""))
        return {
            "business_profile": bp_dict,
            "tech_stack": tech,
            "prior_business_claims": [c for c in biz_claims if c],
        }

    def detect_tech_stack(self) -> Dict[str, Any]:
        """Deterministic tech-stack fingerprinter from crawled PageEvidence and headers."""
        pages = list(getattr(self.bb, "pages", []) or [])
        headers_blob = ""
        html_blob = ""
        for p in pages[:5]:
            hdrs = getattr(p, "headers", None) or getattr(p, "response_headers", None) or {}
            if isinstance(hdrs, dict):
                headers_blob += " ".join(f"{k}:{v}" for k, v in hdrs.items()).lower() + " "
            raw = str(getattr(p, "html", None) or getattr(p, "raw_html", None) or "")
            html_blob += raw[:25000].lower() + " "

        frameworks: List[str] = []
        if "/_next/" in html_blob or "__next_data__" in html_blob or "x-powered-by:next.js" in headers_blob:
            frameworks.append("nextjs")
        if "wp-content/" in html_blob or "wp-includes/" in html_blob:
            frameworks.append("wordpress")
        if "cdn.shopify.com" in html_blob or "shopify.theme" in html_blob:
            frameworks.append("shopify")
        if "data-wf-domain" in html_blob or "webflow" in html_blob:
            frameworks.append("webflow")
        if not frameworks and ("data-reactroot" in html_blob or "vite" in html_blob or 'id="root"' in html_blob):
            frameworks.append("react_spa")

        infra: List[str] = []
        if "cloudflare" in headers_blob or "cf-ray" in headers_blob:
            infra.append("cloudflare")
        if "vercel" in headers_blob or "x-vercel-id" in headers_blob:
            infra.append("vercel")
        if "nginx" in headers_blob:
            infra.append("nginx")

        primary_stack = frameworks[0] if frameworks else "static_html"
        return {
            "primary_framework": primary_stack,
            "frameworks_detected": frameworks,
            "infrastructure": infra,
        }

