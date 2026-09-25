"""
Dristik AI Performance & Resource Analyzer
Measures TTFB, content encoding compression, page payload weight, and asset distribution.
"""
from typing import Dict, Any
from app.evidence.store import EvidenceStore

def analyze_performance_metrics(
    url: str,
    ttfb_ms: float,
    content_length_bytes: int,
    headers: Dict[str, str],
    evidence_store: EvidenceStore
) -> Dict[str, Any]:
    content_encoding = headers.get("content-encoding", "none")
    is_compressed = content_encoding.lower() in ["gzip", "br", "deflate", "zstd"]
    
    server = headers.get("server", "unspecified")
    size_kb = round(content_length_bytes / 1024, 2)
    
    evidence_store.add_evidence(
        source_type="performance",
        analyzer="performance_analyzer",
        url=url,
        text=f"TTFB: {ttfb_ms:.1f}ms, Payload Size: {size_kb} KB, Compression: {content_encoding}",
        value={
            "ttfb_ms": round(ttfb_ms, 1),
            "payload_size_kb": size_kb,
            "content_encoding": content_encoding,
            "is_compressed": is_compressed,
            "server": server
        }
    )
    
    return {
        "ttfb_ms": round(ttfb_ms, 1),
        "payload_size_kb": size_kb,
        "is_compressed": is_compressed,
        "content_encoding": content_encoding,
        "server": server
    }
