# Evidence policy

A finding is about the pages that were fetched. The default crawl is a representative sample, not the whole site.

Evidence records live in `app.evidence.store` and `app.evidence.graph`. Hashes are `app.evidence.provenance`. Contradictions are `app.evidence.contradiction_detector`. Gaps are `app.evidence.evidence_validator`.

Do not invent Search Console clicks, GA4 sessions, live citation rates, conversion rates, or Core Web Vitals from HTML. A missing source stays unmeasured. Response time is not Largest Contentful Paint. An automated accessibility check is not a WCAG certificate.

The code that decides this for the published dossier is the scoring and report modules, not a second estimator in the pillar packages.
