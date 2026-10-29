"""
Dristik AI GEO Backward-Compatibility Module.

NOTE: This module is retained for backward compatibility.
The canonical implementation has been renamed to `semantic_retrieval.py` to reflect
Dristik's controlled semantic retrieval methodology and avoid misleading claims
about simulating proprietary external AI engine retrieval architectures.
"""
from app.geo.semantic_retrieval import (
    SemanticRetrievalAnalyzer,
    ControlledRetrievalAnalyzer,
    RagRetrievalSimulator,
    RetrievalMethodology,
    RetrievalAnalysisConfig,
    AnalyzedChunk,
    SimulatedChunk,
    ControlledRetrievalReport,
    RagSimulationReport,
    semantic_retrieval_analyzer,
    controlled_retrieval_analyzer,
    rag_retrieval_simulator,
)

__all__ = [
    "SemanticRetrievalAnalyzer",
    "ControlledRetrievalAnalyzer",
    "RagRetrievalSimulator",
    "RetrievalMethodology",
    "RetrievalAnalysisConfig",
    "AnalyzedChunk",
    "SimulatedChunk",
    "ControlledRetrievalReport",
    "RagSimulationReport",
    "semantic_retrieval_analyzer",
    "controlled_retrieval_analyzer",
    "rag_retrieval_simulator",
]
