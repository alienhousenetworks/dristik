import { Finding } from '../types';

export type FindingNature = 'VERIFIED_DOM_FACT' | 'SINGLE_SOURCE_UNVERIFIED' | 'LLM_INFERENCE';

export interface FindingClassification {
  nature: FindingNature;
  badgeLabel: string;
  badgeClass: string;
  tagLabel: string;
  canonicalConfidence: 'CERTAIN' | 'LIKELY' | 'MEDIUM' | 'GUESSING';
  confidenceClass: string;
  observationHeading: string;
  observationHelp: string;
  recommendationHeading: string;
  recommendationHelp: string;
  containerClass: string;
  isCheckable: boolean;
  checkMethod: string;
}

/**
 * Enforces a single canonical confidence and provenance taxonomy across all finding cards.
 * Prevents drift between badge labels, confidence pills, and narrative disclaimers.
 */
export function classifyFindingNature(finding: Finding): FindingClassification {
  const descText = `${finding.description || ''} ${finding.finding || ''} ${finding.title || ''}`;
  const descLower = descText.toLowerCase();

  // 1. Check for single-source unverified status or confidence capped at MEDIUM
  const isSingleSource =
    finding.source_integrity_label === 'SINGLE_SOURCE_UNVERIFIED' ||
    descText.includes('SINGLE_SOURCE_UNVERIFIED') ||
    descLower.includes('confidence capped at medium') ||
    (finding.confidence_rubric as any) === 'MEDIUM';

  if (isSingleSource) {
    return {
      nature: 'SINGLE_SOURCE_UNVERIFIED',
      badgeLabel: '⚠️ SINGLE-SOURCE UNVERIFIED',
      badgeClass: 'bg-amber-50 text-amber-900 border-amber-300 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-800 font-mono font-bold',
      tagLabel: 'Single-Source Unverified',
      canonicalConfidence: 'MEDIUM',
      confidenceClass: 'text-amber-700 dark:text-amber-400 font-semibold',
      observationHeading: '⚠️ Single-Source Unverified Observation',
      observationHelp: 'Observed from single crawl capture without external corroboration. Confidence is capped at MEDIUM per the non-speculative data constitution.',
      recommendationHeading: '🛠️ Verification & Engineering Remediation',
      recommendationHelp: 'Validate against live server headers or external DNS/API endpoints before deploy.',
      containerClass: 'border-l-4 border-l-amber-500 bg-amber-50/20 dark:bg-amber-950/10 border-amber-200 dark:border-amber-900/40',
      isCheckable: true,
      checkMethod: 'Verify via Browser DevTools & External Endpoints',
    };
  }

  const hasSelectors = Boolean(
    finding.evidence &&
    finding.evidence.some((ev) => Boolean(ev.selector || ev.snippet || ev.value))
  );

  const isTechnicalCategory =
    finding.category === 'TECHNICAL_SEO' ||
    finding.category === 'SCHEMA' ||
    finding.category === 'AI_SEARCH';

  const isExplicitDOMDefect =
    descLower.includes('sitemap') ||
    descLower.includes('robots.txt') ||
    descLower.includes('http') ||
    descLower.includes('404') ||
    descLower.includes('status code') ||
    descLower.includes('latency') ||
    descLower.includes('ttfb') ||
    descLower.includes('h1') ||
    descLower.includes('meta description') ||
    descLower.includes('viewport') ||
    descLower.includes('canonical') ||
    descLower.includes('schema') ||
    descLower.includes('json-ld') ||
    descLower.includes('alt attribute') ||
    descLower.includes('ssl') ||
    descLower.includes('https');

  const isPureGuessing =
    finding.confidence_rubric === 'GUESSING' ||
    finding.held_from_executive === true;

  // A finding is a VERIFIED_DOM_FACT if it has concrete DOM evidence or represents an empirical technical defect,
  // is corroborated or verified, and is not an ungrounded guess.
  const isVerifiedFact =
    !isPureGuessing &&
    (finding.source_integrity_label === 'CORROBORATED' ||
      hasSelectors ||
      isExplicitDOMDefect ||
      (isTechnicalCategory && Boolean(finding.evidence?.length)));

  if (isVerifiedFact) {
    const conf = (finding.confidence_rubric === 'CERTAIN' || finding.confidence_rubric === 'LIKELY')
      ? finding.confidence_rubric
      : 'CERTAIN';

    return {
      nature: 'VERIFIED_DOM_FACT',
      badgeLabel: '🔬 VERIFIED DOM FACT',
      badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800 font-mono font-bold',
      tagLabel: 'DOM / Network Fact',
      canonicalConfidence: conf,
      confidenceClass: 'text-emerald-700 dark:text-emerald-400 font-semibold',
      observationHeading: '🔬 Verified Empirical DOM Observation',
      observationHelp: 'Deterministic finding verified directly from DOM syntax trees, HTTP response codes, or network timings. 100% checkable via browser DevTools or curl.',
      recommendationHeading: '🛠️ Deterministic Engineering Remediation',
      recommendationHelp: 'Direct code-level fix to resolve the verified DOM defect.',
      containerClass: 'border-l-4 border-l-emerald-600 bg-white dark:bg-ink-900 border-slate-300 dark:border-ink-700',
      isCheckable: true,
      checkMethod: 'Inspect DOM / HTTP Headers / Chrome DevTools',
    };
  }

  const infConf = (finding.confidence_rubric === 'CERTAIN' || finding.confidence_rubric === 'LIKELY' || finding.confidence_rubric === 'GUESSING')
    ? finding.confidence_rubric
    : 'LIKELY';

  return {
    nature: 'LLM_INFERENCE',
    badgeLabel: '💡 COGNITIVE MODEL INFERENCE',
    badgeClass: 'bg-purple-50 text-purple-800 border-purple-300 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800 font-mono font-bold',
    tagLabel: 'Cognitive Inference',
    canonicalConfidence: infConf,
    confidenceClass: 'text-purple-700 dark:text-purple-400 font-semibold',
    observationHeading: '💡 Model-Generated Narrative Deduction',
    observationHelp: 'Heuristic analysis generated by cognitive agents based on market psychology and copy clarity. This is an advisory hypothesis, not a raw DOM measurement.',
    recommendationHeading: '🧠 Strategic AI Advisory Directive',
    recommendationHelp: 'Strategic and commercial guidance synthesized by LLM reasoning.',
    containerClass: 'border-l-4 border-l-purple-500 bg-purple-50/20 dark:bg-purple-950/10 border-purple-200 dark:border-purple-900/40',
    isCheckable: false,
    checkMethod: 'Advisory Review / User Experience Testing',
  };
}
