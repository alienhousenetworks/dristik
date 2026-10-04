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
    try:
        from app.workers.scheduler import scheduler
        await scheduler.start()
    except Exception as exc:
        logging.getLogger(__name__).warning("Autonomous scheduler startup skipped: %s", exc)
    yield
    try:
        from app.workers.scheduler import scheduler
        await scheduler.stop()
    except Exception as exc:
        logging.getLogger(__name__).warning("Autonomous scheduler shutdown skipped: %s", exc)



from typing import Optional
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
from app.domain.enums import UserRole
from app.identity.authorizer import ORG_STAFF_ROLES, UserIdentity
from app.identity.deps import get_current_user_optional
from app.identity import service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Dristik AI: Enterprise Evidence-Driven Website Intelligence Platform",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

security = HTTPBasic(auto_error=False)


def verify_docs_access(
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    current_user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> UserIdentity:
    """Ensure only Admin or Staff can access API documentation."""
    # 1. Existing session cookie or Bearer token
    if current_user:
        is_staff_or_admin = (
            current_user.is_system
            or current_user.role in (UserRole.SYSTEM_ADMIN, UserRole.OWNER, UserRole.ADMIN)
            or current_user.role in ORG_STAFF_ROLES
        )
        if is_staff_or_admin:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators and staff members.",
        )

    # 2. HTTP Basic Auth dialog in browser
    if credentials:
        try:
            user, _ = service.login(credentials.username, credentials.password)
            is_staff_or_admin = (
                user.is_system
                or user.role in (UserRole.SYSTEM_ADMIN, UserRole.OWNER, UserRole.ADMIN)
                or user.role in ORG_STAFF_ROLES
            )
            if is_staff_or_admin:
                return user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted to administrators and staff members.",
            )
        except ValueError:
            pass

    # 3. Prompt browser for credentials
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin or Staff authentication required.",
        headers={"WWW-Authenticate": "Basic"},
    )


@app.get("/docs", include_in_schema=False)
async def get_documentation(_user: UserIdentity = Depends(verify_docs_access)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{settings.APP_NAME} - Swagger UI")


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(_user: UserIdentity = Depends(verify_docs_access)):
    return get_redoc_html(openapi_url="/openapi.json", title=f"{settings.APP_NAME} - ReDoc")


@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(_user: UserIdentity = Depends(verify_docs_access)):
    return JSONResponse(
        get_openapi(
            title=settings.APP_NAME,
            version=settings.APP_VERSION,
            description="Dristik AI: Enterprise Evidence-Driven Website Intelligence Platform",
            routes=app.routes,
        )
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
