import { AuditSectionDefinition } from './types';

export const AUDIT_PARTS: Array<{ id: string; title: string }> = [
  { id: 'I', title: 'Executive intelligence and strategic assessment' },
  { id: 'II', title: 'Technical SEO and website infrastructure' },
  { id: 'III', title: 'On-page SEO and content intelligence' },
  { id: 'IV', title: 'Off-page SEO, authority and competitive visibility' },
  { id: 'V', title: 'Specialized SEO and emerging search surfaces' },
  { id: 'VI', title: 'Conversion, analytics and business outcomes' },
  { id: 'VII', title: 'Remediation, validation and continuous improvement' },
  { id: 'A', title: 'Appendices' },
];

function section(number: string, part: string, title: string, checks: string[]): AuditSectionDefinition {
  return { number, part, title, checks };
}

export const AUDIT_SECTIONS: AuditSectionDefinition[] = [
  section('01', 'I', 'Executive summary', [
    'Website and business overview',
    'Primary business objectives',
    'Organic search health summary',
    'Top critical errors and opportunities',
    'Search visibility and traffic trends',
    'Content and authority strengths',
    'AI search visibility summary',
    'Conversion and revenue opportunities',
    'Competitor position overview',
    'Immediate action recommendations',
  ]),
  section('02', 'I', 'Website health and SEO scorecard', [
    'Technical SEO score',
    'On-page SEO score',
    'Content quality score',
    'Backlink and authority score',
    'User experience score',
    'Local SEO score, where applicable',
    'International SEO score, where applicable',
    'AEO and GEO measurement',
    'Measurement confidence and evidence coverage',
  ]),
  section('03', 'I', 'Business and website understanding', [
    'Business model and offerings',
    'Target audience and locations',
    'Website type and platform',
    'Main conversion actions',
    'Search demand aligned with the business',
    'Revenue-critical landing pages',
  ]),
  section('04', 'I', 'Risk and opportunity assessment', [
    'Critical technical risks',
    'Search visibility risks',
    'Content quality risks',
    'Index bloat and crawl waste',
    'Conversion leakage',
    'High-value opportunities from recorded findings',
  ]),
  section('05', 'I', 'Competitive landscape', [
    'Recorded competitors',
    'Keyword overlap only when the same provider measured both domains',
    'Content and landing-page comparison when both sides were crawled',
    'Backlink comparison only from a named provider',
    'AI citation competitors only from a live run',
  ]),
  section('06', 'I', 'Prioritization and business impact', [
    'Issue severity and affected URLs',
    'Implementation effort where recorded',
    '30/60/90-day roadmap items stored on this audit',
    'Owners and deadlines only when assigned',
  ]),
  section('07', 'II', 'Crawlability and discovery', [
    'HTTP responses for crawled URLs',
    'Robots.txt when fetched',
    'Robots meta and X-Robots-Tag when present on a crawled page',
    'Internal links in the sample',
    'Sitemap discovery',
    'Orphan pages only when a sitemap and crawl graph were both stored',
  ]),
  section('08', 'II', 'Indexability and index coverage', [
    'Indexable versus non-indexable URLs in the sample',
    'Noindex, canonical conflicts, soft 404s, and duplicates when classified',
    'Search Console coverage only for URLs with a stored coverage state',
    'Important pages missing from the index only when inspection data exists',
  ]),
  section('09', 'II', 'URL architecture and normalization', [
    'Path depth of crawled URLs',
    'HTTP and HTTPS mix',
    'Query parameters on crawled URLs',
    'Trailing-slash mix when both forms appear',
  ]),
  section('10', 'II', 'Canonicalization and duplicate control', [
    'Canonical tag on crawled pages',
    'Canonical destination when a canonical audit ran',
    'Conflicting canonical signals recorded by the audit',
  ]),
  section('11', 'II', 'Redirects and broken URLs', [
    '3xx responses in the sample',
    'Redirect chains when the redirect audit ran',
    'Broken internal links when a link audit stored them',
    'HTTP to HTTPS host variants when probed',
  ]),
  section('12', 'II', 'XML sitemaps', [
    'Sitemap discovery',
    'Sitemap URL when recorded',
    'Indexable URL inclusion only when sitemap URLs were fetched',
  ]),
  section('13', 'II', 'Site architecture and internal link structure', [
    'Click depth from crawled links',
    'Internal link counts on crawled pages',
    'Anchor text when an anchor audit ran',
    'Orphan URLs when both the sitemap and the crawl graph exist',
  ]),
  section('14', 'II', 'HTTP status, hosting and server reliability', [
    '2xx, 3xx, 4xx, and 5xx counts',
    'HTTPS on crawled URLs',
    'Time to first byte on crawled URLs',
    'CDN, cache-control, and geographic delivery only when those headers or probes were stored',
  ]),
  section('15', 'II', 'JavaScript SEO and rendering', [
    'Raw HTML versus rendered DOM only when a render delta was stored',
    'Content that required JavaScript only when that comparison exists',
    'Blocked resources when the indexation record lists them',
  ]),
  section('16', 'II', 'Core Web Vitals and page speed', [
    'Field LCP, INP, and CLS only from a stored field source',
    'Lab timings only when a real Lighthouse run was stored',
    'Crawl TTFB is reported separately and is not a Core Web Vital',
  ]),
  section('17', 'II', 'Mobile SEO and responsive behavior', [
    'Viewport tag on crawled pages',
    'Mobile and desktop field data only when both were stored',
    'Tap targets, interstitials, and device parity were not assumed',
  ]),
  section('18', 'II', 'HTTPS, security and website integrity', [
    'HTTPS on crawled URLs',
    'Security response headers when the crawl stored them',
    'This is a header baseline, not a penetration test or a malware certification',
  ]),
  section('19', 'II', 'Structured data and search appearance', [
    'Schema types found in the crawled sample',
    'Validation errors when a schema validation report ran',
    'Rich-result eligibility is not claimed from valid syntax alone',
  ]),
  section('20', 'III', 'Title tags and search snippets', [
    'Missing, duplicate, and length of titles in the sample',
    'Meta descriptions present in the sample',
    'Search-result title rewrites only when Search Console supplies them',
  ]),
  section('21', 'III', 'Headings and document structure', [
    'H1 presence and count',
    'Heading hierarchy when that rollup ran',
    'H1 to title alignment only when both texts were stored',
  ]),
  section('22', 'III', 'Keyword research and search intent', [
    'Queries from a connected Search Console property',
    'Keyword to URL mapping only for those queries',
    'Volume, difficulty, and seasonality only from a named provider and date',
  ]),
  section('23', 'III', 'Content quality and usefulness', [
    'Extracted word count',
    'Recorded content findings',
    'Originality, expertise, and editorial review only when the page states them',
  ]),
  section('24', 'III', 'Search intent and content-to-query alignment', [
    'On-page question assessments stored for this crawl',
    'Intent mismatch only when a content module recorded it',
    'Irrelevant traffic only when analytics is connected',
  ]),
  section('25', 'III', 'Topical authority and semantic coverage', [
    'Topic notes from the topical module when it ran on the sample',
    'Competing pages in the sample',
    'No topical score is treated as a ranking',
  ]),
  section('26', 'III', 'Content duplication, cannibalization and decay', [
    'Duplicate titles and headings in the sample',
    'Query-level cannibalization only when one Search Console query maps to more than one URL',
    'Traffic decay only when a historical Search Console comparison exists',
  ]),
  section('27', 'III', 'Internal linking and anchor text', [
    'Internal link counts',
    'Generic anchors when an anchor audit ran',
    'Links to redirects when that graph was stored',
  ]),
  section('28', 'III', 'Images and visual SEO', [
    'Images missing alt text on crawled pages',
    'Image file names, formats, and sitemaps only when stored',
  ]),
  section('29', 'III', 'Video SEO', [
    'VideoObject schema in the sample',
    'Transcripts, video sitemaps, and watch-page indexing only when those sources were fetched',
  ]),
  section('30', 'III', 'Content governance and editorial operations', [
    'Editorial calendar, ownership, and review workflow',
    'These operations are not visible to a crawl',
  ]),
  section('31', 'IV', 'Backlink profile', [
    'Referring domains and anchors only from a named provider',
    'Vendor metrics keep the vendor name',
    'No toxicity score is invented from a missing provider',
  ]),
  section('32', 'IV', 'Digital PR, brand mentions and authority signals', [
    'Unlinked mentions and press coverage only from a measured source',
    'Brand sentiment is not inferred from HTML',
  ]),
  section('33', 'IV', 'Competitor SEO benchmarking', [
    'Competitors that were actually measured',
    'Keyword and backlink gaps only when the same provider measured both domains',
    'An uncrawled rival stays blank',
  ]),
  section('34', 'IV', 'SERP visibility and ranking performance', [
    'Search Console clicks, impressions, CTR, and position when connected',
    'SERP features and rank history only from the provider that measured them',
  ]),
  section('35', 'IV', 'Local SEO and Google Business Profile', [
    'Selected only for a local or multi-location business, or when a local module ran',
    'Name, address, and phone conflicts in the sample',
    'Google Business Profile fields only when the module stored them',
    'Map-pack rank is not invented',
  ]),
  section('36', 'IV', 'International and multilingual SEO', [
    'hreflang on crawled pages or a stored international module',
    'Return tags and x-default only when the module checked them',
    'Geotargeting is not inferred from a country name in the footer',
  ]),
  section('37', 'IV', 'Search spam and policy compliance', [
    'Pattern risks recorded as findings',
    'A missing check is not a clean bill of compliance',
    'No manual action is claimed unless Search Console reports one',
  ]),
  section('38', 'V', 'E-commerce SEO', [
    'Selected for a catalog business or when product schema was crawled',
    'Product URLs in the sample',
    'Merchant Center, price, and availability feeds only when connected',
  ]),
  section('39', 'V', 'Publisher, editorial and news SEO', [
    'Selected for a publisher or when news schema was crawled',
    'Article dates and author markup in the sample',
    'Google News visibility only when a source reports it',
  ]),
  section('40', 'V', 'Programmatic SEO and large-scale websites', [
    'Selected when a large URL space was discovered',
    'The crawl remains a sample',
    'Template quality gates are not claimed for unfetched URLs',
  ]),
  section('41', 'V', 'SaaS, B2B and lead-generation SEO', [
    'Selected when the business profile is SaaS, B2B, or lead generation',
    'Crawled landing pages, pricing, and forms in the sample',
    'CRM pipeline is not invented',
  ]),
  section('42', 'V', 'App store optimization and app discovery', [
    'Included only when an app listing or app link was in scope',
    'Store creative, ratings, and install funnels otherwise stay out of this audit',
  ]),
  section('43', 'V', 'Accessibility and semantic experience', [
    'Automated checks when an accessibility screen ran',
    'Not a WCAG certification and not a ranking score',
  ]),
  section('44', 'V', 'Voice, conversational and multimodal search', [
    'Voice and visual search are reported only from queries that were actually run',
  ]),
  section('45', 'V', 'Answer engine optimization', [
    'On-page question coverage, answerability, and claim grounding',
    'A completed assessment is not an answered question',
    'Live answer appearances stay in the citation section',
  ]),
  section('46', 'V', 'Generative engine optimization', [
    'On-page extractability of the crawled pages',
    'Not a live citation rate and not a per-engine rank',
  ]),
  section('47', 'V', 'AI search visibility and citation intelligence', [
    'Engines actually queried, prompt count, and repeat count',
    'Mention rate, citation rate, and competitor visibility when returned',
    'Google AI Overviews, Google AI Mode, and Bing Copilot stay unqueried unless those products were queried',
    'Citation accuracy stays blank until a span check exists',
  ]),
  section('48', 'VI', 'Google Search Console intelligence', [
    'Clicks, impressions, CTR, and average position for the connected property',
    'Query and page rows that were stored',
    'A disconnected property is not shown as zero clicks',
  ]),
  section('49', 'VI', 'Analytics and conversion tracking', [
    'GA4 sessions and landing pages when connected',
    'Key events when the property returned them',
    'Consent, attribution, and ecommerce integrity only when those checks ran',
  ]),
  section('50', 'VI', 'Conversion rate optimization', [
    'On-page CTA and form observations from the crawl',
    'A key-event rate only when landing pages, key events, and sessions exist',
    'That rate is not a 0–100 grade',
  ]),
  section('51', 'VI', 'Organic revenue and attribution', [
    'Revenue, pipeline, and acquisition cost only from a connected source that reports them',
    'Key events are not labeled as revenue',
  ]),
  section('52', 'VI', 'Forecasting and opportunity modeling', [
    'No rank, traffic, or revenue forecast is produced',
    'Assumptions are not presented as expected gains',
  ]),
  section('53', 'VII', 'Detailed issue register and remediation plan', [
    'Finding id, severity, evidence, and recommendation',
    'Scope label: page, sample, or inference',
    'Root cause only when the finding establishes one',
  ]),
  section('54', 'VII', 'Post-fix verification and regression testing', [
    'Before-and-after checks stored on a finding',
    'Verified, partial, and unverified outcomes',
    'A patch suggestion is not a completed retest',
  ]),
  section('55', 'VII', 'Monitoring, governance and ongoing SEO operations', [
    'A stored comparison with an earlier audit',
    'Scheduled monitoring is not claimed from a single audit',
  ]),
  section('A', 'A', 'Audit scope', [
    'Domain, crawl limit, languages, and exclusions',
  ]),
  section('B', 'A', 'Methodology', [
    'What was crawled, which connectors ran, and how a section status is chosen',
  ]),
  section('C', 'A', 'URL inventory', [
    'Crawled URLs and discovered count when stored',
  ]),
  section('D', 'A', 'Page-level audit', [
    'Per-URL findings for crawled pages',
  ]),
  section('E', 'A', 'Keyword inventory', [
    'Queries from Search Console or a named rank provider',
  ]),
  section('F', 'A', 'Competitor inventory', [
    'Competitors selected for this audit and why they were included',
  ]),
  section('G', 'A', 'Backlink inventory', [
    'Referring domains from a named provider',
  ]),
  section('H', 'A', 'Structured data results', [
    'Schema types and validation errors in the sample',
  ]),
  section('I', 'A', 'Performance evidence', [
    'Field versus lab source, device, and date when stored',
  ]),
  section('J', 'A', 'Search Console evidence', [
    'Property, period, and available rows',
  ]),
  section('K', 'A', 'AI benchmark evidence', [
    'Engines, prompts, repeats, and surfaces that were not queried',
  ]),
  section('L', 'A', 'Remediation backlog', [
    'Finding ids, severity, and verification status',
  ]),
  section('M', 'A', 'Change log', [
    'Comparison with a previous audit when one was stored',
  ]),
  section('N', 'A', 'Limitations', [
    'Sample size, missing integrations, and conclusions the audit does not make',
  ]),
  section('O', 'A', 'Glossary', [
    'Status labels and the difference between a measurement, an inference, and a missing source',
  ]),
];
