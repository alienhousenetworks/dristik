# Report specification

Section books:

- SEO: `app.reports.seo_audit_book.render_seo_audit_book`
- GEO: `app.reports.geo_audit_book.render_geo_audit_book`
- AEO: `app.reports.aeo_audit_book.render_aeo_audit_book`
- CRO: `app.cro.reporting.render_cro_audit_book`

`app.reports.report_composer.render_section_book` selects one of those. HTML publication is `PublicationHtmlRenderer`. PDF publication is `PdfPublishingPipeline`.

The SEO Jinja book is `app/reports/templates/seo_audit_book.html`. `audit_book.html` includes that file. Checklist lines are results from the sealed report. A missing connector is not a zero and not a pass.
