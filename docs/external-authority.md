# External Authority & Entity Intelligence

External authority is a separate data pillar. Crawl depth does not limit it. A 3-page or 5-page crawl is only a crawl configuration. Backlinks, search performance, analytics, business profiles, and brand mentions are stored only when a provider returns them.

Dristik does not calculate a universal authority score. Ahrefs Domain Rating, Semrush Authority Score, and Majestic Trust Flow stay labeled with the vendor that produced them. They are not Google ranking metrics and they are not combined.

Missing providers are `NOT_CONNECTED` or `NOT_APPLICABLE`. They are not SEO failures. The crawl audit still completes when a connector is down or disconnected.

The older telemetry connectors under `backend/app/connectors/` are not this engine. Those connectors still return fixture numbers for older tests when a credential is present. This pillar does not read those fixtures.

## What Dristik can measure

| Source | Measured when connected | Not claimed |
| --- | --- | --- |
| Google Search Console | Verified properties, clicks, impressions, CTR, average position, queries, pages, countries, devices, search appearance, sitemaps, optional URL Inspection | A page missing from a sampled query list is not deindexed |
| Google Analytics 4 | Organic users, sessions, engagement, landing pages, key events, revenue when the property returns it | Rankings, backlinks, or a single attribution truth |
| Bing Webmaster | Sites, query stats, traffic, crawl stats, Bing's own link count | Ahrefs, Semrush, or Majestic metrics |
| Ahrefs, Semrush, Majestic | Backlinks, referring domains, and that vendor's own authority metric | A shared authority score |
| DataForSEO / SerpAPI | Backlinks or SERP rows, including a knowledge-graph element only when the payload contains one | Knowledge Graph presence without that element |
| Google Business Profile | Search and Maps impressions, website clicks, calls, direction requests, bookings and menu interactions when returned | An SEO defect when the business is non-local |
| Citations | NAP comparison against the business profile you saved, missing rows only for directories you listed | That a directory is authoritative because it exists |
| Brand mentions | Linked, unlinked, potential-entity, and unverified mentions | Sentiment, unless a provider that returns sentiment is explicitly enabled |

Evidence basis on each finding is `DIRECT_PROVIDER_EVIDENCE`, `INFERRED`, or `UNVERIFIED`. Coverage states are `MEASURED`, `PARTIALLY_MEASURED`, `NOT_CONNECTED`, `NOT_APPLICABLE`, `UNAVAILABLE`, and `INFERRED`.

## What Dristik cannot measure from HTML

Referring domains, lost links, organic clicks, GA4 key events, Business Profile actions, and unlinked brand mentions. The report says the provider is not connected instead of assigning a low score.

## Storage

SQLite database `EXTERNAL_AUTHORITY_DB_PATH` (default `data/external_authority.db`), separate from the audit database.

Tables: `external_connections`, `external_accounts`, `external_properties`, `external_snapshots`, `external_raw_payloads`, `external_records`, `external_profiles`, `oauth_states`, `external_jobs`.

Views: `search_performance_records`, `backlink_records`, `referring_domain_records`, `brand_mention_records`, `business_listing_records`, `business_profile_metrics`, `entity_signals`, `competitor_signals`.

Snapshots are kept per provider, domain, and period. Supported periods are 7 days, 28 days, 90 days, and 12 months. The same period and end date replaces that snapshot. A later end date is a new snapshot, which is how trends are read.

Raw provider payloads are stored separately from normalized records. Reports do not include tokens.

## Security

`EXTERNAL_INTEGRATION_ENCRYPTION_KEY` is required before any customer credential is stored. The value is a Fernet key or a passphrase. Passphrases are hashed to a key. There is no plaintext fallback.

OAuth is used for Google Search Console, GA4, Business Profile, Bing, and for Ahrefs or Semrush when a client id and secret are configured. API keys are accepted only where the vendor does not require OAuth, or as the documented fallback for Ahrefs, Semrush, Majestic, DataForSEO, SerpAPI, citations, and brand mentions. Dristik does not ask for a provider account password. DataForSEO uses its API login and API password.

Tokens are refreshed when they expire within two minutes and `OAUTH_TOKEN_REFRESH_ENABLED` is true. Disconnect revokes the token when the provider supports revocation and deletes the ciphertext. `OAUTH_DEBUG_LOG_TOKENS` is ignored. Token values are redacted from this package's logs.

## OAuth setup

One Google Cloud OAuth client can serve Search Console, GA4, and Business Profile. Each Connect action requests only that provider's scope:

- Search Console: `https://www.googleapis.com/auth/webmasters.readonly`
- GA4: `https://www.googleapis.com/auth/analytics.readonly`
- Business Profile: `https://www.googleapis.com/auth/business.manage`

Authorized redirect URI:

`http://localhost:8000/api/v1/external-authority/oauth/callback`

Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`, or the existing `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Enable the Search Console API, the Google Analytics Data API and Admin API, and the Business Profile APIs you intend to call.

Bing uses Microsoft identity platform OAuth and the current JSON API at `https://ssl.bing.com/webmaster/api.svc/json`. The retired SOAP API is not called. Scope default: `offline_access https://ssl.bing.com/webmaster/api/.default`.

Ahrefs and Semrush OAuth URLs are settings and can be changed. Without a client id and secret, those two providers accept an API key. Majestic is API-key only.

## Collection cost

`EXTERNAL_COLLECTION_PLAN` is `FREE`, `STANDARD`, or `ADVANCED`.

- FREE: Search Console, GA4, Bing, Business Profile. Default cache 24 hours.
- STANDARD: citations and brand mentions, plus the free providers. Default cache 12 hours.
- ADVANCED: Ahrefs, Semrush, Majestic, DataForSEO, SerpAPI. Default cache 168 hours.

Automatic audit enqueue skips providers above the plan. A manual sync may still collect a connected advanced provider. Audits read stored snapshots. `EXTERNAL_SYNC_ON_AUDIT` defaults to false, so a provider outage cannot fail the crawl.

URL Inspection is off unless `GSC_URL_INSPECTION_ENABLED=true`. Sampled Search Analytics rows are capped by `EXTERNAL_GSC_ROW_LIMIT` (default 250). Hitting the cap marks the snapshot `PARTIALLY_MEASURED`.

## API

Mounted at `/api/v1/external-authority` and `/api/external-authority`.

- `GET /providers`
- `GET /coverage`
- `GET /health`
- `POST /oauth/start`
- `GET /oauth/callback`
- `POST /connect`
- `POST /disconnect`
- `GET /properties`
- `POST /properties/select`
- `GET|PUT /brand`
- `GET|PUT /competitors`
- `GET|PUT /local-business`
- `POST /sync`
- `GET /jobs` and `GET /jobs/{job_id}`
- `GET /report`
- `GET /findings`
- `GET /snapshots`

When a signed-in user is present, `project_id` is that user's organization. Responses never include credentials. Connecting without an encryption key returns HTTP 503.

## Jobs

`sync_gsc_data`, `sync_ga4_data`, `sync_bing_data`, `sync_backlinks`, `sync_gbp_data`, `sync_brand_mentions`, `sync_citations`, `sync_serp`.

Jobs retry rate limits and transient errors with backoff, up to 4 attempts. The idempotency key is project, job, domain, period, and the UTC date. Auth failures mark that provider's token expired and leave the other providers in the job to finish. A failed Ahrefs sync does not fail the crawl audit.

## Report shape

`ExecutiveReport.external_authority` holds the pillar. `universal_authority_score` is always null. Measured, non-info findings can be copied into the audit finding list. They use category `EXTERNAL_AUTHORITY`, which is not part of the composite score weights. Info and not-connected rows stay in the external report.

Example coverage row:

```json
{
  "provider": "ahrefs",
  "display_name": "Ahrefs",
  "connection_status": "NOT_CONNECTED",
  "data_state": "NOT_CONNECTED",
  "note": "Not connected."
}
```

Example finding when Search Console is connected:

```json
{
  "severity": "HIGH",
  "evidence_basis": "DIRECT_PROVIDER_EVIDENCE",
  "provider": "google_search_console",
  "scope": "PERIOD_VERIFIED",
  "title": "Organic search clicks declined 34% over the selected comparison period."
}
```

Example finding when no backlink provider is connected:

```json
{
  "severity": "INFO",
  "data_state": "NOT_CONNECTED",
  "title": "Backlink authority could not be measured because no backlink data provider is connected."
}
```

## Unsupported or limited

- No universal authority score.
- No sentiment unless `BRAND_MENTIONS_SENTIMENT_ENABLED` is true and the provider returns a sentiment field.
- No Knowledge Graph claim without a knowledge-graph element in a connected SERP payload.
- No deindex claim from a page merely missing a Search Analytics sample.
- URL Inspection requires the broader Search Console scope and is disabled by default.
- Citation providers are configurable. No directory is hardcoded as authoritative.
- Competitor gaps are reported only when both domains were collected from the same provider. The wording states the measured difference and does not rank one domain as better.
- DataForSEO in this pillar stays off until `DATAFORSEO_ENABLED=true`, even if a login is present for the older keyword connector.
- SerpAPI stays off until `SERPAPI_ENABLED=true`.
