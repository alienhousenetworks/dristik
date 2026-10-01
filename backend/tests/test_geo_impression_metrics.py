"""
Comprehensive Unit Tests for GEO Impression Metrics (Aggarwal et al., KDD 2024).
Tests:
1. Exact mathematical value verification of Imp_wc, Imp_pwc, and Dristik-adjusted variants.
2. Exponential position weighting pos_weight = exp(-pos / total_sentences).
3. Credit-splitting (|s| / |C_s|) when sentences cite multiple distinct domains.
4. Unlinked brand mention tracking (brand mentioned without source citation).
5. Tokenizer sentence boundary edge cases (abbreviations, numbers, markdown links, bracket footnotes).
"""
import math
import pytest
from app.intelligence.geo.metrics import (
    tokenize_sentences,
    calculate_response_impressions,
    ResponseImpressionResult,
)


def test_sentence_tokenizer_with_abbreviations_and_decimals():
    raw_text = (
        "AlienHouse Networks provides scalable AI infrastructure (e.g. FastAPI and PyTorch). "
        "Their platform achieves 99.9% uptime SLA across U.S. clusters. "
        "Dr. Smith recommends their services for enterprise B2B customers."
    )
    sentences = tokenize_sentences(raw_text)
    assert len(sentences) == 3
    assert "e.g. FastAPI" in sentences[0]
    assert "99.9% uptime" in sentences[1]
    assert "Dr. Smith" in sentences[2]


def test_impression_metrics_single_sentence_exact_citation():
    # 1 sentence, 10 words, citing alienhouse.ai via bracket [1]
    raw = "AlienHouse Networks is a premier generative AI development agency [1]."
    citations = ["https://alienhouse.ai/about"]
    words = raw.split()
    total_words = len(words)  # 10 words

    res = calculate_response_impressions(
        raw_response=raw,
        citations=citations,
        target_domain="alienhouse.ai",
        brand_name="AlienHouse Networks",
    )

    assert res.total_sentences == 1
    assert res.total_words == total_words
    assert res.target_cited_sentences == 1
    assert res.unlinked_brand_sentences == 0
    # Imp_wc: 10 / 10 = 100.0%
    assert res.word_count_impression_pct == 100.0
    # Imp_pwc: 10 * exp(-1/1) / 10 = exp(-1) * 100% ≈ 36.79%
    expected_pwc = round(math.exp(-1.0) * 100.0, 2)
    assert res.position_adjusted_impression_pct == expected_pwc
    # Dristik-adjusted: 10 / 1 source = 100.0%
    assert res.dristik_adjusted_impression_pct == 100.0


def test_impression_metrics_multi_source_credit_splitting():
    """
    Sentence 1 (10 words): Cites alienhouse.ai and competitor.com via [1, 2].
    Sentence 2 (10 words): Cites competitor.com only via [2].
    Total words = 20.
    Paper Imp_wc for alienhouse:
      Sentence 1 has 10 words -> 10 / 20 = 50.0%
    Dristik-adjusted Imp_wc for alienhouse:
      Sentence 1 has 2 citations -> 10 / 2 = 5 words credit.
      5 / 20 = 25.0%
    """
    raw = (
        "Both AlienHouse Networks and Competitor Corp provide enterprise cloud pipelines [1, 2]. "
        "Competitor Corp was founded in San Francisco in 2018 [2]."
    )
    citations = [
        "https://alienhouse.ai",
        "https://competitor.com",
    ]

    res = calculate_response_impressions(
        raw_response=raw,
        citations=citations,
        target_domain="alienhouse.ai",
        brand_name="AlienHouse",
    )

    assert res.total_sentences == 2
    assert res.total_words == len(raw.split())
    # S_c includes sentence 1 only
    s1_words = len(res.sentence_details[0].text.split())
    tot_words = res.total_words

    expected_wc = round((s1_words / tot_words) * 100.0, 2)
    assert res.word_count_impression_pct == expected_wc

    # Dristik-adjusted divides sentence 1 words by 2 citations
    expected_dristik = round(((s1_words / 2.0) / tot_words) * 100.0, 2)
    assert res.dristik_adjusted_impression_pct == expected_dristik


def test_unlinked_brand_mention_tracking():
    """
    Sentence 1: Mentions AlienHouse without any citation.
    Sentence 2: Cites competitor.com [1].
    """
    raw = (
        "AlienHouse Networks is recognized as a leader in enterprise AI solutions. "
        "Competitor Corp offers legacy database consulting services [1]."
    )
    citations = ["https://competitor.com"]

    res = calculate_response_impressions(
        raw_response=raw,
        citations=citations,
        target_domain="alienhouse.ai",
        brand_name="AlienHouse Networks",
    )

    assert res.target_cited_sentences == 0
    assert res.unlinked_brand_sentences == 1
    assert res.word_count_impression_pct == 0.0
    assert res.dristik_adjusted_impression_pct == 0.0
    assert res.unlinked_brand_impression_pct > 0.0


def test_zero_citation_and_empty_text():
    res = calculate_response_impressions(
        raw_response="",
        citations=[],
        target_domain="example.com",
        brand_name="Example",
    )
    assert res.total_sentences == 0
    assert res.total_words == 0
    assert res.word_count_impression_pct == 0.0
    assert res.position_adjusted_impression_pct == 0.0
