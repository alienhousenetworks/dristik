# Dristik architecture

The backend layout and the rules for what each package owns are in [backend/docs/architecture.md](../backend/docs/architecture.md).

The audit measures a representative sample. Scoring, evidence, and report claims follow the live modules named there: `app.scoring`, `app.evidence`, and `app.reports`. Pillars in `app.pillars` call those engines. They do not publish a second composite.

The HTTP application is `app.main`, which mounts `app.api.router.mount_http`.
