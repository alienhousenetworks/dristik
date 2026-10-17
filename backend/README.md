# Dristik backend

FastAPI application for the Dristik audit. The package map is [docs/architecture.md](docs/architecture.md).

```bash
cd backend
python -m pytest tests/unit tests/contract tests/security tests/geo tests/integration/test_crawl_pipeline.py tests/test_domain_pillars.py
```

Run the API from this directory:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The container build that includes Playwright is the repository root `Dockerfile`. `deployment/Dockerfile` is the same image with this directory as the build context.
