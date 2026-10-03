import { ExecutiveReport, VisualIntelligencePayload, ChartSpecification, SpotlightMetric } from '../types';

/**
 * Client-side visual intelligence synthesizer.
 * Evaluates the report signals dynamically to generate tailored visualizations
 * and spotlight metrics if not already precomputed by the backend.
 */
export function synthesizeVisualIntelligenceFallback(report: ExecutiveReport): VisualIntelligencePayload {
  const domain = report.domain || 'Target Domain';
  const manifest = report.crawl_manifest;
  const pages = manifest?.pages || [];
  const pageCount = pages.length;
  
  // Crawl TTFB signals
  const ttfbs = pages.map((p) => p.ttfb_ms).filter((v): v is number => typeof v === 'number' && v > 0);
  const avgTtfb = ttfbs.length > 0 ? ttfbs.reduce((a, b) => a + b, 0) / ttfbs.length : null;
  const maxTtfb = ttfbs.length > 0 ? Math.max(...ttfbs) : null;
  const minTtfb = ttfbs.length > 0 ? Math.min(...ttfbs) : null;
  const ttfbVariance = maxTtfb != null && minTtfb != null ? maxTtfb - minTtfb : 0;

  // Findings Severity signals
  const findings = report.findings || [];
  const totalDefects = findings.length;
  const sevCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
  for (const f of findings) {
    const sev = (f.severity || 'INFO') as keyof typeof sevCounts;
    if (sev in sevCounts) sevCounts[sev]++;
    else sevCounts.LOW++;
  }

  // Pillar scores use only numbers the audit produced. Missing categories are omitted.
  const catScores = report.scores?.category_scores || {};
  const weighted = (parts: Array<[number | undefined, number]>): number | null => {
    const present = parts.filter((part): part is [number, number] => typeof part[0] === 'number');
    if (!present.length) return null;
    const weight = present.reduce((sum, part) => sum + part[1], 0);
    return Math.round(present.reduce((sum, part) => sum + part[0] * part[1], 0) / weight);
  };
  const seoScore = weighted([
    [catScores['TECHNICAL_SEO']?.score, 0.6],
    [catScores['ON_PAGE_SEO']?.score, 0.4],
  ]);
  const readiness = report.honest_scores?.ai_readiness_score;
  const geoScore = typeof catScores['GEO']?.score === 'number'
    ? Math.round(catScores['GEO'].score)
    : (typeof readiness === 'number' ? Math.round(readiness) : null);
  const sxoScore = typeof report.honest_scores?.human_score === 'number'
    ? Math.round(report.honest_scores.human_score)
    : (typeof catScores['UX_CONVERSION']?.score === 'number' ? Math.round(catScores['UX_CONVERSION'].score) : null);
  const croScore = typeof catScores['UX_CONVERSION']?.score === 'number'
    ? Math.round(catScores['UX_CONVERSION'].score)
    : null;
  const brandScore = weighted([
    [catScores['SCHEMA']?.score, 0.5],
    [catScores['TRUST_AUTHORITY']?.score, 0.5],
  ]);

  const bizModel = (report.business_profile?.business_model || '').toLowerCase();
  const isTransactional = ['saas', 'ecommerce', 'e-commerce', 'lead gen', 'subscription', 'pricing'].some((k) => bizModel.includes(k));

  // Case Diagnosis Tags
  const caseTags: string[] = [];
  if ((maxTtfb != null && maxTtfb > 700) || (ttfbVariance > 300 && pageCount >= 2)) {
    caseTags.push('Latency Volatility Detected');
  }
  if (seoScore != null && geoScore != null && Math.abs(seoScore - geoScore) >= 20) {
    caseTags.push('Search and AI-readiness scores diverge');
  }
  if (sevCounts.CRITICAL + sevCounts.HIGH >= 4) {
    caseTags.push('High Critical Defect Concentration');
  }
  if (isTransactional) {
    caseTags.push('High-Friction Conversion Funnel');
  }
  if (caseTags.length === 0) {
    caseTags.push('No extra diagnosis tags from the measured signals');
  }
  const auditCaseProfile = caseTags.join(' · ');

  // AI-Curated Charts
  const charts: ChartSpecification[] = [];
  let priority = 1;

  // 1. Radar — only pillars that have a measured score. No invented industry baseline.
  const pillarPoints: Array<[string, number]> = [
    ['Search (SEO)', seoScore],
    ['AI readiness', geoScore],
    ['Experience', sxoScore],
    ['Conversion', croScore],
    ['Brand', brandScore],
  ].filter((point): point is [string, number] => typeof point[1] === 'number');
  if (pillarPoints.length > 0) {
    const strongest = pillarPoints.reduce((best, point) => (point[1] > best[1] ? point : best));
    const weakest = pillarPoints.reduce((best, point) => (point[1] < best[1] ? point : best));
    charts.push({
      id: 'chart_pillar_radar',
      chart_type: 'radar',
      title: 'Measured pillar scores',
      subtitle: 'Scores produced by this audit. Pillars without a score are omitted.',
      ai_insight: `Strongest measured pillar is ${strongest[0]} (${strongest[1]}/100). Lowest measured pillar is ${weakest[0]} (${weakest[1]}/100).`,
      category: 'OVERALL',
      data: {
        labels: pillarPoints.map(([label]) => label),
        target_values: pillarPoints.map(([, value]) => value),
        benchmark_values: [],
      },
      config: {
        max_value: 100,
        target_label: domain,
        target_color: '#2e6f5e',
        benchmark_label: 'No industry baseline measured',
        benchmark_color: '#94a3b8',
      },
      is_recommended: true,
      priority_order: priority++,
    });
  }

  // 2. Latency Curve
  if (ttfbs.length > 0 && maxTtfb != null && avgTtfb != null) {
    const pageItems = pages.slice(0, 8).flatMap((p) => {
      if (typeof p.ttfb_ms !== 'number') return [];
      let slug = p.url.replace(`https://${domain}`, '').replace(`http://${domain}`, '');
      if (!slug || slug === '/') slug = '/ (Home)';
      else if (slug.length > 20) slug = slug.slice(0, 18) + '…';
      return [{
        label: slug,
        value: Math.round(p.ttfb_ms),
        full_url: p.url,
      }];
    });

    if (pageItems.length === 0) {
      // No measured TTFB samples. Do not invent /about or /pricing timings.
    } else charts.push({
      id: 'chart_ttfb_latency',
      chart_type: 'latency_curve',
      title: 'Crawl Latency & Response Speed (TTFB)',
      subtitle: 'Page-by-page server response times measured across crawl paths vs Google budget thresholds',
      ai_insight: `Peak measured TTFB was ${Math.round(maxTtfb)}ms across ${ttfbs.length} page(s).`,
      category: 'TECHNICAL_SEO',
      data: {
        points: pageItems,
        fast_threshold: 200,
        warning_threshold: 800,
        unit: 'ms',
      },
      config: {
        curve_color: '#0284c7',
        fast_color: '#16a34a',
        warning_color: '#dc2626',
      },
      is_recommended: true,
      priority_order: priority++,
    });
  }

  // 3. Live engine visibility. One composite bar only when a live run measured it.
  // A single on-page score is never split into per-engine "Cited" ranks.
  const liveVisibility = report.honest_scores?.ai_visibility_status === 'MEASURED'
    ? report.honest_scores?.ai_visibility_score
    : null;
  if (typeof liveVisibility === 'number') {
    charts.push({
      id: 'chart_ai_engine_matrix',
      chart_type: 'engine_comparison_bar',
      title: 'Live citation measurement',
      subtitle: 'Composite from engines that were actually queried. Not inferred from HTML.',
      ai_insight: `Live citation composite is ${Math.round(liveVisibility)}/100. Per-engine ranks are omitted unless each engine returned its own measurement.`,
      category: 'GEO',
      data: {
        engines: [{ name: 'Measured composite', readiness: Math.round(liveVisibility), benchmark: 0, status: 'Measured' }],
        visibility_status: 'MEASURED',
      },
      config: { bar_color: '#2e6f5e', benchmark_color: '#94a3b8' },
      is_recommended: true,
      priority_order: priority++,
    });
  } else {
    charts.push({
      id: 'chart_ai_engine_matrix',
      chart_type: 'engine_comparison_bar',
      title: 'Live citation measurement',
      subtitle: 'Not measured on this audit.',
      ai_insight: 'ChatGPT, Perplexity, and Google AI Overview citations were not queried. On-page AI readiness is a separate score.',
      category: 'GEO',
      data: { engines: [], visibility_status: 'NOT_MEASURED' },
      config: { bar_color: '#2e6f5e', benchmark_color: '#94a3b8' },
      is_recommended: false,
      priority_order: priority++,
    });
  }

  // 4. Defect Donut
  if (totalDefects >= 2) {
    charts.push({
      id: 'chart_defect_donut',
      chart_type: 'defect_donut',
      title: 'Defect Severity & Technical Debt Load',
      subtitle: 'Breakdown of audited code, schema, and content findings categorized by executive severity',
      ai_insight: `${sevCounts.CRITICAL} critical and ${sevCounts.HIGH} high findings are in this crawl sample.`,
      category: 'OVERALL',
      data: {
        total: totalDefects,
        segments: [
          { label: 'Critical Blocker', count: sevCounts.CRITICAL, color: '#ef4444' },
          { label: 'High Severity', count: sevCounts.HIGH, color: '#f59e0b' },
          { label: 'Medium Drag', count: sevCounts.MEDIUM, color: '#eab308' },
          { label: 'Low / Advisory', count: sevCounts.LOW + sevCounts.INFO, color: '#10b981' },
        ],
      },
      config: { inner_radius: 58, outer_radius: 90 },
      is_recommended: true,
      priority_order: priority++,
    });
  }

  // 5. Journey Funnel
  if ((isTransactional || totalDefects > 5) && seoScore != null && sxoScore != null && croScore != null) {
    charts.push({
      id: 'chart_journey_funnel',
      chart_type: 'journey_funnel',
      title: 'Category scores along the journey',
      subtitle: 'These are category scores from this audit, not a measured visitor funnel.',
      ai_insight: 'No first-party session funnel was connected. Stages repeat the measured category scores.',
      category: 'UX_CONVERSION',
      data: {
        stages: [
          { stage: 'Search', score: seoScore, drop_reason: 'Technical and on-page category score' },
          { stage: 'Experience', score: sxoScore, drop_reason: 'Human or experience category score' },
          { stage: 'Conversion', score: croScore, drop_reason: 'Conversion category score' },
        ],
      },
      config: { funnel_color: '#2e6f5e' },
      is_recommended: isTransactional,
      priority_order: priority++,
    });
  }

  // Spotlight Metrics
  const spotlightMetrics: SpotlightMetric[] = [];
  if (avgTtfb != null) {
    spotlightMetrics.push({
      id: 'metric_avg_ttfb',
      label: 'Average Crawl TTFB',
      value: `${Math.round(avgTtfb)}`,
      unit: 'ms',
      change_indicator: avgTtfb <= 200 ? 'At or under 200ms' : (avgTtfb > 800 ? 'Over 800ms' : 'Between 200ms and 800ms'),
      status: avgTtfb <= 200 ? 'good' : (avgTtfb > 800 ? 'bad' : 'warning'),
      significance: 'Lab TTFB from this crawl. It is not a CrUX field measurement.',
      category: 'TECHNICAL_SEO',
    });
  }
  if (geoScore != null) {
    spotlightMetrics.push({
      id: 'metric_citation_readiness',
      label: 'On-page AI readiness',
      value: `${geoScore}`,
      unit: '/ 100',
      change_indicator: liveVisibility != null ? `Live citations ${Math.round(liveVisibility)}` : 'Live citations not measured',
      status: geoScore >= 75 ? 'good' : (geoScore >= 50 ? 'warning' : 'bad'),
      significance: 'How extractable the crawled pages are. This is not a ChatGPT or Perplexity citation rank.',
      category: 'GEO',
    });
  }
  spotlightMetrics.push(
    {
      id: 'metric_blocker_density',
      label: 'Critical Blockers',
      value: sevCounts.CRITICAL,
      unit: 'defects',
      change_indicator: 'Zero-tolerance goal',
      status: sevCounts.CRITICAL > 0 ? 'bad' : 'good',
      significance: sevCounts.CRITICAL > 0 ? 'Urgent blocker issues requiring immediate fix.' : 'No critical blocker defects identified.',
      category: 'OVERALL',
    },
    {
      id: 'metric_crawl_coverage',
      label: 'Crawled pages',
      value: pageCount,
      unit: 'pages',
      change_indicator: 'This crawl',
      status: pageCount > 0 ? 'good' : 'warning',
      significance: 'Pages fetched for this audit.',
      category: 'OVERALL',
    },
  );
  if (seoScore != null && geoScore != null) {
    const delta = Math.abs(seoScore - geoScore);
    spotlightMetrics.push({
      id: 'metric_tripartite_delta',
      label: 'Search vs AI readiness',
      value: `${delta}`,
      unit: 'pts',
      change_indicator: delta < 15 ? 'Close' : 'Apart',
      status: delta < 15 ? 'good' : 'warning',
      significance: 'Difference between the search category score and on-page AI readiness. Not a ranking gap.',
      category: 'GEO',
    });
  }

  const selectedNames = charts.map((c) => c.title).join(', ');
  const aiRationale = `AI Diagnostic Assessment for ${domain}: Based on ${pageCount} crawled page(s) and ${totalDefects} verified findings, our cognition engine identified ${auditCaseProfile.toLowerCase()}. Rather than rendering generic fixed graphs, the AI dynamically curated: ${selectedNames}. This specifically isolates latency bottlenecks, generative AI citation gaps, and actionable defect remediation priorities for C-suite decision-makers.`;

  return {
    ai_rationale: aiRationale,
    audit_case_profile: auditCaseProfile,
    selected_visualizations: charts,
    spotlight_metrics: spotlightMetrics,
    available_customizations: [
      'chart_pillar_radar',
      'chart_ttfb_latency',
      'chart_ai_engine_matrix',
      'chart_defect_donut',
      'chart_journey_funnel',
    ],
    generated_at: new Date().toISOString().replace('T', ' ').slice(0, 16) + ' UTC',
  };
}
