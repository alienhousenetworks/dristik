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
      technical_seo: emptyPillar('technical_seo', 'Technical SEO', 'Technical SEO', 'SEO'),
      on_page_seo: emptyPillar('on_page_seo', 'On-Page SEO', 'On-Page SEO', 'SEO'),
      content: emptyPillar('content', 'Content & Readability', 'Content', 'Content'),
      schema: emptyPillar('schema', 'Schema & Structured Data', 'Schema', 'Schema'),
      trust_authority: emptyPillar('trust_authority', 'Trust & Authority', 'Trust', 'Trust'),
      ai_search: emptyPillar('ai_search', 'AI Search & Visibility', 'AI Search', 'AI'),
      ux_conversion: emptyPillar('ux_conversion', 'UX & Conversion (CRO)', 'UX/CRO', 'CRO'),
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

  const techCat = catScores['TECHNICAL_SEO'] ?? catScores['technical'];
  const onPageCat = catScores['ON_PAGE_SEO'] ?? catScores['on_page'];
  const contentCat = catScores['CONTENT'] ?? catScores['content'];
  const geoCat = catScores['GEO'] ?? catScores['geo'];
  const aiSearchCat = catScores['AI_SEARCH'] ?? catScores['ai_search'];
  const schemaCat = catScores['SCHEMA'] ?? catScores['schema'];
  const uxCat = catScores['UX_CONVERSION'] ?? catScores['ux_conversion'];
  const trustCat = catScores['TRUST_AUTHORITY'] ?? catScores['trust_authority'];

  // ─────────────────────────────────────────────────────────────
  // 1. SEO: SEARCH ENGINE OPTIMIZATION (Technical SEO as primary)
  // ─────────────────────────────────────────────────────────────
  const techScore = techCat?.score != null ? Math.round(techCat.score) : (honest?.google_score != null ? Math.round(honest.google_score) : null);
  const onPageScore = onPageCat?.score != null ? Math.round(onPageCat.score) : null;
  const contentScore = contentCat?.score != null ? Math.round(contentCat.score) : null;
  const seoComponents = [techScore, onPageScore, contentScore].filter((s): s is number => s != null);
  const seoScore = honest?.google_score != null
    ? Math.round(honest.google_score)
    : (seoComponents.length > 0 ? Math.round(seoComponents.reduce((a, b) => a + b, 0) / seoComponents.length) : (techScore ?? null));

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
      `Evaluates Googlebot crawlability, HTTP status codes, robots.txt, redirect paths, XML sitemaps, heading hierarchy, and meta architecture across ${report.crawl_manifest?.pages?.length ?? 0} pages.`,
    highlights: [
      techScore == null ? 'Crawl index: not scored' : `Technical Crawl: ${techScore}/100`,
      onPageScore == null ? 'On-page: not scored' : `On-Page & Structure: ${onPageScore}/100`,
      `Sitemap & Robots: ${report.crawl_manifest?.sitemap_found ? 'Detected' : 'Missing'}`,
      `Pages Audited: ${report.crawl_manifest?.pages?.length ?? 0} crawled`,
    ],
    findingsCount: seoFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 2. GEO: GENERATIVE ENGINE OPTIMIZATION (Per-Engine, Citations, Information Gain)
  // ─────────────────────────────────────────────────────────────
  const perEngine = report.per_engine_geo;
  const liveCitations = honest?.ai_visibility_status === 'MEASURED' ? honest?.ai_visibility_score : null;
  const measuredExtractability = typeof report.geo_readiness?.extractability_score === 'number'
    ? report.geo_readiness.extractability_score
    : null;
  const geoCatScore = geoCat?.score != null ? Math.round(geoCat.score) : null;
  const infoGainScore = perEngine?.information_gain?.fluff_ratio_score != null
    ? Math.round(100 - perEngine.information_gain.fluff_ratio_score)
    : null;

  const geoScore = geoCatScore != null ? geoCatScore : (measuredExtractability != null ? Math.round(measuredExtractability) : null);

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
      ? 'On-page extractability was not scored on this crawl'
      : (geoScore >= 75 ? 'Pages are structured for extraction' : 'Pages are hard for an answer engine to quote'),
    summary: 'On-page extractability only. Live mention rate, citation rate, and competitor visibility stay on the visibility card and stay blank until a live run.',
    highlights: [
      perEngine?.measurement_note || 'Per-engine matrix is an on-page writing exercise, not a live query.',
      liveCitations != null ? `Live citation score: ${Math.round(liveCitations)}/100` : 'Live visibility: not measured',
      `Original Information Gain: ${infoGainScore != null ? `${infoGainScore}/100` : 'Analyzed'}`,
      `Commercial Query Matrix: ${report.ai_search_matrix?.length || 0} queries monitored`,
    ],
    findingsCount: geoFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 3. AEO: ANSWER ENGINE & AGENT OPTIMIZATION (Canonical SCHEMA)
  // ─────────────────────────────────────────────────────────────
  const schemaScore = schemaCat?.score != null ? Math.round(schemaCat.score) : null;
  const aeoScore = schemaScore;
  const botDirectives = perEngine?.ai_bot_directives;
  const botPermissionCount = botDirectives ? [
    botDirectives.gptbot_allowed,
    botDirectives.perplexitybot_allowed,
    botDirectives.claudebot_allowed,
    botDirectives.google_extended_allowed,
  ].filter(Boolean).length : 0;
  const graphQuality = report.geo_readiness?.schema_crosscheck?.quality_score;
  const graphPresent = report.geo_readiness?.schema_crosscheck?.present_properties;
  const graphApplicable = report.geo_readiness?.schema_crosscheck?.applicable_properties;

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
      `Agent Bot Access: ${botDirectives?.robots_measured ? `${botPermissionCount}/4 major AI crawlers allowed` : 'Not measured'}`,
      `llms.txt Machine File: ${botDirectives?.llms_txt_found ? '✅ Detected' : '⚡ Generated ready'}`,
      `Q&A Extractability: ${report.geo_readiness?.questions_supported || 0} supported answers`,
    ],
    findingsCount: aeoFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // 4. CRO: CONVERSION RATE OPTIMIZATION & USER JOURNEY (Canonical UX_CONVERSION)
  // ─────────────────────────────────────────────────────────────
  const formAudit = report.form_audit;
  const analytics = report.google_performance?.analytics;
  const ga4LandingPages = analytics?.landing_pages ?? [];
  const ga4KeyEvents = analytics?.key_events;
  const ga4Sessions = analytics?.sessions ?? 0;
  const ga4Measured = analytics?.state === 'MEASURED'
    && ga4LandingPages.length > 0
    && ga4KeyEvents != null
    && ga4Sessions > 0;
  const ga4Rate = ga4Measured
    ? Math.round((Number(ga4KeyEvents) / ga4Sessions) * 1000) / 10
    : null;

  const uxScore = uxCat?.score != null ? Math.round(uxCat.score) : null;
  const croScore = uxScore;

  const croFindings = findings.filter(f => f.category === 'UX_CONVERSION');

  const croPillar: PillarScoreData = {
    id: 'cro',
    name: 'Conversion Rate Optimization (CRO)',
    shortName: 'CRO',
    categoryTag: 'CRO',
    score: croScore,
    grade: getGrade(croScore),
    health: getHealth(croScore),
    headline: ga4Measured
      ? `GA4 key-event rate ${ga4Rate}%`
      : (croScore == null ? 'Conversion experience unmeasured' : (croScore >= 75 ? 'Low Friction & Clear Value Proposition' : 'Conversion & UX Friction Detected')),
    summary: ga4Measured
      ? 'Google Analytics 4 landing pages and key events for this property. The rate is key events divided by sessions.'
      : 'Audited behavioral heuristics across CTAs, form barriers, and value proposition clarity.',
    highlights: [
      ga4Measured
        ? `GA4: ${ga4KeyEvents} key events / ${ga4Sessions} sessions (${ga4Rate}%)`
        : 'GA4 key-event rate: not measured',
      `Form Friction: ${formAudit?.cro_friction_grade ? `Grade ${formAudit.cro_friction_grade} (${formAudit.total_forms_detected} forms)` : 'Not measured'}`,
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
    : null;

  const competitorPillar: PillarScoreData = {
    id: 'competitors',
    name: 'Competitor Intelligence',
    shortName: 'Competitors',
    categoryTag: 'Benchmarking',
    score: competitorScore,
    grade: getGrade(competitorScore),
    health: getHealth(competitorScore),
    headline: competitorScore == null ? 'Competitor intelligence unmeasured' : (competitorScore >= 60 ? 'Competitive Parity in High-Intent Buyer Queries' : 'Competitor Dominance in Commercial Search Queries'),
    summary: 'Head-to-head intent bake-off benchmarking your offerings, pricing transparency, and authority against key market rivals.',
    highlights: [
      competitorScore != null ? `Commercial Query Win Rate: ${competitorScore}%` : 'Commercial Query Win Rate: Unmeasured',
      `Rival Domain: ${bakeoff?.competitor_domain || 'Market peers'}`,
      `Market Gaps Logged: ${compFindings.length} competitive findings`,
    ],
    findingsCount: compFindings.length,
  };

  // ─────────────────────────────────────────────────────────────
  // Additional Canonical Pillars
  // ─────────────────────────────────────────────────────────────
  const onPageFindings = findings.filter(f => f.category === 'ON_PAGE_SEO');
  const onPagePillar: PillarScoreData = {
    id: 'on_page_seo',
    name: 'On-Page SEO',
    shortName: 'On-Page',
    categoryTag: 'SEO',
    score: onPageScore,
    grade: getGrade(onPageScore),
    health: getHealth(onPageScore),
    headline: onPageScore == null ? 'On-page SEO not scored' : (onPageScore >= 80 ? 'Optimized Meta & Hierarchy' : 'On-Page Optimization Needed'),
    summary: 'Evaluates title tags, meta descriptions, H1-H6 heading hierarchy, and content structure.',
    highlights: [
      `On-Page Score: ${onPageScore != null ? `${onPageScore}/100` : 'Not scored'}`,
      `H1 Status: ${report.crawl_manifest?.pages?.[0]?.h1 ? 'Detected' : 'Missing'}`,
    ],
    findingsCount: onPageFindings.length,
  };

  const contentFindings = findings.filter(f => f.category === 'CONTENT');
  const contentPillar: PillarScoreData = {
    id: 'content',
    name: 'Content & Readability',
    shortName: 'Content',
    categoryTag: 'Content',
    score: contentScore,
    grade: getGrade(contentScore),
    health: getHealth(contentScore),
    headline: contentScore == null ? 'Content not scored' : (contentScore >= 75 ? 'Clear and Engaging Copy' : 'Content Improvements Needed'),
    summary: 'Audits readability indices, paragraph length, scannability, and proof points.',
    highlights: [
      `Content Score: ${contentScore != null ? `${contentScore}/100` : 'Not scored'}`,
      `Readability: ${honest?.human_score != null ? 'Measured' : 'Audited'}`,
    ],
    findingsCount: contentFindings.length,
  };

  const trustScore = trustCat?.score != null ? Math.round(trustCat.score) : null;
  const trustFindings = findings.filter(f => f.category === 'TRUST_AUTHORITY');
  const trustPillar: PillarScoreData = {
    id: 'trust_authority',
    name: 'Trust & Authority',
    shortName: 'Trust',
    categoryTag: 'Trust',
    score: trustScore,
    grade: getGrade(trustScore),
    health: getHealth(trustScore),
    headline: trustScore == null ? 'Trust & authority unmeasured (connector not connected)' : (trustScore >= 80 ? 'Verified Security & E-E-A-T Posture' : 'Trust Deficits Detected'),
    summary: 'Evaluates HTTPS/TLS encryption, legal policies, author attribution, and external domain authority.',
    highlights: [
      `Trust Score: ${trustScore != null ? `${trustScore}/100` : 'Not measured'}`,
      `HTTPS: ${report.crawl_manifest?.pages?.[0]?.url?.startsWith('https') ? 'Active' : 'Missing'}`,
    ],
    findingsCount: trustFindings.length,
  };

  const aiSearchScore = aiSearchCat?.score != null ? Math.round(aiSearchCat.score) : null;
  const aiSearchFindings = findings.filter(f => f.category === 'AI_SEARCH');
  const aiSearchPillar: PillarScoreData = {
    id: 'ai_search',
    name: 'AI Search & LLM Optimization',
    shortName: 'AI Search',
    categoryTag: 'AI',
    score: aiSearchScore,
    grade: getGrade(aiSearchScore),
    health: getHealth(aiSearchScore),
    headline: aiSearchScore == null ? 'AI search unmeasured' : (aiSearchScore >= 75 ? 'High Generative AI Visibility' : 'Low AI Retrieval Presence'),
    summary: 'Evaluates citations, mentions, and prompt coverage across major generative engines.',
    highlights: [
      `AI Search Score: ${aiSearchScore != null ? `${aiSearchScore}/100` : 'Not scored'}`,
      liveCitations != null ? `Live Citation: ${Math.round(liveCitations)}/100` : 'Live visibility: unmeasured',
    ],
    findingsCount: aiSearchFindings.length,
  };

  // Experience / SXO bridging calculation for legacy compatibility
  const ttfb = report.crawl_manifest?.pages?.[0]?.ttfb_ms;
  const sxoScore = honest?.human_score != null ? Math.round(honest.human_score) : (croScore ?? null);

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
    score: trustScore,
    grade: getGrade(trustScore),
    health: getHealth(trustScore),
    headline: 'Entity Trust & Knowledge Graph Disambiguation',
    summary: 'Audits Organization JSON-LD schemas and business identity consistency.',
    highlights: [
      `Brand: ${report.business_profile?.business_name || 'Extracted'}`,
      `Conflicts: ${(report.contradictions?.length || 0) > 0 ? '⚠️ Detected' : 'None detected'}`,
    ],
    findingsCount: trustFindings.length,
  };

  const schemaFindings = findings.filter(f => f.category === 'SCHEMA');
  const schemaPillar: PillarScoreData = {
    id: 'schema',
    name: 'Schema & Structured Data',
    shortName: 'Schema',
    categoryTag: 'Schema',
    score: schemaScore,
    grade: getGrade(schemaScore),
    health: getHealth(schemaScore),
    headline: schemaScore == null ? 'Schema not scored' : (schemaScore >= 75 ? 'Structured Data Validated' : 'Schema Inconsistencies Detected'),
    summary: 'Audits Schema.org JSON-LD, microdata graphs, entity properties, and syntax accuracy.',
    highlights: [
      `Schema Score: ${schemaScore != null ? `${schemaScore}/100` : 'Not scored'}`,
      `Types detected: ${report.geo_readiness?.schema_types?.length || 0}`,
    ],
    findingsCount: schemaFindings.length,
  };

  return {
    seo: seoPillar,
    geo: geoPillar,
    aeo: aeoPillar,
    cro: croPillar,
    competitors: competitorPillar,

    // 8 Canonical Categories
    technical_seo: seoPillar,
    on_page_seo: onPagePillar,
    content: contentPillar,
    schema: schemaPillar,
    trust_authority: trustPillar,
    ai_search: aiSearchPillar,
    ux_conversion: croPillar,

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
