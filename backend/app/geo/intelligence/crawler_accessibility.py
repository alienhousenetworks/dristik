"""
AI Crawler Accessibility Intelligence — Phase 4.2

Builds a dedicated AI crawler accessibility engine evaluating:
- GPTBot (Model training)
- OAI-SearchBot (Search retrieval)
- ChatGPT-User (On-demand user prompt browsing)
- ClaudeBot (Anthropic model training)
- PerplexityBot (Perplexity live search indexing)
- Googlebot (Google Search & AI Overviews)
- Google-Extended (Gemini training policy)
- Bingbot (Bing & Copilot indexation)
- Robots.txt rules, HTTP headers, CDN bot challenges, and WAF behavior

STRICT GUARDRAIL:
Keeps crawler identities and their distinct purposes separate.
Search retrieval access, user-requested fetching, and model-training access are NOT interchangeable.
"""
from __future__ import annotations

import asyncio
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

import httpx

from app.core.security.ssrf import is_safe_url
from app.crawl.robots import check_ai_bots_robots, evaluate_robots


AI_UA_PROBES: Dict[str, str] = {
    "GPTBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
        "GPTBot/1.2; +https://openai.com/gptbot"
    ),
    "OAI-SearchBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
        "OAI-SearchBot/1.0; +https://openai.com/searchbot"
    ),
    "ClaudeBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
        "ClaudeBot/1.0; +claudebot@anthropic.com"
    ),
    "PerplexityBot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
        "PerplexityBot/1.0; +https://perplexity.ai/perplexitybot"
    ),
    "Bytespider": (
        "Mozilla/5.0 (Linux; Android 5.0) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Mobile Safari/537.36 (compatible; Bytespider; spider-feedback@bytedance.com)"
    ),
}

_WAF_BLOCK_STATUSES = frozenset({401, 403, 406, 429, 451, 503})


class CrawlerPurpose(str, Enum):
    SEARCH_RETRIEVAL = "SEARCH_RETRIEVAL"
    USER_REQUESTED_FETCH = "USER_REQUESTED_FETCH"
    MODEL_TRAINING = "MODEL_TRAINING"
    GENERAL_WEB_INDEX = "GENERAL_WEB_INDEX"


class CrawlerAccessStatus(BaseModel):
    bot_name: str
    purpose: CrawlerPurpose
    is_allowed: bool
    restriction_source: Optional[str] = None  # ROBOTS_TXT, HTTP_HEADER, CDN_WAF, JAVASCRIPT_WALL
    disallowed_paths: List[str] = Field(default_factory=list)
    impact_note: str


class CrawlerAccessibilityReport(BaseModel):
    model_config = {"protected_namespaces": ()}
    search_retrieval_allowed: bool

    user_fetch_allowed: bool
    model_training_allowed: bool
    crawlers_evaluated: List[CrawlerAccessStatus] = Field(default_factory=list)
    cdn_waf_challenges_detected: bool = False
    js_rendering_wall_detected: bool = False
    ai_ua_probe: Dict[str, int] = Field(default_factory=dict)
    ai_ua_blocked: List[str] = Field(default_factory=list)
    partial_path_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    executive_synthesis: str
    actionable_remediation: List[str] = Field(default_factory=list)


class CrawlerAccessibilityEngine:
    """
    Evaluates AI search bots, on-demand fetchers, and training crawlers independently.
    """

    KNOWN_AI_BOTS: Dict[str, Dict[str, Any]] = {
        "OAI-SearchBot": {
            "purpose": CrawlerPurpose.SEARCH_RETRIEVAL,
            "desc": "Powers ChatGPT Search real-time citations and answer cards.",
        },
        "PerplexityBot": {
            "purpose": CrawlerPurpose.SEARCH_RETRIEVAL,
            "desc": "Powers Perplexity AI search retrieval and live web sources.",
        },
        "Claude-SearchBot": {
            "purpose": CrawlerPurpose.SEARCH_RETRIEVAL,
            "desc": "Powers Anthropic Claude live search results and citations.",
        },
        "Googlebot": {
            "purpose": CrawlerPurpose.GENERAL_WEB_INDEX,
            "desc": "Powers Google Search and Google AI Overviews synthesized answers.",
        },
        "Bingbot": {
            "purpose": CrawlerPurpose.GENERAL_WEB_INDEX,
            "desc": "Powers Bing Search and Microsoft Copilot answer grounding.",
        },
        "ChatGPT-User": {
            "purpose": CrawlerPurpose.USER_REQUESTED_FETCH,
            "desc": "Fetches page on-demand when a ChatGPT user pastes a link.",
        },
        "Claude-User": {
            "purpose": CrawlerPurpose.USER_REQUESTED_FETCH,
            "desc": "Fetches page on-demand when a Claude user requests a URL.",
        },
        "Perplexity-User": {
            "purpose": CrawlerPurpose.USER_REQUESTED_FETCH,
            "desc": "Fetches page on-demand when a Perplexity user requests a URL.",
        },
        "GPTBot": {
            "purpose": CrawlerPurpose.MODEL_TRAINING,
            "desc": "Crawls web content for OpenAI model pre-training and fine-tuning.",
        },
        "ClaudeBot": {
            "purpose": CrawlerPurpose.MODEL_TRAINING,
            "desc": "Crawls web content for Anthropic Claude model training.",
        },
        "Google-Extended": {
            "purpose": CrawlerPurpose.MODEL_TRAINING,
            "desc": "Controls whether Google uses site content for Gemini and Vertex AI training.",
        },
    }

    @classmethod
    async def probe_ai_user_agents(
        cls,
        root_url: str,
        robots_txt: str = "",
        browser_status: int = 200,
        timeout: float = 8.0,
        delay: float = 0.2,
    ) -> Dict[str, Any]:
        """Actively probe `root_url` with real AI crawler User-Agents to detect silent WAF/CDN blocks.

        Only probes bots that robots.txt allows when baseline browser fetch returned HTTP 200.
        Never bypasses WAF/CAPTCHA; surfaces differential HTTP 401/403/406/429/451/503 responses.
        """
        probe: Dict[str, int] = {}
        ua_blocked: List[str] = []
        if browser_status != 200:
            return {"ai_ua_probe": probe, "ai_ua_blocked": ua_blocked, "skipped": "baseline_not_200"}
        safe, reason = is_safe_url(root_url)
        if not safe:
            return {"ai_ua_probe": probe, "ai_ua_blocked": ua_blocked, "skipped": f"ssrf_blocked: {reason}"}

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for bot, ua in AI_UA_PROBES.items():
                if not evaluate_robots(robots_txt, "/", user_agent=bot).allowed:
                    continue
                try:
                    resp = await client.get(root_url, headers={"User-Agent": ua})
                    status = int(resp.status_code)
                except Exception:
                    status = 0
                probe[bot] = status
                if status in _WAF_BLOCK_STATUSES:
                    ua_blocked.append(bot)
                if delay > 0:
                    await asyncio.sleep(delay)
        return {"ai_ua_probe": probe, "ai_ua_blocked": ua_blocked}

    @classmethod
    def evaluate_crawler_access(
        cls,
        robots_txt: str = "",
        headers: Optional[Dict[str, str]] = None,
        cdn_headers: Optional[Dict[str, str]] = None,
        is_client_rendered_only: bool = False,
        sample_paths: Sequence[str] = (),
        ai_ua_probe: Optional[Dict[str, int]] = None,
        page_path: str = "/",
    ) -> CrawlerAccessibilityReport:
        hdrs = {k.lower(): v.lower() for k, v in (headers or {}).items()}
        cdn = {k.lower(): v.lower() for k, v in (cdn_headers or {}).items()}
        statuses: List[CrawlerAccessStatus] = []
        recs: List[str] = []

        # Check HTTP headers for noai directives
        x_robots = hdrs.get("x-robots-tag", "")
        has_noai_header = "noai" in x_robots or "noimageai" in x_robots

        # Check CDN/WAF challenges (passive headers + active differential UA probe)
        probe_map = dict(ai_ua_probe or {})
        ua_blocked = [bot for bot, code in probe_map.items() if code in _WAF_BLOCK_STATUSES]
        cf_mitigation = "cf-mitigated" in cdn or "cf-chl-bypass" in cdn
        has_bot_challenge = cf_mitigation or "cloudflare-challenge" in str(hdrs.values()) or bool(ua_blocked)

        _, partial_blocks = check_ai_bots_robots(robots_txt, sample_paths=sample_paths, bots=tuple(cls.KNOWN_AI_BOTS.keys()))
        partial_by_bot = {p["bot"]: p for p in partial_blocks}

        search_allowed = True
        user_fetch_allowed = True
        training_allowed = True

        for bot_name, meta in cls.KNOWN_AI_BOTS.items():
            purpose = meta["purpose"]
            desc = meta["desc"]

            target_path = page_path if page_path.startswith("/") else f"/{page_path}"
            decision = evaluate_robots(robots_txt, target_path, user_agent=bot_name)
            is_blocked = not decision.allowed
            restr_src: Optional[str] = "ROBOTS_TXT" if is_blocked else None
            disallowed: List[str] = []
            if is_blocked and decision.matched_rule:
                disallowed.append(decision.matched_rule)
            elif bot_name in partial_by_bot:
                disallowed.extend(str(p) for p in partial_by_bot[bot_name].get("paths", []))

            if not is_blocked and bot_name in ua_blocked:
                is_blocked = True
                restr_src = f"CDN_WAF (HTTP {probe_map[bot_name]} on AI UA probe)"

            if has_noai_header and purpose == CrawlerPurpose.MODEL_TRAINING:
                is_blocked = True
                restr_src = "HTTP_HEADER (X-Robots-Tag: noai)"

            if is_blocked:
                if purpose in (CrawlerPurpose.SEARCH_RETRIEVAL, CrawlerPurpose.GENERAL_WEB_INDEX):
                    search_allowed = False
                    if restr_src and restr_src.startswith("CDN_WAF"):
                        recs.append(f"Allow {bot_name} in WAF/CDN bot rules (robots.txt permits it, but CDN returned HTTP {probe_map[bot_name]}).")
                    else:
                        recs.append(f"Unblock {bot_name} in robots.txt to restore generative search citation eligibility.")
                elif purpose == CrawlerPurpose.USER_REQUESTED_FETCH:
                    user_fetch_allowed = False
                    recs.append(f"Allow {bot_name} so users can share site links in conversational prompts.")
                elif purpose == CrawlerPurpose.MODEL_TRAINING:
                    training_allowed = False
                    if restr_src and restr_src.startswith("CDN_WAF"):
                        recs.append(f"Review WAF/CDN rule returning HTTP {probe_map[bot_name]} for {bot_name} while robots.txt permits it.")

            statuses.append(
                CrawlerAccessStatus(
                    bot_name=bot_name,
                    purpose=purpose,
                    is_allowed=not is_blocked,
                    restriction_source=restr_src,
                    disallowed_paths=disallowed,
                    impact_note=desc,
                )
            )

        # JS Wall Check
        if is_client_rendered_only:
            recs.append("Static HTML payload contains near-empty DOM; AI crawlers without full headless JS will miss body copy.")

        # Synthesis
        synth_parts = []
        if search_allowed:
            synth_parts.append("AI search retrieval crawlers (OAI-SearchBot, PerplexityBot, Googlebot) have full indexing access.")
        else:
            synth_parts.append("WARNING: Critical AI search retrieval crawlers are blocked in robots.txt or WAF/CDN.")

        if not training_allowed:
            synth_parts.append("Model training crawlers (GPTBot, ClaudeBot, Google-Extended) are restricted.")
        else:
            synth_parts.append("Model training crawlers are permitted full content access.")

        return CrawlerAccessibilityReport(
            search_retrieval_allowed=search_allowed,
            user_fetch_allowed=user_fetch_allowed,
            model_training_allowed=training_allowed,
            crawlers_evaluated=statuses,
            cdn_waf_challenges_detected=has_bot_challenge,
            js_rendering_wall_detected=is_client_rendered_only,
            ai_ua_probe=probe_map,
            ai_ua_blocked=ua_blocked,
            partial_path_blocks=partial_blocks,
            executive_synthesis=" ".join(synth_parts),
            actionable_remediation=recs,
        )
