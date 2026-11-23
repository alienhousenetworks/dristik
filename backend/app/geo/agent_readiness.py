"""
Agent readiness: can an automated buyer extract this site?

Signals are measured from the crawl (robots, schema, quotable answers) and
one HEAD of /llms.txt. Missing checks stay NOT_MEASURED. The score is the
share of checks that were actually run and passed. It is not a citation rank.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.crawl.robots import evaluate_robots
from app.domain.models import AgentReadinessReport, AgentReadinessSignal, CrawlManifest, PageEvidence
from app.core.security.ssrf import is_safe_url

_AI_SEARCH_BOTS = {"oai-searchbot", "perplexitybot", "claude-searchbot"}
_AI_TRAINING_BOTS = {"gptbot", "claudebot", "google-extended", "applebot-extended", "ccbot", "anthropic-ai"}
_AI_BOTS = _AI_SEARCH_BOTS | _AI_TRAINING_BOTS


def _signal(key: str, status: str, summary: str) -> AgentReadinessSignal:
    return AgentReadinessSignal(key=key, status=status, summary=summary)


def _robots_signal(manifest: Optional[CrawlManifest], page_path: str = "/") -> AgentReadinessSignal:
    if manifest is None or manifest.robots_txt_found is None:
        return _signal("ai_bot_robots", "NOT_MEASURED", "robots.txt was not fetched on this crawl.")
    if not manifest.robots_txt_found:
        return _signal("ai_bot_robots", "MISSING", "No robots.txt was found. AI crawler policy is unpublished.")
    text = manifest.robots_txt_content or ""
    if not text.strip():
        return _signal("ai_bot_robots", "NOT_MEASURED", "robots.txt was reported present but its body was not stored.")

    target_path = page_path if page_path.startswith("/") else f"/{page_path}"
    blocked_search: List[str] = []
    allowed_search_explicit: List[str] = []
    for bot in sorted(_AI_SEARCH_BOTS):
        dec = evaluate_robots(text, target_path, user_agent=bot)
        if not dec.allowed:
            blocked_search.append(bot)
        elif dec.matched_group and dec.matched_group.lower() != "*":
            allowed_search_explicit.append(bot)

    blocked_training = [
        bot for bot in sorted(_AI_TRAINING_BOTS)
        if not evaluate_robots(text, target_path, user_agent=bot).allowed
    ]

    if allowed_search_explicit and not blocked_search:
        return _signal(
            "ai_bot_robots",
            "PRESENT",
            f"robots.txt permits AI search crawlers ({', '.join(allowed_search_explicit)}) overriding general rules.",
        )
    if blocked_search:
        return _signal(
            "ai_bot_robots",
            "MISSING",
            f"robots.txt disallows search crawlers: {', '.join(blocked_search)}.",
        )
    if blocked_training:
        return _signal(
            "ai_bot_robots",
            "PRESENT",
            f"robots.txt permits AI search bots while selectively restricting training bots ({', '.join(blocked_training[:3])}).",
        )

    return _signal(
        "ai_bot_robots",
        "PRESENT",
        "robots.txt does not disallow the whole site for AI search or training bots (GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot).",
    )


def _faq_signal(pages: List[PageEvidence]) -> AgentReadinessSignal:
    types = {t.lower() for page in pages for t in (page.schema_types or [])}
    if any(t in types for t in ("faqpage", "qapage")):
        return _signal("faq_schema", "PRESENT", "FAQPage or QAPage schema is present on a crawled URL.")
    if not pages:
        return _signal("faq_schema", "NOT_MEASURED", "No pages were crawled, so FAQ schema was not checked.")
    return _signal("faq_schema", "MISSING", "No FAQPage or QAPage schema on the crawled pages.")


def _definition_signal(pages: List[PageEvidence]) -> AgentReadinessSignal:
    if not pages:
        return _signal("extractable_definition", "NOT_MEASURED", "No pages were crawled.")
    for page in pages:
        text = " ".join(page.h1 or []) + " " + (page.body_text or "")
        words = re.findall(r"\b[\w']+\b", text)
        if 40 <= len(words) <= 80 and (page.h2 or page.h1):
            return _signal(
                "extractable_definition",
                "PRESENT",
                "A crawled page has a short heading-led passage an agent can quote.",
            )
    headings = sum(len(page.h2 or []) + len(page.h3 or []) for page in pages)
    if headings >= 3:
        return _signal(
            "extractable_definition",
            "PRESENT",
            f"{headings} H2/H3 blocks give an agent a structure to extract.",
        )
    return _signal(
        "extractable_definition",
        "MISSING",
        "The crawl sample has no short quotable definition and fewer than 3 subheadings.",
    )


async def validate_llms_txt(
    website_url: str,
    robots_txt: str = "",
    max_links: int = 6,
) -> dict:
    """Fetch /llms.txt, sample linked same-site URLs for HTTP 200 health, and check robots contradictions."""
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    if not parsed.netloc:
        return {"present": False, "status": "NOT_MEASURED", "reason": "No host available"}
    root_host = parsed.netloc.lower().removeprefix("www.")
    target = f"{parsed.scheme or 'https'}://{parsed.netloc}/llms.txt"
    safe, reason = is_safe_url(target)
    if not safe:
        return {"present": False, "status": "NOT_MEASURED", "reason": reason}

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(target, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
            if resp.status_code != 200:
                return {
                    "present": False,
                    "status": "MISSING" if resp.status_code == 404 else "NOT_MEASURED",
                    "http_status": resp.status_code,
                    "url": target,
                }
            body = resp.text[:200_000]
            urls: List[str] = []
            for u in re.findall(r"https?://[^\s)\]>\"'`]+", body):
                u = u.rstrip(".,;:")
                h = urlparse(u).netloc.lower().removeprefix("www.")
                if (h == root_host or h.endswith("." + root_host)) and u not in urls:
                    urls.append(u)

            broken: List[dict] = []
            robots_blocked: List[dict] = []
            sample = urls[:max_links]
            for u in sample:
                if robots_txt:
                    denied = [
                        b for b in ("GPTBot", "ClaudeBot", "PerplexityBot")
                        if not evaluate_robots(robots_txt, u, user_agent=b).allowed
                    ]
                    if denied:
                        robots_blocked.append({"url": u, "bots": denied})
                u_safe, _ = is_safe_url(u)
                if not u_safe:
                    continue
                try:
                    lr = await client.head(u, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
                    if lr.status_code == 405:
                        lr = await client.get(u, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
                    if lr.status_code != 200:
                        broken.append({"url": u, "status": lr.status_code})
                except Exception as exc:
                    broken.append({"url": u, "status": 0, "error": str(exc)[:120]})

            return {
                "present": True,
                "status": "PRESENT",
                "http_status": 200,
                "url": target,
                "total_links": len(urls),
                "checked": len(sample),
                "broken": broken,
                "robots_blocked": robots_blocked,
            }
    except Exception as exc:
        return {"present": False, "status": "NOT_MEASURED", "reason": str(exc)}


async def _llms_file_signal(website_url: str, filename: str, signal_key: str) -> AgentReadinessSignal:
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    if not parsed.netloc:
        return _signal(signal_key, "NOT_MEASURED", f"No host was available to request /{filename}.")
    target = f"{parsed.scheme or 'https'}://{parsed.netloc}/{filename}"
    safe, reason = is_safe_url(target)
    if not safe:
        return _signal(signal_key, "NOT_MEASURED", f"/{filename} was not requested: {reason}")
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            response = await client.head(target, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
            if response.status_code == 405:
                response = await client.get(target, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
    except Exception as exc:
        return _signal(signal_key, "NOT_MEASURED", f"/{filename} request failed: {exc}")
    if response.status_code == 200 and len(response.content or b"") >= 0:
        return _signal(signal_key, "PRESENT", f"{target} returned HTTP {response.status_code}.")
    if response.status_code == 404:
        return _signal(signal_key, "MISSING", f"{target} returned HTTP 404.")
    return _signal(signal_key, "NOT_MEASURED", f"{target} returned HTTP {response.status_code}, which is not a presence check.")


async def _llms_txt_signal(website_url: str, robots_txt: str = "") -> AgentReadinessSignal:
    return await _llms_file_signal(website_url, "llms.txt", "llms_txt")


async def _llms_full_txt_signal(website_url: str) -> AgentReadinessSignal:
    return await _llms_file_signal(website_url, "llms-full.txt", "llms_full_txt")


def _score(signals: List[AgentReadinessSignal]) -> Optional[float]:
    measured = [s for s in signals if s.status in ("PRESENT", "MISSING")]
    if not measured:
        return None
    present = sum(1 for s in measured if s.status == "PRESENT")
    return round(100.0 * present / len(measured), 1)


async def evaluate_agent_readiness(
    website_url: str,
    pages: List[PageEvidence],
    manifest: Optional[CrawlManifest] = None,
) -> AgentReadinessReport:
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    page_path = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
    signals = [
        _robots_signal(manifest, page_path=page_path),
        _faq_signal(pages),
        _definition_signal(pages),
        await _llms_txt_signal(website_url),
        await _llms_full_txt_signal(website_url),
    ]
    score = _score(signals)
    present = sum(1 for s in signals if s.status == "PRESENT")
    missing = sum(1 for s in signals if s.status == "MISSING")
    unknown = sum(1 for s in signals if s.status == "NOT_MEASURED")
    if score is None:
        summary = "Agent readiness was not scored because none of the checks completed."
    else:
        summary = (
            f"Agent readiness {score:.0f}/100 from {present} present and {missing} missing checks"
            + (f" ({unknown} not measured)." if unknown else ".")
            + " This is on-site extractability for agents, not a live citation rank."
        )
    return AgentReadinessReport(score=score, signals=signals, summary=summary)
