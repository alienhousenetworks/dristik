import { ExecutiveReport, PillarScoreData, WebsiteIntelligenceRollup } from '../types';

function getHealth(score: number | null): 'GOOD' | 'FAIR' | 'POOR' {
  if (score == null) return 'POOR';
  if (score >= 80) return 'GOOD';
  if (score >= 60) return 'FAIR';
  return 'POOR';
}

function getGrade(score: number | null): string {
  if (score == null) return '—';
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
      seo: emptyPillar('seo', 'Search Engine Optimization (SEO)', 'SEO', 'SEO'),
      geo: emptyPillar('geo', 'Generative Engine Optimization (GEO)', 'GEO', 'GEO'),
      aeo: emptyPillar('aeo', 'Answer Engine Optimization (AEO)', 'AEO', 'AEO'),
      cro: emptyPillar('cro', 'Conversion Rate Optimization (CRO)', 'CRO', 'CRO'),
      competitors: emptyPillar('competitors', 'Competitor Intelligence', 'Competitors', 'Benchmarking'),
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

  // ─────────────────────────────────────────────────────────────
  // 1. SEO: SEARCH ENGINE OPTIMIZATION (Technical, On-Page & Content)
  // ─────────────────────────────────────────────────────────────
  const techScore = catScores['TECHNICAL_SEO']?.score ?? catScores['technical']?.score ?? honest?.google_score;
  const onPageScore = catScores['ON_PAGE_SEO']?.score;
  const contentScore = catScores['CONTENT']?.score;
  const searchParts = [
    [techScore, 0.45],
    [onPageScore, 0.35],
    [contentScore, 0.20],
  ].filter((pair): pair is [number, number] => typeof pair[0] === 'number');
  const searchWeight = searchParts.reduce((sum, pair) => sum + pair[1], 0);
  const seoScore = searchWeight > 0
    ? Math.round(searchParts.reduce((sum, [value, weight]) => sum + value * weight, 0) / searchWeight)
    : (typeof techScore === 'number' ? Math.round(techScore) : null);

  const seoFindings = findings.filter(f =>
    f.category === 'TECHNICAL_SEO' || f.category === 'ON_PAGE_SEO' || f.category === 'CONTENT'
  );

  const seoPillar: PillarScoreData = {
    id: 'seo',
    name: 'Search Engine Optimization (SEO)',
    shortName: 'SEO',
    categoryTag: 'SEO',
    score: seoScore,
    grade: getGrade(seoScore),
    health: getHealth(seoScore),
    headline: seoScore == null ? 'SEO was not scored' : (seoScore >= 80 ? 'Solid Technical & On-Page Foundation' : 'Crawl, Structure & Technical Debt Detected'),
    summary: catScores['TECHNICAL_SEO']?.summary ||
      `Evaluates Googlebot crawlability, HTTP status codes, robots.txt, redirect paths, XML sitemaps, heading hierarchy, and meta architecture across ${report.crawl_manifest?.pages?.length || 1} pages.`,
    highlights: [
      techScore == null ? 'Crawl index: not scored' : `Technical Crawl: ${Math.round(techScore)}/100`,
      onPageScore == null ? 'On-page: not scored' : `On-Page & Structure: ${Math.round(onPageScore)}/100`,
      `Sitemap & Robots: ${report.crawl_manifest?.sitemap_found ? 'Detected' : 'Missing'}`,
      `Pages Audited: ${report.crawl_manifest?.pages?.length || 1} crawled`,
    ],
    findingsCount: seoFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 2. GEO: GENERATIVE ENGINE OPTIMIZATION (Per-Engine, Citations, Information Gain)
  // ─────────────────────────────────────────────────────────────
  const perEngine = report.per_engine_geo;
  const perEngineOverall = perEngine?.overall_engine_score;
  const liveCitations = honest?.ai_visibility_status === 'MEASURED' ? honest?.ai_visibility_score : null;
  const geoCatScore = catScores['GEO']?.score;
  const infoGainScore = perEngine?.information_gain?.fluff_ratio_score != null
    ? Math.round(100 - perEngine.information_gain.fluff_ratio_score)
    : null;

  const geoParts = [perEngineOverall, liveCitations, geoCatScore, infoGainScore].filter(
    (n): n is number => typeof n === 'number'
  );
  const geoScore = geoParts.length
    ? Math.round(geoParts.reduce((sum, n) => sum + n, 0) / geoParts.length)
    : (typeof perEngineOverall === 'number' ? Math.round(perEngineOverall) : (typeof geoCatScore === 'number' ? Math.round(geoCatScore) : null));

  const geoFindings = findings.filter(f => f.category === 'GEO' || (f.category === 'AI_SEARCH' && f.title?.toLowerCase().includes('citation')));

  const geoPillar: PillarScoreData = {
    id: 'geo',
    name: 'Generative Engine Optimization (GEO)',
    shortName: 'GEO',
    categoryTag: 'GEO',
    score: geoScore,
    grade: getGrade(geoScore),
    health: getHealth(geoScore),
    headline: geoScore == null
      ? 'GEO was not scored on this crawl'
      : (geoScore >= 75 ? 'Strong Multi-Engine Visibility & Citation Grounding' : 'Low Visibility in ChatGPT, Perplexity & AI Overviews'),
    summary: 'Measures multi-engine generative presence across ChatGPT, Perplexity, Google SGE/AIO, and Claude/Gemini, benchmarked against original research and citations.',
    highlights: [
      perEngine ? `Per-Engine Grade: ${perEngine.overall_engine_grade}` : 'Engine Benchmark: Calibrating',
      liveCitations != null ? `Live AI Citations: ${Math.round(liveCitations)}/100` : 'Citations: Verified on-page signals',
      `Original Information Gain: ${infoGainScore != null ? `${infoGainScore}/100` : 'Analyzed'}`,
      `Commercial Query Matrix: ${report.ai_search_matrix?.length || 0} queries monitored`,
    ],
    findingsCount: geoFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 3. AEO: ANSWER ENGINE & AGENT OPTIMIZATION (Agent Readiness, llms.txt, Schema, Q&A)
  // ─────────────────────────────────────────────────────────────
  const schemaScore = catScores['SCHEMA']?.score;
  const extractabilityScore = report.geo_readiness?.extractability_score ?? null;
  const botDirectives = perEngine?.ai_bot_directives;
  const botPermissionCount = botDirectives ? [
    botDirectives.gptbot_allowed,
    botDirectives.perplexitybot_allowed,
    botDirectives.claudebot_allowed,
    botDirectives.google_extended_allowed,
  ].filter(Boolean).length : 0;
  const botScore = botDirectives ? (botPermissionCount / 4) * 100 : null;
  const graphQuality = report.geo_readiness?.schema_crosscheck?.quality_score;
  const graphPresent = report.geo_readiness?.schema_crosscheck?.present_properties;
  const graphApplicable = report.geo_readiness?.schema_crosscheck?.applicable_properties;

  const aeoParts = [schemaScore, extractabilityScore, botScore].filter((n): n is number => typeof n === 'number');
  const aeoScore = aeoParts.length
    ? Math.round(aeoParts.reduce((sum, n) => sum + n, 0) / aeoParts.length)
    : null;

  const aeoFindings = findings.filter(f =>
    f.category === 'SCHEMA' || (f.category === 'AI_SEARCH' && !f.title?.toLowerCase().includes('citation'))
  );

  const aeoPillar: PillarScoreData = {
    id: 'aeo',
    name: 'Answer Engine & Agent Optimization (AEO)',
    shortName: 'AEO',
    categoryTag: 'AEO',
    score: aeoScore,
    grade: getGrade(aeoScore),
    health: getHealth(aeoScore),
    headline: aeoScore == null
      ? 'AEO was not scored on this crawl'
      : (aeoScore >= 75 ? 'Structured for Autonomous Agents & Machine Extractability' : 'Unstructured Data Restricting Agent Retrieval'),
    summary: 'Audits Schema.org JSON-LD graphs, machine-readable documentation (llms.txt), AI bot crawler accessibility, and 50-question deterministic extractability.',
    highlights: [
      typeof graphQuality === 'number'
        ? `Entity graph quality: ${Math.round(graphQuality)}/100 (${graphPresent ?? 0} of ${graphApplicable ?? 0} applicable properties)`
        : `JSON-LD types observed: ${report.geo_readiness?.schema_types?.length || 0}`,
      `Agent Bot Access: ${botDirectives ? `${botPermissionCount}/4 major AI crawlers allowed` : 'Not measured'}`,
      `llms.txt Machine File: ${botDirectives?.llms_txt_found ? '✅ Detected' : '⚡ Generated ready'}`,
      `Q&A Extractability: ${report.geo_readiness?.questions_supported || 0} supported answers`,
    ],
    findingsCount: aeoFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 4. CRO: CONVERSION RATE OPTIMIZATION & USER JOURNEY
  // ─────────────────────────────────────────────────────────────
  const humanScore = honest?.human_score ?? catScores['UX_CONVERSION']?.score;
  const formAudit = report.form_audit;
  const formScore = formAudit ? Math.max(0, 100 - (formAudit.friction_score || 0)) : null;

  const croParts = [humanScore, formScore].filter((n): n is number => typeof n === 'number');
  const croScore = croParts.length
    ? Math.round(croParts.reduce((sum, n) => sum + n, 0) / croParts.length)
    : (typeof humanScore === 'number' ? Math.round(humanScore) : 65);

  const croFindings = findings.filter(f => f.category === 'UX_CONVERSION');

  const croPillar: PillarScoreData = {
    id: 'cro',
    name: 'Conversion Rate Optimization (CRO)',
    shortName: 'CRO',
    categoryTag: 'CRO',
    score: croScore,
    grade: getGrade(croScore),
    health: getHealth(croScore),
    headline: croScore >= 75 ? 'Clear Value Proposition & Frictionless Conversion Path' : 'Conversion Friction in Forms, CTAs & User Flow',
    summary: 'Audits form field complexity, missing labels, CTA action verbs, 5-second value proposition clarity, and visual UX friction barriers.',
    highlights: [
      `Form Friction: ${formAudit ? `Grade ${formAudit.cro_friction_grade} (${formAudit.total_forms_detected} forms)` : 'Evaluated'}`,
      `Primary CTA: ${report.business_profile?.primary_cta ? `"${report.business_profile.primary_cta}"` : 'Not detected'}`,
      `Value Prop Clarity: ${report.business_profile?.value_proposition ? 'Extracted' : 'Missing clear hero'}`,
      `UX Friction Hazards: ${report.semantic_business?.friction_points?.length || 0} logged`,
    ],
    findingsCount: croFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 5. COMPETITOR INTELLIGENCE & BENCHMARKS
  // ─────────────────────────────────────────────────────────────
  const bakeoff = report.competitor_bakeoff;
  const compFindings = findings.filter(f => f.category === 'COMPETITIVE');
  const totalBakeoff = (bakeoff?.target_wins || 0) + (bakeoff?.competitor_wins || 0) + (bakeoff?.ties || 0);
  const competitorScore = totalBakeoff > 0
    ? Math.round(((bakeoff?.target_wins || 0) / totalBakeoff) * 100)
    : 70;

  const competitorPillar: PillarScoreData = {
    id: 'competitors',
    name: 'Competitor Intelligence',
    shortName: 'Competitors',
    categoryTag: 'Benchmarking',
    score: competitorScore,
    grade: getGrade(competitorScore),
    health: getHealth(competitorScore),
    headline: competitorScore >= 60 ? 'Competitive Parity in High-Intent Buyer Queries' : 'Competitor Dominance in Commercial Search Queries',
    summary: 'Head-to-head intent bake-off benchmarking your offerings, pricing transparency, and authority against key market rivals.',
    highlights: [
      `Commercial Query Win Rate: ${competitorScore}%`,
      `Rival Domain: ${bakeoff?.competitor_domain || 'Market peers'}`,
      `Market Gaps Logged: ${compFindings.length} competitive findings`,
    ],
    findingsCount: compFindings.length,
  };

  // Experience / SXO bridging calculation for legacy compatibility
  const ttfb = report.crawl_manifest?.pages?.[0]?.ttfb_ms;
  const sxoScore = Math.round(((seoScore || 70) + (croScore || 70)) / 2);

  const experiencePillar: PillarScoreData = {
    id: 'website_experience',
    name: 'Website Experience (SXO)',
    shortName: 'Experience',
    categoryTag: 'SXO',
    score: sxoScore,
    grade: getGrade(sxoScore),
    health: getHealth(sxoScore),
    headline: 'Sub-second Latency & Seamless User Experience',
    summary: 'Search Experience Optimization (SXO) bridges search discovery to user satisfaction through TTFB and mobile UX.',
    highlights: [
      typeof ttfb === 'number' ? `Server TTFB: ${ttfb}ms` : 'Server TTFB: Checked',
      `Mobile Viewport: ${report.crawl_manifest?.pages?.[0]?.viewport ? 'Configured' : 'Missing'}`,
    ],
    findingsCount: croFindings.length,
  };

  const brandPillar: PillarScoreData = {
    id: 'brand_entity_intelligence',
    name: 'Brand & Entity Intelligence',
    shortName: 'Brand & Entity',
    categoryTag: 'Entity',
    score: aeoScore,
    grade: getGrade(aeoScore),
    health: getHealth(aeoScore),
    headline: 'Entity Trust & Knowledge Graph Disambiguation',
    summary: 'Audits Organization JSON-LD schemas and business identity consistency.',
    highlights: [
      `Brand: ${report.business_profile?.business_name || 'Extracted'}`,
      `Conflicts: ${(report.contradictions?.length || 0) > 0 ? '⚠️ Detected' : 'None detected'}`,
    ],
    findingsCount: aeoFindings.length,
  };

  return {
    seo: seoPillar,
    geo: geoPillar,
    aeo: aeoPillar,
    cro: croPillar,
    competitors: competitorPillar,
    // Legacy pillar mappings for backward compatibility
    search_intelligence: seoPillar,
    ai_search_intelligence: geoPillar,
    website_experience: experiencePillar,
    conversion_intelligence: croPillar,
    brand_entity_intelligence: brandPillar,
    sxo_score: sxoScore,
    sxo_health: getHealth(sxoScore),
  };
}
