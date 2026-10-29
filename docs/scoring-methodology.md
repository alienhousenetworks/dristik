# Dristik 2.0 Scoring Methodology

## Scoring Framework
Dristik calculates domain health across 6 core pillars, normalized on a 0-100 scale:
1. **Technical SEO** (Weight: 25%)
2. **Content & On-Page Quality** (Weight: 20%)
3. **Generative Engine Optimization (GEO)** (Weight: 15%)
4. **Authority & Competitive Profile** (Weight: 15%)
5. **User Experience & Core Web Vitals** (Weight: 15%)
6. **Conversion & Business Readiness** (Weight: 10%)

## Confidence & Severity Weighting
Findings are penalized according to severity:
- **CRITICAL**: -15 points per issue
- **HIGH**: -8 points per issue
- **MEDIUM**: -3 points per issue
- **LOW**: -1 point per issue
- **INFORMATIONAL**: 0 points penalty
Scores are calibrated using log-sigmoid scaling to prevent single-page anomalies from distorting domain-wide health.
