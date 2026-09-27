export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export type Category =
  | 'TECHNICAL_SEO'
  | 'ON_PAGE_SEO'
  | 'CONTENT'
  | 'GEO'
  | 'AI_SEARCH'
  | 'SCHEMA'
  | 'UX_CONVERSION'
  | 'TRUST_AUTHORITY'
  | 'COMPETITIVE';

export interface FindingEvidence {
  evidence_id?: string;
  url?: string;
  element: string;
  value: string;
  selector?: string;
  line_number?: number;
  snippet?: string;
  source?: string;
  excerpt?: string;
  type?: string;
  state?: string;
  evidence_class?: EvidenceClass;
  evidence_subtype?: string;
}

export interface CodePatch {
  patch_id: string;
  title: string;
  category: Category;
  target_file: string;
  before_snippet?: string;
  after_snippet: string;
  explanation: string;
  release_status?: string;
}

export interface Finding {
  finding_id: string;
  category: Category;
  severity: Severity;
  title: string;
  description: string;
  evidence: FindingEvidence[];
  evidence_refs: string[];
  rule_id?: string;
  confidence: number;
  confidence_label: string;
  impact: number;
  effort: number;
  priority: number;
  recommendation: string;
  verification_status: string;
  verification_notes?: string;
  business_impact?: string;
  observation_type?: string;
  code_patch?: CodePatch;
  source_integrity_label?: "CORROBORATED" | "CONTESTED" | "SINGLE_SOURCE_UNVERIFIED" | "NOT_APPLICABLE";
  claim_family?: "icp" | "pricing" | "performance" | "trust" | "authorship";
  routed_to?: string;
  finding?: string;
  confidence_rubric?: "CERTAIN" | "LIKELY" | "GUESSING";
  confidence_basis?: string;
  materiality?: "CRITICAL" | "MAJOR" | "MINOR";
  source_agreement?: number;
  adversarial_reviewed?: boolean;
  held_from_executive?: boolean;
  why_it_matters?: string;
  validation_criteria?: string;
  remediation_verification?: RemediationVerificationReport;
  resolution_status?: 'OPEN' | 'RESOLVED' | 'VERIFYING' | 'REGRESSED' | string;
  evidence_class?: EvidenceClass;
  evidence_subtype?: string;
  epistemic_level?: string;
  evidence_scope?: 'PAGE_VERIFIED' | 'SAMPLE_VERIFIED' | 'ORIGIN_VERIFIED' | 'INDEX_OBSERVED' | 'SITE_INFERRED' | 'EXTERNAL_MEASURED';
  scope_hit_count?: number | null;
  scope_sample_size?: number | null;
  cro_dissection?: CroEvidenceDissection;
  surfaces_affected?: Array<{
    surface: string;
    url?: string;
    selector?: string;
    details?: string;
  }>;
}

export interface CroEvidenceDissection {
  observed_facts: string[];
  inferred_impact: string;
  requires_analytics: {
    actual_abandonment_rate: string;
    cta_conversion_rate: string;
    form_completion_rate: string;
    [key: string]: string;
  };
  analytics_connected: boolean;
  grounded_metrics?: Record<string, any> | null;
}

export interface VerificationCheckItem {
  name: string;
  passed: boolean;
  detail: string;
}

export interface RemediationVerificationReport {
  verification_id: string;
  finding_id: string;
  analysis_id?: string;
  target_url: string;
  stage: 'FIX' | 'RECRAWL' | 'RECHECK' | 'COMPARE' | 'CERTIFY' | string;
  status: 'RESOLVED' | 'PARTIALLY_RESOLVED' | 'FAILED_RECHECK' | 'PENDING' | string;
  before_state: string;
  after_state: string;
  checks: VerificationCheckItem[];
  passed_checks_count: number;
  total_checks_count: number;
  score_delta?: number | null;
  verified_at: string;
  evidence_seal: string;
  certified_by?: string;
  recrawl_status_code?: number;
  recrawl_ttfb_ms?: number;
  recrawl_content_type?: string;
}

export interface Claim {
  id: string;
  agent_id: string;
  statement: string;
  claim_type: string;
  category: Category;
  severity: Severity;
  evidence_refs: string[];
  confidence: number;
  verification_status: string;
  recommendation?: string;
  source_integrity_label?: "CORROBORATED" | "CONTESTED" | "SINGLE_SOURCE_UNVERIFIED" | "NOT_APPLICABLE";
  ground_truth_relation?: "CONFIRMS" | "CONTRADICTS" | "MISSING_EXTERNAL" | "NOT_APPLICABLE";
  claim_family?: "icp" | "pricing" | "performance" | "trust" | "authorship";
  confidence_band?: "HIGH" | "MEDIUM" | "LOW";
  routed_to?: string;
}

export interface BusinessProfile {
  business_name: string;
  industry: string;
  niche: string;
  sub_niche?: string;
  products: string[];
  services: string[];
  target_audience: string;
  geography: string;
  business_model: string;
  value_proposition: string;
  primary_cta?: string;
  secondary_cta?: string;
  primary_intent: string;
  confidence: number;
}

export interface ThreeWayComparison {
  human_visitor_perspective: string;
  search_engine_perspective: string;
  ai_answer_engine_perspective: string;
}

export interface EngineQueryResult {
  engine: string;
  was_mentioned: boolean;
  position?: number | null;
  was_cited: boolean;
  cited_url?: string | null;
  source_used?: string;
  is_factually_correct?: boolean | null;
  answer_completeness?: 'Complete' | 'Partial' | 'Missing' | 'Diverted';
  brand_accuracy?: 'Accurate' | 'Distorted' | 'Omitted' | 'Unverified';
  competitor_confusion?: boolean;
  has_hallucination?: boolean;
  hallucination_note?: string | null;
  competitor_cited_instead?: string | null;
  source_domains_used?: string[];
  synthesized_snippet?: string;
  extractability_health?: string;
  failure_reason?: string | null;
  failure_code?: string | null;
}

export interface LiveBenchmarkRow {
  query: string;
  engine: string;
  was_mentioned: boolean;
  was_cited: boolean;
  is_factually_correct?: boolean | null;
  source_used: string;
  position?: number | null;
  answer_completeness?: string;
  brand_accuracy?: string;
  competitor_confusion?: boolean;
  has_hallucination?: boolean;
  hallucination_note?: string | null;
}

export interface AiSearchQueryEvaluation {
  query: string;
  question_type: string;
  evidence_quality: string;
  score: number;
  detected_answer: string;
  evidence_snippet?: string;
  gap_analysis: string;
  citation_probability?: number;
  after_score?: number;
  after_answer?: string;
  delta?: number;
  is_simulated?: boolean;
  provenance_mode?: string;
  provenance_label?: 'LIVE_QUERIED' | 'MODEL_PREDICTED';
  model_version?: string;
  queried_at?: string;
  // Mode B Benchmark attributes if evaluated against real engines
  engine?: string;
  was_mentioned?: boolean;
  was_cited?: boolean;
  is_factually_correct?: boolean | null;
  source_used?: string;
  position?: number | null;
  answer_completeness?: string;
  brand_accuracy?: string;
  competitor_confusion?: boolean;
  has_hallucination?: boolean;
}

export interface EvidenceLedgerItem {
  id: string;
  source_type: string;
  analyzer?: string;
  url?: string;
  selector?: string;
  text?: string;
  value?: any;
  hash?: string;
  content_sha256?: string;
  raw_snapshot_id?: string;
  fetched_at?: string;
  metadata?: Record<string, any>;
}

export interface CommercialQueryEvaluation {
  question_key: string;
  question_title: string;
  buyer_query: string;
  before_score: number;
  before_answer: string;
  before_evidence_status: string;
  after_score?: number;
  after_answer?: string;
  delta?: number;
  patch_citation_gain?: number;
  evidence_snippet?: string;
  gap_analysis?: string;
}

export interface CompetitorBakeoffItem {
  question_key: string;
  question_title: string;
  target_answer: string;
  target_score: number;
  target_status: string;
  competitor_answer: string;
  competitor_score: number;
  competitor_status: string;
  winner: string;
  commercial_takeaway: string;
}

export interface CompetitorBakeoffResult {
  competitor_domain: string;
  evaluations: CompetitorBakeoffItem[];
  target_wins: number;
  competitor_wins: number;
  ties: number;
  executive_takeaway: string;
}

export interface HonestScores {
  human_score: number;
  google_score: number;
  ai_readiness_score?: number | null;
  ai_visibility_score?: number | null;
  ai_visibility_status?: string;
  ai_citation_score?: number | null;
  overall_score: number;
  score_band: string;
  human_summary: string;
  google_summary: string;
  ai_citation_summary: string;
  evidence_refs: string[];
  ai_citation_status?: string;
}

export interface CharacterSafeCopy {
  title: string;
  title_char_count: number;
  title_status: string;
  meta_description: string;
  meta_char_count: number;
  meta_status: string;
  hero_headline: string;
  hero_subhead: string;
  hero_word_count: number;
  hero_status: string;
  primary_cta: string;
}


export interface ScoreDeductionItem {
  finding_id: string;
  title: string;
  severity: string;
  points_lost: number;
  why_it_matters?: string;
}

export interface ScoreFormulaComponent {
  component: string;
  points_earned: number;
  points_possible: number;
  status: 'PASS' | 'PARTIAL' | 'DEFICIT';
  provenance?: string;
}

export interface MathematicalDerivationRow {
  category: string;
  category_label: string;
  raw_score: number;
  weight_pct: number;
  weight: number;
  weighted_points: number;
}

export interface CategoryScore {
  category: Category;
  score: number;
  confidence: number;
  weight: number;
  weighted_score: number;
  strengths: string[];
  weaknesses: string[];
  summary: string;
  deductions?: ScoreDeductionItem[];
  formula_breakdown?: ScoreFormulaComponent[];
}

export interface OverallScoreResult {
  overall_score: number;
  overall_confidence: number;
  evidence_coverage: number;
  grade: string;
  health_label: string;
  category_scores: Record<string, CategoryScore>;
  intent_adjusted_weights: Record<string, number>;
  mathematical_derivation?: MathematicalDerivationRow[];
}

export interface RoadmapItem {
  timeframe: string;
  title: string;
  description: string;
  impact: string;
  effort: string;
  category: Category;
  related_finding_id?: string;
  code_snippet?: string;
}

export interface ExecutiveActionItem {
  rank: number;
  priority: 'P0' | 'P1' | 'P2' | 'P3' | string;
  action: string;
  impact: 'Very High' | 'High' | 'Medium' | 'Low' | string;
  effort: 'Low' | 'Medium' | 'High' | string;
  expected_outcome: string;
  estimated_engineer_hours: number;
  dependencies: string[];
  validation: string;
  category?: Category | string;
  related_finding_id?: string;
}

export interface ExecutiveTopActionsPlan {
  actions: ExecutiveActionItem[];
  total_engineer_hours: number;
  dependencies_flow: string;
  validation_mode: string;
}

export interface AuditSnapshot {
  snapshot_id: string;
  run_label: string;
  date: string;
  score: number;
  category_scores: Record<string, number>;
  evidence_seal: string;
  verified_schema_types: string[];
  findings_count: number;
  status: 'HEALTHY' | 'IMPROVED' | 'REGRESSION' | string;
}

export interface RegressionItem {
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | string;
  title: string;
  category: string;
  dimension_delta?: number | null;
  description: string;
  evidence_ref?: string;
}

export type EvidenceClass =
  | 'OBSERVED'
  | 'EXTERNALLY_VERIFIED'
  | 'MODEL_INFERRED'
  | 'HYPOTHESIS'
  | 'RECOMMENDATION';

export interface EvidenceTaxonomySubtype {
  id: string;
  name: string;
  description: string;
}

export interface EvidenceTaxonomyClassBreakdown {
  class_id: EvidenceClass;
  label: string;
  title: string;
  epistemic_level: string;
  description: string;
  badge_color: string;
  count: number;
  percentage: number;
  subtypes: EvidenceTaxonomySubtype[];
}

export interface EvidenceTaxonomyReport {
  total_evidence_nodes: number;
  epistemic_integrity_score: number;
  class_counts: Record<string, number>;
  subtype_counts: Record<string, number>;
  classes_breakdown: EvidenceTaxonomyClassBreakdown[];
  description: string;
}

export interface ViewportInspection {
  device: 'desktop' | 'tablet' | 'mobile' | string;
  width: number;
  height: number;
  above_the_fold: Record<string, any>;
  detected_defects: string[];
  screenshot_url?: string;
  dom_anchors: string[];
}

export interface VisualUxInspectionReport {
  inspected_at: string;
  tested_devices: string[];
  viewports: Record<string, ViewportInspection>;
  overall_visual_ux_score?: number | null;
  critical_visual_defects: Array<{
    defect: string;
    severity: string;
    device: string;
    evidence: string;
    remediation: string;
  }>;
  combined_intelligence: Record<string, any>;
}

export interface GscAttributionData {
  queries: Array<{ query: string; impressions: number; clicks: number; ctr: number; position: number }>;
  impressions: number;
  clicks: number;
  ctr: number;
  average_position: number;
  pages: string[];
  countries: Array<{ country: string; clicks: number; pct: number }>;
  devices: Record<string, number>;
  is_connected: boolean;
}

export interface Ga4AttributionData {
  landing_pages: Array<{ path: string; sessions: number; bounce_rate: number; avg_session_duration_s: number }>;
  engagement_rate: number;
  conversion_rate: number;
  funnels: Array<{ step: string; visitors: number; dropoff_pct: number }>;
  events: Array<{ event_name: string; count: number }>;
  traffic_sources: Array<{ source: string; sessions: number; pct: number }>;
  is_connected: boolean;
}

export interface CrmAttributionData {
  lead_source: Array<{ source: string; leads: number; mql: number; sql: number; won: number; revenue_inr: number }>;
  lead_quality_score: number;
  pipeline_value_inr: number;
  closed_revenue_inr: number;
  conversion_rate_lead_to_customer: number;
  is_connected: boolean;
}

export interface LifecycleRevenueIntelligence {
  domain: string;
  stages: Record<string, {
    name: string;
    status: string;
    summary?: string;
    metrics?: Record<string, any>;
  }>;
  gsc: GscAttributionData;
  ga4: Ga4AttributionData;
  crm: CrmAttributionData;
  summary: string;
}

export interface RegressionReport {
  has_regression: boolean;
  regression_count: number;
  score_delta: number;
  baseline_run?: AuditSnapshot;
  current_run?: AuditSnapshot;
  regressions: RegressionItem[];
  historical_timeline: AuditSnapshot[];
  summary: string;
  detected_at: string;
}

export interface TelemetryData {
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  cost_complete?: boolean;
  unpriced_calls?: number;
  cost_basis?: 'provider_billed' | 'operator_rate' | 'list_price' | 'mixed' | 'unpriced' | string;
  models_used?: string[];
  total_latency_ms: number;
  model_calls_count: number;
  agent_timings: Record<string, number>;
}

export interface PageEvidence {
  url: string;
  status_code: number;
  title?: string;
  meta_description?: string;
  h1: string[];
  h2: string[];
  h3: string[];
  word_count: number;
  readability_score: number;
  canonical_url?: string;
  robots_meta?: string;
  viewport?: string;
  og_tags: Record<string, string>;
  twitter_tags: Record<string, string>;
  schema_types: string[];
  raw_schema: Array<Record<string, unknown>>;
  internal_links: string[];
  external_links: string[];
  images_without_alt: number;
  total_images: number;
  ttfb_ms: number;
  dom_elements_count: number;
  scripts_count: number;
  stylesheets_count: number;
  page_type: string;
  body_text?: string;
  ctas?: string[];
  render_mode?: string;
  status_code_class?: string;
  is_indexable?: boolean;
  canonical_status?: string;
  title_pixel_width?: number;
  meta_pixel_width?: number;
  title_pixel_status?: string;
  meta_pixel_status?: string;
  inlinks_count?: number;
  outlinks_internal_count?: number;
  outlinks_external_count?: number;
  thin_content?: boolean;
  hreflang_tags?: Record<string, string>;
}

export interface CopyIssue {
  area: string;
  severity: string;
  issue: string;
  why_it_matters: string;
}

export interface CopySection {
  section_id: string;
  section_name: string;
  status: 'NEEDS_REWRITE' | 'UPDATE_RECOMMENDED' | 'OPTIMIZED' | string;
  current_preview?: string | null;
  suggested_copy: string;
  purpose: string;
  seo_geo_notes?: string | null;
  keywords?: string[];
}

export interface CopyFaqItem {
  question: string;
  answer: string;
  target_engine?: string;
}

export interface SuggestedCopy {
  title: string;
  meta_description: string;
  h1: string;
  hero: string;
  primary_cta: string;
  secondary_cta?: string;
  supporting_points: string[];
  body_rewrite: string;
  geo_snippet?: string | null;
  hook_3sec?: string | null;
  sections?: CopySection[];
  faq_items?: CopyFaqItem[];
  notes?: string;
}

export interface PageSeoAudit {
  score: number;
  title_status: string;
  title_length: number;
  meta_status: string;
  meta_length: number;
  h1_status: string;
  heading_structure: string;
  canonical_status: string;
  robots_status: string;
  og_status: string;
  schema_status: string;
  indexability: string;
  issues: string[];
  strengths: string[];
  recommendations: string[];
}

export interface PageCopyAudit {
  score?: number | null;
  voice: string;
  clarity: string;
  persuasion: string;
  audience_fit: string;
  cta_quality: string;
  geo_score?: number | null;
  seo_score?: number;
  issues: CopyIssue[];
  what_works: string[];
  analysis: string;
  suggested?: SuggestedCopy | null;
  specialist_insights?: Record<string, string>;
  llm_status?: string;
  llm_failure_reason?: string | null;
  llm_failure_code?: string | null;
}

export interface PageUxSignals {
  cta_count: number;
  ctas: string[];
  images_missing_alt: number;
  total_images: number;
  internal_links: number;
  external_links: number;
  ttfb_ms: number;
  readability: number;
  word_count: number;
  viewport?: string;
  scripts_count: number;
}

export interface PageReport {
  url: string;
  page_type: string;
  title?: string;
  overall_score: number;
  seo: PageSeoAudit;
  copywriting: PageCopyAudit;
  ux: PageUxSignals;
  findings: string[];
}

export interface CrawlManifest {
  domain: string;
  base_url: string;
  total_pages_discovered: number;
  pages: PageEvidence[];
  sitemap_found: boolean;
  sitemap_url?: string;
  robots_txt_found: boolean;
  robots_txt_content?: string;
  crawl_health: Record<string, unknown>;
}

export interface ContradictionReport {
  id: string;
  contradiction_type: string;
  declared_type?: string;
  detected_type?: string;
  confidence: number;
  reason: string;
  evidence: FindingEvidence[];
}

export interface SemanticBusinessRepresentation {
  industry: string;
  sub_industry?: string;
  business_model: string;
  secondary_business_models: string[];
  website_type: string;
  primary_intent: string;
  secondary_intents: string[];
  target_audience: string[];
  geography: string[];
  products: string[];
  services: string[];
  product_categories: string[];
  service_categories: string[];
  journey_stages: string[];
  conversion_events: string[];
  friction_points: string[];
  confidence: number;
  evidence: FindingEvidence[];
  consensus_summary?: string;
  is_disputed: boolean;
  contradiction?: ContradictionReport;
  source_provenance?: Record<string, string>;
  llm_status?: string;
  llm_failure_reason?: string | null;
}

export interface OutcomeRecord {
  finding_id: string;
  finding_type: string;
  predicted_impact: string;
  remediated: boolean;
  evidence_condition_resolved: boolean;
  condition_key?: string | null;
  condition_detail?: string;
  external_metric_delta: Record<string, {
    metric: string;
    before?: number | null;
    after?: number | null;
    delta?: number | null;
    direction: string;
    note?: string;
  }>;
  confidence_this_delta_is_attributable_to_the_fix: "LOW" | "MEDIUM" | "HIGH";
  confounds: string[];
  observed_outcome: string;
  attribution_disclaimer?: string;
  horizon_days: number;
}

export interface ExecutiveReport {
  report_id: string;
  analysis_id?: string;
  manifest_id?: string;
  sealed_evidence_snapshot_id?: string;
  website_url: string;
  domain: string;
  generated_at: string;
  business_profile: BusinessProfile;
  semantic_business?: SemanticBusinessRepresentation;
  contradictions?: ContradictionReport[];
  scores: OverallScoreResult;
  story_summary: string;
  what_site_gets_right: string[];
  what_is_holding_it_back: string[];
  primary_strategic_opportunity: string;
  consultant_advice_what_to_ignore: string;
  three_way_comparison: ThreeWayComparison;
  ai_search_matrix: AiSearchQueryEvaluation[];
  findings: Finding[];
  claims?: Claim[];
  code_patches: CodePatch[];
  roadmap_7_days: RoadmapItem[];
  roadmap_30_days: RoadmapItem[];
  roadmap_90_days: RoadmapItem[];
  top_10_actions?: ExecutiveTopActionsPlan;
  regression_report?: RegressionReport;
  evidence_taxonomy?: EvidenceTaxonomyReport;
  visual_ux?: VisualUxInspectionReport;
  lifecycle_revenue?: LifecycleRevenueIntelligence;
  telemetry: TelemetryData;
  crawl_manifest?: CrawlManifest;
  page_reports?: PageReport[];
  crawl_summary: Record<string, unknown>;
  agent_execution_trace: Array<{ step: string; agent: string; details: unknown }>;
  policy_pack?: string;
  honest_scores?: HonestScores;
  agent_readiness?: {
    score: number | null;
    summary: string;
    signals: Array<{ key: string; status: string; summary: string }>;
  };
  ai_visibility_scorecard?: {
    status: string;
    measurement_note?: string;
    engines_measured: number;
    engines_requested: number;
    queries: number;
    repeats: number;
    successful_runs: number;
    failed_runs: number;
    mention_rate_pct?: number | null;
    citation_rate_pct?: number | null;
    citation_accuracy_pct?: number | null;
    entity_accuracy_pct?: number | null;
    service_recognition_pct?: number | null;
    icp_recognition_pct?: number | null;
    pricing_recognition_pct?: number | null;
    competitor_visibility_pct?: number | null;
    hallucination_rate_pct?: number | null;
    source_consistency_pct?: number | null;
    not_measured_reason?: string | null;
  };
  geo_readiness?: {
    visibility_status: string;
    visibility_message: string;
    headline: string;
    questions_total: number;
    questions_supported: number;
    questions_partial: number;
    questions_unsupported: number;
    questions_conflicting: number;
    questions: Array<{
      question_key: string;
      question: string;
      status: string;
      evidence_url?: string | null;
      evidence_snippet?: string | null;
      why: string;
    }>;
    dimensions: Array<{ key: string; label: string; band: string; summary: string }>;
    schema_types: string[];
    extractability_score?: number;
    entity_consistency?: any;
    claims_analysis?: any;
    question_graph_50?: any;
    citation_passages?: any;
    schema_crosscheck?: any;
  };
  commercial_evaluations?: CommercialQueryEvaluation[];
  competitor_bakeoff?: CompetitorBakeoffResult;
  character_safe_copy?: CharacterSafeCopy;
  whatsapp_summary?: string;
  exploratory_hypotheses?: Finding[];
  scoring_rubric_version?: string;
  visual_intelligence?: VisualIntelligencePayload;
  evidence_ledger?: Record<string, EvidenceLedgerItem>;
  integrity_repairs_log?: Array<{ timestamp: string; action: string; description: string; auditable: boolean; }>;
  certification_status?: 'CERTIFIED' | 'DEGRADED_SECTIONS_WITHHELD';
  withheld_sections?: Array<{ check: string; section: string; reason: string; }>;
  meta_rollup?: MetaBucketRollup;
  heading_hierarchy?: HeadingHierarchyRollup;
  host_and_redirects?: RedirectAuditReport;
  click_depth?: ClickDepthReport;
  orphan_pages?: OrphanPageReport;
  anchor_text_audit?: AnchorTextAudit;
  form_audit?: FormAuditReport;
  media_assets?: MediaAssetAuditReport;
  per_engine_geo?: PerEngineAiMatrix;
  security_audit?: SecurityAuditReport;
  schema_validation?: SchemaValidationReport;
  remediation_patches?: RemediationPatch[];
  canonical_audit?: CanonicalAuditRollup;
  http_status_breakdown?: HttpStatusBreakdown;
  competitor_seo_parity?: CompetitorSeoParityMatrix;
}

export interface CanonicalAuditItem {
  url: string;
  canonical_url?: string | null;
  status: 'self' | 'canonicalized' | 'missing' | 'broken' | 'relative' | 'multiple' | 'cross_domain' | string;
  detail: string;
  is_issue: boolean;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO' | string;
}

export interface CanonicalAuditRollup {
  total_pages_evaluated: number;
  self_canonical_count: number;
  canonicalized_count: number;
  missing_canonical_count: number;
  broken_canonical_count: number;
  relative_canonical_count: number;
  multiple_canonical_count: number;
  cross_domain_canonical_count: number;
  canonical_health_score: number;
  items: CanonicalAuditItem[];
  summary: string;
}

export interface HttpStatusItem {
  url: string;
  status_code: number;
  status_class: '2xx' | '3xx' | '4xx' | '5xx' | string;
  status_text: string;
  redirect_target?: string | null;
  inlinks_count: number;
}

export interface BrokenLinkRecord {
  source_url: string;
  target_url: string;
  anchor_text: string;
  status_code: number;
  error_type: string;
}

export interface HttpStatusBreakdown {
  total_urls_checked: number;
  count_2xx: number;
  count_3xx: number;
  count_4xx: number;
  count_5xx: number;
  status_health_score: number;
  pages_2xx: HttpStatusItem[];
  pages_3xx: HttpStatusItem[];
  pages_4xx: HttpStatusItem[];
  pages_5xx: HttpStatusItem[];
  broken_links: BrokenLinkRecord[];
  summary: string;
}

export interface CompetitorSeoParityProfile {
  domain: string;
  brand_name: string;
  is_target: boolean;
  pages_sampled: number;
  technical_health_score: number;
  onpage_score: number;
  content_depth_score: number;
  schema_score: number;
  overall_seo_score: number;
  avg_ttfb_ms: number;
  http_200_rate_pct: number;
  title_optimal_pct: number;
  meta_optimal_pct: number;
  h1_health_pct: number;
  avg_word_count: number;
  schema_types_count: number;
  has_breadcrumbs: boolean;
  modern_image_pct: number;
  summary_verdict: string;
}

export interface CompetitorSeoParityMatrix {
  target_domain: string;
  competitors: CompetitorSeoParityProfile[];
  target_rank: number;
  peer_avg_seo_score: number;
  top_advantages: string[];
  critical_deficits: string[];
  strategic_takeaway: string;
}

export interface SchemaIssue {
  url: string;
  schema_type: string;
  severity: 'ERROR' | 'WARNING';
  field: string;
  message: string;
}

export interface SchemaValidationReport {
  total_pages_with_schema: number;
  total_entities_detected: number;
  valid_entities_count: number;
  entities_with_errors_count: number;
  entities_with_warnings_count: number;
  detected_types: string[];
  issues: SchemaIssue[];
  summary: string;
}

export interface SecurityAuditReport {
  target_domain?: string;
  score?: number;
}

export interface MetaBucketItem {
  url: string;
  text?: string | null;
  char_length: number;
  pixel_length: number;
}

export interface MetaBucketRollup {
  total_pages_evaluated: number;
  missing_titles: MetaBucketItem[];
  too_short_titles: MetaBucketItem[];
  optimal_titles: MetaBucketItem[];
  too_long_titles: MetaBucketItem[];
  duplicate_titles: MetaBucketItem[];
  title_issue_count: number;
  missing_descriptions: MetaBucketItem[];
  too_short_descriptions: MetaBucketItem[];
  optimal_descriptions: MetaBucketItem[];
  too_long_descriptions: MetaBucketItem[];
  duplicate_descriptions: MetaBucketItem[];
  description_issue_count: number;
  truncated_pixel_titles?: MetaBucketItem[];
  truncated_pixel_descriptions?: MetaBucketItem[];
  h1_title_collision_count?: number;
  h1_title_collision_urls?: string[];
  title_summary: string;
  description_summary: string;
}

export interface HeadingIssueItem {
  url: string;
  headings: string[];
  issue_type: string;
  detail: string;
}

export interface HeadingHierarchyRollup {
  total_pages_evaluated: number;
  missing_h1: HeadingIssueItem[];
  multiple_h1: HeadingIssueItem[];
  short_h1: HeadingIssueItem[];
  long_h1: HeadingIssueItem[];
  duplicate_h1: HeadingIssueItem[];
  hierarchy_violations: Array<Record<string, any>>;
  outline_tree_sample: Array<Record<string, any>>;
  total_heading_issues: number;
  h1_health_score: number;
}

export interface RedirectHop {
  status: number;
  url: string;
  location?: string | null;
}

export interface HostVariantProbeResult {
  origin_url: string;
  final_destination: string;
  status_code: number;
  hops: RedirectHop[];
  hop_count: number;
  proper_canonical_redirect: boolean;
  error?: string | null;
}

export interface RedirectAuditReport {
  target_domain: string;
  canonical_destination: string;
  host_variants: Record<string, HostVariantProbeResult>;
  proper_301_consolidation: boolean;
  has_chain_gt_1_hop: boolean;
  has_redirect_loop: boolean;
  redirects_to_4xx: boolean;
  chains_recorded: Array<Record<string, any>>;
  summary: string;
}

export interface ClickDepthReport {
  homepage_url: string;
  total_pages_analyzed: number;
  depth_1_count: number;
  depth_2_count: number;
  depth_3_count: number;
  depth_4_plus_count: number;
  max_click_depth: number;
  pages_by_depth: Record<string, string[]>;
  depth_distribution_pct: Record<string, number>;
  high_depth_warning_count: number;
}

export interface OrphanPageReport {
  total_sitemap_urls: number;
  total_crawled_urls: number;
  orphan_urls: string[];
  orphan_count: number;
  orphan_percentage: number;
  summary: string;
}

export interface AnchorTextAudit {
  total_links_analyzed: number;
  generic_anchor_count: number;
  low_equity_terms_found: Array<{ term: string; count: number }>;
  flagged_anchor_instances: Array<{ url: string; anchor: string; reason: string }>;
  summary: string;
}

export interface FormAuditItem {
  page_url: string;
  form_id?: string | null;
  form_action?: string | null;
  input_count: number;
  missing_labels_count: number;
  input_types: string[];
  submit_button_text: string;
  has_captcha_or_honeypot: boolean;
  has_confirmation_destination: boolean;
  friction_risk: string;
}

export interface FormAuditReport {
  total_forms_detected: number;
  forms: FormAuditItem[];
  forms_with_missing_labels: number;
  forms_without_captcha: number;
  forms_without_confirmation: number;
  cro_friction_grade: string;
  friction_score: number;
  actionable_remedies: string[];
}

export interface MediaAssetItem {
  url: string;
  page_url: string;
  alt_text?: string | null;
  has_alt: boolean;
  is_empty_alt: boolean;
  has_dimensions: boolean;
  format: string;
  is_modern_format: boolean;
  is_insecure_http: boolean;
}

export interface MediaAssetAuditReport {
  total_images_analyzed: number;
  missing_alt_count: number;
  empty_alt_count: number;
  missing_dimensions_count: number;
  modern_format_count: number;
  non_modern_format_count: number;
  mixed_content_count: number;
  mixed_content_urls: string[];
  cls_risk_images: Array<Record<string, string>>;
  summary: string;
}

export interface PerEngineAiScore {
  engine_name: string;
  score: number;
  grade: string;
  readiness_band: string;
  strengths: string[];
  critical_gaps: string[];
  recommended_fixes: string[];
}

export interface InformationGainReport {
  score: number;
  grade: string;
  has_proprietary_statistics: boolean;
  has_benchmark_tables: boolean;
  has_methodology_section: boolean;
  has_executive_quotes: boolean;
  fluff_ratio_score: number;
  original_data_signals: string[];
  commodity_fluff_signals: string[];
  recommendations: string[];
}

export interface AiBotDirectivesReport {
  robots_txt_status: string;
  gptbot_allowed: boolean;
  perplexitybot_allowed: boolean;
  claudebot_allowed: boolean;
  google_extended_allowed: boolean;
  llms_txt_found: boolean;
  llms_txt_url?: string | null;
  llms_txt_generated?: string | null;
  recommendations: string[];
}

export interface PerEngineAiMatrix {
  chatgpt: PerEngineAiScore;
  perplexity: PerEngineAiScore;
  google_aio: PerEngineAiScore;
  claude_gemini: PerEngineAiScore;
  overall_engine_score: number;
  overall_engine_grade: string;
  information_gain: InformationGainReport;
  ai_bot_directives: AiBotDirectivesReport;
}

export interface ChartSpecification {
  id: string;
  chart_type: 'radar' | 'latency_curve' | 'defect_donut' | 'engine_comparison_bar' | 'journey_funnel' | 'content_depth_bar' | 'count_bar';
  title: string;
  subtitle: string;
  ai_insight: string;
  category: string;
  data: Record<string, any>;
  config?: Record<string, any>;
  is_recommended?: boolean;
  priority_order?: number;
}

export interface SpotlightMetric {
  id: string;
  label: string;
  value: string | number;
  unit?: string;
  change_indicator?: string;
  status: 'good' | 'warning' | 'bad' | 'neutral';
  significance: string;
  category: string;
}

export interface VisualIntelligencePayload {
  ai_rationale: string;
  audit_case_profile: string;
  selected_visualizations: ChartSpecification[];
  spotlight_metrics: SpotlightMetric[];
  available_customizations?: string[];
  generated_at: string;
}

export interface AnalysisSummary {
  analysis_id: string;
  website_url: string;
  domain: string;
  status: string;
  progress: number;
  score_overall?: number | null;
  score_band?: string | null;
  started_at: string;
  completed_at?: string | null;
  page_count: number;
}

export interface AnalysisRun {
  analysis_id: string;
  website_url: string;
  status: string;
  progress_percentage: number;
  current_step: string;
  created_at: string;
  updated_at: string;
  error?: string;
  report?: ExecutiveReport;
  telemetry: TelemetryData;
}

export interface PricingPlanLimits {
  max_pages?: number;
  ai_scenarios?: number;
  competitor_analysis?: boolean;
  remediation_code_patches?: boolean;
  executive_story_deck?: boolean;
}

export interface PricingPlan {
  id: string;
  name: string;
  tier: string;
  category: 'one_time' | 'recurring';
  price_inr: number;
  price_display: string;
  price_usd: number;
  badge?: string;
  description: string;
  popular?: boolean;
  deliverables: string[];
  limits?: PricingPlanLimits;
  billing_period?: string;
}

export interface PlansCatalog {
  one_time_audits: PricingPlan[];
  continuous_monitoring: PricingPlan[];
  default_flagship: string;
  currency: string;
  gst_rate: number;
  value_proposition: string;
}

export interface PaymentOrder {
  order_id: string;
  amount_inr: number;
  amount_paise: number;
  currency: string;
  key_id: string;
  plan_id: string;
  plan_name: string;
  target_url: string;
  is_test_mode: boolean;
  gst_amount_inr: number;
  total_amount_inr: number;
}

export interface PaymentVoucher {
  success: boolean;
  voucher_code: string;
  plan_id: string;
  plan_name: string;
  target_url: string;
  payment_id: string;
  timestamp: number;
  message: string;
}

export type TabId =
  | 'overview'
  | 'seo'
  | 'geo'
  | 'aeo'
  | 'cro'
  | 'competitors'
  | 'pages'
  | 'findings'
  | 'patches'
  | 'roadmap'
  | 'verification'
  | 'report'
  | 'plans'
  // Legacy aliases for backward compatibility
  | 'search_intelligence'
  | 'ai_search_intelligence'
  | 'website_experience'
  | 'conversion_intelligence'
  | 'brand_entity_intelligence'
  | 'perspectives'
  | 'ai_citations'
  | 'lead_gen'
  | 'search_console'
  | 'ai_search';

export interface PillarScoreData {
  id: TabId;
  name: string;
  shortName: string;
  categoryTag: string;
  score: number | null;
  grade: string;
  health: 'GOOD' | 'FAIR' | 'POOR';
  headline: string;
  summary: string;
  highlights: string[];
  findingsCount: number;
}

export interface WebsiteIntelligenceRollup {
  // Enterprise separated pillars
  seo: PillarScoreData;
  geo: PillarScoreData;
  aeo: PillarScoreData;
  cro: PillarScoreData;
  competitors: PillarScoreData;
  // Legacy pillar mappings for backward compatibility
  search_intelligence: PillarScoreData;
  ai_search_intelligence: PillarScoreData;
  website_experience: PillarScoreData;
  conversion_intelligence: PillarScoreData;
  brand_entity_intelligence: PillarScoreData;
  sxo_score: number | null;
  sxo_health: 'GOOD' | 'FAIR' | 'POOR';
}

export type AppView =
  | 'home'
  | 'pricing'
  | 'login'
  | 'signup'
  | 'forgot'
  | 'reset'
  | 'account'
  | 'contact'
  | 'team'
  | 'system';

export type OrgRole = 'system_admin' | 'owner' | 'admin' | 'analyst' | 'viewer' | 'auditor';

export interface AuthUser {
  user_id: string;
  email: string;
  full_name: string;
  org_id: string;
  org_name: string;
  role: OrgRole;
  role_label: string;
  is_system: boolean;
  permissions: string[];
  auth_provider?: string;
  avatar_url?: string;
}

export interface AuthSSOProvider {
  name: string;
  configured: boolean;
  client_id_env: string;
  redirect_uri: string;
}

export interface AuthProvidersResponse {
  providers: {
    google: AuthSSOProvider;
    github: AuthSSOProvider;
    [key: string]: AuthSSOProvider;
  };
}

export interface ContactRecord {
  contact_id: string;
  name: string;
  email: string;
  phone?: string;
  company?: string;
  website?: string;
  job_title?: string;
  message: string;
  created_at: number;
}

export interface OrgSummary {
  org_id: string;
  name: string;
  slug: string;
  plan: string;
  is_system: boolean;
  is_active: boolean;
  member_count: number;
}

export interface AdminMember {
  user_id: string;
  email: string;
  full_name: string;
  role: OrgRole;
  role_label: string;
  is_active: boolean;
  is_system: boolean;
  created_at: number;
  last_login_at?: number | null;
  deleted_at?: number | null;
}

export interface AdminOrganization {
  org_id: string;
  name: string;
  slug: string;
  plan: string;
  is_system: boolean;
  is_active: boolean;
  created_at: number;
  deleted_at?: number | null;
  member_count: number;
  member_total: number;
  role_mix: Record<string, number>;
  audit_count: number;
  avg_score?: number | null;
  members: AdminMember[];
}

export interface PlatformOverview {
  generated_at: number;
  organizations: {
    total: number;
    active: number;
    deleted: number;
    customer: number;
    system: number;
  };
  users: {
    total: number;
    active: number;
    deleted: number;
    signed_up_24h: number;
    signed_up_7d: number;
    signed_up_30d: number;
    logged_in_24h: number;
  };
  plan_mix: Record<string, number>;
  role_mix: Record<string, number>;
  audits: { total: number; last_7d: number; last_30d: number };
  contacts: { total: number; last_7d: number };
  database: {
    path: string;
    size_bytes: number;
    tables: Record<string, number>;
    live_sessions: number;
  };
}

export type PatchRiskLevel = 'SAFE_AUTO' | 'HUMAN_APPROVAL' | 'DEVELOPER_REQUIRED';
export type PatchOperation = 'REPLACE' | 'INSERT_HEAD' | 'INSERT_BODY' | 'UPDATE_JSONLD' | 'UPDATE_FILE' | 'APPEND_ROBOTS';
export type PatchApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'APPLIED' | 'ROLLED_BACK' | 'FAILED';
export type ConnectorType =
  | 'wordpress'
  | 'github'
  | 'shopify'
  | 'webflow'
  | 'google_search_console'
  | 'google_analytics_4'
  | 'crm'
  | 'dataforseo'
  | 'live_ai_search'
  | 'crux'
  | 'generic';
export type ConnectorHealthStatus = 'connected' | 'disconnected' | 'error' | 'unauthorized';

export interface RemediationPatch {
  patch_id: string;
  finding_id: string;
  title: string;
  category: Category;
  risk_level: PatchRiskLevel;
  target_url: string;
  target_file: string;
  operation: PatchOperation;
  before_snippet?: string;
  after_snippet: string;
  explanation: string;
  confidence: number;
  approval_status: PatchApprovalStatus;
  approver?: string;
  approved_at?: string;
  applied_via?: string;
  applied_at?: string;
  pr_url?: string;
  pr_number?: number;
  verification_status: string;
  verification_notes?: string;
  citation_score_delta?: number;
  metadata_payload?: Record<string, any>;
}

export interface Integration {
  integration_id: string;
  org_id: string;
  workspace_id: string;
  provider: ConnectorType;
  name: string;
  target_url: string;
  status: ConnectorHealthStatus;
  scopes: string[];
  repository?: string;
  branch?: string;
  created_at: string;
  last_synced_at?: string;
  error_message?: string;
  settings?: Record<string, any>;
}

export interface RoiInput {
  avg_deal_size_inr: number;
  monthly_visitors: number;
  current_conversion_rate: number;
  expected_traffic_lift_pct: number;
  expected_cro_lift_pct: number;
}

export interface RoiEstimate {
  monthly_visitors: number;
  avg_deal_size_inr: number;
  current_monthly_leads: number;
  current_annual_revenue_inr: number;
  projected_annual_revenue_inr: number;
  annual_upside_inr: number;
  roi_multiple: number;
  high_impact_opportunities: string[];
  methodology: string;
}

export interface VerificationResult {
  patch_id: string;
  target_url: string;
  is_resolved: boolean;
  verified_at: string;
  details: string;
  before_score: number;
  after_score: number;
  score_delta: number;
}
