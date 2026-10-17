# Scoring methodology

The sealed category scores come from `app.scoring.engine`, `app.scoring.weights`, and `app.scoring.calibration`. Calibration v5 benchmarks live in `app.scoring.calibration_v5`.

The number on the cover is `app.scoring.displayed_score.displayed_composite`: Technical Discoverability 30%, GEO extractability 25%, live citations 25%, CRO 20%. A pillar with no measurement is left out and the remaining weights are scaled. `app.scoring.score_explanations.explain_displayed_score` returns that composite. It does not calculate a different one.

An unmeasured check stays unmeasured. Low-confidence findings do not reduce the sealed category score. Live citation stays empty until this run has a successful engine response.
