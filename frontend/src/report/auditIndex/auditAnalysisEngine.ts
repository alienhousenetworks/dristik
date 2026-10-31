import { ExecutiveReport, Finding, PageEvidence } from '../../types';
import { AuditedCheck, AuditFindingRef, SectionAnalysis, SectionStatus } from './types';

export interface AuditContext {
  report: ExecutiveReport;
  pages: PageEvidence[];
  findings: Finding[];
  model: string;
}

function tokens(text: string): Set<string> {
  const words = text.toLowerCase().match(/[a-z0-9_]{3,}/g) || [];
  return new Set(words);
}

function scopeLabel(finding: Finding): string {
  if (finding.confidence_rubric === 'GUESSING') return 'Guessing — not a measured defect';
  return finding.evidence_scope || 'URL not attached';
}

export function toFindingRef(finding: Finding): AuditFindingRef {
  return {
    id: finding.finding_id,
    severity: finding.severity,
    title: finding.title,
    scope: scopeLabel(finding),
    description: finding.description,
    action: finding.recommendation,
    priority: finding.priority,
  };
}

export function assignFindingsToChecks(
  findings: Finding[],
  checks: string[]
): Map<string, Finding[]> {
  const assigned = new Map<string, Finding[]>();
  for (const check of checks) {
    assigned.set(check, []);
  }

  for (const finding of findings) {
    const fText = `${finding.title || ''} ${finding.description || ''} ${finding.finding_id || ''}`.toLowerCase();
    const fTokens = tokens(fText);
    let bestCheck: string | null = null;
    let bestScore = 0;

    for (const check of checks) {
      const cLower = check.toLowerCase();
      const cTokens = tokens(cLower);
      let score = 0;
      for (const t of fTokens) {
        if (cTokens.has(t)) score += 1;
      }

      if (/robots\.txt/.test(fText) && /robots\.txt/.test(cLower)) score += 5;
      if (/sitemap/.test(fText) && /sitemap/.test(cLower)) score += 5;
      if (/canonical/.test(fText) && /canonical/.test(cLower)) score += 5;
      if (/redirect|301|302/.test(fText) && /redirect/.test(cLower)) score += 5;
      if (/status|404|500/.test(fText) && /response|status/.test(cLower)) score += 4;
      if (/schema|json-ld|entity/.test(fText) && /schema|structured/.test(cLower)) score += 5;
      if (/title/.test(fText) && /title/.test(cLower)) score += 5;
      if (/h1|heading/.test(fText) && /h1|heading/.test(cLower)) score += 5;
      if (/image|alt/.test(fText) && /image|alt/.test(cLower)) score += 5;
      if (/lcp|inp|cls|vitals/.test(fText) && /lcp|inp|cls|vitals|performance/.test(cLower)) score += 5;
      if (/viewport|mobile/.test(fText) && /viewport|mobile|responsive/.test(cLower)) score += 5;
      if (/security|hsts|csp|https/.test(fText) && /security|https|header/.test(cLower)) score += 5;
      if (/thin|word count/.test(fText) && /thin|quality|completeness/.test(cLower)) score += 4;

      if (score >= 2 && score > bestScore) {
        bestScore = score;
        bestCheck = check;
      }
    }

    if (bestCheck && bestScore >= 2 && assigned.has(bestCheck)) {
      assigned.get(bestCheck)!.push(finding);
    }
  }

  return assigned;
}

export function evaluateAuditCheck(
  ctx: AuditContext,
  sectionNumber: string,
  label: string,
  matchedFindings: Finding[]
): AuditedCheck {
  const verifiedDefects = matchedFindings.filter((finding) => finding.confidence_rubric !== 'GUESSING');
  if (verifiedDefects.length > 0) {
    const top = verifiedDefects[0];
    const fix = top.recommendation && !/implement recommended architectural fix/i.test(top.recommendation)
      ? top.recommendation
      : '';
    return {
      label,
      status: 'ISSUE_VERIFIED',
      result: `${top.title}${fix ? ` Fix: ${fix}` : ''}`,
      findings: verifiedDefects.map(toFindingRef),
    };
  }

  const agent = AGENT_MAP[sectionNumber];
  const who = agent?.name || 'The specialist';
  return {
    label,
    status: 'NOT_TESTED',
    result: `${who} did not publish a judgment for “${label}”. A missing judgment is not a pass and not a defect.`,
  };
}


const AGENT_MAP: Record<string, { id: string; name: string }> = {
  '01': { id: 'strategy.executive.v3', name: 'Executive Strategy Specialist' },
  '02': { id: 'strategy.executive.v3', name: 'SEO Scorecard & Measurement Specialist' },
  '03': { id: 'business.discovery.v3', name: 'Business Discovery Specialist' },
  '04': { id: 'verification.adversarial.v3', name: 'Risk & Policy Verification Specialist' },
  '05': { id: 'competitor.organic.v3', name: 'Competitor Intelligence Specialist' },
  '06': { id: 'strategy.executive.v3', name: 'Prioritization & Roadmap Specialist' },
  '07': { id: 'seo.crawl.v3', name: 'Crawl Infrastructure Specialist' },
  '08': { id: 'seo.indexability.v3', name: 'Indexation & Index Coverage Specialist' },
  '09': { id: 'seo.indexability.v3', name: 'URL Architecture & Normalization Specialist' },
  '10': { id: 'seo.canonical.v3', name: 'Canonicalization & Duplicate Control Specialist' },
  '11': { id: 'seo.redirect.v3', name: 'Redirect & Broken Link Specialist' },
  '12': { id: 'seo.sitemap.v3', name: 'XML Sitemap Architecture Specialist' },
  '13': { id: 'seo.crawl.v3', name: 'Site Architecture & Internal Links Specialist' },
  '14': { id: 'seo.status_reliability.v3', name: 'HTTP & Server Reliability Specialist' },
  '15': { id: 'seo.rendering.v3', name: 'JavaScript & DOM Rendering Specialist' },
  '16': { id: 'ux.experience.v3', name: 'Core Web Vitals & Page Speed Specialist' },
  '17': { id: 'ux.experience.v3', name: 'Mobile SEO & Responsive Behavior Specialist' },
  '18': { id: 'trust.security.v3', name: 'HTTPS & Security Integrity Specialist' },
  '19': { id: 'schema.validation.v3', name: 'Structured Data & Schema Specialist' },
  '20': { id: 'content.intent.v3', name: 'Title Tag & Snippet Copywriting Specialist' },
  '21': { id: 'content.depth.v3', name: 'Heading & Document Outline Specialist' },
  '22': { id: 'business.intent.v3', name: 'Keyword Research & Search Intent Specialist' },
  '23': { id: 'content.depth.v3', name: 'Content Quality & Usefulness Specialist' },
  '24': { id: 'content.intent.v3', name: 'Intent Alignment & Query Mapping Specialist' },
  '25': { id: 'content.authority.v3', name: 'Topical Authority & Semantic Graph Specialist' },
  '26': { id: 'content.decay.v3', name: 'Duplication & Content Decay Specialist' },
  '27': { id: 'content.depth.v3', name: 'Internal Linking & Anchor Text Specialist' },
  '28': { id: 'content.readability.v3', name: 'Visual & Image SEO Specialist' },
  '29': { id: 'seo.specialized.video.v3', name: 'Video & Multimodal SEO Specialist' },
  '30': { id: 'seo.specialized.governance.v3', name: 'Content Governance & Editorial Specialist' },
  '31': { id: 'external.authority.v3', name: 'Backlink Profile & Link Graph Specialist' },
  '32': { id: 'external.authority.v3', name: 'Digital PR & Brand Authority Specialist' },
  '33': { id: 'competitor.organic.v3', name: 'Competitor Benchmarking Specialist' },
  '34': { id: 'competitor.serp.v3', name: 'SERP Visibility & Ranking Specialist' },
  '35': { id: 'seo.specialized.local.v3', name: 'Local SEO & GBP Specialist' },
  '36': { id: 'seo.specialized.international.v3', name: 'International & Hreflang Specialist' },
  '37': { id: 'seo.specialized.policy_compliance.v3', name: 'Search Policy & Anti-Spam Specialist' },
  '38': { id: 'seo.specialized.ecommerce.v3', name: 'E-Commerce & Merchant Feed Specialist' },
  '39': { id: 'seo.specialized.news.v3', name: 'Publisher & News SEO Specialist' },
  '40': { id: 'seo.specialized.programmatic.v3', name: 'Programmatic SEO & Scale Specialist' },
  '41': { id: 'seo.specialized.saas_b2b.v3', name: 'SaaS & B2B Lead-Gen SEO Specialist' },
  '42': { id: 'seo.specialized.app.v3', name: 'App Discovery & Mobile Deep-Link Specialist' },
  '43': { id: 'seo.specialized.accessibility.v3', name: 'Accessibility & Semantic UX Specialist' },
  '44': { id: 'aeo.conversational_intent.v3', name: 'Voice & Multimodal Query Specialist' },
  '45': { id: 'aeo.direct_answer_box.v3', name: 'Answer Engine Optimization (AEO) Specialist' },
  '46': { id: 'geo.extractability.v3', name: 'Generative Engine Optimization (GEO) Specialist' },
  '47': { id: 'ai_search.discoverability.v3', name: 'AI Search & Citation Specialist' },
  '48': { id: 'seo.indexability.v3', name: 'Google Search Console Intelligence Specialist' },
  '49': { id: 'cro.analytics_integrity.v3', name: 'Analytics & Conversion Tracking Specialist' },
  '50': { id: 'ux.conversion.v3', name: 'Conversion Rate Optimization (CRO) Specialist' },
  '51': { id: 'business.commercial.v3', name: 'Organic Revenue & Attribution Specialist' },
  '52': { id: 'seo.specialized.forecasting.v3', name: 'Opportunity Modeling & Forecasting Specialist' },
  '53': { id: 'seo.specialized.governance.v3', name: 'Issue Register & Remediation Specialist' },
  '54': { id: 'seo.specialized.governance.v3', name: 'Post-Fix Verification Specialist' },
  '55': { id: 'seo.specialized.governance.v3', name: 'Monitoring & Operations Specialist' },
};

export function buildSectionAnalysis(
  ctx: AuditContext,
  sectionNumber: string,
  status: SectionStatus,
  summary: string,
  findings: Finding[]
): SectionAnalysis {
  const agent = AGENT_MAP[sectionNumber] || {
    id: 'seo.crawl.v3',
    name: 'Technical SEO Specialist',
  };
  const verified = findings.filter((f) => f.confidence_rubric !== 'GUESSING');
  const top = verified[0];
  const unpublished = `${agent.name} did not publish a judgment for this chapter (${status}). ${ctx.pages.length} crawled page(s) are in the measurement record.`;
  return {
    agentId: agent.id,
    agentName: agent.name,
    executiveSummary: top?.description || summary || unpublished,
    technicalMechanics: top?.description || unpublished,
    rootCause: top?.description || unpublished,
    businessImpact: top?.why_it_matters || unpublished,
    remediation: top?.recommendation || unpublished,
    verificationMethod: unpublished,
  };
}

