import { ExecutiveReport, PillarScoreData, WebsiteIntelligenceRollup } from '../types';

function getHealth(score: number): 'GOOD' | 'FAIR' | 'POOR' {
  if (score >= 80) return 'GOOD';
  if (score >= 60) return 'FAIR';
  return 'POOR';
}

function getGrade(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

export function synthesizePillars(report: ExecutiveReport | undefined | null): WebsiteIntelligenceRollup {
  if (!report) {
    const emptyPillar = (id: any, name: string, shortName: string, categoryTag: string): PillarScoreData => ({
      id,
      name,
      shortName,
      categoryTag,
      score: 0,
      grade: '—',
      health: 'POOR',
      headline: 'Awaiting Audit Data',
      summary: 'No audit evidence available yet.',
      highlights: [],
      findingsCount: 0,
    });

    return {
      search_intelligence: emptyPillar('search_intelligence', 'Search Intelligence (SEO)', 'Search (SEO)', 'SEO'),
      ai_search_intelligence: emptyPillar('ai_search_intelligence', 'AI Search Intelligence (GEO / AEO)', 'AI Search', 'GEO/AEO'),
      website_experience: emptyPillar('website_experience', 'Website Experience (SXO)', 'Experience (SXO)', 'SXO'),
      conversion_intelligence: emptyPillar('conversion_intelligence', 'Conversion Intelligence (CRO)', 'Conversion (CRO)', 'CRO'),
      brand_entity_intelligence: emptyPillar('brand_entity_intelligence', 'Brand & Entity Intelligence', 'Brand & Entity', 'Entity'),
      sxo_score: 0,
      sxo_health: 'POOR',
    };
  }

  const findings = report.findings || [];
  const catScores = report.scores?.category_scores || {};
  const honest = report.honest_scores;

  // 1. SEARCH INTELLIGENCE (SEO)
  // Categories: TECHNICAL_SEO (40%), ON_PAGE_SEO (30%), CONTENT (30%)
  const techScore = catScores['TECHNICAL_SEO']?.score ?? catScores['technical']?.score ?? (honest?.google_score ?? 65);
  const onPageScore = catScores['ON_PAGE_SEO']?.score ?? techScore;
  const contentScore = catScores['CONTENT']?.score ?? 70;
  const searchScore = Math.round((techScore * 0.4) + (onPageScore * 0.3) + (contentScore * 0.3));

  const searchFindings = findings.filter(f =>
    f.category === 'TECHNICAL_SEO' || f.category === 'ON_PAGE_SEO' || f.category === 'CONTENT'
  );

  const searchPillar: PillarScoreData = {
    id: 'search_intelligence',
    name: 'Search Intelligence (SEO)',
    shortName: 'Search (SEO)',
    categoryTag: 'SEO',
    score: searchScore,
    grade: getGrade(searchScore),
    health: getHealth(searchScore),
    headline: searchScore >= 80 ? 'Robust Crawlability & Search Footprint' : 'Technical & On-Page Remediation Needed',
    summary: catScores['TECHNICAL_SEO']?.summary ||
      `Evaluates Googlebot crawlability, HTML5 semantic structure, meta tags, and internal link graphs across ${report.crawl_manifest?.pages?.length || 1} pages.`,
    highlights: [
      `Google Crawl Index: ${Math.round(techScore)}/100`,
      `On-Page & HTML: ${Math.round(onPageScore)}/100`,
      `Content Depth & EEAT: ${Math.round(contentScore)}/100`,
      `Sitemap & Robots: ${report.crawl_manifest?.sitemap_found ? 'Detected' : 'Missing'}`,
    ],
    findingsCount: searchFindings.length,
  };

  // 2. AI SEARCH INTELLIGENCE (GEO / AEO)
  // Categories: GEO (45%), AI_SEARCH (40%), SCHEMA (15%) or live honest AI citation score
  const readiness = honest?.ai_readiness_score ?? null;
  const liveCitations = honest?.ai_visibility_status === 'MEASURED' ? honest?.ai_visibility_score : null;
  const geoParts = [catScores['GEO']?.score, catScores['AI_SEARCH']?.score, readiness].filter(
    (n): n is number => typeof n === 'number'
  );
  const finalAiScore = geoParts.length
    ? Math.round(geoParts.reduce((sum, n) => sum + n, 0) / geoParts.length)
    : 0;

  const aiFindings = findings.filter(f =>
    f.category === 'GEO' || f.category === 'AI_SEARCH' || f.category === 'SCHEMA'
  );

  const aiPillar: PillarScoreData = {
    id: 'ai_search_intelligence',
    name: 'AI Search Intelligence (GEO / AEO)',
    shortName: 'AI Search',
    categoryTag: 'GEO/AEO',
    score: finalAiScore,
    grade: getGrade(finalAiScore),
    health: getHealth(finalAiScore),
    headline: geoParts.length === 0
      ? 'AI readiness was not scored from this crawl'
      : (finalAiScore >= 75 ? 'On-page answers are extractable' : 'On-page extractability has gaps'),
    summary: catScores['GEO']?.summary ||
      'On-page answer extractability from the crawl. Live ChatGPT, Perplexity, and Gemini citations are shown only when an engine run measured them.',
    highlights: [
      readiness != null ? `On-page AI readiness: ${Math.round(readiness)}/100` : 'On-page AI readiness: not scored',
      `Verified Q&A Matrix: ${report.ai_search_matrix?.length || 0} commercial queries`,
      `Extractable Snippets: ${report.geo_readiness?.questions_supported || 0} supported`,
      liveCitations != null
        ? `Live citations: ${Math.round(liveCitations)}/100`
        : 'Live citations: not measured',
    ],
    findingsCount: aiFindings.length,
  };

  // 3. WEBSITE EXPERIENCE & SXO (SEARCH EXPERIENCE)
  // Bridges Search & AI Search through User Experience, Performance, Accessibility & Information Architecture
  const ttfb = report.crawl_manifest?.pages?.[0]?.ttfb_ms ?? 300;
  const ttfbScore = ttfb < 200 ? 95 : ttfb < 500 ? 80 : ttfb < 1000 ? 60 : 40;
  const uxScore = catScores['UX_CONVERSION']?.score ?? (honest?.human_score ?? 70);
  const sxoScore = Math.round((uxScore * 0.5) + (ttfbScore * 0.3) + (searchScore * 0.2));

  const expFindings = findings.filter(f =>
    f.category === 'UX_CONVERSION' && (f.title?.toLowerCase().includes('mobile') || f.title?.toLowerCase().includes('speed') || f.title?.toLowerCase().includes('nav') || f.title?.toLowerCase().includes('performance'))
  );

  const experiencePillar: PillarScoreData = {
    id: 'website_experience',
    name: 'Website Experience (SXO)',
    shortName: 'Experience (SXO)',
    categoryTag: 'SXO',
    score: sxoScore,
    grade: getGrade(sxoScore),
    health: getHealth(sxoScore),
    headline: sxoScore >= 80 ? 'Fast, Fluid & Intent-Satisfying Journey' : 'Speed & UX Friction Degrading Search Experience',
    summary: 'Search Experience Optimization (SXO) bridges discovery to satisfaction through sub-second TTFB, mobile viewport fluidity, WCAG accessibility, and clear navigation architecture.',
    highlights: [
      `SXO Intent Index: ${sxoScore}/100`,
      `Server TTFB: ${ttfb}ms (${ttfb < 300 ? 'Fast' : 'Needs Optimization'})`,
      `Mobile Viewport: ${report.crawl_manifest?.pages?.[0]?.viewport ? 'Configured' : 'Missing'}`,
      `Information Architecture: ${report.crawl_manifest?.pages?.length || 1} pages mapped`,
    ],
    findingsCount: expFindings.length,
  };

  // 4. CONVERSION INTELLIGENCE (CRO & BUSINESS OUTCOMES)
  // Categories: CRO heuristics, CTAs, forms, pricing, lead gen
  const humanScore = honest?.human_score ?? (catScores['UX_CONVERSION']?.score ?? 70);
  const croScore = Math.round(humanScore);

  const croFindings = findings.filter(f =>
    f.category === 'UX_CONVERSION' || f.category === 'COMPETITIVE'
  );

  const conversionPillar: PillarScoreData = {
    id: 'conversion_intelligence',
    name: 'Conversion Intelligence (CRO)',
    shortName: 'Conversion (CRO)',
    categoryTag: 'CRO',
    score: croScore,
    grade: getGrade(croScore),
    health: getHealth(croScore),
    headline: croScore >= 75 ? 'Compelling Value Proposition & Conversion Funnel' : 'High Friction in CTAs, Pricing & Lead Conversion',
    summary: 'Analyzes 5-second value proposition clarity, CTA action verb strength, form barriers, pricing transparency, and commercial intent fulfillment.',
    highlights: [
      `Conversion Intent Score: ${croScore}/100`,
      `Primary CTA: ${report.business_profile?.primary_cta || 'Unspecified'}`,
      `Business Model: ${report.semantic_business?.business_model || report.business_profile?.business_model || 'Identified'}`,
      `Commercial Friction: ${report.semantic_business?.friction_points?.length || 0} barriers logged`,
    ],
    findingsCount: croFindings.length,
  };

  // 5. BRAND & ENTITY INTELLIGENCE
  // Categories: TRUST_AUTHORITY (50%), SCHEMA (40%), Contradiction Penalty (10%)
  const trustScore = catScores['TRUST_AUTHORITY']?.score ?? 75;
  const schemaScore = catScores['SCHEMA']?.score ?? 70;
  const contradictionPenalty = (report.contradictions?.length || 0) > 0 ? 15 : 0;
  const brandScore = Math.max(20, Math.round(((trustScore * 0.6) + (schemaScore * 0.4)) - contradictionPenalty));

  const brandFindings = findings.filter(f =>
    f.category === 'TRUST_AUTHORITY' || f.category === 'SCHEMA'
  );

  const brandPillar: PillarScoreData = {
    id: 'brand_entity_intelligence',
    name: 'Brand & Entity Intelligence',
    shortName: 'Brand & Entity',
    categoryTag: 'Entity',
    score: brandScore,
    grade: getGrade(brandScore),
    health: getHealth(brandScore),
    headline: (report.contradictions?.length || 0) > 0
      ? 'Identity Contradiction Detected Across Web Signals'
      : brandScore >= 80 ? 'Verified Entity & High Brand Trust' : 'Weak Knowledge Graph Disambiguation & Social Proof',
    summary: 'Audits Organization JSON-LD schemas, sameAs Knowledge Graph disambiguation, business identity consistency across pages, and customer trust proofs.',
    highlights: [
      `Entity Trust Score: ${brandScore}/100`,
      `Schema Graph: ${report.geo_readiness?.schema_types?.length || 0} structured types`,
      `Brand Identity: ${report.business_profile?.business_name || 'Verified'}`,
      `Identity Conflicts: ${(report.contradictions?.length || 0) > 0 ? '⚠️ Detected' : 'None detected'}`,
    ],
    findingsCount: brandFindings.length,
  };

  return {
    search_intelligence: searchPillar,
    ai_search_intelligence: aiPillar,
    website_experience: experiencePillar,
    conversion_intelligence: conversionPillar,
    brand_entity_intelligence: brandPillar,
    sxo_score: sxoScore,
    sxo_health: getHealth(sxoScore),
  };
}
