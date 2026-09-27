"""
Dristik AI Meta Title & Description Rollup Analyzer
Classifies all crawled URLs into standard agency diagnostic buckets:
Titles:
  - missing (0 chars)
  - too_short (< 30 chars)
  - optimal (50-60 chars)
  - too_long (> 60 chars)
  - duplicate (identical title across multiple URLs)
Descriptions:
  - missing (0 chars)
  - too_short (< 70 chars)
  - optimal (150-160 chars)
  - too_long (> 160 chars)
  - duplicate (identical description across multiple URLs)
Computes estimated pixel rendering width and tracks affected URL lists.
"""
from typing import List, Dict, Optional
from collections import defaultdict
from app.domain.models import PageEvidence, MetaBucketItem, MetaBucketRollup

# Proportional character width estimation for standard Google SERP font (Arial / Roboto)
_CHAR_PIXEL_WIDTHS: Dict[str, float] = {
    "i": 3.8, "l": 3.8, "j": 3.8, "f": 4.5, "r": 5.0, "t": 5.0,
    "m": 13.0, "w": 12.0, "M": 13.5, "W": 14.0,
    "A": 9.5, "B": 9.0, "C": 9.5, "D": 9.5, "E": 8.5,
    " ": 4.0, "-": 5.0, "|": 3.8, ".": 3.8, ",": 3.8,
}
_DEFAULT_CHAR_WIDTH = 8.5


def estimate_pixel_width(text: Optional[str]) -> int:
    """Estimates SERP pixel width for a text string."""
    if not text:
        return 0
    width = sum(_CHAR_PIXEL_WIDTHS.get(c, _DEFAULT_CHAR_WIDTH) for c in text)
    return int(round(width))


class MetaRollupAnalyzer:
    @staticmethod
    def analyze(pages: List[PageEvidence]) -> MetaBucketRollup:
        total = len(pages)
        if total == 0:
            return MetaBucketRollup(
                total_pages_evaluated=0,
                title_summary="No pages crawled to evaluate meta tags.",
                description_summary="No pages crawled to evaluate meta descriptions."
            )

        # -------------------------------------------------------------
        # 1. Track Duplicate Collisions
        # -------------------------------------------------------------
        title_url_map: Dict[str, List[str]] = defaultdict(list)
        desc_url_map: Dict[str, List[str]] = defaultdict(list)

        for p in pages:
            t = (p.title or "").strip()
            d = (p.meta_description or "").strip()
            if t:
                title_url_map[t.lower()].append(p.url)
            if d:
                desc_url_map[d.lower()].append(p.url)

        # -------------------------------------------------------------
        # 2. Bucket Titles
        # -------------------------------------------------------------
        missing_titles: List[MetaBucketItem] = []
        too_short_titles: List[MetaBucketItem] = []
        optimal_titles: List[MetaBucketItem] = []
        too_long_titles: List[MetaBucketItem] = []
        duplicate_titles: List[MetaBucketItem] = []

        seen_dup_titles = set()

        for p in pages:
            t = (p.title or "").strip()
            t_len = len(t)
            px = estimate_pixel_width(t)
            item = MetaBucketItem(url=p.url, text=t or None, char_length=t_len, pixel_length=px)

            if t_len == 0:
                missing_titles.append(item)
            elif t_len < 30:
                too_short_titles.append(item)
            elif 50 <= t_len <= 60:
                optimal_titles.append(item)
            elif t_len > 60:
                too_long_titles.append(item)

            # Check duplicate collision
            if t and len(title_url_map[t.lower()]) > 1:
                duplicate_titles.append(item)

        # -------------------------------------------------------------
        # 3. Bucket Descriptions
        # -------------------------------------------------------------
        missing_descriptions: List[MetaBucketItem] = []
        too_short_descriptions: List[MetaBucketItem] = []
        optimal_descriptions: List[MetaBucketItem] = []
        too_long_descriptions: List[MetaBucketItem] = []
        duplicate_descriptions: List[MetaBucketItem] = []

        for p in pages:
            d = (p.meta_description or "").strip()
            d_len = len(d)
            px = estimate_pixel_width(d)
            item = MetaBucketItem(url=p.url, text=d or None, char_length=d_len, pixel_length=px)

            if d_len == 0:
                missing_descriptions.append(item)
            elif d_len < 70:
                too_short_descriptions.append(item)
            elif 150 <= d_len <= 160:
                optimal_descriptions.append(item)
            elif d_len > 160:
                too_long_descriptions.append(item)

            # Check duplicate collision
            if d and len(desc_url_map[d.lower()]) > 1:
                duplicate_descriptions.append(item)

        title_issues = (
            len(missing_titles)
            + len(too_short_titles)
            + len(too_long_titles)
            + len(duplicate_titles)
        )
        desc_issues = (
            len(missing_descriptions)
            + len(too_short_descriptions)
            + len(too_long_descriptions)
            + len(duplicate_descriptions)
        )

        title_summary = (
            f"Evaluated {total} pages: {len(optimal_titles)} optimal (50-60 chars), "
            f"{len(missing_titles)} missing, {len(too_short_titles)} short (<30), "
            f"{len(too_long_titles)} long (>60), {len(duplicate_titles)} duplicates."
        )

        desc_summary = (
            f"Evaluated {total} pages: {len(optimal_descriptions)} optimal (150-160 chars), "
            f"{len(missing_descriptions)} missing, {len(too_short_descriptions)} short (<70), "
            f"{len(too_long_descriptions)} long (>160), {len(duplicate_descriptions)} duplicates."
        )

        return MetaBucketRollup(
            total_pages_evaluated=total,
            missing_titles=missing_titles,
            too_short_titles=too_short_titles,
            optimal_titles=optimal_titles,
            too_long_titles=too_long_titles,
            duplicate_titles=duplicate_titles,
            title_issue_count=title_issues,
            missing_descriptions=missing_descriptions,
            too_short_descriptions=too_short_descriptions,
            optimal_descriptions=optimal_descriptions,
            too_long_descriptions=too_long_descriptions,
            duplicate_descriptions=duplicate_descriptions,
            description_issue_count=desc_issues,
            title_summary=title_summary,
            description_summary=desc_summary
        )


def analyze_meta_rollup(pages: List[PageEvidence]) -> MetaBucketRollup:
    return MetaRollupAnalyzer.analyze(pages)
