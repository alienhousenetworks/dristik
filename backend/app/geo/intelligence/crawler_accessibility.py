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

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    def evaluate_crawler_access(
        cls,
        robots_txt: str = "",
        headers: Optional[Dict[str, str]] = None,
        cdn_headers: Optional[Dict[str, str]] = None,
        is_client_rendered_only: bool = False,
    ) -> CrawlerAccessibilityReport:
        hdrs = {k.lower(): v.lower() for k, v in (headers or {}).items()}
        cdn = {k.lower(): v.lower() for k, v in (cdn_headers or {}).items()}
        statuses: List[CrawlerAccessStatus] = []
        recs: List[str] = []

        # Parse robots.txt blocks by user-agent
        ua_blocks: Dict[str, List[str]] = {"*": []}
        curr_ua = "*"
        for raw_line in (robots_txt or "").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = [p.strip() for p in line.split(":", 1)]
                k_low = k.lower()
                if k_low == "user-agent":
                    curr_ua = v
                    if curr_ua not in ua_blocks:
                        ua_blocks[curr_ua] = []
                elif k_low == "disallow":
                    ua_blocks[curr_ua].append(v)

        # Check HTTP headers for noai directives
        x_robots = hdrs.get("x-robots-tag", "")
        has_noai_header = "noai" in x_robots or "noimageai" in x_robots

        # Check CDN/WAF challenges
        cf_mitigation = "cf-mitigated" in cdn or "cf-chl-bypass" in cdn
        has_bot_challenge = cf_mitigation or "cloudflare-challenge" in str(hdrs.values())

        search_allowed = True
        user_fetch_allowed = True
        training_allowed = True

        for bot_name, meta in cls.KNOWN_AI_BOTS.items():
            purpose = meta["purpose"]
            desc = meta["desc"]

            # Specific UA rule or fallback to '*'
            rules = ua_blocks.get(bot_name)
            if rules is None:
                # Check wildcard
                rules = ua_blocks.get("*", [])

            is_blocked = False
            restr_src = None
            disallowed: List[str] = []

            for r in rules:
                if r in ("/", "/*"):
                    is_blocked = True
                    restr_src = "ROBOTS_TXT"
                    disallowed.append(r)
                elif r:
                    disallowed.append(r)

            if has_noai_header and purpose == CrawlerPurpose.MODEL_TRAINING:
                is_blocked = True
                restr_src = "HTTP_HEADER (X-Robots-Tag: noai)"

            if is_blocked:
                if purpose in (CrawlerPurpose.SEARCH_RETRIEVAL, CrawlerPurpose.GENERAL_WEB_INDEX):
                    search_allowed = False
                    recs.append(f"Unblock {bot_name} in robots.txt to restore generative search citation eligibility.")
                elif purpose == CrawlerPurpose.USER_REQUESTED_FETCH:
                    user_fetch_allowed = False
                    recs.append(f"Allow {bot_name} so users can share site links in conversational prompts.")
                elif purpose == CrawlerPurpose.MODEL_TRAINING:
                    training_allowed = False

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
            synth_parts.append("WARNING: Critical AI search retrieval crawlers are blocked in robots.txt.")

        if not training_allowed:
            synth_parts.append("Model training crawlers (GPTBot, ClaudeBot, Google-Extended) are intentionally restricted.")
        else:
            synth_parts.append("Model training crawlers are permitted full content access.")

        return CrawlerAccessibilityReport(
            search_retrieval_allowed=search_allowed,
            user_fetch_allowed=user_fetch_allowed,
            model_training_allowed=training_allowed,
            crawlers_evaluated=statuses,
            cdn_waf_challenges_detected=has_bot_challenge,
            js_rendering_wall_detected=is_client_rendered_only,
            executive_synthesis=" ".join(synth_parts),
            actionable_remediation=recs,
        )
