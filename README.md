# Dristik AI — Enterprise Evidence-Driven Website Intelligence & Growth Auditor

> **Architecture:** problem, solution, features, flows, outputs, full backend tree, and the 35-agent Kahn DAG — [AI_ARCHITECTURE_AND_AGENTS.md](AI_ARCHITECTURE_AND_AGENTS.md). Full product map (parameters, APIs, gaps) — [DRISTIK_PRODUCT_REPORT.md](DRISTIK_PRODUCT_REPORT.md).

Dristik AI is an enterprise-grade autonomous website intelligence platform. It treats LLMs/SLMs not as an unconstrained source of truth, but as a replaceable inference engine operating strictly over a **Deterministic Evidence Plane**, a **Typed Cognitive Blackboard**, an **Adversarial Verification Loop**, and a **Deterministic Scoring Engine**.

---

## ⚡ Core Architecture

```
Website URL
   │
   ▼
[Zero-Trust SSRF Guard]
   │
   ▼
[Multi-page crawl + deterministic analyzers] ──► PageEvidence, ev_NNN, snap_<sha256>
   │
   ▼
[Wave-0 site facts + ExternalEvidenceEnricher] ──► ext_NNN (DNS/TLS/headers; CrUX if configured)
   │
   ▼
[35-agent AgentPool] ──► 6 Kahn waves (Business, SEO, Schema, Content, GEO, AI Search, UX/CRO/Trust, Verification)
   │
   ▼
[PageIntelligenceAgent] ──► per-URL SEO + 5 copywriters
   │
   ▼
[Integrity gate + CERTAIN/LIKELY/GUESSING rubric]
   │
   ▼
[ScoringEngine + GEO readiness + 7/30/90 + patch ZIP]
   │
   ▼
[Seal manifest.json] ──► ExecutiveReport over SSE
```

---

## 🚀 Quickstart

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure Together AI API (optional, deterministic fallback included)
cp .env.example .env

# Run unit & integration test suite
PYTHONPATH=. pytest tests/test_pipeline.py -v

# Start FastAPI Gateway
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run build
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## ⚙️ Configuration (.env)

```env
TOGETHER_API_KEY=your_together_api_key_here
TOGETHER_BASE_URL=https://api.together.xyz/v1
TOGETHER_MODEL_FAST=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
TOGETHER_MODEL_REASONING=meta-llama/Llama-3.3-70B-Instruct-Turbo
TOGETHER_TEMPERATURE=0.2
TOGETHER_MAX_TOKENS=3000

SSRF_PROTECTION_ENABLED=true
MAX_CRAWL_PAGES=5
```

---

## 🛡️ Enterprise Differentiators
- **90% Token Reduction**: Deterministic HTML cleaner strips boilerplate prior to LLM reasoning, keeping audits at **<$0.003/audit**.
- **Decoupled Confidence**: Exposes `Score (0-100)` alongside `Model Confidence (0-100%)` and `Evidence Coverage (0-100%)`.
- **Answerability Simulation**: Simulates commercial query answering across ChatGPT / Perplexity / Gemini perspectives.
- **Drop-in Code Fixes**: Direct copy-paste JSON-LD Organization/Product schemas, OpenGraph meta tags, and robots.txt directives inside the interactive Evidence Drawer.
# dristik
