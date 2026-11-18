"""
Image & Media Intelligence — Phase 3.8

Audits visual and video media assets:
- Image accessibility (Informative vs. decorative images)
- Decorative image classification (Enforces empty alt="" rather than keyword stuffing)
- Modern image formats (WebP, AVIF vs. legacy PNG/JPG)
- Responsive attributes (srcset and sizes)
- Lazy loading best practices & LCP hero image anti-pattern detection
- Video indexing signals and VideoObject schema

STRICT GUARDRAIL:
Do not recommend adding descriptive alt text to decorative images;
decorative images must carry empty alt="" per W3C WCAG guidelines.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MediaAssetAudit(BaseModel):
    src: str
    asset_type: str  # "IMAGE" or "VIDEO"
    is_decorative: bool
    alt_text: Optional[str] = None
    has_empty_alt: bool = False
    has_srcset: bool = False
    format_type: str  # "WEBP", "AVIF", "PNG", "JPEG", "SVG", "MP4"
    is_lazy_loaded: bool = False
    is_lcp_candidate: bool = False
    defects: List[str] = Field(default_factory=list)
    recommendation: Optional[str] = None


class MediaIntelligenceReport(BaseModel):
    total_images_inspected: int
    total_videos_inspected: int
    missing_alt_informative_count: int
    decorative_images_count: int
    legacy_format_count: int  # JPEG/PNG where WebP/AVIF is preferred
    lcp_image_lazy_loaded: bool
    assets: List[MediaAssetAudit] = Field(default_factory=list)
    actionable_remediation: List[str] = Field(default_factory=list)


class MediaIntelligenceEngine:
    """
    Audits visual assets, enforces WCAG decorative image rules, and inspects Core Web Vitals image delivery.
    """

    DECORATIVE_INDICATORS = [
        "icon", "spacer", "divider", "bg-", "background", "bullet", "arrow", "decoration", "shadow", "shape"
    ]

    @classmethod
    def audit_media(
        cls,
        html: str,
        is_hero_image_present: bool = True,
    ) -> MediaIntelligenceReport:
        assets: List[MediaAssetAudit] = []
        recs: List[str] = []

        # 1. Inspect Images
        img_tags = re.findall(r"<img[^>]+>", html, re.IGNORECASE)
        missing_alt_inf = 0
        decorative_count = 0
        legacy_count = 0
        lcp_lazy = False

        for i, tag in enumerate(img_tags):
            src_m = re.search(r'src=["\']([^"\']+)["\']', tag, re.IGNORECASE)
            src = src_m.group(1) if src_m else f"inline-img-{i}"

            # Format detection
            low_src = src.lower()
            if ".webp" in low_src:
                fmt = "WEBP"
            elif ".avif" in low_src:
                fmt = "AVIF"
            elif ".svg" in low_src:
                fmt = "SVG"
            elif ".png" in low_src:
                fmt = "PNG"
            elif ".jpg" in low_src or ".jpeg" in low_src:
                fmt = "JPEG"
            else:
                fmt = "UNKNOWN"

            # Check decorative classification
            is_decor = any(ind in low_src for ind in cls.DECORATIVE_INDICATORS)
            if 'role="presentation"' in tag.lower() or 'aria-hidden="true"' in tag.lower():
                is_decor = True

            # Alt inspection
            has_alt = 'alt=' in tag.lower()
            alt_m = re.search(r'alt=["\'](.*?)["\']', tag, re.IGNORECASE)
            alt_val = alt_m.group(1) if alt_m else None
            is_empty_alt = alt_val == ""

            has_srcset = 'srcset=' in tag.lower()
            is_lazy = 'loading="lazy"' in tag.lower() or "loading='lazy'" in tag.lower()

            # First large non-decorative image is LCP candidate
            is_lcp = (i == 0 and not is_decor and is_hero_image_present)

            defects: List[str] = []
            rec = None

            # WCAG Decorative vs Informative Guardrail
            if is_decor:
                decorative_count += 1
                if not has_alt or not is_empty_alt:
                    defects.append("Decorative asset should carry empty alt='' to prevent screen-reader noise.")
                    rec = "Set alt='' (empty string) for this decorative asset per WCAG standards."
            else:
                if not has_alt or (alt_val is not None and not alt_val.strip()):
                    missing_alt_inf += 1
                    defects.append("Informative content image missing descriptive alt attribute.")
                    rec = "Add descriptive alternative text explaining image content for users and search crawlers."

            # Legacy format check
            if fmt in ("JPEG", "PNG") and not is_decor:
                legacy_count += 1
                defects.append(f"Image delivered in legacy format ({fmt}); WebP or AVIF offers ~35–50% byte savings.")
                if not rec:
                    rec = "Convert to next-gen WebP or AVIF format."

            # Responsive image check
            if not has_srcset and not is_decor and fmt != "SVG":
                defects.append("Image lacks responsive srcset/sizes attributes.")

            # LCP lazy loading anti-pattern
            if is_lcp and is_lazy:
                lcp_lazy = True
                defects.append("CRITICAL: LCP hero image is lazy-loaded, which delays Largest Contentful Paint.")
                rec = "Remove loading='lazy' and add fetchpriority='high' to this hero image."

            assets.append(
                MediaAssetAudit(
                    src=src,
                    asset_type="IMAGE",
                    is_decorative=is_decor,
                    alt_text=alt_val,
                    has_empty_alt=is_empty_alt,
                    has_srcset=has_srcset,
                    format_type=fmt,
                    is_lazy_loaded=is_lazy,
                    is_lcp_candidate=is_lcp,
                    defects=defects,
                    recommendation=rec,
                )
            )

        # 2. Inspect Video Elements
        video_tags = re.findall(r"<video[^>]+>.*?</video>", html, re.IGNORECASE | re.DOTALL)
        video_count = len(video_tags)
        has_video_schema = "VideoObject" in html
        if video_count > 0 and not has_video_schema:
            recs.append("Add Schema.org VideoObject markup to embedded videos to enable video search rich snippets.")

        if missing_alt_inf > 0:
            recs.append(f"Provide descriptive alt text for {missing_alt_inf} informative image(s).")
        if lcp_lazy:
            recs.append("Remove lazy loading on the hero LCP image candidate.")
        if legacy_count > 0:
            recs.append(f"Convert {legacy_count} legacy JPEG/PNG images to modern WebP/AVIF format.")

        return MediaIntelligenceReport(
            total_images_inspected=len(img_tags),
            total_videos_inspected=video_count,
            missing_alt_informative_count=missing_alt_inf,
            decorative_images_count=decorative_count,
            legacy_format_count=legacy_count,
            lcp_image_lazy_loaded=lcp_lazy,
            assets=assets,
            actionable_remediation=recs,
        )
