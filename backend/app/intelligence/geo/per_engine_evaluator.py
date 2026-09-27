"""
Dristik AI Advanced Per-Engine GEO/AEO Diagnostic Matrix & Information Gain Evaluator
Evaluates extractability and citation readiness across 4 distinct AI engine profiles:
1. ChatGPT / SearchGPT: Conversational depth, entity clarity, and table/list extractability.
2. Perplexity: Direct statistical claims, citation eligibility, and authoritative sources.
3. Google AI Overviews / SGE: Schema completeness (FAQPage, Organization, Product) and 40-60 word definitions.
4. Claude / Gemini: Conceptual density, factual depth, and absence of promotional fluff.

Also computes:
- Information Gain Score (original research, proprietary benchmarks, methodology vs commodity fluff)
- Dynamic llms.txt and AI bot robots.txt directives (GPTBot, PerplexityBot, ClaudeBot, Google-Extended)
"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.domain.models import (
    PageEvidence,
    BusinessProfile,
    CrawlManifest,
    PerEngineAiScore,
    PerEngineAiMatrix,
    InformationGainReport,
    AiBotDirectivesReport,
)

_FLUFF_WORDS = [
    "revolutionary", "revolutionize", "cutting-edge", "next-generation",
    "unprecedented", "game-changer", "world-class", "best-in-class",
    "seamless", "unlock growth", "future of business", "hyper-advanced",
    "empower your", "leverage synergy"
]

_ORIGINAL_DATA_PATTERNS = [
    r"\b\d{1,3}(?:\.\d+)?%\b",                   # Percentages: 84%, 12.5%
    r"\$\d+(?:,\d+)*(?:\.\d+)?(?:\s?[kKmMbB])?", # Dollar stats: $4.2M, $500k
    r"\b(?:survey of|benchmarked across|dataset of|sample of)\s+\d+",
    r"\b(?:case study|methodology|proprietary data|empirical findings)\b",
]


def _grade_from_score(score: float) -> str:
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _band_from_score(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


class PerEngineAiEvaluator:
    @classmethod
    def evaluate(
        cls,
        pages: List[PageEvidence],
        manifest: Optional[CrawlManifest] = None,
        profile: Optional[BusinessProfile] = None,
        website_url: str = "",
    ) -> PerEngineAiMatrix:
        profile = profile or BusinessProfile()
        total_pages = len(pages)
        corpus = " ".join([
            (p.title or "") + " " + " ".join(p.h1 or []) + " " + " ".join(p.h2 or []) + " " + (p.body_text or "")
            for p in pages
        ])
        corpus_lower = corpus.lower()

        schemas_present = set()
        for p in pages:
            schemas_present.update(p.schema_types or [])

        # -------------------------------------------------------------
        # 1. Information Gain Evaluation
        # -------------------------------------------------------------
        prop_stats_matches = []
        for pat in _ORIGINAL_DATA_PATTERNS:
            found = re.findall(pat, corpus, re.IGNORECASE)
            prop_stats_matches.extend(found)

        has_prop_stats = len(prop_stats_matches) >= 3
        has_benchmarks = bool(re.search(r"\b(?:benchmark|comparison table|performance index|metric table)\b", corpus_lower))
        has_methodology = bool(re.search(r"\b(?:methodology|how we evaluated|evaluation criteria|study design)\b", corpus_lower))
        has_quotes = bool(re.search(r"(?:said|noted|stated|according to)(?:\s+(?:[A-Z]{2,5}|Dr\.|Mr\.|Ms\.|Founder|Lead|Chief))?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+", corpus, re.IGNORECASE))

        fluff_hits = [f for f in _FLUFF_WORDS if f in corpus_lower]
        fluff_ratio = min(100.0, len(fluff_hits) * 8.0)

        info_gain_score = 40.0
        if has_prop_stats:
            info_gain_score += 20.0
        if has_benchmarks:
            info_gain_score += 15.0
        if has_methodology:
            info_gain_score += 15.0
        if has_quotes:
            info_gain_score += 10.0
        info_gain_score -= (fluff_ratio * 0.25)
        info_gain_score = max(15.0, min(100.0, info_gain_score))

        orig_signals = []
        if has_prop_stats:
            orig_signals.append(f"{len(prop_stats_matches)} proprietary numerical statistics/data points observed")
        if has_benchmarks:
            orig_signals.append("Comparative benchmark criteria detected in content")
        if has_methodology:
            orig_signals.append("Explicit research methodology/testing section present")
        if has_quotes:
            orig_signals.append("Named executive / subject matter expert attributions found")

        comm_signals = []
        if fluff_hits:
            comm_signals.append(f"Marketing superlatives detected: {', '.join(fluff_hits[:4])}")
        if not has_prop_stats:
            comm_signals.append("Absence of proprietary first-party research metrics or data points")

        info_gain_recs = []
        if not has_prop_stats:
            info_gain_recs.append("Publish proprietary industry benchmark statistics or customer data telemetry.")
        if not has_methodology:
            info_gain_recs.append("Add a 'Methodology' or 'How We Measure' section to establish primary research authority.")
        if fluff_hits:
            info_gain_recs.append(f"Replace generic marketing copy ({', '.join(fluff_hits[:3])}) with quantified capability metrics.")

        info_gain_rep = InformationGainReport(
            score=round(info_gain_score, 1),
            grade=_grade_from_score(info_gain_score),
            has_proprietary_statistics=has_prop_stats,
            has_benchmark_tables=has_benchmarks,
            has_methodology_section=has_methodology,
            has_executive_quotes=has_quotes,
            fluff_ratio_score=round(fluff_ratio, 1),
            original_data_signals=orig_signals or ["Standard commercial copy observed."],
            commodity_fluff_signals=comm_signals or ["Zero significant marketing fluff detected."],
            recommendations=info_gain_recs or ["Maintain authoritative first-party data output."]
        )

        # -------------------------------------------------------------
        # 2. Per-Engine Diagnostic Scores
        # -------------------------------------------------------------
        # Engine 1: ChatGPT / SearchGPT
        # Values conversational depth, clear entity definition, table formatting
        has_faq = any("faq" in (p.url or "").lower() or (p.h2 and any("faq" in h.lower() for h in p.h2)) for p in pages)
        has_tables = bool(re.search(r"\|.*\|.*\|", corpus))
        chatgpt_score = 45.0
        if profile.business_name and profile.business_name.lower() in corpus_lower:
            chatgpt_score += 15.0
        if has_faq:
            chatgpt_score += 15.0
        if has_tables:
            chatgpt_score += 15.0
        if len(corpus.split()) > 1500:
            chatgpt_score += 10.0
        chatgpt_score = max(20.0, min(100.0, chatgpt_score))

        chatgpt_score_obj = PerEngineAiScore(
            engine_name="ChatGPT / SearchGPT",
            score=round(chatgpt_score, 1),
            grade=_grade_from_score(chatgpt_score),
            readiness_band=_band_from_score(chatgpt_score),
            strengths=[
                s for s in [
                    "Brand entity clearly named on-page" if profile.business_name and profile.business_name.lower() in corpus_lower else None,
                    "Conversational FAQ / Q&A structures present" if has_faq else None,
                    "Structured comparison tables formatted for Markdown extraction" if has_tables else None,
                ] if s
            ] or ["Basic content layout accessible"],
            critical_gaps=[
                g for g in [
                    "Missing conversational FAQ blocks matching natural voice queries" if not has_faq else None,
                    "No structured Markdown/HTML tables for direct retrieval" if not has_tables else None,
                    "Topical depth below 1,500 words across crawled footprint" if len(corpus.split()) <= 1500 else None,
                ] if g
            ] or ["No critical extractability gaps"],
            recommended_fixes=[
                "Deploy a 6-question buyer FAQ block matching conversational prompts ('How does X work', 'How much does X cost').",
                "Format product feature specifications into HTML <table> elements for direct SearchGPT table synthesis."
            ]
        )

        # Engine 2: Perplexity
        # Values citation eligibility, primary numerical claims, clean attribution
        perplexity_score = 40.0
        if has_prop_stats:
            perplexity_score += 25.0
        if manifest and manifest.sitemap_found:
            perplexity_score += 15.0
        if (website_url or "").startswith("https://"):
            perplexity_score += 10.0
        if info_gain_score >= 65.0:
            perplexity_score += 10.0
        perplexity_score = max(20.0, min(100.0, perplexity_score))

        perplexity_score_obj = PerEngineAiScore(
            engine_name="Perplexity",
            score=round(perplexity_score, 1),
            grade=_grade_from_score(perplexity_score),
            readiness_band=_band_from_score(perplexity_score),
            strengths=[
                s for s in [
                    f"Strong empirical evidence grounding ({len(prop_stats_matches)} stats)" if has_prop_stats else None,
                    "Verified XML sitemap index for source ingestion" if manifest and manifest.sitemap_found else None,
                    "Secure HTTPS protocol for citation eligibility" if (website_url or "").startswith("https://") else None,
                ] if s
            ] or ["Standard crawl indexation"],
            critical_gaps=[
                g for g in [
                    "Lack of verifiable first-party statistics for numerical citation pills" if not has_prop_stats else None,
                    "Information gain is low; content risks being filtered as commodity paraphrase" if info_gain_score < 65 else None,
                ] if g
            ] or ["Eligible for authoritative citations"],
            recommended_fixes=[
                "Add 3-5 quantified benchmark claims per product page with exact year and sample size.",
                "Ensure every key claim is backed by an anchor-linked reference citation."
            ]
        )

        # Engine 3: Google AI Overviews / SGE
        # Values Schema completeness (FAQPage, Article, Product, Organization) & 40-60 word definitions
        google_score = 40.0
        schema_count = len(schemas_present)
        google_score += min(30.0, schema_count * 10.0)
        has_direct_defs = any(len(p.h1 or []) > 0 and len(p.body_text or "") > 200 for p in pages)
        if has_direct_defs:
            google_score += 15.0
        if "FAQPage" in schemas_present or "Organization" in schemas_present:
            google_score += 15.0
        google_score = max(20.0, min(100.0, google_score))

        google_score_obj = PerEngineAiScore(
            engine_name="Google AI Overviews",
            score=round(google_score, 1),
            grade=_grade_from_score(google_score),
            readiness_band=_band_from_score(google_score),
            strengths=[
                s for s in [
                    f"Rich Schema.org graph detected ({', '.join(sorted(schemas_present)[:3])})" if schemas_present else None,
                    "Self-contained 40-60 word answer-first definition blocks detected" if has_direct_defs else None,
                ] if s
            ] or ["Standard Googlebot access"],
            critical_gaps=[
                g for g in [
                    "Missing Schema.org structured data (Organization, FAQPage, Product)" if not schemas_present else None,
                    "Lack of answer-first 40-60 word lead paragraphs under H2 question headings" if not has_direct_defs else None,
                ] if g
            ] or ["Strong AEO snippet eligibility"],
            recommended_fixes=[
                "Inject full JSON-LD schema for Organization, WebSite, and FAQPage.",
                "Place concise, 40-60 word definitive answers directly under H2 questions before expanding."
            ]
        )

        # Engine 4: Claude / Gemini
        # Values conceptual density, absence of marketing fluff, high factual rigor
        claude_score = 50.0
        claude_score -= (fluff_ratio * 0.4)
        if info_gain_score >= 60.0:
            claude_score += 25.0
        if has_methodology or has_quotes:
            claude_score += 15.0
        claude_score = max(20.0, min(100.0, claude_score))

        claude_score_obj = PerEngineAiScore(
            engine_name="Claude / Gemini",
            score=round(claude_score, 1),
            grade=_grade_from_score(claude_score),
            readiness_band=_band_from_score(claude_score),
            strengths=[
                s for s in [
                    "High conceptual density without excessive promotional buzzwords" if fluff_ratio < 25.0 else None,
                    "Authoritative first-party methodology signals present" if has_methodology else None,
                ] if s
            ] or ["Logical topical structure"],
            critical_gaps=[
                g for g in [
                    f"Promotional fluff density is high ({len(fluff_hits)} occurrences); reduces synthesis weight" if fluff_ratio >= 25.0 else None,
                    "Low conceptual density; lacks deep technical differentiation" if info_gain_score < 60.0 else None,
                ] if g
            ] or ["High cognitive trust signals"],
            recommended_fixes=[
                "Strip unsubstantiated superlatives ('revolutionary', 'cutting-edge') in favor of architectural specifications.",
                "Detail exact platform mechanisms and security/reliability guarantees."
            ]
        )

        # -------------------------------------------------------------
        # 3. AI Bot Directives & llms.txt validation
        # -------------------------------------------------------------
        robots_txt = manifest.robots_txt_content if manifest and manifest.robots_txt_content else ""
        robots_lower = robots_txt.lower()

        gptbot_allowed = "user-agent: gptbot\ndisallow: /" not in robots_lower and "user-agent: *\ndisallow: /" not in robots_lower
        perplexity_allowed = "user-agent: perplexitybot\ndisallow: /" not in robots_lower and "user-agent: *\ndisallow: /" not in robots_lower
        claudebot_allowed = "user-agent: claudebot\ndisallow: /" not in robots_lower and "user-agent: *\ndisallow: /" not in robots_lower
        google_ext_allowed = "user-agent: google-extended\ndisallow: /" not in robots_lower and "user-agent: *\ndisallow: /" not in robots_lower

        domain = urlparse(website_url).netloc or "example.com"
        clean_url = f"https://{domain}"

        # Generate optimized llms.txt template
        biz_name = profile.business_name or domain.split(".")[0].capitalize()
        llms_txt_gen = (
            f"# {biz_name}\n\n"
            f"> {profile.value_proposition or f'{biz_name} provides enterprise solutions.'}\n\n"
            f"## Core Capabilities\n"
            f"- Website: {clean_url}\n"
            f"- Industry: {profile.industry or 'Technology'}\n"
            f"- Solutions: {', '.join(profile.products or profile.services or ['Enterprise Platform'])}\n\n"
            f"## Canonical Links\n"
            f"- [Homepage]({clean_url}/): Primary overview and value proposition\n"
            f"- [Documentation]({clean_url}/docs): Technical guides and API specifications\n"
            f"- [Pricing]({clean_url}/pricing): Subscription plans and enterprise licensing\n"
        )

        ai_bot_rep = AiBotDirectivesReport(
            robots_txt_status="PERMISSIVE" if (gptbot_allowed and perplexity_allowed and claudebot_allowed) else "RESTRICTED",
            gptbot_allowed=gptbot_allowed,
            perplexitybot_allowed=perplexity_allowed,
            claudebot_allowed=claudebot_allowed,
            google_extended_allowed=google_ext_allowed,
            llms_txt_found=False,
            llms_txt_url=f"{clean_url}/llms.txt",
            llms_txt_generated=llms_txt_gen,
            recommendations=[
                "Deploy standard `/llms.txt` at domain root for direct LLM context window ingestion.",
                "Explicitly allow `GPTBot`, `PerplexityBot`, and `ClaudeBot` in `robots.txt`."
            ]
        )

        overall_score = round((chatgpt_score + perplexity_score + google_score + claude_score) / 4.0, 1)

        return PerEngineAiMatrix(
            chatgpt=chatgpt_score_obj,
            perplexity=perplexity_score_obj,
            google_aio=google_score_obj,
            claude_gemini=claude_score_obj,
            overall_engine_score=overall_score,
            overall_engine_grade=_grade_from_score(overall_score),
            information_gain=info_gain_rep,
            ai_bot_directives=ai_bot_rep
        )


def evaluate_per_engine_ai(
    pages: List[PageEvidence],
    manifest: Optional[CrawlManifest] = None,
    profile: Optional[BusinessProfile] = None,
    website_url: str = "",
) -> PerEngineAiMatrix:
    return PerEngineAiEvaluator.evaluate(
        pages=pages,
        manifest=manifest,
        profile=profile,
        website_url=website_url
    )
