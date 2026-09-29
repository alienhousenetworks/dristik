"""
Dristik AI Media Payload & Mixed Content Analyzer
Parses all <img> elements and page subresources to evaluate:
- Missing alt text or empty alt="" attributes
- Missing explicit width and height dimensions (causing Cumulative Layout Shift / CLS)
- Next-gen image format adoption (WebP, AVIF, SVG vs PNG, JPEG, GIF)
- Mixed content: scans HTTPS pages for subresources loaded over insecure http://
"""
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from app.domain.models import PageEvidence, MediaAssetItem, MediaAssetAuditReport

_MODERN_FORMATS = {"webp", "avif", "svg"}
_LEGACY_FORMATS = {"png", "jpeg", "jpg", "gif", "bmp", "tiff"}


class MediaAssetAnalyzer:
    @staticmethod
    def analyze_media(pages: List[PageEvidence], raw_html_map: Optional[Dict[str, str]] = None) -> MediaAssetAuditReport:
        raw_html_map = raw_html_map or {}
        flagged_images: List[MediaAssetItem] = []
        cls_risks: List[Dict[str, str]] = []
        mixed_content_urls: List[str] = []

        total_images = 0
        missing_alt_count = 0
        empty_alt_count = 0
        missing_dim_count = 0
        modern_count = 0
        non_modern_count = 0

        for p in pages:
            is_page_https = (p.url or "").startswith("https://")
            html = raw_html_map.get(p.url) or getattr(p, "raw_html", None)
            if not html and getattr(p, "snapshot_path", None):
                try:
                    from pathlib import Path
                    sp = Path(p.snapshot_path)
                    if sp.exists():
                        html = sp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

            if html:
                soup = BeautifulSoup(html, "html.parser")
                imgs = soup.find_all("img")
                total_images += len(imgs)

                # Check mixed content across all subresources on HTTPS pages (img, script, link, iframe)
                if is_page_https:
                    for tag in soup.find_all(["img", "script", "link", "iframe", "video", "audio"]):
                        src = tag.get("src") or tag.get("href")
                        if src and src.strip().lower().startswith("http://"):
                            mixed_content_urls.append(src)

                for img in imgs:
                    src = (img.get("src") or img.get("data-src") or "").strip()
                    alt = img.get("alt")
                    has_alt = alt is not None
                    is_empty_alt = (alt == "" or (alt is not None and not alt.strip()))
                    is_decorative = (
                        is_empty_alt
                        or (img.get("role") or "").lower() in ("presentation", "none")
                        or img.get("aria-hidden") == "true"
                    )

                    has_w = bool(img.get("width") or (img.get("style") and "width" in img.get("style")))
                    has_h = bool(img.get("height") or (img.get("style") and "height" in img.get("style")))
                    has_dimensions = has_w and has_h

                    # Determine image format extension
                    parsed_path = urlparse(src).path.lower()
                    ext = parsed_path.split(".")[-1] if "." in parsed_path else "other"
                    is_modern = ext in _MODERN_FORMATS
                    is_legacy = ext in _LEGACY_FORMATS

                    if is_modern:
                        modern_count += 1
                    elif is_legacy:
                        non_modern_count += 1

                    # WCAG 2.2: Only flag as missing alt if it has no alt attribute and is not declared decorative
                    if not has_alt and not is_decorative:
                        missing_alt_count += 1
                    elif is_decorative:
                        empty_alt_count += 1

                    if not has_dimensions:
                        missing_dim_count += 1
                        if len(cls_risks) < 10:
                            cls_risks.append({
                                "page_url": p.url,
                                "img_src": src[:120],
                                "reason": "Missing explicit width/height causing layout shift (CLS hazard)"
                            })

                    is_insecure = is_page_https and src.startswith("http://")

                    # An image is flagged only if it has a genuine defect:
                    # missing alt (non-decorative), missing dimensions (CLS), legacy format (optimization), or insecure HTTP
                    has_defect = (not has_alt and not is_decorative) or (not has_dimensions) or (not is_modern and is_legacy) or is_insecure

                    if has_defect:
                        flagged_images.append(MediaAssetItem(
                            url=src,
                            page_url=p.url,
                            alt_text=alt,
                            has_alt=has_alt,
                            is_empty_alt=is_empty_alt,
                            has_dimensions=has_dimensions,
                            format=ext,
                            is_modern_format=is_modern,
                            is_insecure_http=is_insecure
                        ))
            else:
                # Derive from page evidence metrics if raw html not present
                page_img_count = p.total_images or 0
                page_missing_alt = p.images_without_alt or 0
                total_images += page_img_count
                missing_alt_count += page_missing_alt

        summary = (
            f"Evaluated {total_images} total image assets across {len(pages)} pages: "
            f"{missing_alt_count} informative images missing alt text (WCAG 2.2 non-compliant), "
            f"{empty_alt_count} decorative images with alt=\"\" or role=\"presentation\" (WCAG compliant), "
            f"{missing_dim_count} missing dimensions (CLS risk), "
            f"{non_modern_count} legacy formats (PNG/JPEG) vs {modern_count} modern (WebP/AVIF), "
            f"{len(mixed_content_urls)} mixed content HTTP subresources detected."
        )

        return MediaAssetAuditReport(
            total_images_analyzed=total_images,
            missing_alt_count=missing_alt_count,
            empty_alt_count=empty_alt_count,
            decorative_alt_compliant_count=empty_alt_count,
            missing_dimensions_count=missing_dim_count,
            modern_format_count=modern_count,
            non_modern_format_count=non_modern_count,
            mixed_content_count=len(mixed_content_urls),
            mixed_content_urls=mixed_content_urls,
            cls_risk_images=cls_risks,
            summary=summary
        )


def analyze_media_assets(pages: List[PageEvidence], raw_html_map: Optional[Dict[str, str]] = None) -> MediaAssetAuditReport:
    return MediaAssetAnalyzer.analyze_media(pages, raw_html_map)
