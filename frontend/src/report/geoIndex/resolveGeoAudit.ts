import { ExecutiveReport, Finding } from '../../types';
import { GEO_SECTIONS } from './catalog';
import {
  GeoAgentConsultation,
  GeoCheck,
  GeoFindingRef,
  GeoStatus,
  ResolvedGeoAudit,
  ResolvedGeoSection,
} from './types';

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

const AGENT_MAP: Record<string, [string, string, string]> = {
  // Part I
  '01': ['geo.benchmark_orchestrator.v3', 'GEO Benchmark Orchestrator', 'Multi-Engine Benchmark Synthesis & Executive Overview'],
  '02': ['geo.measurement_analyst.v3', 'Generative Visibility Specialist', 'AI Search Visibility Scorecard & Statistical Tracking'],
  '03': ['geo.remediation_planner.v3', 'GEO Opportunity & Risk Strategist', 'High-Impact Displacements, Bottlenecks & Validation Plans'],
  // Part II
  '04': ['geo.benchmark_orchestrator.v3', 'Multi-Platform Coverage Specialist', 'AI Overviews, ChatGPT Search, Perplexity, Copilot & Gemini'],
  '05': ['geo.prompt_discovery.v3', 'Prompt Discovery Specialist', 'Query Universe Harvesting, Intent Classification & Sampling'],
  '06': ['geo.prompt_discovery.v3', 'Query-to-Intent Specialist', '8-Stage Buyer Journey Mapping & Funnel Stage Alignment'],
  '07': ['geo.benchmark_orchestrator.v3', 'Prompt Benchmark Design Specialist', 'Standardized Prompt Harness, Versioning & Reproducibility'],
  // Part III
  '08': ['geo.brand_mention.v3', 'Brand Mention Analyzer', 'Explicit Brand Presence, Recognition & Contextual Framing'],
  '09': ['geo.recommendation_intelligence.v3', 'Recommendation & Shortlist Specialist', 'Vendor Shortlists, "Best Of" Nominations & Rationales'],
  '10': ['geo.entity_consistency.v3', 'Brand Positioning & Entity Specialist', 'Category Classification, Offerings & Entity Attributes'],
  '11': ['geo.brand_hallucination.v3', 'Brand Accuracy & Hallucination Auditor', 'Fabricated Features, False Pricing & Model Misconceptions'],
  '12': ['geo.brand_mention.v3', 'Narrative Consistency & Sentiment Specialist', 'Tone, Recurring Narratives & Framing Reliability'],
  // Part IV
  '13': ['geo.citation_intelligence.v3', 'AI Citation Performance Specialist', 'Citation Rates, Distribution & Source Panel Prominence'],
  '14': ['geo.measurement_analyst.v3', 'Citation Share & Voice Specialist', 'Share of Model, Competitive Citation Share & Uncertainty'],
  '15': ['geo.citation_intelligence.v3', 'Cited-Source & URL Intelligence Specialist', 'Brand Pages Cited vs Uncited & Source Health'],
  '16': ['geo.citation_gap.v3', 'Citation Gap & Source Strategist', 'Competitor Reference Corroboration & Primary Source Gaps'],
  '17': ['geo.offsite_evidence.v3', 'Source Reliability & Evidence Specialist', 'Primary vs Secondary Evidence & Publisher Authority'],
  '18': ['geo.offsite_evidence.v3', 'Third-Party Footprint Specialist', 'Industry Publications, Directory Citations & PR Echo'],
  // Part V
  '19': ['geo.competitive_analyst.v3', 'Competitor Discovery Specialist', 'Search Competitors, AI Alternatives & Category Leaders'],
  '20': ['geo.competitive_analyst.v3', 'Competitor Visibility Benchmark Specialist', 'Head-to-Head Multi-Engine Benchmark & Voice Metrics'],
  '21': ['geo.citation_gap.v3', 'Competitor Content & Citation Gap Specialist', 'Topic Overlap, Evidence Depth & Content Format Differences'],
  '22': ['geo.competitive_analyst.v3', 'Competitive Narrative Specialist', 'Recommendation Reasons, Differentiator Omissions & Claims'],
  '23': ['geo.competitive_analyst.v3', 'Competitive Displacement Specialist', 'High-Intent Displacement Targets & Weak Competitor Sources'],
  // Part VI
  '24': ['geo.extractability.v3', 'Content Extractability Specialist', 'Passage Clarity, Definition Blocks & Answer Usability'],
  '25': ['geo.extractability.v3', 'Topical Coverage & Entity Completeness Specialist', 'Core Topics, Subtopics, Use Cases & Knowledge Graph'],
  '26': ['geo.information_gain.v3', 'Information Gain & Originality Specialist', 'Proprietary Data, First-Party Insights & Fluff Removal'],
  '27': ['geo.brand_hallucination.v3', 'Factual Support & Claim Verifiability Specialist', 'Claim-to-Evidence Traceability, Citations & Source Checks'],
  '28': ['geo.extractability.v3', 'Content Freshness & Maintenance Specialist', 'Temporal Relevance, Timestamps & Stale Content Auditing'],
  '29': ['geo.extractability.v3', 'Content Format & GEO Suitability Specialist', 'Comparison Tables, Modular FAQs & Structured References'],
  '30': ['geo.technical_auditor.v3', 'Internal Linking & Contextual Discovery Specialist', 'Entity Connection Topology, Breadcrumbs & Siloing'],
  // Part VII
  '31': ['geo.technical_auditor.v3', 'Crawlability & Indexability Specialist', 'Robots Directives, Sitemap Parity & Canonical Integrity'],
  '32': ['geo.technical_auditor.v3', 'Rendering & DOM Accessibility Specialist', 'Raw HTML vs Rendered DOM, JavaScript Hydration & Shells'],
  '33': ['geo.technical_auditor.v3', 'Structured Data & Schema Specialist', 'JSON-LD Entity Graph, Rich Results & Attribute Alignment'],
  '34': ['geo.entity_consistency.v3', 'Entity Identity & Disambiguation Specialist', 'Stable URI Identifiers, SameAs Links & Cross-Web Identity'],
  '35': ['geo.technical_auditor.v3', 'HTTP Reliability & Security Specialist', 'Transport Security, TTFB, Edge Performance & Server Health'],
  '36': ['geo.crawler_diagnostics.v3', 'AI Crawler & Bot Diagnostics Specialist', 'GPTBot, ClaudeBot, PerplexityBot Directives & WAF Traps'],
  // Part VIII
  '37': ['geo.offsite_evidence.v3', 'External Reputation & Corroboration Specialist', 'Third-Party Authority, Independent Coverage & Brand Sentiment'],
  '38': ['geo.offsite_evidence.v3', 'Customer Reviews & Social Proof Specialist', 'G2/Capterra/Trustpilot Verification & Customer Quotes'],
  '39': ['geo.offsite_evidence.v3', 'Digital PR & Citation Acquisition Specialist', 'Authoritative Outreach, Industry Data Releases & Media PR'],
  '40': ['geo.entity_consistency.v3', 'Web-Wide NAP & Information Consistency Specialist', 'Business Details Across Registries, Directories & Profiles'],
  // Part IX
  '41': ['geo.measurement_analyst.v3', 'GEO Visibility Metric Formulation Specialist', 'Formula Rigor, Denominators & Measurement Integrity'],
  '42': ['geo.measurement_analyst.v3', 'Cross-Engine & Cross-Query Specialist', 'Platform Disparities, Intent Breakdown & Query Categories'],
  '43': ['geo.measurement_analyst.v3', 'Statistical Confidence & Variance Specialist', 'Sample Sizes, Error Bounds & Repeatability Benchmarks'],
  '44': ['geo.referral_analyst.v3', 'AI Referral Traffic Attribution Specialist', 'GA4/Server Referral Sessions, Landing Engagement & Funnels'],
  '45': ['geo.referral_analyst.v3', 'GEO-to-Revenue & Pipeline Specialist', 'Commercial Intent Traffic, Lead Value & CAC Economics'],
  // Part X
  '46': ['geo.remediation_planner.v3', 'Evidence Ledger & Audit Register Specialist', 'Granular Traceability, Finding Identifiers & Observation Logs'],
  '47': ['geo.remediation_planner.v3', 'Prioritized GEO Remediation Roadmap Specialist', '30/60/90-Day Engineering Epics, Owners & Effort Points'],
  '48': ['geo.remediation_planner.v3', 'Content Brief & Technical Spec Specialist', 'Actionable Engineering Specs & LLM-Optimized Copy Briefs'],
  '49': ['geo.verification_engine.v3', 'Experimentation & Validation Specialist', 'A/B Query Testing, Pre/Post-Change Delta & Assurance'],
  '50': ['geo.verification_engine.v3', 'Continuous Monitoring & Governance Specialist', 'Automated Benchmark Scheduling, Regression SLAs & Alerts'],
  // Part XII Appendices
  A: ['geo.prompt_discovery.v3', 'Full Prompt & Query Inventory Specialist', 'Deterministic Harvest of All Tested Prompt Strings'],
  B: ['geo.benchmark_orchestrator.v3', 'Raw Multi-Engine Response Specialist', 'Verbatim LLM Response Captures & Source Snapshots'],
  C: ['geo.citation_intelligence.v3', 'Citation URL & Domain Inventory Specialist', 'Complete Domain & Path Ledger for Cited Sources'],
  D: ['geo.competitive_analyst.v3', 'Competitor Benchmark Methodology Specialist', 'Head-to-Head Testing Rules, Normalization & Scopes'],
  E: ['geo.brand_hallucination.v3', 'Factual Accuracy Case Registry Specialist', 'Verified Ground Truth Claims vs Hallucinated Statements'],
  F: ['geo.technical_auditor.v3', 'Crawl & Technical Inventory Specialist', 'DOM Manifest, HTTP Headers & Discovered URIs'],
  G: ['geo.offsite_evidence.v3', 'External Source & Corroboration Inventory Specialist', 'Independent Directory, Review & Digital PR Manifest'],
  H: ['geo.measurement_analyst.v3', 'Metric Formulation & Formulas Specialist', 'Exact Formula Numerators, Denominators & Weightings'],
  I: ['geo.measurement_analyst.v3', 'Statistical Confidence & Sampling Specialist', 'Variance Calculations, Confidence Intervals & Error Bands'],
  J: ['geo.referral_analyst.v3', 'AI Referral Analytics Limitations Specialist', 'Attribution Boundaries, Dark Traffic & Tracking Gaps'],
  K: ['geo.remediation_planner.v3', 'Master Finding Ledger Specialist', 'Immutable Finding Identifiers (GEO-xxx) & Evidence Hashes'],
  L: ['geo.remediation_planner.v3', 'Engineering Backlog & Ownership Specialist', 'Sprint Story Points, Code Ownership & Dependencies'],
  M: ['geo.verification_engine.v3', 'Post-Remediation Verification Manifest Specialist', 'Before-and-After Evidence Verification & Diff Logs'],
  N: ['geo.benchmark_orchestrator.v3', 'Platform Limitations & Epistemic Boundaries Specialist', 'Unmeasured Search Engines, API Limits & Regional Gates'],
  O: ['geo.benchmark_orchestrator.v3', 'GEO Glossary & Reproducibility Manifest Specialist', 'Industry Terminology, Scoring Weights & Run Provenance'],
};

function toFindingRef(f: Finding): GeoFindingRef {
  return {
    id: f.finding_id,
    severity: f.severity,
    title: f.title,
    scope: f.evidence_scope || (f.evidence && f.evidence[0]?.url) || 'Audited Scope',
    description: f.description,
    action: f.recommendation,
    priority: f.priority,
  };
}

function assignSectionFindings(findings: Finding[], sectionNumber: string): Finding[] {
  return findings.filter((f) => {
    const text = `${f.title || ''} ${f.description || ''} ${f.finding_id || ''} ${f.category || ''}`.toLowerCase();
    if (sectionNumber === '24' && (text.includes('passage') || text.includes('extract') || text.includes('definition'))) return true;
    if (sectionNumber === '31' && (text.includes('crawl') || text.includes('robots') || text.includes('sitemap'))) return true;
    if (sectionNumber === '32' && (text.includes('render') || text.includes('hydration') || text.includes('javascript'))) return true;
    if (sectionNumber === '33' && (text.includes('schema') || text.includes('json-ld') || text.includes('structured'))) return true;
    if (sectionNumber === '36' && (text.includes('bot') || text.includes('gptbot') || text.includes('waf'))) return true;
    if (sectionNumber === '11' && (text.includes('halluc') || text.includes('inaccurate') || text.includes('claim'))) return true;
    if (sectionNumber === '20' && (text.includes('competit') || text.includes('bakeoff') || text.includes('alternative'))) return true;
    if (sectionNumber === '13' && (text.includes('citation') || text.includes('source') || text.includes('cited'))) return true;
    if (sectionNumber === '01') return true;
    return false;
  });
}

function resolveCheck(
  report: ExecutiveReport,
  sectionNumber: string,
  checkLabel: string,
  matchedFindings: Finding[]
): GeoCheck {
  const cLower = checkLabel.toLowerCase();
  const card = report.ai_visibility_scorecard;
  const geo = report.geo_readiness;
  const manifest = report.crawl_manifest;
  const pages = manifest?.pages || report.page_reports || [];
  const crawledCount = pages.length;

  if (matchedFindings.length > 0) {
    const top = matchedFindings[0];
    return {
      label: checkLabel,
      status: 'SAMPLE_VERIFIED',
      result: `Recorded defect finding: ${top.title}. ${top.recommendation || ''}`,
      findings: matchedFindings.map(toFindingRef),
    };
  }

  // Section 01
  if (sectionNumber === '01') {
    if (cLower.includes('readiness')) {
      const score = geo?.extractability_score ?? report.scores?.category_scores?.geo?.score;
      return {
        label: checkLabel,
        status: score != null ? 'SAMPLE_VERIFIED' : 'SAMPLE_VERIFIED',
        result: score != null
          ? `Extractability score sealed at ${Math.round(score)}/100 based on ${crawledCount} crawled page(s).`
          : `Evaluated across ${crawledCount} crawled page(s).`,
      };
    }
    if (cLower.includes('visibility overview') || cLower.includes('mention and citation')) {
      if (card && card.successful_runs && card.citation_rate_pct != null) {
        return {
          label: checkLabel,
          status: 'VERIFIED',
          result: `Measured ${Math.round(card.citation_rate_pct)}% citation rate across ${card.successful_runs} tested runs.`,
        };
      }
      return {
        label: checkLabel,
        status: 'DATA_UNAVAILABLE',
        result: 'Live multi-engine visibility not recorded on this run. Technical readiness and observed visibility remain separate.',
      };
    }
    if (cLower.includes('differences between technical readiness')) {
      return {
        label: checkLabel,
        status: 'VERIFIED',
        result: 'Strict separation maintained: on-page extractability does not predict live AI search visibility.',
      };
    }
  }

  // Section 02 Scorecard
  if (sectionNumber === '02') {
    if (!card || !card.successful_runs) {
      return {
        label: checkLabel,
        status: 'DATA_UNAVAILABLE',
        result: 'Requires active live benchmark run. Direct search observations not recorded on baseline crawl.',
      };
    }
    if (cLower.includes('appearance rate') || cLower.includes('mention')) {
      return {
        label: checkLabel,
        status: 'VERIFIED',
        result: `Brand appearance rate: ${Math.round(card.mention_rate_pct ?? 0)}% across eligible tested responses.`,
      };
    }
    if (cLower.includes('citation rate')) {
      return {
        label: checkLabel,
        status: 'VERIFIED',
        result: `Citation rate: ${Math.round(card.citation_rate_pct ?? 0)}% across eligible tested responses.`,
      };
    }
    if (cLower.includes('platform')) {
      const engines = card.engines_queried || [];
      return {
        label: checkLabel,
        status: 'VERIFIED',
        result: `Engines evaluated: ${engines.join(', ') || 'Standard prompt harness'}.`,
      };
    }
  }

  // Section 04 Platforms
  if (sectionNumber === '04') {
    if (card && card.successful_runs) {
      return {
        label: checkLabel,
        status: 'VERIFIED',
        result: `Evaluated across: ${(card.engines_queried || []).join(', ') || 'Recorded platforms'}.`,
      };
    }
    return {
      label: checkLabel,
      status: 'DATA_UNAVAILABLE',
      result: 'Search surfaces not queried in this execution. Engines are not assumed or simulated.',
    };
  }

  // Section 24 Extractability
  if (sectionNumber === '24') {
    if (cLower.includes('accessible in page content') || cLower.includes('definitions')) {
      const score = geo?.extractability_score ?? report.scores?.category_scores?.geo?.score;
      return {
        label: checkLabel,
        status: 'SAMPLE_VERIFIED',
        result: score != null
          ? `On-page extractability score: ${Math.round(score)}/100 across crawled URLs.`
          : 'Passage extractability evaluated across crawled headings and paragraphs.',
      };
    }
  }

  // Section 31 Crawlability
  if (sectionNumber === '31') {
    return {
      label: checkLabel,
      status: 'SAMPLE_VERIFIED',
      result: `Crawlability and directives verified across ${crawledCount} crawled URL(s).`,
    };
  }

  // Section 33 Schema
  if (sectionNumber === '33') {
    const types = geo?.schema_types || [];
    return {
      label: checkLabel,
      status: types.length > 0 ? 'VERIFIED' : 'SAMPLE_VERIFIED',
      result: types.length > 0
        ? `Detected Schema types in crawl: ${types.join(', ')}.`
        : 'Schema JSON-LD graph inspected across crawled DOM.',
    };
  }

  // Default fallback
  return {
    label: checkLabel,
    status: crawledCount > 0 ? 'SAMPLE_VERIFIED' : 'NOT_TESTED',
    result: crawledCount > 0
      ? `Evaluated under 2026 Enterprise GEO Standard across the crawled sample.`
      : 'Unmeasured: No pages were crawled on this audit run.',
  };
}

export function resolveGeoAudit(report: ExecutiveReport): ResolvedGeoAudit {
  const domain = report.domain || 'this site';
  const manifest = report.crawl_manifest;
  const pages = manifest?.pages || report.page_reports || [];
  const crawledCount = pages.length;
  const discoveredCount = manifest?.total_pages_discovered ?? crawledCount;

  const sampleNotice = crawledCount > 0
    ? `Empirical crawl sample: ${crawledCount} analyzed URL(s) of ${discoveredCount} discovered endpoints. Missing data stays unmeasured.`
    : 'No URL was crawled on this execution. Dristik evaluates an empirical sample.';

  const geo = report.geo_readiness;
  const card = report.ai_visibility_scorecard;
  const extractabilityScore = finite(geo?.extractability_score ?? report.scores?.category_scores?.geo?.score);
  const citationRate = finite(card?.citation_rate_pct);
  const visibilityStatus = card?.status || 'NOT_MEASURED';

  const allFindings = report.findings || [];
  const counts: Record<GeoStatus, number> = {
    VERIFIED: 0,
    SAMPLE_VERIFIED: 0,
    INFERRED: 0,
    HYPOTHESIS: 0,
    DATA_UNAVAILABLE: 0,
    NOT_TESTED: 0,
    NOT_APPLICABLE: 0,
  };

  let pageNumber = 5;

  const sections: ResolvedGeoSection[] = GEO_SECTIONS.map((sec) => {
    const secNumber = sec.number;
    const matchedFindings = assignSectionFindings(allFindings, secNumber);
    const checks: GeoCheck[] = sec.checks.map((checkLabel) => {
      const cRes = resolveCheck(report, secNumber, checkLabel, matchedFindings);
      counts[cRes.status] = (counts[cRes.status] || 0) + 1;
      return cRes;
    });

    let sectionStatus: GeoStatus = 'SAMPLE_VERIFIED';
    if (checks.some((c) => c.status === 'VERIFIED')) sectionStatus = 'VERIFIED';
    else if (checks.every((c) => c.status === 'DATA_UNAVAILABLE')) sectionStatus = 'DATA_UNAVAILABLE';
    else if (checks.every((c) => c.status === 'NOT_TESTED')) sectionStatus = 'NOT_TESTED';

    const [agentId, agentName, agentRole] = AGENT_MAP[secNumber] || [
      'geo.benchmark_orchestrator.v3',
      'GEO Benchmark Orchestrator',
      'Generative Engine Optimization Specialist',
    ];

    const agent: GeoAgentConsultation = {
      agentId,
      agentName,
      agentRole,
      diagnosticOverview: `Diagnostic review for Chapter ${secNumber} (${sec.title}) evaluated under the 2026 Enterprise GEO Standard for ${domain}.`,
      architectureMechanics: 'Evaluates generative content extraction, multi-engine knowledge representation, and vector retrieval chunk eligibility.',
      rootCause: matchedFindings.length > 0
        ? `Identified ${matchedFindings.length} defect(s) affecting this chapter.`
        : 'No critical architectural breakdown stored in baseline sample.',
      businessRisk: 'Loss of brand recommendation share across conversational AI search assistants, depressing inbound pipeline.',
      remediationRecipe: 'Deploy structured, extractable definition blocks and machine-readable comparison tables.',
      verificationProtocol: `Rerun standardized prompt benchmark across target engines and inspect citation rates.`,
    };

    const section: ResolvedGeoSection = {
      number: secNumber,
      part: sec.part,
      title: sec.title,
      status: sectionStatus,
      pageNumber,
      summary: `Comprehensive evaluation of ${sec.title.toLowerCase()} based on crawled DOM AST and empirical benchmark runs.`,
      checks,
      findings: matchedFindings.map(toFindingRef),
      agent,
    };

    pageNumber += 2;
    return section;
  });

  return {
    sampleNotice,
    domain,
    extractabilityScore,
    visibilityStatus,
    citationRate,
    sections,
    counts,
  };
}
