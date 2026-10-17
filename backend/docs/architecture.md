# Backend architecture

Dristik audits a representative sample of a site. The default crawl is 5 pages. Findings are about the fetched pages. A missing connector stays unmeasured.

## Pillars

`app.pillars` is the domain boundary. Each pillar package exposes `pillar.py` and the service that pillar owns. The registry maps `PillarId` to those classes.

| Pillar | Entry | Engine it calls |
| --- | --- | --- |
| Crawling | `pillars/crawling` | `app.crawl` |
| SEO | `pillars/seo` | `app.agents.seo` |
| GEO | `pillars/geo` | `app.agents.geo` and the citation catalog |
| AEO | `pillars/aeo` | `app.agents.aeo` |
| CRO | `app/cro` | `app.cro` |
| Remediation | `pillars/remediation` | `app.remediation` |
| Reporting | `pillars/reporting` | `app.reports` |

The sealed score is still `app.scoring.engine`. Pillar `calculate_pillar_score` is the domain helper used by the pillar contract. It is not a second published composite. The published composite is `app.scoring.displayed_score.displayed_composite`.

## Agents

Specialist implementations live under the names in `app.agents` and modular domains:

- SEO: `technical`, `content`, `internal_linking`, `structured_data`
- GEO: `citation_analyzer`, `readiness_analyzer`, `information_gain`, `engine_analyzer`
- AEO: `direct_answers`, `conversational_intent`, `consensus_analyzer`
- CRO: `app.cro.agents` (`conversion`, `form_abandonment`, `trust`, `visual_ux`)
- Discovery: `brand_discovery`, `business_discovery`, `product_discovery`, `crawl_discovery`
- Deck: `slide_builder`, `pptx_generator`
- Runtime: `base_agent`, `reasoner`, `registry`, `execution_context`

The previous module names import those implementations. The specialist pool remains `SPECIALIST_AGENTS_V3` in `app.agents.runtime.registry`.

## Other boundaries

- Crawl URL rules: `app.crawl.url_frontier`, `robots`, `deduplication`
- Evidence: `graph`, `store`, `coverage`, `provenance`, `contradiction_detector`, `evidence_validator`
- Orchestration: `agent_pool`, `pipeline_dag`, `planner`, `integrity_gate`, `execution_manager`, `dependency_resolver`
- HTTP: `app.api.router.mount_http`. `app.api.v1.router` lists those same routers. `app.api.v1.endpoints` re-exports them.
- Identity: opaque session tokens in `app.identity.jwt`. Authorization is `app.identity.authorization`.
- Persistence DTOs: `app.persistence.models`. The orchestrator store remains `app.persistence.repository`.
- Workers: in-process queue and `DristikScheduler`. A Celery broker is not started.

Packages that already owned a live engine stay in place: `intelligence`, `connectors`, `commercial`, `external_authority`, and `seo_audit`. The new modules call them. They do not replace them.
