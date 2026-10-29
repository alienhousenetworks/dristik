"""
AI Crawler Access Log Analyzer (Layer 1 / Layer 2 Extension).
Parses web server / CDN access logs (Cloudflare, Nginx, Apache, AWS CloudFront)
to measure AI crawler activity, crawl frequency, blocked paths, and crawl budget health.
"""
from __future__ import annotations

import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

KNOWN_AI_BOTS: Dict[str, re.Pattern] = {
    "GPTBot": re.compile(r"GPTBot/([0-9\.]+)", re.I),
    "ChatGPT-User": re.compile(r"ChatGPT-User/([0-9\.]+)", re.I),
    "PerplexityBot": re.compile(r"PerplexityBot/([0-9\.]+)", re.I),
    "ClaudeBot": re.compile(r"ClaudeBot/([0-9\.]+)|Claude-Web/([0-9\.]+)", re.I),
    "Google-Extended": re.compile(r"Google-Extended", re.I),
    "Amazonbot": re.compile(r"Amazonbot/([0-9\.]+)", re.I),
    "Bytespider": re.compile(r"Bytespider", re.I),
    "Applebot-Extended": re.compile(r"Applebot-Extended", re.I),
}

# Standard Combined Log Format regex: IP - - [date] "METHOD PATH HTTP/X" STATUS BYTES "REFERER" "USER_AGENT"
CLF_REGEX = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)(?:\s+"(?P<referer>[^"]*)")?(?:\s+"(?P<agent>[^"]*)")?',
    re.I
)


class CrawlerHit(BaseModel):
    bot_name: str
    ip_address: str
    path: str
    status_code: int
    timestamp: str
    user_agent: str
    is_blocked: bool = False


class CrawlerLogAnalysis(BaseModel):
    total_lines_parsed: int
    total_ai_bot_hits: int
    bot_breakdown: Dict[str, int] = Field(default_factory=dict)
    status_code_breakdown: Dict[str, int] = Field(default_factory=dict)
    blocked_bot_hits: int = 0
    top_crawled_paths: List[Dict[str, Any]] = Field(default_factory=list)
    bot_health_score: float = 100.0
    recommendations: List[str] = Field(default_factory=list)


class AiCrawlerLogAnalyzer:
    """
    Parses and analyzes server/CDN access logs to provide observability into
    AI crawler behavior and indexing health.
    """

    def analyze_logs(self, log_content: str) -> CrawlerLogAnalysis:
        lines = [ln.strip() for ln in log_content.strip().split("\n") if ln.strip()]
        total_lines = len(lines)
        if total_lines == 0:
            return CrawlerLogAnalysis(
                total_lines_parsed=0,
                total_ai_bot_hits=0,
                bot_breakdown={},
                status_code_breakdown={},
                blocked_bot_hits=0,
                top_crawled_paths=[],
                bot_health_score=100.0,
                recommendations=["Provide server or CDN access log text to analyze AI crawler traffic."],
            )

        hits: List[CrawlerHit] = []
        path_counts: Dict[str, int] = {}
        bot_counts: Dict[str, int] = {bot: 0 for bot in KNOWN_AI_BOTS}
        status_counts: Dict[str, int] = {}

        for line in lines:
            m = CLF_REGEX.search(line)
            if m:
                agent = m.group("agent") or ""
                path = m.group("path") or ""
                status = int(m.group("status") or "200")
                ip = m.group("ip") or "unknown"
                time_str = m.group("time") or ""
            else:
                # Fallback simple line scan
                agent = line
                path = "/"
                status = 403 if " 403 " in line else (429 if " 429 " in line else 200)
                ip = line.split(" ")[0] if " " in line else "unknown"
                time_str = ""

            # Check if user agent matches known AI crawler bot
            matched_bot = None
            for bname, pattern in KNOWN_AI_BOTS.items():
                if pattern.search(agent):
                    matched_bot = bname
                    break

            if matched_bot:
                bot_counts[matched_bot] = bot_counts.get(matched_bot, 0) + 1
                status_key = str(status)
                status_counts[status_key] = status_counts.get(status_key, 0) + 1
                path_counts[path] = path_counts.get(path, 0) + 1
                is_blocked = status in (401, 403, 429)

                hits.append(CrawlerHit(
                    bot_name=matched_bot,
                    ip_address=ip,
                    path=path,
                    status_code=status,
                    timestamp=time_str,
                    user_agent=agent[:150],
                    is_blocked=is_blocked,
                ))

        total_bot_hits = len(hits)
        blocked_hits = sum(1 for h in hits if h.is_blocked)

        # Health score: 100 - (blocked_ratio * 100)
        health_score = 100.0
        if total_bot_hits > 0:
            blocked_ratio = blocked_hits / total_bot_hits
            health_score = max(0.0, round((1.0 - blocked_ratio) * 100.0, 1))

        # Top paths
        sorted_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_paths = [{"path": p, "crawl_count": c} for p, c in sorted_paths]

        # Active bot breakdown (only include bots with > 0 hits)
        active_bots = {k: v for k, v in bot_counts.items() if v > 0}

        # Recommendations
        recs: List[str] = []
        if total_bot_hits == 0:
            recs.append("No AI search crawler hits detected in the provided log sample. Verify your WAF / robots.txt allows GPTBot and PerplexityBot.")
        else:
            if blocked_hits > 0:
                recs.append(f"{blocked_hits} AI crawler request(s) were blocked (403/429). Inspect Cloudflare WAF or rate-limiting rules.")
            if "GPTBot" not in active_bots:
                recs.append("GPTBot (OpenAI/SearchGPT) was not observed in the log sample.")
            if "PerplexityBot" not in active_bots:
                recs.append("PerplexityBot was not observed in the log sample.")
            if not recs:
                recs.append("AI crawlers are successfully indexing your site without blocks or rate limiting.")

        return CrawlerLogAnalysis(
            total_lines_parsed=total_lines,
            total_ai_bot_hits=total_bot_hits,
            bot_breakdown=active_bots,
            status_code_breakdown=status_counts,
            blocked_bot_hits=blocked_hits,
            top_crawled_paths=top_paths,
            bot_health_score=health_score,
            recommendations=recs,
        )


crawler_log_analyzer = AiCrawlerLogAnalyzer()
