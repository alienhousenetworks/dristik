"""
Crawl Orchestration & Operating Profiles — Enterprise Crawling & Ingestion (Phase 1.2)

Adaptive crawl scheduler with 4 operating profiles (Quick, Standard, Deep, Enterprise),
per-host rate-limiting, priority queues, and state checkpointing.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.crawl.url_discovery import DiscoveredUrl


class CrawlProfile(str, Enum):
    QUICK = "QUICK"             # 10–25 pages (rapid diagnostic)
    STANDARD = "STANDARD"       # 100–500 pages (standard commercial audit)
    DEEP = "DEEP"               # 500–2,500 pages (deep enterprise scan)
    ENTERPRISE = "ENTERPRISE"   # 2,500–10,000+ pages (full catalog audit)


class RobotsPolicy(str, Enum):
    OBEY = "OBEY"
    WARN = "WARN"
    IGNORE = "IGNORE"


@dataclass
class CrawlBudgetConfig:
    profile: CrawlProfile = CrawlProfile.STANDARD
    max_pages: int = 500
    max_concurrency: int = 5
    requests_per_second: float = 5.0
    timeout_seconds: float = 15.0
    max_redirects: int = 5
    respect_robots_txt: RobotsPolicy = RobotsPolicy.OBEY
    crawl_delay_seconds: float = 0.2
    retry_limit: int = 3
    retry_backoff_factor: float = 1.5
    excluded_path_regexes: List[str] = field(default_factory=list)

    @classmethod
    def from_profile(cls, profile: CrawlProfile, **overrides: Any) -> "CrawlBudgetConfig":
        profile_budgets = {
            CrawlProfile.QUICK: 25,
            CrawlProfile.STANDARD: 250,
            CrawlProfile.DEEP: 1500,
            CrawlProfile.ENTERPRISE: 5000,
        }
        cfg = cls(
            profile=profile,
            max_pages=profile_budgets.get(profile, 250),
            max_concurrency=3 if profile == CrawlProfile.QUICK else (8 if profile == CrawlProfile.ENTERPRISE else 5),
            requests_per_second=2.0 if profile == CrawlProfile.QUICK else 5.0,
        )
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


class PriorityCrawlQueue:
    """
    Tiered queue prioritizing Homepage (0) -> High-Intent Commercial (1) -> Content (2) -> Utility (3).
    """

    def __init__(self):
        self._queues: Dict[int, List[DiscoveredUrl]] = {0: [], 1: [], 2: [], 3: []}
        self._queued_hashes: Set[str] = set()

    def push(self, url: DiscoveredUrl) -> bool:
        if url.url_hash in self._queued_hashes:
            return False
        tier = max(0, min(3, url.priority_tier))
        self._queues[tier].append(url)
        self._queued_hashes.add(url.url_hash)
        return True

    def pop(self) -> Optional[DiscoveredUrl]:
        for tier in (0, 1, 2, 3):
            if self._queues[tier]:
                return self._queues[tier].pop(0)
        return None

    def __len__(self) -> int:
        return sum(len(q) for q in self._queues.values())

    def contains(self, url_hash: str) -> bool:
        return url_hash in self._queued_hashes


class CrawlScheduler:
    """
    Manages rate-limiting, concurrency, robots rules, exclusions, and state checkpoints.
    """

    def __init__(self, run_id: str, config: CrawlBudgetConfig, checkpoint_dir: Optional[Path] = None):
        self.run_id = run_id
        self.config = config
        self.checkpoint_dir = checkpoint_dir or Path(f"data/runs/{run_id}")
        self.queue = PriorityCrawlQueue()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}
        self.excluded_urls: Set[str] = set()
        self.last_request_time: float = 0.0
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        self.is_cancelled: bool = False

    def is_path_excluded(self, url: str) -> bool:
        """Evaluates user-configured regex exclusions."""
        for pattern in self.config.excluded_path_regexes:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def schedule_url(self, url: DiscoveredUrl) -> bool:
        if len(self.crawled_urls) + len(self.queue) >= self.config.max_pages:
            return False
        if self.is_path_excluded(url.normalized_url):
            self.excluded_urls.add(url.normalized_url)
            return False
        return self.queue.push(url)

    async def throttle(self):
        """Enforces per-host rate limit and crawl-delay."""
        min_interval = max(
            1.0 / self.config.requests_per_second if self.config.requests_per_second > 0 else 0.2,
            self.config.crawl_delay_seconds
        )
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def checkpoint_state(self) -> Dict[str, Any]:
        """Saves current scheduler state for inspection or resumption."""
        state = {
            "run_id": self.run_id,
            "profile": self.config.profile.value,
            "crawled_count": len(self.crawled_urls),
            "queued_count": len(self.queue),
            "failed_count": len(self.failed_urls),
            "excluded_count": len(self.excluded_urls),
            "timestamp": time.time(),
        }
        try:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            chk_file = self.checkpoint_dir / "crawl_checkpoint.json"
            chk_file.write_text(json.dumps(state, indent=2))
        except Exception:
            pass
        return state

    def cancel(self):
        self.is_cancelled = True
