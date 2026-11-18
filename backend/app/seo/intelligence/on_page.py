"""
On-Page SEO Intelligence — Phase 3.4

Performs comprehensive page-level diagnostics across 17 vectors:
1. Title quality
2. Meta description
3. H1 uniqueness & presence
4. H2/H3 semantic hierarchy
5. Content relevance
6. Keyword placement
7. Entity coverage
8. Image alt text
9. Image filenames
10. Internal links
11. External links
12. Anchor text quality
13. Language declarations
14. Duplicate content
15. Thin content
16. Content freshness
17. Metadata consistency
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
from pydantic import BaseModel, Field



class OnPageDiagnosticVector(BaseModel):
    vector_name: str
    status: str  # "PASS", "WARNING", "FAIL"
    score: float  # 0.0 to 1.0
    observed_value: Any
    recommendation: Optional[str] = None


class PageOnPageReport(BaseModel):
    url: str
    target_keyword: Optional[str] = None
    diagnostics: List[OnPageDiagnosticVector] = Field(default_factory=list)
    overall_on_page_score: float  # 0.0 to 100.0
    critical_defects: List[str] = Field(default_factory=list)


class OnPageSeoEngine:
    """
    Evaluates all 17 on-page SEO vectors for a given page snapshot.
    """

    @classmethod
    def evaluate_page(
        cls,
        url: str,
        html: str,
        target_keyword: Optional[str] = None,
        all_pages_content: Optional[List[str]] = None,
    ) -> PageOnPageReport:
        vectors: List[OnPageDiagnosticVector] = []
        kw = (target_keyword or "").strip().lower()

        # Helper extractors
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        raw_title = title_match.group(1).strip() if title_match else ""

        meta_desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        raw_desc = meta_desc_match.group(1).strip() if meta_desc_match else ""

        h1_matches = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        h1_texts = [re.sub(r"<[^>]+>", "", h).strip() for h in h1_matches]

        h2_matches = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
        h3_matches = re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.IGNORECASE | re.DOTALL)

        # Body text extraction
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
        body_html = body_match.group(1) if body_match else html
        clean_text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body_html, flags=re.IGNORECASE | re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        words = clean_text.split()
        word_count = len(words)
        first_100_words = " ".join(words[:100]).lower()

        # 1. Title Quality (50–60 chars)
        t_len = len(raw_title)
        if 40 <= t_len <= 65:
            t_status, t_score, t_rec = "PASS", 1.0, None
        elif t_len == 0:
            t_status, t_score, t_rec = "FAIL", 0.0, "Add an informative title tag between 50–60 characters."
        else:
            t_status, t_score, t_rec = "WARNING", 0.7, f"Title length ({t_len} chars) deviates from optimal 50–60 chars."
        vectors.append(OnPageDiagnosticVector(vector_name="Title Quality", status=t_status, score=t_score, observed_value=raw_title, recommendation=t_rec))

        # 2. Meta Description (120–160 chars)
        d_len = len(raw_desc)
        if 110 <= d_len <= 165:
            d_status, d_score, d_rec = "PASS", 1.0, None
        elif d_len == 0:
            d_status, d_score, d_rec = "FAIL", 0.0, "Add a compelling meta description between 120–160 characters."
        else:
            d_status, d_score, d_rec = "WARNING", 0.7, f"Meta description length ({d_len} chars) deviates from optimal 120–160 chars."
        vectors.append(OnPageDiagnosticVector(vector_name="Meta Description", status=d_status, score=d_score, observed_value=raw_desc, recommendation=d_rec))

        # 3. H1 Uniqueness & Presence
        if len(h1_texts) == 1:
            h1_status, h1_score, h1_rec = "PASS", 1.0, None
        elif len(h1_texts) == 0:
            h1_status, h1_score, h1_rec = "FAIL", 0.0, "Page is missing an H1 heading."
        else:
            h1_status, h1_score, h1_rec = "WARNING", 0.5, f"Multiple H1 headings detected ({len(h1_texts)}). Consolidate to a single primary H1."
        vectors.append(OnPageDiagnosticVector(vector_name="H1 Uniqueness", status=h1_status, score=h1_score, observed_value=h1_texts, recommendation=h1_rec))

        # 4. H2/H3 Semantic Hierarchy
        has_h2 = len(h2_matches) > 0
        has_h3 = len(h3_matches) > 0
        if has_h3 and not has_h2:
            hier_status, hier_score, hier_rec = "WARNING", 0.5, "Skipped heading level: H3 tags present without parent H2 headings."
        elif not has_h2 and word_count > 400:
            hier_status, hier_score, hier_rec = "WARNING", 0.7, "Long-form content lacks organizing H2 subheadings."
        else:
            hier_status, hier_score, hier_rec = "PASS", 1.0, None
        vectors.append(OnPageDiagnosticVector(vector_name="Heading Hierarchy", status=hier_status, score=hier_score, observed_value={"h1": len(h1_texts), "h2": len(h2_matches), "h3": len(h3_matches)}, recommendation=hier_rec))

        # 5. Content Relevance
        rel_score = 1.0 if word_count >= 300 else 0.6
        vectors.append(OnPageDiagnosticVector(vector_name="Content Relevance", status="PASS" if rel_score == 1.0 else "WARNING", score=rel_score, observed_value={"word_count": word_count}, recommendation="Expand topical content coverage." if rel_score < 1.0 else None))

        # 6. Keyword Placement
        if kw:
            in_title = kw in raw_title.lower()
            in_h1 = any(kw in h.lower() for h in h1_texts)
            in_intro = kw in first_100_words
            kp_count = sum([in_title, in_h1, in_intro])
            kp_score = kp_count / 3.0
            kp_status = "PASS" if kp_score >= 0.66 else "WARNING"
            kp_rec = "Ensure target keyword appears in Title, primary H1, and first 100 words." if kp_score < 1.0 else None
        else:
            kp_status, kp_score, kp_rec = "PASS", 1.0, None
        vectors.append(OnPageDiagnosticVector(vector_name="Keyword Placement", status=kp_status, score=kp_score, observed_value={"keyword": kw, "matches": {"in_title": kw in raw_title.lower() if kw else True}}, recommendation=kp_rec))

        # 7. Entity Coverage
        entities_found = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", clean_text[:2000]))
        vectors.append(OnPageDiagnosticVector(vector_name="Entity Coverage", status="PASS" if entities_found >= 5 else "WARNING", score=1.0 if entities_found >= 5 else 0.7, observed_value=f"Identified {entities_found} named entity candidates."))

        # 8. Image Alt Text
        imgs = re.findall(r"<img[^>]+>", html, re.IGNORECASE)
        imgs_missing_alt = [img for img in imgs if 'alt=' not in img.lower()]
        img_score = 1.0 if not imgs_missing_alt else max(0.0, 1.0 - (len(imgs_missing_alt) / max(len(imgs), 1)))
        vectors.append(OnPageDiagnosticVector(vector_name="Image Alt Text", status="PASS" if img_score == 1.0 else "WARNING", score=round(img_score, 2), observed_value={"total_images": len(imgs), "missing_alt": len(imgs_missing_alt)}, recommendation=f"Add descriptive alt attributes to {len(imgs_missing_alt)} image(s)." if imgs_missing_alt else None))

        # 9. Image Filenames
        bad_filenames = [img for img in imgs if re.search(r'src=["\'][^"\']*(?:IMG_|DSC_|screenshot|image_)[0-9]+', img, re.IGNORECASE)]
        vectors.append(OnPageDiagnosticVector(vector_name="Image Filenames", status="PASS" if not bad_filenames else "WARNING", score=1.0 if not bad_filenames else 0.8, observed_value=f"{len(bad_filenames)} generic filenames detected.", recommendation="Use descriptive hyphen-separated image filenames." if bad_filenames else None))

        # 10. Internal Links
        internal_links = re.findall(r'<a[^>]*href=["\'](/[^"\']+|https?://[^"\']*)["\']', html, re.IGNORECASE)
        vectors.append(OnPageDiagnosticVector(vector_name="Internal Links", status="PASS" if len(internal_links) >= 3 else "WARNING", score=1.0 if len(internal_links) >= 3 else 0.6, observed_value={"link_count": len(internal_links)}))

        # 11. External Links
        external_links = [l for l in internal_links if l.startswith("http") and urlparse(url).netloc not in l]
        vectors.append(OnPageDiagnosticVector(vector_name="External Links", status="PASS", score=1.0, observed_value={"outbound_links": len(external_links)}))

        # 12. Anchor Text Quality
        generic_anchors = re.findall(r'<a[^>]*>\s*(?:click here|read more|learn more|link|here)\s*</a>', html, re.IGNORECASE)
        vectors.append(OnPageDiagnosticVector(vector_name="Anchor Text Quality", status="PASS" if not generic_anchors else "WARNING", score=1.0 if not generic_anchors else 0.7, observed_value={"generic_anchor_count": len(generic_anchors)}, recommendation=f"Replace {len(generic_anchors)} generic anchor texts with descriptive phrases." if generic_anchors else None))

        # 13. Language Declarations
        has_lang = bool(re.search(r'<html[^>]*lang=["\'][a-z]{2}(?:-[a-z]{2})?["\']', html, re.IGNORECASE))
        vectors.append(OnPageDiagnosticVector(vector_name="Language Declaration", status="PASS" if has_lang else "WARNING", score=1.0 if has_lang else 0.5, observed_value={"declared": has_lang}, recommendation="Declare language attribute on <html> element." if not has_lang else None))

        # 14. Duplicate Content Check
        is_duplicate = False
        if all_pages_content and len(all_pages_content) > 1:
            my_set = set(clean_text.lower().split())
            for other in all_pages_content:
                other_set = set(other.lower().split())
                if my_set and other_set:
                    jaccard = len(my_set & other_set) / len(my_set | other_set)
                    if jaccard > 0.85:
                        is_duplicate = True
                        break
        vectors.append(OnPageDiagnosticVector(vector_name="Duplicate Content", status="FAIL" if is_duplicate else "PASS", score=0.0 if is_duplicate else 1.0, observed_value={"is_near_duplicate": is_duplicate}, recommendation="Consolidate duplicate content or declare canonical target." if is_duplicate else None))

        # 15. Thin Content Check
        is_thin = word_count < 250 and not any(u in url for u in ["/cart", "/login", "/contact"])
        vectors.append(OnPageDiagnosticVector(vector_name="Thin Content Check", status="WARNING" if is_thin else "PASS", score=0.5 if is_thin else 1.0, observed_value={"word_count": word_count}, recommendation="Expand content depth; page has fewer than 250 words." if is_thin else None))

        # 16. Content Freshness
        has_date = bool(re.search(r'(?:datePublished|dateModified|publish-date|updated-date|datetime=)', html, re.IGNORECASE))
        vectors.append(OnPageDiagnosticVector(vector_name="Content Freshness", status="PASS" if has_date else "OBSERVATION", score=1.0 if has_date else 0.8, observed_value={"timestamp_found": has_date}))

        # 17. Metadata Consistency
        og_title = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        og_val = og_title.group(1).strip() if og_title else ""
        meta_consistent = (not og_val) or (og_val.lower() in raw_title.lower() or raw_title.lower() in og_val.lower())
        vectors.append(OnPageDiagnosticVector(vector_name="Metadata Consistency", status="PASS" if meta_consistent else "WARNING", score=1.0 if meta_consistent else 0.8, observed_value={"og_matches_title": meta_consistent}))

        # Calculate Rollup Score
        overall_score = round((sum(v.score for v in vectors) / len(vectors)) * 100, 1)
        critical_defects = [f"{v.vector_name}: {v.recommendation}" for v in vectors if v.status == "FAIL" and v.recommendation]

        return PageOnPageReport(
            url=url,
            target_keyword=target_keyword,
            diagnostics=vectors,
            overall_on_page_score=overall_score,
            critical_defects=critical_defects,
        )
