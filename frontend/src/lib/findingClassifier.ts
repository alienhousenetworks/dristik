import { Finding, EvidenceClass } from '../types';

export type FindingNature =
  | 'OBSERVED'
  | 'EXTERNALLY_VERIFIED'
  | 'MODEL_INFERRED'
  | 'HYPOTHESIS'
  | 'RECOMMENDATION'
  | 'VERIFIED_DOM_FACT' // backwards compat
  | 'SINGLE_SOURCE_UNVERIFIED' // backwards compat
  | 'LLM_INFERENCE'; // backwards compat

export interface FindingClassification {
  nature: FindingNature;
  evidenceClass: EvidenceClass;
  evidenceSubtype: string;
  badgeLabel: string;
  badgeClass: string;
  tagLabel: string;
  epistemicLevel: string;
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
 * Enforces Dristik's First-Class Evidence Taxonomy:
 * 1. OBSERVED: Directly measured (DOM, HTTP, AST, Headers, Screenshot, Accessibility tree, Schema)
 * 2. EXTERNALLY VERIFIED: Confirmed through external source (Search, Directory, Profile, Registry, GSC, Analytics)
 * 3. MODEL-INFERRED: LLM interpretation of observed evidence
 * 4. HYPOTHESIS: Potential issue requiring verification (Single-source unverified, working hypothesis)
 * 5. RECOMMENDATION: Proposed remediation
 */
export function classifyFindingNature(finding: Finding): FindingClassification {
  const descText = `${finding.description || ''} ${finding.finding || ''} ${finding.title || ''}`;
  const descLower = descText.toLowerCase();

  // 1. HYPOTHESIS / SINGLE-SOURCE UNVERIFIED
  const isHypothesis =
    finding.evidence_class === 'HYPOTHESIS' ||
    finding.source_integrity_label === 'SINGLE_SOURCE_UNVERIFIED' ||
    descText.includes('SINGLE_SOURCE_UNVERIFIED') ||
    descLower.includes('working hypothesis') ||
    descLower.includes('unverified anomaly') ||
    descLower.includes('confidence capped at medium') ||
    (finding.confidence_rubric as any) === 'MEDIUM';

  if (isHypothesis) {
    const subtype = finding.evidence_subtype || 'SINGLE_SOURCE_UNVERIFIED';
    return {
      nature: 'HYPOTHESIS',
      evidenceClass: 'HYPOTHESIS',
      evidenceSubtype: subtype,
      badgeLabel: '⚠️ HYPOTHESIS · REQUIRES VERIFICATION',
      badgeClass:
        'bg-amber-100 text-amber-950 border-amber-400 dark:bg-amber-950/70 dark:text-amber-200 dark:border-amber-700 font-mono font-black tracking-wide',
      tagLabel: 'Working Hypothesis [Single-Source]',
      epistemicLevel: 'Level 4 · Working Hypothesis / Single-Source',
      canonicalConfidence: 'MEDIUM',
      confidenceClass: 'text-amber-700 dark:text-amber-400 font-semibold',
      observationHeading: '⚠️ Working Hypothesis (Single-Source Observation)',
      observationHelp:
        'Observed during single crawl without multi-source confirmation. Flagged as a working hypothesis requiring verification before engineering deployment.',
      recommendationHeading: '🛠️ Verification & Engineering Remediation',
      recommendationHelp: 'Validate against live server headers or external DNS/API endpoints before deploy.',
      containerClass:
        'border-l-4 border-l-amber-500 bg-amber-50/30 dark:bg-amber-950/20 border-amber-300 dark:border-amber-900/60 shadow-xs',
      isCheckable: true,
      checkMethod: 'Corroborate via Browser DevTools & External Endpoints',
    };
  }

  // 2. EXTERNALLY VERIFIED
  const hasExternalEvidence =
    finding.evidence_class === 'EXTERNALLY_VERIFIED' ||
    finding.source_integrity_label === 'CORROBORATED' ||
    Boolean(
      finding.evidence?.some(
        (ev) => ev.type === 'external_ground_truth' || ev.evidence_id?.startsWith('ext_')
      )
    ) ||
    descLower.includes('google search console') ||
    descLower.includes('gsc') ||
    descLower.includes('whois') ||
    descLower.includes('registry');

  if (hasExternalEvidence) {
    const subtype =
      finding.evidence_subtype ||
      (descLower.includes('gsc') || descLower.includes('search console')
        ? 'GSC'
        : descLower.includes('ssl') || descLower.includes('cert')
        ? 'CERTIFICATE_REGISTRY'
        : 'SEARCH');

    return {
      nature: 'EXTERNALLY_VERIFIED',
      evidenceClass: 'EXTERNALLY_VERIFIED',
      evidenceSubtype: subtype,
      badgeLabel: `🌐 EXTERNALLY VERIFIED [${subtype}]`,
      badgeClass:
        'bg-sky-100 text-sky-950 border-sky-400 dark:bg-sky-950/70 dark:text-sky-200 dark:border-sky-700 font-mono font-black tracking-wide',
      tagLabel: `External Source [${subtype}]`,
      epistemicLevel: 'Level 2 · Corroborated External Signal',
      canonicalConfidence: 'CERTAIN',
      confidenceClass: 'text-sky-700 dark:text-sky-400 font-semibold',
      observationHeading: '🌐 Corroborated External Record',
      observationHelp:
        'Confirmed through third-party authoritative APIs (Google Search Console, DNS/Certificate Registries, Business Directories, or Live Search Queries).',
      recommendationHeading: '🛠️ Authoritative System Action',
      recommendationHelp: 'Actionable adjustment to third-party integrations, search console, or DNS records.',
      containerClass:
        'border-l-4 border-l-sky-600 bg-sky-50/20 dark:bg-sky-950/15 border-sky-300 dark:border-sky-900/60 shadow-xs',
      isCheckable: true,
      checkMethod: 'Cross-reference External API / Registry',
    };
  }

  // 3. OBSERVED (Directly Measured: DOM, HTTP, AST, Headers, Screenshot, Accessibility tree, Schema)
  const hasSelectors = Boolean(
    finding.evidence &&
      finding.evidence.some((ev) => Boolean(ev.selector || ev.snippet || ev.value || ev.element))
  );

  const isTechnicalCategory =
    finding.category === 'TECHNICAL_SEO' ||
    finding.category === 'SCHEMA' ||
    finding.category === 'ON_PAGE_SEO';

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

  const isDirectlyObserved =
    finding.evidence_class === 'OBSERVED' ||
    hasSelectors ||
    (isTechnicalCategory && Boolean(finding.evidence?.length)) ||
    isExplicitDOMDefect;

  if (isDirectlyObserved) {
    let subtype = finding.evidence_subtype || 'DOM';
    if (descLower.includes('schema') || descLower.includes('json-ld') || finding.category === 'SCHEMA') {
      subtype = 'SCHEMA';
    } else if (descLower.includes('http') || descLower.includes('status code') || descLower.includes('ttfb')) {
      subtype = 'HTTP';
    } else if (descLower.includes('header')) {
      subtype = 'HEADERS';
    } else if (descLower.includes('accessibility') || descLower.includes('aria')) {
      subtype = 'ACCESSIBILITY_TREE';
    }

    const conf =
      finding.confidence_rubric === 'CERTAIN' || finding.confidence_rubric === 'LIKELY'
        ? finding.confidence_rubric
        : 'CERTAIN';

    return {
      nature: 'OBSERVED',
      evidenceClass: 'OBSERVED',
      evidenceSubtype: subtype,
      badgeLabel: `🔬 OBSERVED · DIRECTLY MEASURED [${subtype}]`,
      badgeClass:
        'bg-emerald-100 text-emerald-950 border-emerald-400 dark:bg-emerald-950/70 dark:text-emerald-200 dark:border-emerald-700 font-mono font-black tracking-wide',
      tagLabel: `Directly Measured [${subtype}]`,
      epistemicLevel: 'Level 1 · Deterministic Ground Truth',
      canonicalConfidence: conf,
      confidenceClass: 'text-emerald-700 dark:text-emerald-400 font-semibold',
      observationHeading: '🔬 Directly Measured Observation (Empirical Ground Truth)',
      observationHelp:
        'Deterministic finding verified directly from DOM syntax trees, HTTP response codes, or network timings. 100% checkable via browser DevTools or curl.',
      recommendationHeading: '🛠️ Deterministic Engineering Remediation',
      recommendationHelp: 'Direct code-level fix to resolve the verified DOM or infrastructure defect.',
      containerClass:
        'border-l-4 border-l-emerald-600 bg-emerald-50/15 dark:bg-emerald-950/15 border-emerald-300 dark:border-emerald-900/60 shadow-xs',
      isCheckable: true,
      checkMethod: 'Inspect DOM / HTTP Headers / Chrome DevTools',
    };
  }

  // 4. RECOMMENDATION (Explicit code patch without standalone observed issue)
  if (finding.evidence_class === 'RECOMMENDATION' || (finding.code_patch && descLower.startsWith('recommendation'))) {
    return {
      nature: 'RECOMMENDATION',
      evidenceClass: 'RECOMMENDATION',
      evidenceSubtype: 'CODE_PATCH',
      badgeLabel: '🛠️ RECOMMENDATION · REMEDIATION DIRECTIVE',
      badgeClass:
        'bg-indigo-100 text-indigo-950 border-indigo-400 dark:bg-indigo-950/70 dark:text-indigo-200 dark:border-indigo-700 font-mono font-black tracking-wide',
      tagLabel: 'Proposed Remediation [Patch]',
      epistemicLevel: 'Level 5 · Actionable Engineering Intervention',
      canonicalConfidence: 'LIKELY',
      confidenceClass: 'text-indigo-700 dark:text-indigo-400 font-semibold',
      observationHeading: '🛠️ Actionable Remediation Directive',
      observationHelp: 'Concrete engineering directive or code patch proposing a remediation to improve site health.',
      recommendationHeading: '🛠️ Implementation Guide',
      recommendationHelp: 'Code diff or configuration patch ready for staging review.',
      containerClass:
        'border-l-4 border-l-indigo-600 bg-indigo-50/20 dark:bg-indigo-950/15 border-indigo-300 dark:border-indigo-900/60 shadow-xs',
      isCheckable: true,
      checkMethod: 'Run Automated Patch Validation Loop',
    };
  }

  // 5. MODEL-INFERRED (LLM Interpretation of observed evidence)
  const infConf =
    finding.confidence_rubric === 'CERTAIN' ||
    finding.confidence_rubric === 'LIKELY' ||
    finding.confidence_rubric === 'GUESSING'
      ? finding.confidence_rubric
      : 'LIKELY';

  return {
    nature: 'MODEL_INFERRED',
    evidenceClass: 'MODEL_INFERRED',
    evidenceSubtype: 'SEMANTIC_SYNTHESIS',
    badgeLabel: '💡 MODEL-INFERRED [LLM INTERPRETATION]',
    badgeClass:
      'bg-purple-100 text-purple-950 border-purple-400 dark:bg-purple-950/70 dark:text-purple-200 dark:border-purple-700 font-mono font-black tracking-wide',
    tagLabel: 'Cognitive Model Deduction',
    epistemicLevel: 'Level 3 · Cognitive Model Deduction',
    canonicalConfidence: infConf,
    confidenceClass: 'text-purple-700 dark:text-purple-400 font-semibold',
    observationHeading: '💡 Model-Inferred Deduction (LLM Reasoning)',
    observationHelp:
      'Heuristic analysis generated by cognitive agents based on market psychology and copy clarity. This is an advisory deduction, not a raw DOM measurement.',
    recommendationHeading: '🧠 Strategic AI Advisory Directive',
    recommendationHelp: 'Strategic and commercial guidance synthesized by LLM reasoning.',
    containerClass:
      'border-l-4 border-l-purple-500 bg-purple-50/25 dark:bg-purple-950/15 border-purple-300 dark:border-purple-900/60 shadow-xs',
    isCheckable: false,
    checkMethod: 'Advisory Review / User Experience Testing',
  };
}
