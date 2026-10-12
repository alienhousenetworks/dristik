/**
 * Dristik Adaptive Publication Architecture & Report-Type Classifier.
 * 
 * Supports the 8 core report families:
 * A. Complete Website Intelligence Audit (COMPLETE)
 * B. SEO Audit Book (SEO)
 * C. GEO — Generative Engine Optimization Audit Book (GEO)
 * D. AEO — Answer Engine Optimization Audit Book (AEO)
 * E. CRO — Conversion Rate Optimization Audit Book (CRO)
 * F. Competitor Analysis Book (COMPETITOR)
 * G. Other or Custom Audit (CUSTOM)
 * H. Multi-discipline or Hybrid Audit (HYBRID)
 * 
 * Deterministically maps audit evidence to book structure, chapters, and metadata.
 */

import { ExecutiveReport } from '../types';
import { NormalizedReport } from './models/normalizedReport';

export type ReportFamily =
  | 'COMPLETE'
  | 'SEO'
  | 'GEO'
  | 'AEO'
  | 'CRO'
  | 'COMPETITOR'
  | 'CUSTOM'
  | 'HYBRID';

export interface PublicationChapterDescriptor {
  id: string;
  number: string;
  part: string;
  title: string;
  shortTitle: string;
  description: string;
  isAppendix?: boolean;
}

export interface PublicationCustomization {
  titleOverride?: string;
  subtitleOverride?: string;
  classificationOverride?: string;
  includeToc?: boolean;
  includeFrontMatter?: boolean;
  includeAppendices?: boolean;
  exhaustiveMode?: boolean;
}

export interface PublicationManifest {
  family: ReportFamily;
  familyDisplayName: string;
  seriesLabel: string;
  reportTypeBadge: string;
  title: string;
  subtitle: string;
  purposeSummary: string;
  classification: string;
  reportingPeriod: string;
  auditDate: string;
  reportRef: string;
  chapters: PublicationChapterDescriptor[];
  includeToc: boolean;
  includeFrontMatter: boolean;
  includeAppendices: boolean;
  exhaustiveMode: boolean;
  evidenceStats: {
    observedCount: number;
    measuredCount: number;
    derivedCount: number;
    recommendedCount: number;
    unmeasuredCount: number;
  };
}

/**
 * Programmatically detects the audit report family from actual report data and metadata.
 */
export function detectReportFamily(
  report: ExecutiveReport | NormalizedReport,
  userOverride?: ReportFamily | null
): ReportFamily {
  if (userOverride) {
    return userOverride;
  }

  // Check explicit policy pack or audit type
  const policyPack = ('meta' in report ? report.meta.policyPack : (report as ExecutiveReport).policy_pack || '').toLowerCase();
  if (policyPack.includes('seo_only') || policyPack === 'seo') return 'SEO';
  if (policyPack.includes('geo_only') || policyPack === 'geo') return 'GEO';
  if (policyPack.includes('aeo_only') || policyPack === 'aeo') return 'AEO';
  if (policyPack.includes('cro_only') || policyPack === 'cro') return 'CRO';
  if (policyPack.includes('competitor') || policyPack === 'competitors') return 'COMPETITOR';

  // Evaluate measured disciplines based on available evidence and data
  let hasSeo = false;
  let hasGeo = false;
  let hasAeo = false;
  let hasCro = false;
  let hasCompetitor = false;

  if ('meta' in report) {
    const norm = report as NormalizedReport;
    const ledger = norm.scorecard?.ledger || [];
    hasSeo = Boolean(
      norm.technicalSeo?.pages?.length ||
      norm.meta?.pagesAnalyzed > 0 ||
      ledger.some((l) => l.categoryKey === 'TECHNICAL_SEO' && l.included && l.rawScore != null)
    );
    hasGeo = Boolean(
      norm.geo?.dimensions?.length ||
      norm.geo?.attributionRewrites?.length ||
      ledger.some((l) => l.categoryKey === 'GEO' && l.included && l.rawScore != null)
    );
    hasAeo = Boolean(
      norm.aeo?.liveObservation?.isMeasured ||
      (norm.aeo?.totalSandboxQuestions != null && norm.aeo.totalSandboxQuestions > 0) ||
      (norm.aeo?.auditedQuestions && norm.aeo.auditedQuestions.length > 0) ||
      ledger.some((l) => l.categoryKey === 'AEO' && l.included && l.rawScore != null)
    );
    hasCro = Boolean(
      norm.conversion?.fiveSecondHook ||
      norm.conversion?.characterSafeCopy ||
      (norm.conversion?.formCount != null && norm.conversion.formCount > 0) ||
      (norm.conversion?.contradictions && norm.conversion.contradictions.length > 0) ||
      ledger.some((l) => l.categoryKey === 'UX_CONVERSION' && l.included && l.rawScore != null)
    );
    hasCompetitor = Boolean(
      norm.competitive?.isRealCompetitorDataAvailable ||
      ledger.some((l) => l.categoryKey === 'COMPETITIVE_INTELLIGENCE' && l.included && l.rawScore != null)
    );
  } else {
    const raw = report as ExecutiveReport;
    const catScores = raw.scores?.category_scores || {};
    hasSeo = Boolean(raw.crawl_manifest?.pages?.length || raw.page_reports?.length || raw.canonical_audit || raw.meta_rollup || catScores['TECHNICAL_SEO']?.score != null);
    hasGeo = Boolean(raw.geo_readiness?.extractability_score != null || raw.per_engine_geo || catScores['GEO']?.score != null);
    hasAeo = Boolean(raw.dynamic_sandbox_evaluations?.length || raw.ai_search_matrix?.length || catScores['AEO']?.score != null);
    hasCro = Boolean(raw.cro_audit || raw.form_audit || raw.visual_ux || catScores['UX_CONVERSION']?.score != null);
    hasCompetitor = Boolean(raw.competitor_bakeoff?.competitors?.length || raw.competitor_bakeoff?.evaluations?.length || raw.competitor_bakeoff?.competitor_domain || raw.competitor_seo_parity || catScores['COMPETITIVE_INTELLIGENCE']?.score != null);
  }

  const measuredCount = [hasSeo, hasGeo, hasAeo, hasCro, hasCompetitor].filter(Boolean).length;

  if (measuredCount >= 3) {
    return 'COMPLETE';
  }
  if (measuredCount === 2) {
    return 'HYBRID';
  }
  if (hasSeo && measuredCount === 1) return 'SEO';
  if (hasGeo && measuredCount === 1) return 'GEO';
  if (hasAeo && measuredCount === 1) return 'AEO';
  if (hasCro && measuredCount === 1) return 'CRO';
  if (hasCompetitor && measuredCount === 1) return 'COMPETITOR';

  return 'CUSTOM';
}

/**
 * Resolves the publication manifest based on report family and customizations.
 */
export function buildPublicationManifest(
  report: NormalizedReport,
  family: ReportFamily,
  customization: PublicationCustomization = {}
): PublicationManifest {
  const domain = report.meta.domain || 'audited-property.com';
  const brandName = report.meta.brandName || domain;
  const analysisId = report.meta.analysisId || 'analysis-000';
  const generatedAt = report.meta.generatedAt || new Date().toISOString();

  // Calculate evidence integrity categories
  const findings = report.appendices.findings || [];
  let observedCount = 0;
  let measuredCount = 0;
  let derivedCount = 0;
  let recommendedCount = report.appendices.patches.length;
  let unmeasuredCount = 0;

  findings.forEach((f) => {
    const hasDomRef = f.evidenceItems.some((e) => e.selector || e.snippet);
    if (hasDomRef) observedCount++;
    else derivedCount++;
  });

  report.scorecard.ledger.forEach((l) => {
    if (l.included && l.rawScore != null) measuredCount++;
    else if (!l.included || l.rawScore == null) unmeasuredCount++;
  });

  const titlesByFamily: Record<
    ReportFamily,
    {
      displayName: string;
      badge: string;
      defaultTitle: string;
      defaultSubtitle: string;
      purpose: string;
    }
  > = {
    COMPLETE: {
      displayName: 'Complete Website Intelligence Audit',
      badge: 'COMPLETE DIGITAL ASSET AUDIT DOSSIER',
      defaultTitle: 'Complete Website Intelligence Audit',
      defaultSubtitle: 'SEO · GEO · AEO · CRO · TECHNICAL HEALTH & ENTITY READINESS',
      purpose: `Comprehensive multi-discipline assurance evaluating search crawlability, generative AI extractability, live answer visibility, and conversion ergonomics for ${brandName}.`,
    },
    SEO: {
      displayName: 'Technical SEO & Organic Search Audit',
      badge: 'TECHNICAL SEO & SEARCH ARCHITECTURE AUDIT',
      defaultTitle: 'Technical SEO & Organic Search Audit',
      defaultSubtitle: 'CRAWL INFRASTRUCTURE · INDEXABILITY · CANONICAL ROUTING · CORE WEB VITALS',
      purpose: `Independent engineering audit examining technical indexability, response latencies, sitemaps, heading hierarchy, and search engine discoverability for ${domain}.`,
    },
    GEO: {
      displayName: 'Generative Engine Optimization (GEO) Assessment',
      badge: 'GENERATIVE ENGINE OPTIMIZATION AUDIT',
      defaultTitle: 'Generative Engine Optimization Assessment',
      defaultSubtitle: 'FIRST-PARTY EXTRACTABILITY · ENTITY CLARITY · LLM BOT DIRECTIVES',
      purpose: `In-depth analysis of first-party DOM extractability, /llms.txt bot accessibility, and machine-readable entity clarity for generative models.`,
    },
    AEO: {
      displayName: 'Answer Engine Optimization (AEO) Audit',
      badge: 'ANSWER ENGINE OPTIMIZATION AUDIT',
      defaultTitle: 'Answer Engine Optimization (AEO) Audit',
      defaultSubtitle: 'QUERY INTENT · PASSAGE EXTRACTABILITY · MULTI-MODEL CITATION BENCHMARK',
      purpose: `Systematic evaluation of question coverage, direct answer clarity, and live citation visibility across ChatGPT, Perplexity, Gemini, Claude, and Google AIO.`,
    },
    CRO: {
      displayName: 'Conversion Experience & CRO Audit',
      badge: 'CONVERSION EXPERIENCE & ERGONOMICS AUDIT',
      defaultTitle: 'Conversion Experience & CRO Audit',
      defaultSubtitle: 'VALUE PROPOSITION · CTA ERGONOMICS · USER FRICTION & ENGAGEMENT',
      purpose: `Empirical review of value proposition clarity, landing page hierarchy, call-to-action discoverability, and interaction friction across sampled URLs.`,
    },
    COMPETITOR: {
      displayName: 'Competitive Digital Visibility Analysis',
      badge: 'COMPETITIVE INTELLIGENCE & BENCHMARK',
      defaultTitle: 'Competitive Digital Visibility Analysis',
      defaultSubtitle: 'HEAD-TO-HEAD INQUIRY TESTING · PARITY MATRIX · MARKET GAP ANALYSIS',
      purpose: `Head-to-head empirical comparison of brand visibility, schema coverage, and commercial question presence against recorded industry competitors.`,
    },
    HYBRID: {
      displayName: 'Multi-Discipline Digital Audit',
      badge: 'INTEGRATED MULTI-DISCIPLINE AUDIT',
      defaultTitle: 'Multi-Discipline Digital Intelligence Audit',
      defaultSubtitle: 'CROSS-DISCIPLINE FINDINGS & UNIFIED REMEDIATION BLUEPRINT',
      purpose: `Focused multi-discipline audit combining applicable assessment chapters into a unified findings register and execution roadmap.`,
    },
    CUSTOM: {
      displayName: 'Digital Asset Intelligence Audit',
      badge: 'CUSTOM DIGITAL ASSET AUDIT DOSSIER',
      defaultTitle: 'Digital Asset Intelligence Audit',
      defaultSubtitle: 'EVIDENCE-GROUNDED TECHNICAL & STRATEGIC REVIEW',
      purpose: `Tailored digital asset assessment based on available audit telemetry and verified empirical evidence.`,
    },
  };

  const metaInfo = titlesByFamily[family];

  // Build chapter list based on report family
  const chapters: PublicationChapterDescriptor[] = [];

  // Executive Part (Always present)
  chapters.push({
    id: 'ch_brief',
    number: '00',
    part: 'PART I: EXECUTIVE DIAGNOSTIC & BASELINE',
    title: 'Executive Brief & Audit Snapshot',
    shortTitle: '00 / EXECUTIVE BRIEF',
    description: 'High-level synthesis, 4 core signals, 5-Pillar Scorecard, Tri-Perspective cognitive diagnosis, and visual diagnostic matrix.',
  });

  // Discipline chapters
  if (family === 'COMPLETE' || family === 'SEO' || family === 'HYBRID') {
    chapters.push({
      id: 'ch_seo',
      number: '01',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Discoverability & Technical SEO',
      shortTitle: '01 / TECHNICAL SEO',
      description: 'Crawl architecture, canonical host routing, 301 consolidation, TTFB latency curves, robots.txt directives, and XML sitemaps.',
    });
  }

  if (family === 'COMPLETE' || family === 'GEO' || family === 'HYBRID') {
    chapters.push({
      id: 'ch_geo',
      number: family === 'GEO' ? '01' : '02',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Generative Engine Optimization (GEO)',
      shortTitle: `${family === 'GEO' ? '01' : '02'} / GEO READINESS`,
      description: 'First-party DOM extractability, 8-dimension breakdown, /llms.txt AI-bot permissions, and entity attribution rewrites.',
    });
  }

  if (family === 'COMPLETE' || family === 'AEO' || family === 'HYBRID') {
    chapters.push({
      id: 'ch_aeo',
      number: family === 'AEO' ? '01' : '03',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Answer Engine Visibility (AEO) & AI Citations',
      shortTitle: 'AEO & AI CITATIONS',
      description: 'Live visibility across ChatGPT, Perplexity, Google AIO, Claude & Gemini. Dynamic question digest & Re-Query uplift delta.',
    });
  }

  if (family === 'COMPLETE' || family === 'COMPETITOR' || (family === 'HYBRID' && report.competitive.isRealCompetitorDataAvailable)) {
    chapters.push({
      id: 'ch_competitive',
      number: family === 'COMPETITOR' ? '01' : '04',
      part: 'PART II: AUDIT CHAPTERS',
      title: report.competitive.isRealCompetitorDataAvailable
        ? 'Competitive Intelligence & Knowledge Graph'
        : 'Knowledge Graph & Entity Readiness',
      shortTitle: 'COMPETITIVE INTELLIGENCE',
      description: report.competitive.isRealCompetitorDataAvailable
        ? 'Recorded competitor bake-off, schema types extracted from the sample, and social meta presence.'
        : 'Schema types extracted from the sample and unmeasured competitor benchmark notice.',
    });
  }

  if (family === 'COMPLETE' || family === 'CRO' || family === 'HYBRID') {
    chapters.push({
      id: 'ch_conversion',
      number: family === 'CRO' ? '01' : '05',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Conversion Ergonomics & Production Copy',
      shortTitle: 'CONVERSION ERGONOMICS',
      description: 'Crawled value-proposition copy, CTA hierarchy, form screening, and character-safe production copy recommendations.',
    });
  }

  if (family === 'COMPLETE' || family === 'SEO') {
    chapters.push({
      id: 'ch_page_by_page',
      number: family === 'SEO' ? '02' : '06',
      part: 'PART II: AUDIT CHAPTERS',
      title: 'Page-by-Page Audit Review',
      shortTitle: 'PAGE-BY-PAGE REVIEW',
      description: 'Sampled URL inventory: SERP metadata, H1 outlines, and copy recommendations for the analyzed URLs.',
    });
  }

  // Strategic Remediation Part
  chapters.push({
    id: 'ch_roadmap',
    number: '07',
    part: 'PART III: REMEDIATION & GOVERNANCE',
    title: 'Strategic Priorities & 90-Day Implementation Roadmap',
    shortTitle: '07 / 90-DAY ROADMAP',
    description: 'Executive Top-10 Action Plan with effort/impact calculations, NOW / NEXT / ONGOING roadmap, and commercial financial model.',
  });

  // Master Audit Index (if complete)
  if (family === 'COMPLETE') {
    chapters.push({
      id: 'ch_audit_index',
      number: '07b',
      part: 'PART III: REMEDIATION & GOVERNANCE',
      title: 'Master Audit Index & Dimension Coverage',
      shortTitle: 'MASTER AUDIT INDEX',
      description: 'All 55 sections and appendices A–O. Each categorized as measured, inferred, unavailable, not tested, or not applicable.',
    });
  }

  chapters.push({
    id: 'ch_methodology',
    number: '08',
    part: 'PART III: REMEDIATION & GOVERNANCE',
    title: 'Research Methodology & Sampling Parameters',
    shortTitle: '08 / METHODOLOGY',
    description: 'Audit scope, crawl depth boundaries, multi-engine testing protocol, confidence algorithms, and known operational limitations.',
  });

  // Appendices Part
  if (customization.includeAppendices !== false) {
    chapters.push({
      id: 'ch_appendix',
      number: '09',
      part: 'PART IV: APPENDICES & TECHNICAL REGISTERS',
      title: 'Institutional Findings Register & Evidence Ledger',
      shortTitle: '09 / EVIDENCE REGISTERS',
      description: 'Exhaustive verified defect register, production code patches with file paths, cryptographic verification proofs, and SHA-256 AST ledger.',
      isAppendix: true,
    });
  }

  // Renumber body chapters cleanly in sequence
  let bodyCounter = 1;
  chapters.forEach((ch) => {
    if (ch.id === 'ch_brief') {
      ch.number = '00';
    } else if (ch.isAppendix) {
      ch.number = 'APP';
    } else if (ch.id === 'ch_audit_index') {
      ch.number = 'IDX';
    } else {
      ch.number = String(bodyCounter).padStart(2, '0');
      bodyCounter++;
    }
  });

  return {
    family,
    familyDisplayName: metaInfo.displayName,
    seriesLabel: 'DRISTIK // WEBSITE INTELLIGENCE / DIGITAL AUDIT SERIES',
    reportTypeBadge: metaInfo.badge,
    title: customization.titleOverride || metaInfo.defaultTitle,
    subtitle: customization.subtitleOverride || metaInfo.defaultSubtitle,
    purposeSummary: metaInfo.purpose,
    classification: customization.classificationOverride || 'STRICTLY CONFIDENTIAL // C-SUITE DOSSIER',
    reportingPeriod: 'Observed audit crawl window',
    auditDate: generatedAt.slice(0, 10),
    reportRef: analysisId.slice(0, 12).toUpperCase(),
    chapters,
    includeToc: customization.includeToc !== false,
    includeFrontMatter: customization.includeFrontMatter !== false,
    includeAppendices: customization.includeAppendices !== false,
    exhaustiveMode: Boolean(customization.exhaustiveMode),
    evidenceStats: {
      observedCount,
      measuredCount,
      derivedCount,
      recommendedCount,
      unmeasuredCount,
    },
  };
}
