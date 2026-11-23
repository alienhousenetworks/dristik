"""RFC 9309-compliant robots.txt parser shared across Crawl, GEO, and AEO.

Adapted in part from GeoLook's MIT-licensed RFC 9309 semantics:
- Multiple User-agent lines share one rule group
- Specific UA group overrides '*' regardless of file order
- Longest matching path wins; Allow beats Disallow on equal length
- Supports '*' mid-path wildcards and '$' end-of-path anchors
- Empty Disallow values are treated as allow-all (not a blocking rule)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse


AI_CRAWLER_BOTS: Tuple[str, ...] = (
    "GPTBot",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-SearchBot",
    "PerplexityBot",
    "Bytespider",
    "Google-Extended",
    "ChatGPT-User",
)


def declared_sitemaps(content: str) -> List[str]:
    """Return absolute Sitemap: URLs from a robots.txt body."""
    sitemap_urls: List[str] = []
    for line in (content or "").splitlines():
        cleaned = line.split("#", 1)[0].strip()
        if cleaned.lower().startswith("sitemap:"):
            sitemap_url = cleaned.split(":", 1)[1].strip()
            if sitemap_url.startswith("http"):
                sitemap_urls.append(sitemap_url)
    return sitemap_urls


@dataclass
class RobotsGroup:
    user_agents: List[str] = field(default_factory=list)
    allow: List[str] = field(default_factory=list)
    disallow: List[str] = field(default_factory=list)
    rules: List[Tuple[bool, str]] = field(default_factory=list)


@dataclass
class RobotsDecision:
    allowed: bool
    matched_rule: Optional[str]
    matched_group: Optional[str]
    user_agent: str
    path: str
    reason: str


def parse_robots(content: str) -> List[RobotsGroup]:
    """Parse User-agent groups per RFC 9309. A missing or empty body yields no groups."""
    groups: List[RobotsGroup] = []
    current: Optional[RobotsGroup] = None
    last_was_agent = False

    for raw_line in (content or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, value = line.split(":", 1)
        key = field_name.strip().lower()
        token = value.strip()
        if key == "user-agent":
            if current is None or not last_was_agent:
                current = RobotsGroup(user_agents=[token])
                groups.append(current)
            else:
                current.user_agents.append(token)
            last_was_agent = True
        elif key == "allow" and current is not None:
            last_was_agent = False
            if token:
                current.allow.append(token)
                current.rules.append((True, token))
        elif key == "disallow" and current is not None:
            last_was_agent = False
            if token:
                current.disallow.append(token)
                current.rules.append((False, token))
        else:
            last_was_agent = False
    return groups


def _robots_rule_rx(pattern: str) -> re.Pattern[str]:
    rx = re.escape(pattern).replace(r"\*", ".*")
    if rx.endswith(r"\$"):
        rx = rx[:-2] + "$"
    return re.compile("^" + rx)


def _normalize_target_path(target_url_or_path: str) -> str:
    if not target_url_or_path:
        return "/"
    if "://" in target_url_or_path:
        parsed = urlparse(target_url_or_path)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return path
    return target_url_or_path if target_url_or_path.startswith("/") else f"/{target_url_or_path}"


def evaluate_robots(
    robots_txt: str,
    target_url_or_path: str = "/",
    user_agent: str = "*",
) -> RobotsDecision:
    """Evaluate whether `user_agent` may crawl `target_url_or_path` under RFC 9309."""
    path = _normalize_target_path(target_url_or_path)
    groups = parse_robots(robots_txt or "")
    ua_l = (user_agent or "*").strip().lower()

    specific: Optional[RobotsGroup] = None
    spec_len = -1
    spec_name: Optional[str] = None
    wildcard: Optional[RobotsGroup] = None

    for g in groups:
        for agent in g.user_agents:
            al = agent.strip().lower()
            if al == "*":
                if wildcard is None:
                    wildcard = g
            elif ua_l != "*" and al and (al in ua_l or ua_l in al) and len(al) > spec_len:
                specific = g
                spec_len = len(al)
                spec_name = agent

    chosen = specific or wildcard
    chosen_name = spec_name if specific is not None else ("*" if wildcard is not None else None)
    if chosen is None:
        return RobotsDecision(
            allowed=True,
            matched_rule=None,
            matched_group=None,
            user_agent=user_agent,
            path=path,
            reason="No matching User-agent group; allowed by default.",
        )

    match_len = -1
    allowed = True
    matched_rule: Optional[str] = None
    for is_allow, pat in chosen.rules:
        if _robots_rule_rx(pat).match(path):
            plen = len(pat)
            if plen > match_len or (plen == match_len and is_allow and not allowed):
                match_len = plen
                allowed = is_allow
                matched_rule = f"{'Allow' if is_allow else 'Disallow'}: {pat}"

    reason = (
        f"Matched '{matched_rule}' in group '{chosen_name}'."
        if matched_rule
        else f"No matching path rule in group '{chosen_name}'; allowed by default."
    )
    return RobotsDecision(
        allowed=allowed,
        matched_rule=matched_rule,
        matched_group=chosen_name,
        user_agent=user_agent,
        path=path,
        reason=reason,
    )


def sitewide_disallow(content: str, user_agent: str = "*") -> bool:
    """True when the RFC 9309-selected group disallows the root path '/'."""
    return not evaluate_robots(content or "", "/", user_agent=user_agent).allowed


def check_ai_bots_robots(
    robots_txt: str,
    sample_paths: Sequence[str] = (),
    bots: Sequence[str] = AI_CRAWLER_BOTS,
) -> Tuple[List[str], List[Dict[str, object]]]:
    """Return `(sitewide_blocked_bots, partial_path_blocks)` across `sample_paths`."""
    blocked: List[str] = []
    partial: List[Dict[str, object]] = []
    norm_paths = [_normalize_target_path(p) for p in sample_paths if p]
    for bot in bots:
        root_dec = evaluate_robots(robots_txt, "/", user_agent=bot)
        if not root_dec.allowed:
            blocked.append(bot)
            continue
        denied: List[Tuple[str, Optional[str]]] = []
        for p in norm_paths:
            dec = evaluate_robots(robots_txt, p, user_agent=bot)
            if not dec.allowed:
                denied.append((p, dec.matched_rule))
        if denied:
            partial.append(
                {
                    "bot": bot,
                    "rule": denied[0][1],
                    "paths": [p for p, _ in denied[:5]],
                    "count": len(denied),
                    "sampled": len(norm_paths),
                }
            )
    return blocked, partial
