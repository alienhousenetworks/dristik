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

from app.domain.models import AgentReadinessReport, AgentReadinessSignal, CrawlManifest, PageEvidence
from app.core.security.ssrf import is_safe_url

_AI_SEARCH_BOTS = {"oai-searchbot", "perplexitybot", "claude-searchbot"}
_AI_TRAINING_BOTS = {"gptbot", "claudebot", "google-extended", "applebot-extended", "ccbot", "anthropic-ai"}
_AI_BOTS = _AI_SEARCH_BOTS | _AI_TRAINING_BOTS


def _signal(key: str, status: str, summary: str) -> AgentReadinessSignal:
    return AgentReadinessSignal(key=key, status=status, summary=summary)


def _robots_signal(manifest: Optional[CrawlManifest]) -> AgentReadinessSignal:
    if manifest is None or manifest.robots_txt_found is None:
        return _signal("ai_bot_robots", "NOT_MEASURED", "robots.txt was not fetched on this crawl.")
    if not manifest.robots_txt_found:
        return _signal("ai_bot_robots", "MISSING", "No robots.txt was found. AI crawler policy is unpublished.")
    text = (manifest.robots_txt_content or "").lower()
    if not text.strip():
        return _signal("ai_bot_robots", "NOT_MEASURED", "robots.txt was reported present but its body was not stored.")

    # RFC 9309 Group parser: specific bot groups take precedence over '*'
    groups: dict[str, list[tuple[str, str]]] = {}
    current_agents: list[str] = []

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        if key == "user-agent":
            current_agents.append(value)
            if value not in groups:
                groups[value] = []
        elif key in ("allow", "disallow"):
            for agent in current_agents:
                groups[agent].append((key, value))
        else:
            current_agents = []

    # Check search bots and training bots individually
    wildcard_rules = groups.get("*", [])
    wildcard_blocked = any(k == "disallow" and v in ("/", "/*") for k, v in wildcard_rules)

    blocked_search = []
    allowed_search = []
    for bot in _AI_SEARCH_BOTS:
        bot_rules = groups.get(bot)
        if bot_rules is not None:
            if any(k == "disallow" and v in ("/", "/*") for k, v in bot_rules):
                blocked_search.append(bot)
            elif any(k == "allow" and v in ("/", "/*") for k, v in bot_rules):
                allowed_search.append(bot)
        elif wildcard_blocked:
            blocked_search.append(bot)

    blocked_training = []
    for bot in _AI_TRAINING_BOTS:
        bot_rules = groups.get(bot)
        if bot_rules is not None:
            if any(k == "disallow" and v in ("/", "/*") for k, v in bot_rules):
                blocked_training.append(bot)
        elif wildcard_blocked:
            blocked_training.append(bot)

    if allowed_search and not any(groups.get(bot) and any(k == "disallow" and v in ("/", "/*") for k, v in groups[bot]) for bot in _AI_SEARCH_BOTS):
        return _signal(
            "ai_bot_robots",
            "PRESENT",
            f"robots.txt permits AI search crawlers ({', '.join(sorted(allowed_search))}) overriding general rules.",
        )
    elif blocked_search:
        return _signal(
            "ai_bot_robots",
            "MISSING",
            f"robots.txt disallows search crawlers: {', '.join(sorted(blocked_search))}.",
        )
    elif blocked_training:
        return _signal(
            "ai_bot_robots",
            "PRESENT",
            f"robots.txt permits AI search bots while selectively restricting training bots ({', '.join(sorted(blocked_training)[:3])}).",
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


async def _llms_txt_signal(website_url: str) -> AgentReadinessSignal:
    parsed = urlparse(website_url if "://" in website_url else f"https://{website_url}")
    if not parsed.netloc:
        return _signal("llms_txt", "NOT_MEASURED", "No host was available to request /llms.txt.")
    target = f"{parsed.scheme or 'https'}://{parsed.netloc}/llms.txt"
    safe, reason = is_safe_url(target)
    if not safe:
        return _signal("llms_txt", "NOT_MEASURED", f"/llms.txt was not requested: {reason}")
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            response = await client.head(target, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
            if response.status_code == 405:
                response = await client.get(target, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
    except Exception as exc:
        return _signal("llms_txt", "NOT_MEASURED", f"/llms.txt request failed: {exc}")
    if response.status_code == 200 and len(response.content or b"") >= 0:
        # HEAD often has an empty body. 200 is enough to say the URL exists.
        return _signal("llms_txt", "PRESENT", f"{target} returned HTTP {response.status_code}.")
    if response.status_code == 404:
        return _signal("llms_txt", "MISSING", f"{target} returned HTTP 404.")
    return _signal("llms_txt", "NOT_MEASURED", f"{target} returned HTTP {response.status_code}, which is not a presence check.")


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
    signals = [
        _robots_signal(manifest),
        _faq_signal(pages),
        _definition_signal(pages),
        await _llms_txt_signal(website_url),
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
