"""robots.txt parsing used by the crawler.

Sitemap discovery is the rule the crawler applies. Allow and Disallow groups
are parsed for inspection. They are not a new crawl filter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


def declared_sitemaps(content: str) -> List[str]:
    """Return absolute Sitemap: URLs from a robots.txt body."""
    sitemap_urls: List[str] = []
    for line in (content or "").splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            if sitemap_url.startswith("http"):
                sitemap_urls.append(sitemap_url)
    return sitemap_urls


@dataclass
class RobotsGroup:
    user_agents: List[str] = field(default_factory=list)
    allow: List[str] = field(default_factory=list)
    disallow: List[str] = field(default_factory=list)


def parse_robots(content: str) -> List[RobotsGroup]:
    """Parse User-agent groups. A missing or empty body yields no groups."""
    groups: List[RobotsGroup] = []
    current: RobotsGroup | None = None
    for raw_line in (content or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, value = line.split(":", 1)
        key = field_name.strip().lower()
        token = value.strip()
        if key == "user-agent":
            if current is None or current.allow or current.disallow:
                current = RobotsGroup(user_agents=[token])
                groups.append(current)
            else:
                current.user_agents.append(token)
        elif key == "allow" and current is not None:
            current.allow.append(token)
        elif key == "disallow" and current is not None:
            current.disallow.append(token)
    return groups


def sitewide_disallow(content: str, user_agent: str = "*") -> bool:
    """True when a matching group disallows the whole site."""
    agent = user_agent.lower()
    for group in parse_robots(content):
        names = [name.lower() for name in group.user_agents]
        if agent not in names and "*" not in names:
            continue
        if "/" in group.disallow and not any(path == "/" for path in group.allow):
            return True
    return False
