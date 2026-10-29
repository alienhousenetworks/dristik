# Agent catalog

The pool that `AgentPool` runs is `SPECIALIST_AGENTS_V3` in `app.agents.runtime.registry`. Wave order is `topological_waves` in `app.orchestration.dependency_resolver`.

Domain wrappers, which call that runtime, are:

- SEO: `app.agents.seo.technical`, `content`, `internal_linking`, `structured_data`
- GEO: `app.agents.geo.citation_analyzer`, `readiness_analyzer`, `information_gain`, `engine_analyzer`
- AEO: `app.agents.aeo.direct_answers`, `conversational_intent`, `consensus_analyzer`
- CRO: `app.cro.agents` (`conversion_analyzer`, `form_abandonment`, `trust_analyzer`, `visual_ux`)
- Discovery: `app.agents.discovery.brand_discovery`, `business_discovery`, `product_discovery`, `crawl_discovery`
- Deck: `app.agents.deck.slide_builder`, `pptx_generator`
- Reasoners: `app.agents.runtime.reasoner`

Older filenames such as `technical_seo_agent` and `reasoners` import these modules.

Gemini and Claude capability ids in the pool are not separate from `ai_search.google.v3` and `ai_search.cross_engine.v3`. Live citation measurement is the gateway catalog in `app.pillars.geo.citation_models`, not a pool simulation.
