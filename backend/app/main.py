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


import json
from fastapi.responses import HTMLResponse, JSONResponse, Response

@app.get("/docs", include_in_schema=False)
async def get_documentation(_user: UserIdentity = Depends(verify_docs_access)):
    html_resp = get_swagger_ui_html(openapi_url="/openapi.json", title=f"{settings.APP_NAME} - Swagger UI")
    body = html_resp.body.decode("utf-8")
    top_bar = """
    <div style="background: #0f172a; border-bottom: 1px solid #334155; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 9999;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-weight: 700; font-size: 16px; letter-spacing: -0.02em;">Dristik AI API Hub</span>
        <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 12px; font-weight: 600; padding: 3px 8px; border-radius: 9999px; border: 1px solid rgba(56, 189, 248, 0.3);">340+ Endpoints</span>
      </div>
      <div style="display: flex; align-items: center; gap: 10px;">
        <a id="download-json-btn" href="/api/v1/openapi/download" download="dristik_api_list.json" style="display: inline-flex; align-items: center; gap: 8px; background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: background 0.15s ease;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
          ⬇ 1-Click Download JSON
        </a>
        <a id="download-md-btn" href="/api/v1/openapi/markdown" download="dristik_api_list.md" style="display: inline-flex; align-items: center; gap: 8px; background: #1e293b; border: 1px solid #475569; color: #f1f5f9; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 500;">
          ⬇ Download Markdown (.md)
        </a>
        <a href="/redoc" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; background: #334155; color: #e2e8f0; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 500;">
          ReDoc View
        </a>
      </div>
    </div>
    """
    body = body.replace('<div id="swagger-ui">', top_bar + '<div id="swagger-ui">')
    return HTMLResponse(content=body)


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


@app.get("/api/v1/openapi/download", include_in_schema=False)
@app.get("/openapi.json/download", include_in_schema=False)
async def download_openapi_json(_user: UserIdentity = Depends(verify_docs_access)):
    schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Dristik AI: Enterprise Evidence-Driven Website Intelligence Platform",
        routes=app.routes,
    )
    return Response(
        content=json.dumps(schema, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="dristik_api_list.json"'},
    )


@app.get("/api/v1/openapi/markdown", include_in_schema=False)
async def download_openapi_markdown(_user: UserIdentity = Depends(verify_docs_access)):
    schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Dristik AI: Enterprise Evidence-Driven Website Intelligence Platform",
        routes=app.routes,
    )
    lines = [
        f"# {settings.APP_NAME} - API Reference List",
        f"**Version**: {settings.APP_VERSION}  ",
        f"**Total Paths**: {len(schema.get('paths', {}))}  \n",
        "| Method | Endpoint Path | Summary | Tags |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for path, methods in sorted(schema.get("paths", {}).items()):
        for method, spec in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch", "options", "head"):
                continue
            summary = (spec.get("summary") or spec.get("description") or "").replace("\n", " ").strip()
            if len(summary) > 80:
                summary = summary[:77] + "..."
            tags = ", ".join(spec.get("tags", []))
            lines.append(f"| `{method.upper()}` | `{path}` | {summary or '-'} | {tags or '-'} |")

    return Response(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dristik_api_list.md"'},
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
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
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
