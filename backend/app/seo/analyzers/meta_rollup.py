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
from app.crawl.analyzers.pixel_calculator import (
    calculate_title_pixel_width,
    calculate_meta_pixel_width,
    GOOGLE_TITLE_MAX_PX,
    GOOGLE_META_MAX_PX,
)


def estimate_pixel_width(text: Optional[str]) -> int:
    """Estimates SERP pixel width for a text string using Arial 18px metric."""
    if not text:
        return 0
    return calculate_title_pixel_width(text)


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
        # 2. Bucket Titles & Pixel Truncations
        # -------------------------------------------------------------
        missing_titles: List[MetaBucketItem] = []
        too_short_titles: List[MetaBucketItem] = []
        optimal_titles: List[MetaBucketItem] = []
        too_long_titles: List[MetaBucketItem] = []
        duplicate_titles: List[MetaBucketItem] = []
        truncated_pixel_titles: List[MetaBucketItem] = []

        # H1-Title collisions (wasted keyword diversification)
        h1_title_collision_urls: List[str] = []

        for p in pages:
            t = (p.title or "").strip()
            t_len = len(t)
            px = calculate_title_pixel_width(t)
            item = MetaBucketItem(url=p.url, text=t or None, char_length=t_len, pixel_length=px)

            if t_len == 0:
                missing_titles.append(item)
            elif t_len < 30:
                too_short_titles.append(item)
            elif 50 <= t_len <= 60:
                optimal_titles.append(item)
            elif t_len > 60:
                too_long_titles.append(item)

            if px > GOOGLE_TITLE_MAX_PX:
                truncated_pixel_titles.append(item)

            # Check duplicate collision
            if t and len(title_url_map[t.lower()]) > 1:
                duplicate_titles.append(item)

            # Check H1 vs Title collision
            if t and p.h1:
                first_h1 = (p.h1[0] or "").strip().lower()
                if first_h1 == t.lower():
                    h1_title_collision_urls.append(p.url)

        # -------------------------------------------------------------
        # 3. Bucket Descriptions & Pixel Truncations
        # -------------------------------------------------------------
        missing_descriptions: List[MetaBucketItem] = []
        too_short_descriptions: List[MetaBucketItem] = []
        optimal_descriptions: List[MetaBucketItem] = []
        too_long_descriptions: List[MetaBucketItem] = []
        duplicate_descriptions: List[MetaBucketItem] = []
        truncated_pixel_descriptions: List[MetaBucketItem] = []

        for p in pages:
            d = (p.meta_description or "").strip()
            d_len = len(d)
            px = calculate_meta_pixel_width(d)
            item = MetaBucketItem(url=p.url, text=d or None, char_length=d_len, pixel_length=px)

            if d_len == 0:
                missing_descriptions.append(item)
            elif d_len < 70:
                too_short_descriptions.append(item)
            elif 150 <= d_len <= 160:
                optimal_descriptions.append(item)
            elif d_len > 160:
                too_long_descriptions.append(item)

            if px > GOOGLE_META_MAX_PX:
                truncated_pixel_descriptions.append(item)

            # Check duplicate collision
            if d and len(desc_url_map[d.lower()]) > 1:
                duplicate_descriptions.append(item)

        title_issues = (
            len(missing_titles)
            + len(too_short_titles)
            + len(too_long_titles)
            + len(duplicate_titles)
            + len(truncated_pixel_titles)
        )
        desc_issues = (
            len(missing_descriptions)
            + len(too_short_descriptions)
            + len(too_long_descriptions)
            + len(duplicate_descriptions)
            + len(truncated_pixel_descriptions)
        )

        title_summary = (
            f"Evaluated {total} pages: {len(optimal_titles)} optimal (50-60 chars), "
            f"{len(missing_titles)} missing, {len(too_short_titles)} short (<30), "
            f"{len(too_long_titles)} long (>60), {len(truncated_pixel_titles)} exceed Google 580px width, "
            f"{len(duplicate_titles)} duplicates across URLs."
        )

        desc_summary = (
            f"Evaluated {total} pages: {len(optimal_descriptions)} optimal (150-160 chars), "
            f"{len(missing_descriptions)} missing, {len(too_short_descriptions)} short (<70), "
            f"{len(too_long_descriptions)} long (>160), {len(truncated_pixel_descriptions)} exceed Google 960px width, "
            f"{len(duplicate_descriptions)} duplicates."
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
            truncated_pixel_titles=truncated_pixel_titles,
            truncated_pixel_descriptions=truncated_pixel_descriptions,
            h1_title_collision_count=len(h1_title_collision_urls),
            h1_title_collision_urls=h1_title_collision_urls,
            title_summary=title_summary,
            description_summary=desc_summary
        )


def analyze_meta_rollup(pages: List[PageEvidence]) -> MetaBucketRollup:
    return MetaRollupAnalyzer.analyze(pages)
