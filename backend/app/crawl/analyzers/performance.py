"""
Dristik AI Performance & Resource Analyzer
Measures true TTFB, content encoding compression, page payload weight,
render-blocking resources, third-party script tax, font loading, and Core Web Vitals indicators.
"""
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore
from app.domain.models import LabPerformanceMetrics


def analyze_performance_metrics(
    url: str,
    ttfb_ms: float,
    content_length_bytes: int,
    headers: Dict[str, str],
    evidence_store: EvidenceStore,
    soup: Optional[BeautifulSoup] = None,
    timing_data: Optional[Dict[str, Any]] = None,
    dom_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # 1. Content Encoding & Server Info
    headers_lower = {k.lower(): v for k, v in headers.items()}
    content_encoding = headers_lower.get("content-encoding", "none")
    is_compressed = content_encoding.lower() in ["gzip", "br", "deflate", "zstd"]
    server = headers_lower.get("server", "unspecified")
    size_kb = round(content_length_bytes / 1024, 2)

    # 2. Timing Metrics
    timing = timing_data or {}
    effective_ttfb = round(float(timing.get("ttfb_ms") or ttfb_ms), 1)
    fcp_ms = timing.get("fcp_ms")
    if fcp_ms is not None:
        fcp_ms = round(float(fcp_ms), 1)

    dns_ms = round(float(timing.get("dns_ms") or 0.0), 1)
    tcp_ms = round(float(timing.get("tcp_ms") or 0.0), 1)
    tls_ms = round(float(timing.get("tls_ms") or 0.0), 1)
    download_ms = round(float(timing.get("download_ms") or 0.0), 1)
    dom_content_loaded_ms = round(float(timing.get("dom_content_loaded_ms") or 0.0), 1)
    load_event_ms = round(float(timing.get("load_event_ms") or 0.0), 1)

    # 3. Payload & Resource Breakdown
    total_transferred_kb = round(float(timing.get("total_transferred_bytes", content_length_bytes)) / 1024, 1)
    js_payload_kb = round(float(timing.get("js_bytes", 0)) / 1024, 1)
    css_payload_kb = round(float(timing.get("css_bytes", 0)) / 1024, 1)
    image_payload_kb = round(float(timing.get("img_bytes", 0)) / 1024, 1)
    font_payload_kb = round(float(timing.get("font_bytes", 0)) / 1024, 1)

    request_counts = timing.get("request_counts") or {}
    total_requests = timing.get("total_requests") or (1 if content_length_bytes > 0 else 0)

    # 4. Render-Blocking Resources Extraction
    render_blocking: List[Dict[str, Any]] = list(timing.get("render_blocking") or [])
    page_host = urlparse(url).netloc.lower()

    if soup and not render_blocking:
        head = soup.find("head")
        if head:
            # Render-blocking scripts: in head, with src, without async/defer/type=module
            for s in head.find_all("script", src=True):
                attrs = {k.lower(): v for k, v in s.attrs.items()}
                is_async = "async" in attrs
                is_defer = "defer" in attrs
                is_module = attrs.get("type", "").lower() == "module"
                if not (is_async or is_defer or is_module):
                    src = s.get("src", "")
                    render_blocking.append({
                        "url": src[:200],
                        "initiator": "script",
                        "duration_ms": 0
                    })
            # Render-blocking stylesheets in head
            for link in head.find_all("link", rel=lambda r: r and "stylesheet" in (r if isinstance(r, list) else [r])):
                href = link.get("href", "")
                media = link.get("media", "").lower()
                # print media is non-blocking for screen
                if media not in ["print"]:
                    render_blocking.append({
                        "url": href[:200],
                        "initiator": "stylesheet",
                        "duration_ms": 0
                    })

    render_blocking_count = len(render_blocking)

    # 5. Third-Party Scripts & Tracker Tax
    third_party_scripts: List[Dict[str, Any]] = list(timing.get("third_party_scripts") or [])
    third_party_domains_set = set()

    for item in third_party_scripts:
        h = item.get("hostname")
        if h:
            third_party_domains_set.add(h)

    if soup and not third_party_scripts:
        for s in soup.find_all("script", src=True):
            src = s.get("src", "").strip()
            if src.startswith("//"):
                src = "https:" + src
            parsed = urlparse(src)
            src_host = parsed.netloc.lower()
            if src_host and src_host != page_host and not src_host.endswith("." + page_host):
                third_party_domains_set.add(src_host)
                third_party_scripts.append({
                    "url": src[:200],
                    "hostname": src_host,
                    "transfer_bytes": 0
                })

    third_party_scripts_count = len(third_party_scripts)
    third_party_scripts_kb = round(sum(item.get("transfer_bytes", 0) for item in third_party_scripts) / 1024, 1)
    third_party_domains = sorted(list(third_party_domains_set))[:15]

    # 6. Caching Policies
    cache_control = headers_lower.get("cache-control")
    caching_policy = "UNSPECIFIED"
    if cache_control:
        cc_low = cache_control.lower()
        if "no-store" in cc_low:
            caching_policy = "NO_STORE"
        elif "no-cache" in cc_low or "max-age=0" in cc_low:
            caching_policy = "NO_CACHE"
        elif "max-age" in cc_low:
            # Check duration
            try:
                import re
                m = re.search(r"max-age=(\d+)", cc_low)
                if m:
                    sec = int(m.group(1))
                    caching_policy = "LONG_CACHE" if sec >= 86400 else "SHORT_CACHE"
                else:
                    caching_policy = "CACHED"
            except Exception:
                caching_policy = "CACHED"

    # 7. Font Loading & CLS Layout Shift Indicators
    font_display_strategy = None
    if soup:
        font_preloads = soup.find_all("link", rel=lambda r: r and "preload" in (r if isinstance(r, list) else [r]), attrs={"as": "font"})
        if font_preloads:
            font_display_strategy = "PRELOADED_FONTS"

    # Images missing dimensions (direct CLS risk)
    image_assets = (dom_data or {}).get("image_assets", [])
    images_missing_dims = sum(1 for img in image_assets if not img.get("has_dimensions"))
    cls_risk_score = min(round(images_missing_dims * 0.05, 2), 0.5)

    lab_perf = LabPerformanceMetrics(
        ttfb_ms=effective_ttfb,
        fcp_ms=fcp_ms,
        lcp_indicator_ms=round(effective_ttfb + fcp_ms + 400, 1) if (effective_ttfb > 0 and fcp_ms is not None) else None,
        cls_risk_score=cls_risk_score,
        tbt_proxy_ms=round(js_payload_kb * 0.5, 1) if js_payload_kb > 200 else 0.0,
        dns_ms=dns_ms,
        tcp_ms=tcp_ms,
        tls_ms=tls_ms,
        download_ms=download_ms,
        dom_content_loaded_ms=dom_content_loaded_ms,
        load_event_ms=load_event_ms,
        total_transferred_kb=total_transferred_kb,
        js_payload_kb=js_payload_kb,
        css_payload_kb=css_payload_kb,
        image_payload_kb=image_payload_kb,
        font_payload_kb=font_payload_kb,
        total_requests=total_requests,
        request_count_by_type=request_counts,
        render_blocking_count=render_blocking_count,
        render_blocking_resources=render_blocking[:10],
        third_party_scripts_count=third_party_scripts_count,
        third_party_scripts_kb=third_party_scripts_kb,
        third_party_domains=third_party_domains,
        caching_policy=caching_policy,
        cache_control=cache_control,
        content_encoding=content_encoding,
        server=server,
        font_display_strategy=font_display_strategy,
        images_missing_dimensions=images_missing_dims,
    )

    evidence_store.add_evidence(
        source_type="performance",
        analyzer="performance_analyzer",
        url=url,
        text=f"Server TTFB: {effective_ttfb:.1f}ms, Transferred: {total_transferred_kb} KB, Render-blocking assets: {render_blocking_count}, Compression: {content_encoding}",
        value={
            "ttfb_ms": effective_ttfb,
            "payload_size_kb": total_transferred_kb,
            "fcp_ms": fcp_ms,
            "render_blocking_count": render_blocking_count,
            "third_party_scripts_count": third_party_scripts_count,
            "content_encoding": content_encoding,
            "is_compressed": is_compressed,
            "server": server,
            "caching_policy": caching_policy,
        }
    )

    return {
        "ttfb_ms": effective_ttfb,
        "payload_size_kb": total_transferred_kb,
        "is_compressed": is_compressed,
        "content_encoding": content_encoding,
        "server": server,
        "lab_performance": lab_perf,
    }

