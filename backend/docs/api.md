# HTTP API

`app.main` calls `app.api.router.mount_http`. Each live router is mounted at `/api/v1` and `/api`.

Customer reads and writes use the session cookie. A missing session is 401. A run in another organization is 404.

Analysis, findings, crawl progress, and the score explanation are on the analyses router. Report downloads are on the report router from `app.reports.pdf_generator`.

`app.api.v1.endpoints` re-exports those live routers.

Search Console, GA4, and CrUX stay on their connector routes. A disconnected connector is not returned as a zero measurement.
