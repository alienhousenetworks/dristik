"""
Dristik AI FastAPI Main Entrypoint
Enterprise-grade autonomous website intelligence & growth auditor API Gateway.
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import mount_http
from app.core.config import settings, validate_production_configuration
from app.identity.store import get_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_production_configuration(settings)
    get_store().seed_system()
    try:
        from app.external_authority.store import ExternalStore
        ExternalStore().ensure_schema()
    except Exception as exc:
        logging.getLogger(__name__).info("external authority schema init skipped: %s", type(exc).__name__)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Dristik AI: Enterprise Evidence-Driven Website Intelligence Platform",
    lifespan=lifespan,
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
if settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mount_http(app)


@app.get("/health", tags=["Health"])
async def health_check():
    creds = settings.get_llm_credentials()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "active_provider": creds.get("provider", "none"),
        "provider_display_name": creds.get("display_name", "None"),
        "configured_providers": settings.get_configured_providers(),
        "has_active_llm_key": settings.has_active_llm_key,
        "model_fast": creds.get("model_fast"),
        "model_reasoning": creds.get("model_reasoning"),
        "has_together_api_key": bool(settings.TOGETHER_API_KEY)  # backward compat
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Dristik AI — Autonomous Website Intelligence & Growth Auditor",
        "documentation": "/docs",
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
