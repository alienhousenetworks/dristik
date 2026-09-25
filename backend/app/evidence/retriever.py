"""
Dristik AI Deterministic Evidence Retriever (Deterministic RAG)
Filters, scores, and bounds evidence slices for specialist cognitive agents.
"""
from typing import List, Dict, Any, Optional
from app.evidence.models import Evidence
from app.evidence.store import EvidenceStore

AGENT_EVIDENCE_MAP = {
    "business_intelligence": ["meta", "dom", "content", "schema"],
    "geo_analysis": ["dom", "schema", "meta", "content"],
    "ai_search_simulation": ["dom", "content", "meta", "schema"],
    "technical_seo": ["meta", "dom", "robots", "sitemap", "link_graph", "security"],
    "content_intelligence": ["content", "dom", "meta"],
    "ux_conversion": ["dom", "content", "security"],
    "trust_authority": ["security", "meta", "schema", "content"],
    "critic": ["html", "dom", "meta", "schema", "robots", "sitemap", "link_graph", "performance", "security", "content"],
    "synthesizer": ["meta", "dom", "schema", "content"]
}

class EvidenceRetriever:
    def __init__(self, store: EvidenceStore):
        self.store = store

    def retrieve_for_agent(self, capability: str, limit: int = 40) -> List[Evidence]:
        """
        Retrieves top relevant evidence for an agent capability based on source filtering.
        """
        target_types = AGENT_EVIDENCE_MAP.get(capability, ["meta", "dom", "content", "schema"])
        all_ev = self.store.get_all()
        external = [ev for ev in all_ev if ev.source_type == "external" or (ev.id or "").startswith("ext_")]
        
        filtered = [ev for ev in all_ev if ev.source_type in target_types]
        if len(filtered) < limit:
            remaining = [ev for ev in all_ev if ev not in filtered and ev not in external]
            filtered.extend(remaining[:limit - len(filtered)])
        ordered = list(external) + [ev for ev in filtered if ev not in external]
        return ordered[:limit]

    def format_evidence_block(self, evidence_list: List[Evidence]) -> str:
        """
        Formats evidence items into a concise string block with explicit IDs for SLMs.
        """
        lines = []
        for ev in evidence_list:
            text_snippet = (ev.text or "").strip()
            if len(text_snippet) > 200:
                text_snippet = text_snippet[:197] + "..."
            
            val_snippet = ""
            if ev.value is not None:
                val_str = str(ev.value)
                if len(val_str) > 150:
                    val_str = val_str[:147] + "..."
                val_snippet = f" | Value: {val_str}"
            
            sel_str = f" | Selector: {ev.selector}" if ev.selector else ""
            lines.append(f"[{ev.id}] Source: {ev.source_type}{sel_str} | Text: \"{text_snippet}\"{val_snippet}")
        
        return "\n".join(lines)
