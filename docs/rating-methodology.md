# How Dristik rates each section (Scoring Engine v5.0)

This document defines the mathematical rating methodology used by Dristik Scoring Engine v5.0. Every score is on a 0–100 scale. A score describes the representative sample that was crawled (homepage, primary commercial page, high-intent page, secondary commercial page, and strategic pages) plus any verified connector data.

Dristik v5.0 uses an **industry-standard check-based scoring architecture** (modeled after Google Lighthouse, axe-core, and empirical measurement engines) rather than arbitrary finding-based deduction penalties. The legacy system of diminishing deduction steps, confidence multipliers, half-deductions, and provisional 50 placeholders has been fully retired.

---

## 0. Core Mathematical Framework

Every subsection is a list of weighted checks, not a list of deductions.

```
check score:            sᵢ ∈ [0.0, 1.0]
subsection score:       S_sub = 100 × (Σ wᵢ·sᵢ) / (Σ wᵢ)   [over checks that are applicable AND measured]
category score:         S_cat = Σ (subsection budget share × S_sub)
```

Each category has a 100-point budget allocated across its subsections according to the declarative rubric in `backend/app/scoring/scoring_rubric_v5.json`.

### Three Check Evaluation Types

| Type | Scoring Rule | Application |
|---|---|---|
| **Binary** | Pass = 1.0, Fail = 0.0 | HTTPS enforced, robots.txt valid RFC 9309, viewport declared, sitemap valid. |
| **Graded** | $s = \text{passed} / \text{total}$ sampled items | % of sampled URLs with self-referencing canonicals, % of images with alt text, % of claims backed with empirical proof. |
| **Continuous Curve** | Lighthouse-style log-normal curve anchored to $p_{10}$ and $\text{median}$ | Core Web Vitals (LCP, INP, CLS, TTFB), form field friction, sentence length. |

#### Continuous Log-Normal Curve Formulation
For metric values $x$ where lower is better (e.g., LCP p75 in seconds):

$$\mu = \ln(\text{median})$$
$$\sigma = \frac{|\ln(\text{median}) - \ln(p_{10})|}{1.2815515655}$$
$$z = \frac{\ln(x) - \mu}{\sigma}$$
$$\text{score}(x) = 1.0 - \Phi(z)$$

Where $\Phi$ is the standard normal cumulative distribution function. At $x = p_{10}$, the check earns 0.90; at $x = \text{median}$, the check earns 0.50; as $x \to 0$, score approaches 1.00.

---

## 1. Statistical Confidence & Wilson Intervals

For graded checks and sample proportions, Dristik computes a two-sided 95% Wilson score confidence interval:

$$\tilde{p} = \frac{n_{\text{passed}} + \frac{z^2}{2}}{n + z^2}, \quad w = \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}$$
$$\text{CI}_{95\%} = [\max(0, \tilde{p} - w), \min(1, \tilde{p} + w)]$$

Where $z = 1.95996$. This guarantees mathematical honesty: an audit of 5 pages that are all clean reports a sample score of 1.0 with a 95% interval of $[0.565, 1.000]$, honestly reflecting sample uncertainty.

---

## 2. Coverage Threshold Semantics

Dristik strictly separates **what was measured** from **what scored well**:

| Measured Weight Share | Category Status | Rollup Treatment | UI Presentation |
|---|---|---|---|
| **$\ge 60\%$** | `MEASURED` | Included in overall score rollup. | Full category card with confidence interval. |
| **$30\% \text{ to } 59.99\%$** | `PARTIAL` | Included in rollup with intent-adjusted weight. | Displayed with amber "PARTIAL COVERAGE" indicator and wider error bounds. |
| **$< 30\%$** | `NOT_MEASURED` | **Excluded** from overall score rollup ($w_{\text{cat}} = 0$). | Displayed as "Not measured — prerequisite connector or data unavailable". |

When a category is `NOT_MEASURED`, its baseline weight is redistributed proportionally among measured categories:

$$w_i^{\text{active}} = \frac{w_i^{\text{adjusted}}}{\sum_{j \in \text{measured}} w_j^{\text{adjusted}}}$$

No placeholder numbers (like legacy 50 or 65 baselines) are ever injected.

---

## 3. Dynamic Category Gates

Catastrophic defects trigger declarative gates defined strictly in `scoring_rubric_v5.json`:

1. **Critical Indexation Gate (`gate_critical_indexation`)**:
   - Trigger: Sitewide `noindex`, `Disallow: /` blocking all user agents, or homepage HTTP 5xx.
   - Action: Caps Technical SEO category score at **$\le 20.0$**, regardless of other check scores.
2. **Schema-DOM Truthfulness Gate (`gate_schema_contradicts_visible`)**:
   - Trigger: JSON-LD structured data directly contradicts visible page text or pricing.
   - Action: Caps Schema category score at **$\le 60.0$**.
3. **Connector Prerequisite Gates**:
   - Trigger: External authority connector unavailable or live AI Search run unexecuted.
   - Action: Marks category as `NOT_MEASURED` with provenance `CONNECTOR_UNAVAILABLE`.

---

## 4. Root-Cause Deduplication (Single-Charge Rule)

When multiple findings stem from the same underlying architectural defect (e.g., canonical misconfiguration causing both duplicate title tags and indexation warnings):
1. **Primary Finding**: Evaluated against the corresponding check definition in the primary category.
2. **Downstream Findings**: Recorded in the category deduction list with `"is_downstream_consequence": true` and `"points_lost": 0.0`.
3. The site is never double-charged across multiple categories for a single root cause.

---

## 5. Check Auditability & LLM Judge Guardrails

Every check evaluation produces a structured `CheckResult` record:
- `check_id` & `name`
- `score` $\in [0.0, 1.0]$ & `weight`
- `sample_size`, `passed`, `failed`
- `coverage` $\in [0.0, 1.0]$
- `confidence_interval` (Wilson 95% lower and upper bounds)
- `evidence`: List of verified items with URL, HTTP status/metric, and excerpt
- `llm_judge`: If evaluated by an LLM reasoner, includes model version, prompt hash, temperature (0.0), input evidence, and calibration version
- `methodology_version`: `"5.0"`

---

## 6. Category Weights and Intent-Adjusted Rollup

Each scored category has a baseline share. The business intent multiplies some of those shares, then the shares are divided by their total so they add up to 1.

### Baseline shares

| Category | Baseline share |
| --- | ---: |
| Technical SEO | 15% |
| On-page SEO | 10% |
| Content | 15% |
| GEO | 15% |
| AI Search | 15% |
| Schema | 10% |
| UX and conversion | 10% |
| Trust and authority | 10% |

### Intent multipliers

A category missing from a row keeps a multiplier of 1.

| Intent | Multipliers |
| --- | --- |
| SaaS | AI Search 1.25, GEO 1.20, UX 1.15, Technical SEO 0.90 |
| Ecommerce | Schema 1.35, UX 1.30, Trust 1.20, GEO 0.85 |
| Lead generation (also the default when no profile is set) | UX 1.30, Trust 1.25, AI Search 1.15 |
| Content publishing | Content 1.35, GEO 1.25, Technical SEO 1.15, UX 0.75 |
| Agency | Trust 1.30, UX 1.20, GEO 1.15 |

```
adjusted share = baseline × intent multiplier
weight = adjusted share / sum of adjusted shares
overall = round(sum of category score × weight, 1)
```

Trust and authority is included in that sum only when an external-authority connector actually returned evidence, or a trust finding is backed by observed or externally verified evidence. Otherwise Trust is **not measured**: score blank, weight 0, and the other weights are recomputed so they still add up to 100%. Crawl depth does not create this gap. A disconnected provider does.

### Overall grade

| Overall | Grade | Label |
| --- | --- | --- |
| 93–100 | A+ | Exceptional |
| 85–92.9 | A | Excellent |
| 75–84.9 | B | Good |
| 65–74.9 | C | Moderate |
| 50–64.9 | D | Needs Attention |
| Below 50 | F | Low readiness |

### How sure the overall number is

```
evidence coverage = findings that carry evidence / all findings
evidence quality  = findings whose evidence is observed or externally verified / all findings
confidence        = min(0.95, 0.40 + 0.30 × coverage + 0.25 × quality)
```

Each category uses the same formula on its own findings. A category with no findings of its own is shown at confidence 0.50. An audit with no findings has overall confidence 0.

---

## 4. Subsections inside each category

Each category has a 100-point budget split into subsections. A finding’s lost points land on the **first** subsection whose topic words appear in the finding title. Points that match no subsection are spread in proportion to each subsection’s budget. The last subsection is then nudged so the subsection points add up to the category score, as long as that nudge stays within half of the last subsection’s budget.

A subsection is:

- **Pass** when it kept at least 75% of its budget
- **Partial** when it kept at least 40% and less than 75%
- **Deficit** when it kept under 40%

On a provisional-neutral category, every subsection is shown at half its budget.

### Technical SEO — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Crawl accessibility, sitemaps, and international targeting | 25 | robots, sitemap, indexation, hreflang, return tags, x-default |
| HTTPS and transport | 25 | HTTPS, TLS, transport security |
| Response time | 25 | TTFB, latency, load time |
| Canonicals and local NAP | 25 | canonicals, broken links, redirects, name / address / phone conflicts |

### On-page SEO — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Title length and uniqueness | 25 | title tag |
| Meta description | 25 | meta description |
| Single H1 and heading order | 25 | H1 and heading hierarchy |
| Open Graph and social preview | 25 | Open Graph, Twitter cards |

### Content — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Topical coverage and information gain | 25 | thin pages, depth, commodity copy |
| First-party evidence | 25 | unbacked claims, missing proof, missing data |
| Outline and cannibalization | 25 | H2/H3 structure, overlapping subtopics |
| Readability and value-proposition clarity | 25 | Flesch score, scannability, H1 clarity |

### GEO — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Entity clarity and canonical definition | 20 | entity, identity, canonical organization |
| Direct answerability of buyer questions | 20 | answers, questions, extractable statements |
| Structured data grounding | 15 | schema, JSON-LD |
| Commercial question coverage | 15 | pricing, ICP, commercial coverage |
| Citation-ready passage density | 15 | passages and snippets |
| Bot access and semantic consistency | 15 | robots, llms.txt, crawler access |

### AI Search — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Citability and definition blocks | 30 | definition blocks, citability. Measured from the page. |
| Brand identity in answer engines | 25 | brand resolution. Treated as a simulation until a live engine runs. |
| Resistance to competitor displacement | 25 | competitor alternatives. Treated as a simulation until a live engine runs. |
| Commercial question coverage | 20 | pricing and commercial Q&A on the page |

### Schema — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Organization graph | 30 | Organization, sameAs, entity graph |
| WebSite and breadcrumb markup | 25 | WebSite, breadcrumbs, sitelinks |
| FAQ and Q&A markup | 25 | FAQ, question and answer markup |
| Page-text agrees with the markup | 20 | cross-grounding mismatches |

### UX and conversion — 100 points

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Five-second value proposition | 25 | hero clarity |
| Primary call to action | 25 | CTA presence and prominence |
| Form friction | 25 | fields, labels, submit |
| Mobile viewport | 25 | viewport and responsive layout |

### Trust and authority — 100 points, only when measured

| Subsection | Points | What it is reacting to |
| --- | ---: | --- |
| Social proof | 30 | testimonials, logos, reviews |
| Security, compliance, and privacy pages | 25 | privacy, GDPR, SOC 2 statements on the page |
| Corporate origin and contact | 25 | address, phone, email, about |
| Claims without hyperbole | 20 | guarantees and unverifiable superlatives |

When trust is not measured, these four rows are not scored. The report says the connector is unavailable.

---

## 7. Specialized Views (The Three Honest Scores)

These specialized views sit beside the category rollup. They answer distinct stakeholder perspectives: how the audit looks to a human buyer, to Google's ranking crawlers, and to AI answer engines.

In Scoring Engine v5.0, specialized views are **derived directly from the underlying check evaluations and category scores**. There are no separate, conflicting deduction tables:

| Specialized View | Primary Check Pillars | Formulation |
|---|---|---|
| **Human Experience** | UX & Conversion, Audience Readability, Form Friction | $0.50 \times \text{UX\_Conversion} + 0.50 \times \text{Content}$ |
| **Google Readiness** | Technical Infrastructure, Sitemaps, On-Page Signals, Schema | $0.45 \times \text{Technical\_SEO} + 0.35 \times \text{On\_Page\_SEO} + 0.20 \times \text{Schema}$ |
| **AI Readiness** | Entity Resolution, Answerability, DOM Grounding | $0.60 \times \text{GEO} + 0.40 \times \text{Schema}$ (when measured) |

### AI Visibility (Live Engine Measurement)

AI Visibility is reported **only when a live engine citation benchmark has been executed**:
- If executed: The measured citation rate across the plan's minimum query sample (e.g., $N \ge 10$ for Starter, $N \ge 25$ for Growth).
- If not executed: Reported as `None` / `NOT_MEASURED`. On-page readiness is **never** copied or fabricated into the visibility slot.

### Honest Overall
The honest overall score is the weighted average of Human Experience, Google Readiness, and AI Readiness across measured perspectives.

```
honest overall = 0.35 × human + 0.35 × Google + 0.30 × AI readiness
```

AI visibility is not inside this weighted sum.

| Honest overall | Band |
| --- | --- |
| 90–100 | Category benchmark |
| 75–89.9 | Citation ready |
| 50–74.9 | Fragile presence |
| Below 50 | Low readiness |

---

## 6. Report cards on the website

The cards recombine the numbers above. They are display blends. They are not a second deduction engine.

Health on a card: 80 or above is Good, 60–79 is Fair, below 60 is Poor. A blank score is shown as Poor.

Card letter: 90 A, 80 B, 70 C, 60 D, otherwise F.

### Search / SEO card

```
SEO = (0.45 × Technical + 0.35 × On-page + 0.20 × Content) / sum of the weights that exist
```

If only Technical exists, the card is Technical.

### GEO card

Equal average of whichever of these exist:

- Per-engine on-page score (section 8)
- Live AI visibility, only when its status is measured
- GEO category score
- `100 − fluff ratio` from the information-gain check

### AEO card

Equal average of whichever of these exist:

- Schema category score
- GEO extractability composite (section 7)
- Share of the four AI crawlers that are allowed: GPTBot, PerplexityBot, ClaudeBot, Google-Extended. Four allowed is 100. None allowed is 0.

### CRO card

Equal average of the human honest score and `100 − form friction` (section 11). If the form audit did not run, the card is the human score. If neither number exists, the card falls back to 65 so the layout still has a figure. That 65 is a display fallback, not a measurement.

### Competitor card

```
win rate = target wins / (target wins + competitor wins + ties) × 100
```

With no bake-off rows, the card is blank.

### Experience (SXO) card

Average of the SEO card and the CRO card, when both exist. Otherwise whichever of the two exists.

### Brand and entity card

Uses the same number as the AEO card.

### Chart radar

The radar chart uses a different blend from the cards:

| Spoke | Formula |
| --- | --- |
| Search | `0.60 × Technical + 0.40 × On-page`, dropping any side that is blank and renormalizing |
| AI citations | Live citation score when measured, otherwise the GEO category |
| Experience | Human honest score, otherwise the UX category |
| Conversion | UX category |
| Brand and entity | `0.50 × Schema + 0.50 × Trust`, dropping a side that is blank |

A spoke with no measured input is left off the chart.

---

## 7. GEO readiness and its subsections

GEO readiness answers: can an answer engine extract and quote this site from the crawled pages? It is computed from the pages. It is not a live citation rank.

Eight dimensions are scored. The composite uses only the six that are measured and have a weight. External authority and live visibility are reported beside the composite and do not move it.

| Dimension | Weight in the composite |
| --- | ---: |
| Entity clarity | 20% |
| Buyer-question answerability | 25% |
| Content extractability | 15% |
| Citation-ready passages | 15% |
| Retrieval accessibility | 10% |
| Factual grounding | 15% |
| External authority | 0. Always unmeasured from HTML. |
| Live AI visibility | 0 inside this composite. Shown on its own when a live run exists. |

```
extractability = sum(dimension × weight) / sum(weights of measured dimensions)
```

If nothing measured has a weight, the composite is 50.

Dimension band: 70 or above is high, 40–69 is medium, below 40 is low.

### 7.1 Entity clarity

Starts at 30.

| Signal | Change |
| --- | ---: |
| Business name appears on the crawled text | +20 |
| Industry, niche, product, or service is known | +20 |
| No marketing-fluff words | +10 |
| Fluff words present | −10 |
| Entity is consistent across surfaces | +10 |
| Entity is fragmented across surfaces | −15 |

Clamped to 0–100. The consistency input is the score in section 9.3.

### 7.2 Buyer-question answerability

Six canonical questions are checked on the crawled text: what the company is, who it is for, what it costs, what it offers, why to trust it, and how it compares.

| Status | Rule |
| --- | --- |
| Supported | A page hit exists and at least two of the question’s terms appear. For price: one concrete amount. |
| Partial | A related term or a page hit, but no self-contained answer. For price: “contact sales” or “request a quote” with no amount. |
| Conflicting | Two or more different price amounts in the sample. |
| Unsupported | None of the above. |

```
six-question score = (supported / 6) × 60 + (partial / 6) × 20
```

The wider question graph (section 9.1) scores supported as 1 and partial as 0.5:

```
graph score = (supported + 0.5 × partial) / questions × 100
```

When the graph ran, answerability is the average of the six-question score and the graph score. Otherwise it is the six-question score. Clamped to 0–100.

### 7.3 Content extractability

```
heading points   = min(40, number of H2s and H3s × 4)
passage points   = citation-readiness score × 0.40
                   (30 if passage analysis did not run)
question points  = min(20, supported canonical questions × 5)
extractability   = clamp(heading + passage + question, 0, 100)
```

### 7.4 Citation-ready passage density

This dimension is the average passage score from section 9.2. If passage analysis did not run, the dimension is 50.

### 7.5 Retrieval accessibility

Starts at 30. HTTPS adds 30. A fetched robots.txt adds 20. A fetched sitemap adds 20. Maximum 100.

### 7.6 Factual grounding

If any canonical commercial question is conflicting, the dimension is 20.

Otherwise it is the claim-clarity score from section 9.4. If claim extraction did not run and nothing conflicts, the dimension is 50.

### 7.7 External authority dimension

Always unmeasured from the HTML crawl. The stored placeholder is 50 with measured = false, and the weight above is 0, so the placeholder never enters the composite. A real authority reading comes only from a connected provider and is kept under that provider’s name (section 13).

### 7.8 Live AI visibility dimension

Filled only when a live connector returns a rate. The dimension is that rate, clamped to 0–100. Its weight inside the extractability composite is 0, so the live rate is displayed on its own and does not change extractability. When no live run happened, the dimension is unmeasured.

---

## 8. Per-engine on-page scores

These four scores estimate how extractable the crawled copy is for each engine profile. They are computed from the pages. They are not live mention or citation rates. The GEO card may average them in; the honest AI-visibility slot does not.

Information gain is computed first, then each engine.

### Information gain

Fluff ratio = `min(100, number of fluff phrases × 8)`.

```
information gain = 40
                   + 20 if at least three proprietary figures or study phrases
                   + 15 if a benchmark or comparison table is present
                   + 15 if a methodology section is present
                   + 10 if a named-person attribution is present
                   − 0.25 × fluff ratio
```

Clamped to 15–100.

Grade on this family of scores: 90 A+, 80 A, 70 B, 60 C, 50 D, otherwise F. Band: 70 high, 45 medium, otherwise low.

### ChatGPT / SearchGPT

Starts at 45. Adds 15 if the business name is on the page, 15 if an FAQ is present, 15 if a table is present, and 10 if the crawled word count is above 1,500. Clamped to 20–100.

### Perplexity

Starts at 40. Adds 25 if proprietary statistics were found, 15 if a sitemap was found, 10 if the site is HTTPS, and 10 if information gain is 65 or higher. Clamped to 20–100.

### Google AI Overviews

Starts at 40. Adds `min(30, number of schema types × 10)`. Adds 15 if a page has an H1 and more than 200 characters of body. Adds 15 if FAQPage or Organization schema is present. Clamped to 20–100.

### Claude / Gemini

Starts at 50. Subtracts `0.40 × fluff ratio`. Adds 25 if information gain is 60 or higher. Adds 15 if a methodology or a named quote is present. Clamped to 20–100.

### Per-engine overall

```
overall = (ChatGPT + Perplexity + Google AI Overviews + Claude/Gemini) / 4
```

Bot access (allowed or disallowed for GPTBot, PerplexityBot, ClaudeBot, and Google-Extended) is reported next to these scores. It changes the AEO card. It does not change the four engine scores.

---

## 9. Specialist scores that feed the sections above

### 9.1 Question graph

Each buyer question is supported, partial, unsupported, or conflicting. Conflicting and unsupported count as zero.

```
answerability = (supported × 1.0 + partial × 0.5) / questions × 100
```

The same formula is applied inside each question class (identity, audience, pricing, services, comparison, and the rest of the graph).

### 9.2 Citation passages

A passage is a block of 12 to 120 words that is not boilerplate. Each passage is four parts of 25 points.

**Standalone clarity.** Starts at 15. Adds 10 when the passage is 35–75 words, or 5 when it is 25–95 words. Subtracts 10 if it opens on a dangling reference such as “this” or “it” with no named subject. Floor 5.

**Subject attribution.** 25 if the brand is in the first 15 words. 18 if the brand appears later. 10 if the opening is “we” or “our company”. 5 if the subject is unnamed.

**Informational gain.** Starts at 8. Adds 5 for each concrete anchor (a number, a percent, a currency amount, or a factual cue), up to 17.

**Factuality.** Starts at 22. Subtracts 7 for each fluff phrase, up to 17. Floor 5.

```
passage score = clamp(clarity + attribution + gain + factuality, 10, 100)
```

| Passage score | Tier |
| --- | --- |
| 75–100 | Highly citable |
| 50–74.9 | Partially citable |
| Below 50 | Weak |

The page-level citation readiness score is the average of the passage scores. If no passage qualifies, it is 40.

### 9.3 Entity consistency across surfaces

Starts at 100. Compares homepage, about, services, and structured data.

| Disagreement | Deduction |
| --- | ---: |
| Brand name differs | 18 |
| Category cluster disagrees on about or schema | 14 |
| Category cluster disagrees on the services page | 8 |
| Audience disagrees between homepage and about | 6 |

```
consistency = clamp(100 − deductions, 20, 100)
```

85 or above is low fragmentation risk. 60–84 is moderate. Below 60 is severe. The entity is marked fragmented when any disagreement exists and the score is under 80.

### 9.4 Claim clarity

Each declarative sentence of 30–220 characters gets specificity and verifiability, each from 0 to 1.

Specificity starts at 0.50. Adds 0.15 per concrete anchor, up to 0.35. Subtracts 0.20 per fluff token, up to 0.40. Adds 0.10 when the sentence is 8–25 words. Clamped to 0.10–0.98.

Verifiability starts at 0.40. Adds 0.30 if a number or price is present, 0.30 if a compliance term is present, and 0.15 if there are at least two anchors. Subtracts 0.25 if the sentence is fluff. Clamped to 0.10–0.99.

A claim is machine-citable when specificity is at least 0.65 and it is not fluff, or when verifiability is at least 0.70.

```
claim clarity = 0.60 × average specificity × 100 + 0.40 × average verifiability × 100
```

If no claim is extracted, specificity is reported as 50, verifiability as 40, and clarity as 45.

### 9.5 Entity graph quality

For expected schema properties on the sampled pages:

```
completeness = present expected properties / applicable expected properties × 100
consistency  = 100 − 60 × high conflicts − 15 × medium conflicts
```

Consistency is floored at 0.

Grounding looks only at properties the schema actually stated:

```
grounding = (verified + 0.5 × partial) / stated properties × 100
```

Verified means the stated value appears on the page. Partial means it is present but not an exact match. If nothing was stated, grounding is blank, and the quality formula uses completeness in its place.

```
quality = 0.45 × completeness + 0.20 × grounding + 0.35 × consistency
```

If any high-severity identity conflict exists, quality is capped at 59. If the sample has no JSON-LD, quality, completeness, and consistency are 0.

A type is Present when every applicable property is present, Partial when some are, Absent when none are, and Not applicable when that type does not apply to the business.

### 9.6 Agent readiness

Four checks: AI-bot robots policy, FAQ or QA schema, a short quotable definition or at least three H2/H3 blocks, and a live response from `/llms.txt`.

Checks that did not run are left out.

```
agent readiness = 100 × checks present / (checks present + checks missing)
```

If every check failed to run, the score is blank. This is on-site extractability for an agent. It is not a citation rank.

### 9.7 Topical coverage

Three-word phrase overlap between two pages is Jaccard similarity: shared phrases divided by the union of phrases.

Two pages are treated as cannibalizing when similarity is above 0.40, or when they share an H1 and similarity is above 0.25.

```
coverage = min(100, 30 + unique topical entities × 3.5 + min(30, H2 count × 2))
```

Status:

- Pass when average information gain is 70 or higher, there are no unbacked superlatives, and there is no cannibalization cluster.
- Thin commodity when average information gain is under 45, or unbacked claims are 5 or more, or cannibalization clusters are 2 or more.
- Needs improvement in the remaining cases.

### 9.8 Readability

Flesch reading ease, clamped to 0–100. Empty text is reported as 50.

```
reading ease = 206.835
               − 1.015 × (words / sentences)
               − 84.6 × (syllables / words)
```

Syllables are counted from vowel groups, with a silent trailing “e” removed except on words ending in “le”. The target band used in the experience pillar is 60–80. Below 50 triggers the content deduction in section 2 and the human deduction in section 5.

### 9.9 Form friction

Counted across detected forms, then capped at 100.

```
friction = forms missing labels × 20
         + forms without a captcha or honeypot × 15
         + forms without a confirmation destination × 10
```

| Friction | Grade |
| --- | --- |
| Below 15 | A |
| 15–34.9 | B |
| 35–59.9 | C |
| 60–100 | D |

No forms: friction 0 and grade N/A. The CRO card uses `100 − friction` as the ease score.

### 9.10 Accessibility screening

This is an automated WCAG 2.2 style screening. It is not a certification.

Contrast uses the W3C relative-luminance formula. Each color channel is `value / 255`, then linearized (`v / 12.92` at or below 0.04045, otherwise `((v + 0.055) / 1.055) ^ 2.4`). Luminance is `0.2126 R + 0.7152 G + 0.0722 B`.

```
contrast ratio = (lighter luminance + 0.05) / (darker luminance + 0.05)
```

Body text needs 4.5:1. Large text needs 3:1.

```
compliance = checks passed / (checks passed + violations) × 100
```

The same ratio is used for each principle (perceivable, operable, understandable, robust) and for each check group (images, forms, headings, landmarks, tables, contrast, viewport, keyboard, links, focus, target size, language, ARIA, buttons, iframes, duplicate ids, modals).

| Compliance | Status |
| --- | --- |
| 90 or above, and no high-severity violation | Pass |
| 70–89.9 | Needs attention |
| Below 70 | Non-compliant |

---

## 10. Live AI visibility

These rates use successful engine responses only. A failed, timed-out, or empty call is excluded. It is not counted as “the brand was omitted.”

If no successful response exists, every rate stays blank and the status is not measured.

### Mention rate and citation rate

For each engine, and again across all successful responses:

```
mention rate  = responses that name the brand / successful responses × 100
citation rate = responses that cite the site’s own domain / successful responses × 100
```

### Citation tracker score

For each engine that actually answered:

```
engine score = responses where the site was cited / measured responses × 100
tracker score = average of those engine scores, rounded to a whole number
```

Engines that were configured but did not answer are listed as not measured. They are left out of the average. If no engine answered, the tracker score stays blank.

### Share of model

```
share of model           = brand mentions / successful responses × 100
first-party citation share = first-party citations / successful responses × 100
```

Recommendation rank gives a full weight to position 1, 0.75 to positions 2 and 3, 0.40 to position 4 or worse, and 0.50 when the brand is mentioned with no rank. An omission adds nothing.

```
rank score = sum of those weights / successful responses × 100
```

Funnel-weighted share uses the query class:

| Class | Stage | Weight |
| --- | --- | ---: |
| Commercial, comparison, high intent | Decision | 4.0 |
| Services, problem | Consideration | 2.5 |
| Brand, audience, location, and the rest | Awareness | 1.0 |

```
funnel share = sum(weight of mentioned queries) / sum(weight of all successful queries) × 100
```

A competitor’s share is the percent of successful responses that name that competitor. A displacement is recorded when the competitor appears and the target is missing, or when the competitor leads and the target is ranked below first.

### Visibility scorecard

Each rate is hits divided by the responses where that check applied, times 100. A check that was not run stays blank.

| Rate | What counts as a hit |
| --- | --- |
| Entity accuracy | The answer contains the brand, a known service, a known location, the industry, or the audience, over the slots that were available to check |
| Service recognition | A services query whose answer contains a known service term |
| Pricing recognition | A pricing query whose answer contains the brand |
| ICP recognition | An audience query whose answer contains the audience or the brand |
| Competitor visibility | A successful answer that names a known competitor |
| Source consistency | When the same query was repeated at least twice, the share of cited domains that showed up in at least two repeats |

Citation accuracy is left blank. It is not inferred from a keyword match.

Sentiment on an answer is a polarity from −1 to +1: `(positive cue words − negative cue words) / (positive + negative)`. At or above 0.25 is positive. At or below −0.25 is negative. Any negative cue that does not reach those lines is skeptical. No cue words is neutral at 0.

---

## 11. Competitive bake-off

On the competitor card:

```
win rate = target wins / (target wins + competitor wins + ties) × 100
```

Ties count in the denominator, so a tie does not count as a win. With no completed comparisons the rate is blank.

---

## 12. How findings are ordered

Ordering is separate from the points a finding removes.

Commercial order: blocking first, then higher business impact, then higher confidence, then higher technical severity.

Technical order: higher technical severity, then higher confidence, then higher business impact.

The report names the highest-business-impact finding and the highest-technical finding separately when they are not the same finding.

---

## 13. External authority

There is no formula that turns backlinks, search-console clicks, analytics, or directory listings into a Dristik authority score.

When a provider is connected, its own metric is shown with its own name and the date of the snapshot. Ahrefs Domain Rating, Semrush Authority Score, and Majestic Trust Flow are those vendors’ numbers. A DataForSEO or SerpAPI result is one query snapshot, not a rank authority score. Search Console reports clicks, impressions, CTR, and average position for the property and period that were fetched. A page missing from a sampled query list is not treated as deindexed.

When a provider is not connected, not applicable to the business, or down, the section says so. The audit still finishes. Trust’s category weight is removed and the other category weights are renormalized, as described in section 3.

---

## 14. Which number to read

| Question | Read this |
| --- | --- |
| What is the audit’s headline mark? | Overall category rollup in section 3 |
| Why did one pillar move? | That category’s deductions and its subsections in section 4 |
| How does it look to a buyer, to Google, and on the page for answer engines? | Human, Google, and AI readiness in section 5 |
| Did ChatGPT, Perplexity, Gemini, Claude, or Copilot actually mention or cite the site? | Section 10. Blank means the live run did not happen. |
| Can an engine quote the pages we crawled? | GEO extractability in section 7 |
| Is external authority weak? | Only a connected vendor metric. Otherwise the section is not measured. |
