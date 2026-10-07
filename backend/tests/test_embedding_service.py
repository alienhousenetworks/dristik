import pytest
import os
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.crawl.embeddings import embedding_service, EmbeddingService
from app.crawl.vector_store import vector_store, VectorStore
from app.intelligence.competitive.semantic_gap import semantic_gap_engine


def test_max_crawl_pages_parsing():
    assert settings.get_max_crawl_pages(5) == 5
    assert settings.get_max_crawl_pages(10) == 10
    assert settings.get_max_crawl_pages(20) == 20
    assert settings.get_max_crawl_pages(50) == 50
    assert settings.get_max_crawl_pages("all") == 500
    assert settings.get_max_crawl_pages("deep") == 500
    assert settings.get_max_crawl_pages("full") == 500
    assert settings.get_max_crawl_pages("-1") == 500
    assert settings.get_max_crawl_pages("invalid") == 5


def test_e5_query_and_document_prefixes():
    service = EmbeddingService()
    with patch.object(service, "_load_local_model", return_value=None), \
         patch.object(service, "_embed_remote_sync", return_value=None):
        # Zero-fake standard: fail-closed returns [] when neural embedding models are offline
        vec_q = service.embed_query("best fintech billing platform")
        assert vec_q == []

        passages = [
            "Acme provides automated recurring billing APIs for enterprise banks.",
            "Pricing starts at $99 per month with unlimited webhook deliveries."
        ]
        vec_docs = service.embed_documents(passages)
        assert vec_docs == []


def test_vector_store_indexing_and_search(tmp_path):
    test_db = str(tmp_path / "test_vector.db")
    store = VectorStore(db_path=test_db)

    chunks = [
        "Acme Billing automates subscription invoicing and customer management.",
        "Acme Security uses zero-knowledge encryption and SOC2 Type II compliance.",
        "Unrelated text about gardening and outdoor plant watering."
    ]
    # Simple simulated unit vectors
    v1 = [1.0] + [0.0] * 1023
    v2 = [0.8, 0.6] + [0.0] * 1022
    v3 = [0.0, 0.0, 1.0] + [0.0] * 1021

    count = store.save_chunks(
        domain="acme.com",
        url="https://acme.com/product",
        page_type="product",
        chunks=chunks,
        vectors=[v1, v2, v3]
    )
    assert count == 3
    assert store.count_chunks("acme.com") == 3

    # Search for something close to v1
    query_vec = [1.0] + [0.0] * 1023
    results = store.search_similar(query_vec, domain="acme.com", top_k=2)
    assert len(results) == 2
    assert "invoicing" in results[0]["text"]
    assert results[0]["similarity"] == 1.0

    # Clear domain
    deleted = store.clear_domain("acme.com")
    assert deleted == 3
    assert store.count_chunks("acme.com") == 0


def test_semantic_gap_engine_evaluation(tmp_path):
    test_db = str(tmp_path / "test_gap.db")
    store = VectorStore(db_path=test_db)
    mock_vec = [1.0] + [0.0] * 1023
    
    with patch("app.intelligence.competitive.semantic_gap.vector_store", store), \
         patch("app.intelligence.competitive.semantic_gap.embedding_service.is_available", return_value=True), \
         patch("app.intelligence.competitive.semantic_gap.embedding_service.embed_query", return_value=mock_vec):
        # Empty evaluation
        res = semantic_gap_engine.evaluate_intent_coverage("testdomain.com", [])
        assert res["coverage_score"] is None

        # Query evaluation with mock matches
        mock_queries = [
            {"query": "How much does Acme cost?", "intent": "Pricing Discovery"},
            {"query": "What are Acme's security features?", "intent": "Compliance & Trust"}
        ]
        res = semantic_gap_engine.evaluate_intent_coverage("testdomain.com", mock_queries)
        assert res["total_queries_evaluated"] == 2
        assert len(res["evaluations"]) == 2
