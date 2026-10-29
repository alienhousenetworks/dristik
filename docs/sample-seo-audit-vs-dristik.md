# Sample SEO Audit vs Dristik

Source reviewed: `Sample-SEO-Audit-Analysis-Report.pdf` (46 pages, A4).

| Field | Value |
|---|---|
| Title | Sample SEO Audit & Analysis Report |
| Producer | White Label IQ (`whitelabeliq.com`) |
| Sample site | `https://www.abccorp.com/` |
| Stated date | 12 Sep 2025 |
| File created | 23 Sep 2025 (Adobe Illustrator 29.8 → Adobe PDF library 17.00) |
| Compared against | Dristik as implemented in this repo (crawler, analyzers, capability registry, product report) |

This file answers five questions:

1. What the sample report covers and what it claims.
2. Which of those checks Dristik can do today.
3. Which of those checks Dristik does not do.
4. What is weak — in the sample, and in our coverage of the same job.
5. What a professional, industry-standard audit includes for each area.

Dristik is not trying to be a clone of this PDF. The sample is a classic technical-SEO checklist sold as a client PDF. Dristik is an evidence-backed website intelligence audit (SEO + GEO/AEO + conversion + trust) that refuses to invent unmeasured numbers. The comparison below is only about the checks this PDF tries to cover.

---

## 1. What the report mentions

The PDF is a white-label client deliverable. It opens with a cover, a three-page table of contents, a glossary, then one slide-style section per check, and a closing page that claims the fixes will improve rankings, traffic, and “qualified sales.”

It does **not** include keyword research, backlink profile, competitor SERP gaps, content quality scoring, log-file crawl analysis, or a ranked fix list with owners and effort. Almost every section is: a definition, a one- or two-line finding, and sometimes a count or a pie chart.

### 1.1 Sections and the sample’s own findings

Status words below are the report’s words, not Dristik’s judgment.

#### Website indexing and crawlability

| Check | What the sample says |
|---|---|
| GA4 setup | “Set up correctly and displays accurate data.” No property ID, no stream, no event list. |
| Google Search Console setup | Same sentence. No property, no coverage export, no query table. |
| Indexed pages | Indexed 50 (50%), non-indexed 20 (20%), other 30 (30%). No URL list and no reason codes (Crawled – currently not indexed, Duplicate, Soft 404, Blocked by robots, etc.). |
| XML sitemap | An index sitemap is declared in `robots.txt` and “links to all important pages,” but every sitemap URL is `http://` and “needs to be fixed.” |
| SSL / HTTPS | “The website is SSL (HTTPS) secure.” |
| `robots.txt` | File exists and “needs to be optimised based on the SEO standards.” No `Disallow` lines are quoted. |
| `noindex` and `X-Robots-Tag` | No `noindex` on priority landing pages. |
| Custom 404 page | “The appropriate 404 page is not found” and should be designed to the brand, with links onward. |
| 4xx and 5xx | Narrative says “set up correctly,” then shows an empty “Response Codes Issues” chart. |
| www vs non-www canonical host | “Multiple missing canonical and canonicalised issues.” |
| HTTP/HTTPS duplicates and mixed content | “Set up correctly.” |
| 301 redirects | “Multiple 301 permanent redirections found” and they “need to be reviewed” so each hop still makes sense. |
| 302 redirects | Covered only as a glossary definition. No 302 count. |
| 304 caching | “Set up correctly.” No `Cache-Control` / `ETag` / `Last-Modified` evidence. |
| Redirect chains | Named in the glossary. Not given a count or a chain list in the findings. |
| Canonical URLs | Folded into the www/non-www section. No per-URL canonical table. |
| Duplicate content | “No pages were found with duplicate content.” |
| Hreflang | “Not needed. US audience, English only.” |

#### Website structure

| Check | What the sample says |
|---|---|
| URLs with underscores | “Set up correctly.” |
| A URL indexability table | Four identical rows, all `https://www.abccorp.com/`, all “Non Indexable,” all status **404**. |
| Non-descriptive URL slugs | “Set up correctly,” with an empty issues chart. |
| Click depth | “Set up correctly.” Standard stated in the copy: 3 clicks or fewer from the homepage. No depth histogram. |
| Broken links | “Set up correctly,” empty chart. |
| HTML / visual sitemap | “Set up correctly.” No link to an HTML sitemap page. |
| Orphan pages | “Set up correctly,” empty chart. |

#### Web forms

| Check | What the sample says |
|---|---|
| Labels and layout | Advice only: keep the layout clean and follow brand form guidelines. No form inventory. |
| Redundant fields | “No redundant fields found.” The sentence is printed twice, overlapping. |
| Validation before submit | Names accept numbers. Add format rules, clear errors, and a captcha. |
| Thank-you page | Missing after submit. Email signup and contact forms “are not working well” and need a real test. |

#### Page speed

| Check | What the sample says |
|---|---|
| Scope | “Top 10 performing pages from GA4” were used. Those URLs are not listed. |
| Server load test | Named in the table of contents. No result, no tool, no concurrency, no error rate. |
| Performance score | Defines FCP, LCP, TBT, CLS, Speed Index. Does not print a single number. |
| Core Web Vitals | “CWV failed and multiple page speed issues need to be reviewed.” No LCP / INP / CLS values, no field vs lab, no URL. |
| Metric glossary | Also defines INP, FID (retired), and TTFB. |
| Images | “Multiple large images.” Compress, scale, and switch format. A “Click Here” control has no asset list, no byte sizes, no dimensions. |

#### Mobile friendliness and usability

| Check | What the sample says |
|---|---|
| Mobile URLs | Named in the table of contents (separate `m.` host or responsive). No finding. |
| Mobile page speed | Named in the table of contents. No number. |
| Device proof | Placeholder boxes labeled “iOS Screenshot” and “Android Screenshot.” No images in the text layer. |
| Pop-ups | “No intrusive popups.” |
| Layout shift | “No layout shifts” — this contradicts the earlier “CWV failed” line, because CLS is a Core Web Vital. |

#### On-page SEO

The narrative on several of these pages says “set up correctly and displays accurate data” **on the same page** as a large issue count. The counts are the real content. The sentence is boilerplate.

| Check | Counts in the sample | Share of that chart |
|---|---|---|
| Meta titles | Missing 250, short 121, long 11, duplicate 70 (452 title issues) | 55.3% / 26.8% / 2.4% / 15.5% |
| Meta descriptions | Missing 15, short 20, long 18, duplicate 22 (75 issues) | 20% / 26.7% / 24% / 29.3% |
| H1 | Missing 12, short 18, long 15, duplicate 13 (58 issues) | 20.7% / 31.0% / 25.9% / 22.4% |
| H2 | “Set up correctly.” Chart titled “H2 Tag Issues” with no numbers. |
| Anchor text | “Set up correctly.” Chart titled “Anchor Text Issues” with no numbers. Copy warns against “click here” / “read more.” |
| Image alt | “Set up correctly.” Chart titled “Images Alt Attribute Issues” with no numbers. |
| Open Graph | “Set up correctly.” |
| Structured data / microdata | “Set up correctly.” Recommends structured data in general. No types, no errors. |
| Pagination | “Set up correctly.” |
| Security headers | “Set up correctly.” |
| Naked links (URL used as the anchor) | “Set up correctly.” |

#### Close

The last page says implementing on-page SEO, mobile, speed, forms, structure, and crawlability will raise visibility and “drive more qualified sales.” There is no baseline traffic, no forecast, and no prioritized action list. It points to `https://www.whitelabeliq.com/contact-us/`.

### 1.2 Glossary the report teaches the client

GA4, Search Console, XML sitemap, SSL/HTTPS, `robots.txt`, meta tags, 404 page, response codes, canonical URL, hreflang, 301, 302, 304, redirect chains, click depth, broken links, HTML sitemap, orphan pages, form optimization, Core Web Vitals, layout shift, intrusive pop-ups, meta title, meta description, H1/H2, anchor text, alt text.

That glossary is the whole product surface of this PDF. Anything outside it (entities, citations, internal search demand, links from other sites, log files) is absent.

---

## 2. What Dristik can do today

“Can do” means the crawl or a connected connector actually records the signal, and a finding or report can be grounded on that evidence. It does not mean we already print this PDF’s layout.

Default crawl depth in the product UI is **5 pages**. Config allows 5, 10, 20, 50, or `all` (capped at 500). Sitemap discovery keeps about **50 URLs** and only opens a small number of child sitemaps. A sample that reports 250 missing titles is a **sitewide** audit. Dristik can approach that only when `max_crawl_pages` is raised. On the default of 5, these checks are true for the pages we fetched, not for the whole site.

| Sample check | Dristik today | How |
|---|---|---|
| `robots.txt` exists | Yes | Crawler fetches `{origin}/robots.txt`, stores found/not found and the first 2,000 characters, and reads `Sitemap:` lines. |
| XML sitemap exists and is listed | Yes, partially | Tries robots-declared sitemaps plus `/sitemap.xml`, `/sitemap_index.xml`, `/wp-sitemap.xml`. Records found URL and up to ~50 page URLs. Does not flag “sitemap is http while the site is https” as its own rule, but the stored sitemap URL makes that check possible. |
| SSL / HTTPS | Yes | Security analyzer records `is_https` per fetched URL. Scoring applies a technical penalty when the site is not HTTPS. |
| Security headers | Yes, and stricter than the sample | HSTS, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options. The sample only says “set up correctly.” |
| `noindex` in HTML | Yes, per crawled page | `meta name="robots"` content is stored (`robots_meta`). Priority-page misuse can be flagged from that field. |
| HTTP status 4xx / 5xx | Yes, per crawled URL | Each page snapshot has `status_code`. Later audits can show a status change as a regression. |
| Canonical tag present | Yes | Missing canonical is a deterministic technical-SEO claim with a concrete recommendation. |
| www vs non-www | Partial | Canonical href is stored. There is no dedicated host-variant probe (fetch `www`, apex, http, and https and compare the final host). |
| Title present and length | Yes, per page | Title text and character length. Missing title is recorded as evidence. Short / long / duplicate **sitewide buckets** are not a finished report section; the raw fields are there to build them once the crawl is wide enough. |
| Meta description present and length | Yes, per page | Same pattern. Missing description is a medium technical finding. 150–160 characters is the recommendation already written in the technical SEO agent. |
| H1 / H2 / H3 | Yes, per page | Lists are stored. Missing H1 is explicit evidence. Duplicate or short/long H1 across the site is not a finished rollup. |
| Open Graph and Twitter cards | Yes | `og:*` and Twitter tags are extracted per page. |
| JSON-LD and microdata | Yes | Schema types and raw JSON-LD. Organization / Product / Service flags. Missing JSON-LD is evidence. This is stronger than the sample’s one-line “set up correctly.” |
| Hreflang inside the sitemap | Partial | Sitemap parser can read `xhtml:link` hreflang on sitemap URLs. HTML `link rel="alternate" hreflang` on the page is not a first-class audit section. The sample’s “single locale, hreflang not required” judgment is something we can state only after checking those tags and the content languages. |
| Internal and external links | Yes, per page | Counts, sample URLs, sample anchor text. |
| Empty anchors | Yes | Link-graph parser counts anchors with no text and no image. |
| Image alt missing | Yes, per page | Count of images whose `alt` is missing or blank, plus the page total. Decorative-vs-informative is not classified. |
| TTFB, HTML weight, compression | Yes, lab, from our fetch | TTFB in ms, payload KB, `Content-Encoding` (gzip / br / zstd / deflate), `Server` header. This is **not** a Lighthouse score and **not** CrUX. |
| Viewport / mobile meta | Yes | Viewport meta is stored and feeds the experience pillar. |
| JS-rendered DOM | Yes, when Playwright (or Firecrawl) is available | Second-tier render for pages that need JS. Screenshot audit of iOS/Android is not part of this. |
| Google Search Console | Only if the client connects it | Connector exists. Registry status is `NOT_CONNECTED` until credentials are present. When connected, the engine is built for queries, clicks, impressions, CTR, average position. It does not, by itself, print the sample’s “GA4 is set up correctly” sentence. |
| Indexability signals we can defend | Yes, from the crawl | HTTPS, robots body, sitemap presence, canonical, robots meta, status code. GEO readiness already scores a retrieval band from HTTPS + robots.txt + sitemap. |
| Broken-link candidates | Partial | A crawled URL with status ≥ 400 is a broken URL **we requested**. We do not yet probe every outbound href for 404. |
| Click depth and orphans | Partial | Every crawled page stores its internal links, so depth and orphans can be computed for the crawled set. There is no shipped “pages deeper than 3” or “orphan URL list” section. |
| Forms exist on a page | Weak partial | DOM code comments mention forms. What is actually stored is element counts, images, script/style counts, and CTA labels. Form field names, required flags, and label association are not extracted. UX copy can still talk about form friction from visible text. That is not a form test. |
| Duplicate-content hint | Weak partial | Body text and word count are stored per page. There is no near-duplicate (simhash / MinHash) pass and no “thin page” threshold report. |
| Fixes, not only findings | Yes, beyond the sample | Patch pack can emit canonical, Open Graph, JSON-LD, title, robots meta, and a `robots.txt` that points at the sitemap. Apply path exists for WordPress, Shopify, Webflow, and GitHub **after** the client connects them. Default connector status is not connected. |
| Re-check after a fix | Yes | Audit-to-audit regression (score and status-code deltas) and a 30/60/90 outcome recheck design. The sample is a one-shot PDF. |
| Things the sample never covers, which we do | Yes | GEO/AEO readiness (can an answer engine extract identity, ICP, pricing, offer, trust, comparison), evidence tokens per claim, confidence bands, honest “not measured” instead of a fake score, optional competitor URLs, commercial bake-off when the rival was crawled, trust/NAP/privacy links, readability. |

### Honest limits on the rows marked “yes”

- A check is only as wide as the crawl. Five pages cannot support “250 missing titles.”
- `follow_redirects=True` means we store the **final** response. The hop list (301 → 302 → 200) is not a stored chain.
- `robots.txt` is truncated to 2,000 characters.
- Sitemap child expansion is shallow.
- Search volume, live AI citation rank, and revenue attribution stay unavailable until their connectors return real data. The product rule is to say `NOT_CONFIGURED` / `UNAVAILABLE` rather than invent them.

---

## 3. What we do not do

These are checks the sample **names**, that Dristik does **not** currently perform as a real measurement.

| Sample check | Gap |
|---|---|
| “Verify GA4 is set up and shows accurate data” | No GA4 connector. We cannot see property, data stream, enhanced measurement, key events, or internal traffic filters. |
| Indexed vs non-indexed vs “other” pie (50 / 20 / 30) | No Google Index Coverage or URL Inspection pull. Crawl status is not the same thing as “Google has indexed this URL.” |
| Search Console “set up correctly” as a boolean | We can see whether **our** connector is authenticated. We cannot certify the client’s users, sitemaps submitted inside GSC, or country targeting. |
| Branded 404 template | We can observe a 404 status. We do not judge whether the error page matches the brand or links back into the site. |
| `X-Robots-Tag` HTTP header | We read the HTML robots meta, not this response header. A page can be `noindex` in the header and look indexable in our HTML extract. |
| Mixed content (https page loading http images, scripts, iframes) | Not scanned. |
| HTTP and HTTPS duplicate hosts | We do not fetch all four host variants and compare bodies. |
| 301 inventory and “does this redirect still make sense” | Final URL only. No redirect map, no “redirects to a soft 404,” no chain length. |
| 302 vs 301 classification | Not stored, because the redirect is followed inside the HTTP client. |
| 304 / caching correctness | We do not send `If-None-Match` or `If-Modified-Since`. |
| Long redirect chains | Not stored. |
| Full duplicate-content audit | No cross-URL similarity, no parameter duplicates (`?utm`, `?sort`), no trailing-slash duplicates, no print-view duplicates. |
| Underscores vs hyphens in URLs | Not a rule. Easy to add from the URL path. Not shipped. |
| Non-descriptive slugs (`/page-1`, `/id/12345`) | Not a rule. |
| Click-depth report (share of URLs at depth 4+) | Data is latent in the link lists. No report. |
| Sitewide broken-link crawl (internal and external) | We do not HEAD/GET every `href`. |
| HTML sitemap page quality | Not checked. |
| Orphan list (in sitemap, zero inlinks) | Not assembled. Needs the full link graph plus the full sitemap, which the current sitemap cap does not provide. |
| Form labels, redundant fields, input types | Not extracted. |
| Client-side validation and captcha | Not tested. We do not submit forms. |
| Thank-you page and “does the form actually submit” | Not tested. |
| Server load test | No load generator, no concurrency, no p95 under load. |
| PageSpeed Insights score (0–100) | Not called. |
| Core Web Vitals field data (CrUX LCP, INP, CLS) and lab Lighthouse | Performance pillar expects CrUX and, when it is absent, must stay unmeasured. We must not print “CWV failed” without numbers. Our TTFB is a single-server lab sample. |
| Per-image byte size, dimensions, format (WebP/AVIF), responsive `srcset` | We count images and missing alts. We do not measure image weight. |
| Mobile URL strategy (`m.` vs responsive) | Not a check. Viewport meta is the only mobile signal. |
| Real device screenshots | Playwright can render a page. We do not ship iOS and Android screenshots in the report. |
| Intrusive interstitials | Not detected. |
| Layout shift on mobile | CLS is not measured. A sentence like the sample’s “no layout shifts” would be a fabricated claim. |
| H2 quality rollup | H2 text is stored. No missing / duplicate / outline report. |
| Generic anchor text (“click here”, “read more”) as a sitewide issue list | Sample anchors are stored (first ~10–20 per page). No classifier and no issue table. |
| Naked URL anchors | Not classified. |
| Pagination (`rel=next` / `rel=prev`, self-canonical on page 2+, view-all) | Not checked. |
| Rich Results validation | We list schema `@type`. We do not run Google’s Rich Results / schema validator (required properties, errors, warnings). |
| Open Graph completeness (`og:title`, `og:description`, `og:image` 1200×630, `og:url`) | Tags are extracted. There is no pass/fail completeness rule with image-size checks. |
| Top pages by GA4 sessions, then audit only those | No GA4. We cannot reproduce the sample’s “top 10 pages” scope honestly. |
| Impact on qualified sales | No revenue connector by default (`revenue_attribution` is `NOT_CONNECTED`). We do not claim sales lift. |

### Also absent from the sample, and still absent as a live measurement here

A complete SEO program also needs the items below. The sample skips them. We should not pretend the sample’s outline is the full standard, and we should not pretend we already cover these.

| Industry item | Dristik |
|---|---|
| Keyword universe, volume, difficulty, intent | `search_volume` capability is `UNAVAILABLE` until a volume provider is connected. |
| Rank tracking over time | Only if GSC is connected (average position for queries GSC already shows). No third-party rank tracker. |
| Backlinks, referring domains, toxic links, lost links | Not measured. Must stay unmeasured. |
| Log-file crawl stats (Googlebot hit rate, status, wasted crawl) | Not ingested. |
| International targeting beyond a sitemap hreflang parse | No country SERP, no `hreflang` return-tag pair check, no `x-default` check. |
| Content decay and information gain | GEO extractability exists. Editorial decay vs competitors is not a Search Console + analytics time series. |
| Core algorithm / spam policy review (scaled content, doorway, site reputation abuse) | Not a checklist. |

---

## 4. What is not that good

### 4.1 The sample report itself

This PDF is a **template demo**, not a reliable audit of `abccorp.com`. A client who received it would get the wrong picture of several issues.

**The finding sentence and the chart disagree.** Multiple pages say “It’s set up correctly and displays accurate data” and then print a chart of failures. Meta titles show 250 missing titles. Canonicals say “multiple missing canonical issues.” H1 shows 58 issues. Response-code, H2, anchor, and alt pages say “correct” and still render an empty “Issues” chart. The boilerplate was not updated when the numbers were.

**The numbers are not reconcilable.** 250 missing titles implies a crawl of at least a few hundred URLs. Indexed pages are given as 50. The URL table shows the homepage four times, each as non-indexable **404**. A live homepage that 404s cannot also be “SSL secure, sitemap healthy, GA4 accurate” without an explanation. No URL is attached to any of the 452 title issues.

**Charts have no method.** No crawl date range, no user agent, no tool name (Screaming Frog, Sitebulb, Lighthouse, GSC), no inclusion rule (all 200s, or all sitemap URLs, or only indexable). Pie percentages are printed as if they were measurements. The index split (50 / 20 / 30) is too round to trust without a GSC export.

**Placeholders leaked into the file.** Cover line still says `Generated at: MM/DD/YYYY` next to 12 Sep 2025. “iOS Screenshot” and “Android Screenshot” are empty labels. Image advice ends in “Click Here” with no images. “No redundant fields” is drawn twice and overlaps. Grammar is unfinished (“unscured”, “which needs to fixed”, “redudant redundantfields”).

**Core Web Vitals is both failed and fine.** One section says CWV failed. The mobile section says no layout shifts. CLS is one of the three Core Web Vitals. Both sentences cannot be true, and neither has a value. FID is defined even though Google replaced it with INP in 2024. No field-data window (28 days) and no lab run are shown.

**Recommendations do not name a page, a patch, or an owner.** “Compress the large images.” “Optimise robots.txt to SEO standards.” “Review the 301s.” “Design a 404 in the brand.” None of these can be handed to engineering. The close then claims qualified-sales growth. That claim is not supported by any conversion or revenue figure in the document.

**Severity is flat.** A missing H1 on a campaign URL and a homepage that 404s would be the same kind of slide. Industry audits separate critical indexation from hygiene.

**Security is marked correct while the sitemap is HTTP.** An HTTPS site whose sitemap URLs are `http://` is a mixed-host / redirect problem. The security slide does not mention HSTS or mixed content, which is the actual issue the sitemap slide just raised.

**Scope pretending.** Table-of-contents items with no result: server load test, mobile URLs, mobile page speed, 302 count, redirect chains, HTML sitemap proof. The glossary adds pages without adding findings. That is how a 46-page PDF stays thin.

**What a buyer still cannot answer after reading it**

- Which URLs are broken, duplicated, or blocked?
- What should be fixed this week vs this quarter?
- What is the Search Console query set and the striking-distance pages?
- Did anyone render the page in a phone viewport?
- What is LCP, INP, and CLS, on which template, in the field?

### 4.2 Where Dristik is weaker than a good version of this audit

These are real product gaps, not complaints about the sample.

| Weakness | Why it matters |
|---|---|
| Default crawl is 5 pages | A technical audit that reports sitewide title, canonical, and orphan issues is not honest at 5 URLs. The sample at least *pretends* to be sitewide. We should default the technical pass to sitemap-wide, or say “sampled N URLs” in every count. |
| Signals are stored per page and not rolled up | We have title length, H1, canonical, alt, and anchors. We do not yet publish the sample’s useful part: missing / short / long / duplicate counts **with the URL list under each bucket**. |
| Redirects are collapsed | `follow_redirects=True` throws away the 301/302 chain. The sample is also weak here, but a standard crawl keeps every hop. |
| No index coverage | GSC connection is optional and off. Without it, “indexed pages” must not appear. |
| No field performance | TTFB from one fetch is a clue. It is not LCP, INP, or CLS. Printing a performance score today would repeat the sample’s worst habit. |
| Forms are described more than measured | The DOM analyzer’s own comment says it extracts forms. The returned data has no form fields. Thank-you pages and live submit tests do not exist. |
| Broken links, orphans, click depth are not finished reports | The ingredients exist (status codes, internal links, sitemap URLs). The client-facing lists do not. |
| Sitemap and robots caps | 2,000 characters of robots and ~50 sitemap URLs will miss large sites and will miss a sitemap-index that points at many child files. |
| `X-Robots-Tag`, mixed content, host variants, hreflang pairs, pagination | Standard technical crawlers treat these as table stakes. We do not. |
| Report shape | We are stronger on evidence, GEO, and patches. We are weaker on the simple URL-level technical appendix agencies expect to export to a spreadsheet. |

### 4.3 Where we are already ahead of this sample

Worth keeping. Matching the PDF’s weaknesses would make the product worse.

- Every claim is supposed to point at an evidence token. The sample has no evidence.
- Unmeasured metrics stay unmeasured. The sample fills gaps with “set up correctly.”
- Schema, security headers, canonical, and robots are tied to a patch, not only a sentence.
- GEO/AEO readiness is outside this PDF and is the part traditional audits still skip.
- A second audit can show what changed. The sample cannot.

---

## 5. Industry standard

The working standard in 2026 is not a 46-page glossary. It is a **crawl export + Search Console + field performance + a short decision memo**. Tools that define the checks: Google Search Console (coverage, sitemaps, CWV report, queries), PageSpeed Insights / CrUX (field) and Lighthouse (lab), and a site crawler such as Screaming Frog or Sitebulb. Ahrefs or Semrush add keywords and backlinks. GA4 is used only for templates that actually earn traffic, not as a “yes GA4 is installed” tick.

A standard deliverable has four layers:

1. **Decision memo (3–6 pages).** What is blocking indexation or revenue, in priority order, each with affected URL count, example URLs, the fix, who owns it, and how we will know it worked.
2. **URL appendix.** One row per issue per URL. Columns: URL, status, indexability, title, title length, meta description, H1, canonical, robots meta, word count, inlinks, crawl depth, indexability reason.
3. **Measurement appendix.** GSC index reasons, GSC queries, CrUX or PSI for the templates that matter, crawl configuration (date, user agent, URL count, what was excluded).
4. **Explicit non-findings.** “Not measured” is a status. It is never written as “set up correctly.”

Thresholds below are the ones practitioners actually use. They are conventions, not Google “ranking factors” with magic cut-offs.

### Indexing and crawlability

| Check | Standard |
|---|---|
| GA4 | Property and web stream exist, enhanced measurement reviewed, key events match the business (lead, purchase), internal traffic filtered, linked to Search Console. Screenshot or admin export. “Accurate data” requires a comparison to server logs or GSC clicks, not a feeling. |
| Search Console | Domain property preferred, DNS verified, sitemap submitted, coverage report exported, manual actions and security issues empty. |
| Indexed pages | Use the Page indexing report. Group by **reason** (Crawled – currently not indexed, Discovered – currently not indexed, Duplicate without user-selected canonical, Blocked by robots.txt, Excluded by noindex, Soft 404, Alternate page with proper canonical, Not found). A pie of Indexed / Non-indexed / Other with no reasons is not a finding. |
| XML sitemap | 200, `https`, only canonical 200 URLs, no `noindex`, no redirects, no non-canonical. Index sitemap if the site is large. Submitted in GSC. `lastmod` only when it is true. |
| HTTPS | Valid certificate, HTTP → HTTPS 301, one host (www or apex) 301s to the other, HSTS after redirects are stable. No mixed content. |
| `robots.txt` | 200, not blocking CSS/JS, not blocking the whole site by accident, sitemap line is https. Every `Disallow` is listed with a reason. Blocked URLs that still get internal links are called out. |
| `noindex` / `X-Robots-Tag` | Both HTML and header. Any `noindex` on a URL that also sits in the sitemap or the main nav is a defect. |
| 404 page | Real 404 status (not a soft 200), on-brand, links to home, search, or key sections, not `noindex` accidentally applied to real pages. |
| 4xx / 5xx | Internal links to 4xx are broken. 5xx during crawl are critical. Soft 404 (200 with thin “not found” copy) is reported separately. |
| Canonical host | One preferred host. The other three variants (http/https × www/apex) 301 to it in a single hop. |
| Redirects | 301 for permanent moves. 302/307 only when the move is temporary. Chains longer than 1 hop get flattened. Redirect to 4xx is critical. Crawl stores every hop. |
| 304 | Correct `ETag` or `Last-Modified` on static assets and cacheable HTML. A “304 is set up” line without a conditional request is meaningless. HTML that must be fresh should say so. |
| Duplicates | Exact and near-duplicates, parameter URLs, trailing slash, index.html, print views, http/https. Each cluster has one canonical. |
| Hreflang | Only if more than one language or country. Reciprocal tags, valid codes, `x-default`, self-reference, no `noindex` on alternates. “English, US only” is a valid conclusion **after** the tags and the content are checked. |

### Structure

| Check | Standard |
|---|---|
| URL slugs | Hyphens, lowercase, readable words, no underscores, no long IDs in primary landing URLs. |
| Click depth | Important URLs (money pages, top GSC pages) at depth ≤ 3 from the home page. Report the count deeper than 3, not a pass/fail slogan. |
| Broken links | Every internal href checked. External 4xx listed but ranked lower. |
| Orphans | In the sitemap or analytics, with zero internal inlinks. |
| HTML sitemap | Optional. Useful on large content sites. Not a ranking requirement on a small marketing site. Saying “reviewed” with no URL is not a check. |

### Forms

| Check | Standard |
|---|---|
| Labels | Every input has a visible `<label>` or an accessible name. |
| Fields | Only fields the sales or product process uses. Phone and company are justified, not copied from a template. |
| Validation | Types (`email`, `tel`), constraints, errors tied to the field, errors before submit. |
| Spam | Honeypot or captcha appropriate to the spam level. Captcha that blocks humans is itself a finding. |
| Thank-you | Dedicated URL or a confirmed success state so ads and analytics can record the conversion. The form is **submitted in a browser** on desktop and mobile. A PDF that never submits the form cannot claim the form works. |

### Speed

| Check | Standard |
|---|---|
| Field CWV | CrUX, 28-day, by template (home, category, product, article), mobile first. Pass: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 at the 75th percentile. “Failed” without the three numbers is not a result. |
| Lab | Lighthouse / PSI lab on the same templates, with the filmstrip and the LCP element named. Lab explains the cause. Field decides the pass. |
| FID | Do not report. It was replaced by INP. |
| Images | Bytes, displayed size vs intrinsic size, format, `srcset`, width/height to limit CLS, lazy-load below the fold, LCP image **not** lazy-loaded. |
| Load test | Only when the client has a traffic or launch concern. State virtual users, duration, error rate, and p95. It is not part of a normal SEO audit. |
| Scope | Templates plus the top landing pages by GSC clicks or GA4 sessions. Name the URLs. |

### Mobile

| Check | Standard |
|---|---|
| Indexing | Google is mobile-first. One responsive URL is the standard. A separate `m.` host must be linked with canonical and alternate correctly. |
| Proof | At least one real mobile render of the main template, including any interstitial. Empty “iOS Screenshot” boxes fail this. |
| Pop-ups | No full-screen interstitial on landing from search. Cookie bars and small banners are described, not waved through. |
| CLS | Measured, not eyeballed. “No layout shifts” requires a CLS number. |

### On-page

| Check | Standard |
|---|---|
| Title | Present, unique, about 50–60 characters so it does not truncate, primary intent first. Report missing, duplicate, and duplicate-across-near-identical pages separately. |
| Meta description | Unique, about 140–160 characters, written for the click. Missing is a snippet problem, not a hard ranking failure. Do not treat 15 missing descriptions as equal to 250 missing titles. |
| H1 | One clear H1 per page, aligned with the title and the intent. Multiple H1s are usually low if the outline is still clear. |
| H2 | Outline matches the sections a searcher expects. Empty H2 charts are not findings. |
| Anchors | Descriptive. Count “click here”, “read more”, “here”, and naked URLs on internal links. Image links need alt on the image. |
| Alt | Informative images have specific alt. Decorative images have empty alt (`alt=""`). Missing alt and empty alt are not the same finding. |
| Open Graph | `og:title`, `og:description`, `og:url`, `og:image` (large enough to preview, commonly 1200×630). Twitter card if sharing matters. |
| Structured data | Valid JSON-LD for the page type (Organization, Product, Article, FAQ, Breadcrumb). Validate errors vs warnings. “Consider structured data” with no type list is not an audit. |
| Pagination | Self-canonical on each page, unique titles, real content, no `noindex` on page 2 unless intentional. `rel=prev/next` is optional; Google has said it does not use it for indexing. |
| Naked links | Fine in citations and footnotes. A finding only when they dominate internal navigation. |

### How a standard report treats uncertainty

- If GSC is not connected, index counts are omitted.
- If CrUX has no data for a small site, say “no field data,” and show lab only, labeled lab.
- If the crawl is a sample, every percentage says the denominator (`12 of 40 crawled URLs`, not `30%`).
- Sales impact is a hypothesis until analytics shows assisted conversions. It is never the closing sentence by default.

### Minimum bar if Dristik wants to cover this PDF’s job properly

In priority order, these are the additions that would make our technical audit meet the standard without copying the sample’s bad habits.

1. Sitewide crawl (sitemap-bounded) with the denominator printed on every count.
2. Issue rollups with URL lists: title, description, H1, canonical, robots meta, status code, alt, generic anchors.
3. Redirect chain capture (status and URL of each hop) before following.
4. `X-Robots-Tag`, mixed content, and the four host variants.
5. Orphan and click-depth lists from the full internal graph.
6. Broken-link check of internal hrefs.
7. Search Console page-indexing reasons when the connector is on. When it is off, omit index pies.
8. CrUX or PSI for the key templates when a key is configured. When it is off, keep TTFB and label it as a single lab sample.
9. Form inventory (fields, labels, types) plus one real submit path on the primary form.
10. A one-page decision memo in front of the appendix. No glossary padding. No “set up correctly” unless the check ran and passed.

---

## 6. One-page scoreboard

| Area | Sample report | Dristik today | Industry standard |
|---|---|---|---|
| GA4 verification | Claimed, no proof | Not available | Admin evidence or omit |
| GSC index reasons | Fake-round pie | Only if connector is on; coverage reasons not built | Reason-grouped export |
| Robots + sitemap | Found; sitemap stuck on http | Fetched and stored; http-vs-https not its own rule; URL cap is low | Full sitemap, https-only, submitted |
| HTTPS and headers | “Secure,” misses the http sitemap | HTTPS + HSTS/CSP/frame/nosniff | Cert, single host, HSTS, no mixed content |
| Status codes | Empty chart; homepage table says 404 four times | Real status per crawled URL | Full crawl, soft 404 called out |
| Canonicals and redirects | Mentioned, no hop list | Canonical stored; hops discarded | One hop to one canonical host |
| Titles, descriptions, H1 | Counts with no URLs, plus a “correct” sentence | Per page, no sitewide buckets | Buckets + URL list + denominator |
| Schema | “Correct” | Types extracted, missing JSON-LD flagged | Validated JSON-LD for the page type |
| Links, depth, orphans | “Correct,” empty charts | Links stored; lists not shipped | Inlink counts, depth, orphan list |
| Forms | Real findings, messy layout, no URL | Not actually tested | Submit the form on mobile and desktop |
| CWV | “Failed,” no numbers, contradicts CLS line | TTFB only; CWV correctly left unmeasured | Field LCP, INP, CLS at p75 |
| Images | “Multiple large images” | Alt counts only | Bytes, format, LCP image |
| Mobile | Empty screenshot boxes | Viewport meta; no device shots | Rendered mobile proof |
| Evidence and fixes | None | Evidence tokens and patch pack | URL, fix, owner, retest |
| Sales impact | Claimed in the close | Refused unless a revenue source is connected | Hypothesis until measured |

The sample is useful as a **checklist of client expectations**. It is a poor model for how to write the findings. Dristik already covers the on-page and security core on each crawled page, and it already refuses the sample’s worst behavior (invented CWV, invented index totals, invented sales). The gap that matters is turning those per-page signals into a sitewide, URL-level technical appendix, and adding the few measurements that cannot be faked: index reasons, redirect hops, field performance, and a real form submit.
