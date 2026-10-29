"""Copy/paste onboarding for connecting external AI clients to Dristik.

Returned code is staged for human review. This module deliberately does not
execute AI-generated code or shell commands in the API process.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from typing import Literal
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission
from app.api.routes.integrations import universal_connect as uc

router = APIRouter(prefix="/connect/ai-onboarding", tags=["AI Connection Onboarding"])
PROVIDERS = ("chatgpt", "claude", "gemini", "grok", "deepseek", "kimi", "openrouter", "custom")
MAX_RESPONSE_CHARS = 200_000
MAX_FILE_BYTES = 100_000
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"]?[^\s'\"]{12,}"),
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
TOOL_CATALOG = (
    {"name": "dristik_ping", "scope": "capabilities.list"},
    {"name": "dristik_capabilities_list", "scope": "capabilities.list"},
    {"name": "dristik_create_task", "scope": "tasks.create"},
    {"name": "dristik_task_send_message", "scope": "tasks.message"},
    {"name": "dristik_audit_start", "scope": "audit.create"},
)
NEXT_STEP = "Copy the prompt to the selected AI. Keep the Dristik API key out of the prompt; configure it only in a trusted MCP client secret field."
EXECUTION_POLICY = "AI-generated code is staged for review and is never executed by this endpoint."

def _db():
    uc.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(uc.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS uc_ai_onboarding_submissions (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL, created_by TEXT NOT NULL,
      connection_id TEXT NOT NULL, provider TEXT NOT NULL, status TEXT NOT NULL,
      response_sha256 TEXT NOT NULL, response_json TEXT NOT NULL,
      created_at REAL NOT NULL, updated_at REAL NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uc_onboarding_org ON uc_ai_onboarding_submissions(org_id, created_at)")
    return conn

ProviderName = Literal["chatgpt", "claude", "gemini", "grok", "deepseek", "kimi", "openrouter", "custom"]
DEFAULT_GOAL = "Connect this AI to Dristik and verify authorized two-way messaging."


class OnboardingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider: ProviderName
    grant_profile: Literal["read_only", "audit_operator", "workflow_admin", "full_access"] = "audit_operator"
    expires_in_days: int = Field(default=30, ge=1, le=365)
    goal: str = Field(default=DEFAULT_GOAL, max_length=3000)


class OnboardingPromptRequest(BaseModel):
    connection_id: str = Field(min_length=1, max_length=100)
    provider: ProviderName
    goal: str = Field(default=DEFAULT_GOAL, max_length=3000)

class ReturnedFile(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=MAX_FILE_BYTES)

    @field_validator("path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value.strip())
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("File paths must be safe relative paths.")
        if path.parts[0].startswith(".") or any(part in {".git", ".env", "secrets", "credentials"} for part in path.parts):
            raise ValueError("Hidden, repository metadata, and credential paths are not accepted.")
        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            raise ValueError("Private-key and certificate files must not be submitted as code.")
        return str(path)

class OnboardingResponse(BaseModel):
    connection_id: str = Field(min_length=1, max_length=100)
    provider: ProviderName
    summary: str = Field(min_length=1, max_length=8000)
    files: list[ReturnedFile] = Field(default_factory=list, max_length=40)
    setup_commands: list[str] = Field(default_factory=list, max_length=30)
    dependencies: list[str] = Field(default_factory=list, max_length=100)
    environment_variable_names: list[str] = Field(default_factory=list, max_length=100)
    test_plan: list[str] = Field(default_factory=list, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=50)

def _prompt(provider: str, name: str, endpoint: str, email: str, scopes: list[str], goal: str) -> str:
    return f"""You are establishing a sovereign two-way connection with Dristik Autonomous Growth OS for connection profile "{name}".
Selected AI/client: {provider}
Dristik MCP & API Gateway: {endpoint}
Connection identity: {email}
Granted scopes: {json.dumps(scopes)}
Onboarding goal: {goal}

Dristik is an autonomous growth engine operating 105 specialist agents, 12 domains, a deterministic DAG execution pipeline, shared blackboard memory, and multi-engine citation benchmarking.

=== STEP 1: CONFIGURE DRISTIK CREDENTIALS IN YOUR CLIENT ===
1. In your client's settings, configure the Dristik MCP endpoint:
   - Endpoint URL: {endpoint}
   - Header: X-Dristik-Connection-Email: {email}
   - Header: Authorization: Bearer <PASTE_DRISTIK_API_KEY_HERE>
   (Note: Use the one-time API key provided separately by the user in your client secret settings; do NOT output this key in plaintext responses).
2. Test discovery using MCP `tools/list` or ping with `dristik_ping`.

=== STEP 2: PROVIDE YOUR INBOUND CONNECTION DETAILS FOR TWO-WAY LINK ===
To enable Dristik to push audit findings, tasks, blackboard updates, and messages back to you, reply to the user with your inbound connection parameters.
Choose either Option A or Option B:

[Option A: Direct Webhook / WebSocket]
If you have an active webhook or WebSocket endpoint, supply the URL and any required authorization headers.

[Option B: Standalone Integration Bridge Code]
If you do not have a public webhook, provide a complete, runnable Python (FastAPI/uvicorn) or Node.js (Express) bridge script that listens on a local port (e.g., 8088) and relays messages to you.

=== STEP 3: FORMAT YOUR RESPONSE ===
Output your response inside a single code block labeled ```json:dristik-connection:
{{
  "client_name": "{name}",
  "provider": "{provider}",
  "connection_mode": "webhook" | "websocket" | "bridge_code" | "custom_bot",
  "webhook_url": "https://your-webhook-or-callback-url.com/inbound" | null,
  "websocket_url": "wss://your-websocket-url.com" | null,
  "auth_headers": {{ "Authorization": "Bearer <YOUR_AI_OR_SERVICE_TOKEN>" }},
  "supported_capabilities": ["task_updates", "audit_alerts", "chat"],
  "integration_code": "Complete runnable Python or Node.js script if Option B was selected, or null if Option A",
  "status_summary": "Ready to pair with Dristik Brain",
  "pairing_instructions": "Brief instructions on what was configured"
}}

Do not fabricate external URLs. The user will copy your entire response and paste it directly into Dristik's Connect Chatbot to automatically verify and establish the bidirectional channel."""

def _tool_inventory(scopes: list[str]) -> list[dict[str, str]]:
    return [dict(tool) for tool in TOOL_CATALOG if "*" in scopes or tool["scope"] in scopes]

def _provider_prompts(name: str, endpoint: str, email: str, scopes: list[str], goal: str) -> dict[str, str]:
    return {provider: _prompt(provider, name, endpoint, email, scopes, goal) for provider in PROVIDERS}

def _prompt_bundle(provider: str, prompts: dict[str, str], scopes: list[str]) -> dict:
    return {
        "provider": provider,
        "prompt": prompts[provider],
        "prompts": prompts,
        "tool_inventory": _tool_inventory(scopes),
        "next_step": NEXT_STEP,
        "execution_policy": EXECUTION_POLICY,
    }

def _active_connection(connection_id: str, org_id: str) -> dict:
    with uc._db() as base:
        row = base.execute(
            "SELECT id,name,connection_email,scopes_json,status FROM uc_ai_connections WHERE id=? AND org_id=?",
            (connection_id, org_id),
        ).fetchone()
        if row is None or row["status"] != "active":
            raise HTTPException(status_code=404, detail="Connection not found.")
        return dict(row)

@router.post("/kit", status_code=201)
async def create_onboarding_kit(body: OnboardingCreate, request: Request,
                                user: UserIdentity = Depends(require_permission("org:manage"))):
    """Create a scoped Dristik credential and copy/paste prompt for a named AI client."""
    issued = await uc.create_ai_connection(
        uc.AIConnectionCreate(name=body.name, grant_profile=body.grant_profile,
                              expires_in_days=body.expires_in_days),
        user, request,
    )
    prompts = _provider_prompts(body.name, issued["mcp_endpoint"], issued["connection_email"], issued["scopes"], body.goal)
    return {
        "connection": {k: issued[k] for k in ("id", "name", "connection_email", "api_key",
            "grant_profile", "scopes", "expires_at", "mcp_endpoint", "mcp_config", "key_display_policy")},
        **_prompt_bundle(body.provider, prompts, issued["scopes"]),
    }

@router.post("/prompt")
async def onboarding_prompt(body: OnboardingPromptRequest, request: Request,
                            user: UserIdentity = Depends(require_permission("org:manage"))):
    """Return copy/paste prompts for an existing connection. Does not reveal or rotate the API key."""
    row = _active_connection(body.connection_id, user.org_id)
    scopes = json.loads(row["scopes_json"])
    prompts = _provider_prompts(row["name"], uc._resolve_mcp_endpoint(request), row["connection_email"], scopes, body.goal)
    return {"connection_id": row["id"], **_prompt_bundle(body.provider, prompts, scopes)}

@router.post("/response", status_code=201)
async def submit_ai_response(body: OnboardingResponse,
                             user: UserIdentity = Depends(require_permission("org:manage"))):
    """Validate and stage the AI response; never execute returned code or commands."""
    with uc._db() as base:
        row = base.execute("SELECT id FROM uc_ai_connections WHERE id=? AND org_id=?",
                           (body.connection_id, user.org_id)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found.")
    payload = body.model_dump()
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > MAX_RESPONSE_CHARS:
        raise HTTPException(status_code=413, detail="AI response exceeds the staging size limit.")
    for file in body.files:
        for pattern in SECRET_PATTERNS:
            if pattern.search(file.content):
                raise HTTPException(status_code=422, detail=f"Potential secret detected in {file.path}; remove it and use secure secret configuration.")
    if any(re.search(r"(?i)(curl\s+.*\|\s*(sh|bash)|rm\s+-rf\s+[/~]|sudo\s+|docker\s+run\s+.*--privileged)", cmd) for cmd in body.setup_commands):
        raise HTTPException(status_code=422, detail="Privileged or pipe-to-shell setup commands are not accepted.")
    now, submission_id = time.time(), "uobs_" + uuid.uuid4().hex
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    conn = _db()
    try:
        conn.execute("INSERT INTO uc_ai_onboarding_submissions VALUES (?,?,?,?,?,?,?,?,?,?)",
            (submission_id, user.org_id, user.user_id, body.connection_id, body.provider,
             "awaiting_review", digest, encoded, now, now))
        conn.commit()
    finally:
        conn.close()
    return {
        "submission_id": submission_id,
        "connection_id": body.connection_id,
        "status": "awaiting_review",
        "response_sha256": digest,
        "files_staged": len(body.files),
        "setup_commands_staged": len(body.setup_commands),
        "execution_performed": False,
        "next_step": "Review the diff and dependencies, configure secrets separately, then run tests in an isolated disposable sandbox. Production application requires explicit approval.",
    }

@router.get("/submissions")
async def list_submissions(user: UserIdentity = Depends(get_current_user), limit: int = 50):
    limit = max(1, min(limit, 100))
    conn = _db()
    try:
        rows = conn.execute("SELECT id,connection_id,provider,status,response_sha256,created_at,updated_at FROM uc_ai_onboarding_submissions WHERE org_id=? ORDER BY created_at DESC LIMIT ?", (user.org_id, limit)).fetchall()
    finally:
        conn.close()
    return {"submissions": [dict(row) for row in rows]}

@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, user: UserIdentity = Depends(get_current_user)):
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM uc_ai_onboarding_submissions WHERE id=? AND org_id=?", (submission_id, user.org_id)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    payload = json.loads(row["response_json"])
    return {"submission_id": row["id"], "connection_id": row["connection_id"],
            "provider": row["provider"], "status": row["status"],
            "response_sha256": row["response_sha256"], "created_at": row["created_at"],
            "summary": payload["summary"], "files": payload["files"],
            "setup_commands": payload["setup_commands"], "dependencies": payload["dependencies"],
            "environment_variable_names": payload["environment_variable_names"],
            "test_plan": payload["test_plan"], "limitations": payload["limitations"],
            "execution_performed": False}


class HandshakeIngestRequest(BaseModel):
    raw_response: str = Field(min_length=1, max_length=250_000)
    auto_verify_ping: bool = Field(default=True)


def _extract_handshake_payload(raw_text: str) -> dict[str, Any]:
    tagged_match = re.search(r"```(?:json:dristik-connection|json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    parsed = {}
    if tagged_match:
        try:
            parsed = json.loads(tagged_match.group(1))
        except Exception:
            pass
    if not parsed:
        json_match = re.search(r"(\{[\s\S]*\"(?:webhook_url|provider|client_name|connection_mode)\"[\s\S]*\})", raw_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
            except Exception:
                pass

    webhook_url = parsed.get("webhook_url") or parsed.get("callback_url") or parsed.get("endpoint")
    websocket_url = parsed.get("websocket_url")
    auth_headers = parsed.get("auth_headers") or {}
    connection_mode = parsed.get("connection_mode") or ("webhook" if webhook_url else "mcp_client")
    summary = parsed.get("status_summary") or parsed.get("summary") or "External AI configuration parsed"
    integration_code = parsed.get("integration_code") or ""

    if not webhook_url:
        url_match = re.search(r"(?i)\b(?:webhook|callback|endpoint)\s*[:=]\s*['\"]?(https?://[^\s'\"<>]+)", raw_text)
        if url_match:
            webhook_url = url_match.group(1)
            connection_mode = "webhook"

    if not integration_code:
        code_match = re.search(r"```(?:python|javascript|typescript|bash|sh)\s*\n(.*?)\n```", raw_text, re.DOTALL)
        if code_match:
            integration_code = code_match.group(1)

    clean_webhook = (
        str(webhook_url).strip()
        if webhook_url
        and str(webhook_url).strip().lower()
        not in (
            "none",
            "null",
            "<your_inbound_webhook_or_callback_url_or_none>",
            "https://your-webhook-or-callback-url.com/inbound",
        )
        else None
    )
    clean_ws = (
        str(websocket_url).strip()
        if websocket_url
        and str(websocket_url).strip().lower()
        not in (
            "none",
            "null",
            "<your_websocket_url_or_none>",
            "wss://your-websocket-url.com",
        )
        else None
    )

    return {
        "client_name": parsed.get("client_name"),
        "provider": parsed.get("provider"),
        "webhook_url": clean_webhook,
        "websocket_url": clean_ws,
        "auth_headers": auth_headers if isinstance(auth_headers, dict) else {},
        "connection_mode": connection_mode,
        "summary": summary,
        "integration_code": integration_code,
        "pairing_instructions": parsed.get("pairing_instructions"),
        "parsed_json": parsed,
    }


@router.post("/handshake/{connection_id}")
async def pair_ai_connection(
    connection_id: str,
    body: HandshakeIngestRequest,
    user: UserIdentity = Depends(require_permission("org:manage")),
):
    with uc._db() as conn:
        row = conn.execute("SELECT * FROM uc_ai_connections WHERE id=? AND org_id=?", (connection_id, user.org_id)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found.")

    extracted = _extract_handshake_payload(body.raw_response)
    webhook_url = extracted["webhook_url"]
    auth_headers = extracted["auth_headers"]
    connection_mode = extracted["connection_mode"]
    integration_code = extracted["integration_code"]

    now = time.time()
    ping_result = None
    handshake_status = "credentials_saved"

    if webhook_url:
        is_valid_public = True
        try:
            uc._validate_public_audit_url(webhook_url)
        except Exception:
            is_valid_public = False

        if is_valid_public and body.auto_verify_ping:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), follow_redirects=False) as client:
                    ping_payload = {
                        "event": "dristik_handshake_ping",
                        "connection_id": connection_id,
                        "connection_email": row["connection_email"],
                        "timestamp": now,
                        "message": "Dristik Brain Handshake Verification Ping",
                    }
                    req_headers = {"Content-Type": "application/json", **auth_headers}
                    resp = await client.post(webhook_url, json=ping_payload, headers=req_headers)
                    ping_result = {"success": resp.status_code < 400, "status_code": resp.status_code}
                    handshake_status = "verified_active" if resp.status_code < 400 else "ping_non_2xx"
            except Exception as exc:
                ping_result = {"success": False, "error": str(exc)}
                handshake_status = "unverified_endpoint"
        else:
            handshake_status = "unverified_endpoint" if not is_valid_public else "pending_verification"

    if integration_code:
        for pattern in SECRET_PATTERNS:
            if pattern.search(integration_code):
                raise HTTPException(status_code=422, detail="Potential secret detected in integration code; please use environment variables.")
        if any(re.search(r"(?i)(curl\s+.*\|\s*(sh|bash)|rm\s+-rf\s+[/~]|sudo\s+|docker\s+run\s+.*--privileged)", cmd) for cmd in integration_code.splitlines()):
            raise HTTPException(status_code=422, detail="Privileged or destructive commands detected in code snippet.")
        submission_id = "uobs_" + uuid.uuid4().hex
        digest = hashlib.sha256(integration_code.encode("utf-8")).hexdigest()
        encoded = json.dumps({"summary": extracted["summary"], "files": [{"path": "integration_bridge.py", "content": integration_code}], "setup_commands": [], "dependencies": []})
        conn_sub = _db()
        try:
            conn_sub.execute("INSERT INTO uc_ai_onboarding_submissions VALUES (?,?,?,?,?,?,?,?,?,?)",
                             (submission_id, user.org_id, user.user_id, connection_id, row["name"],
                              "staged_bridge", digest, encoded, now, now))
            conn_sub.commit()
        finally:
            conn_sub.close()

    with uc._db() as conn:
        conn.execute(
            "UPDATE uc_ai_connections SET webhook_url=?, outbound_headers_json=?, connection_mode=?, handshake_status=?, last_handshake_at=?, updated_at=? WHERE id=?",
            (webhook_url, json.dumps(auth_headers), connection_mode, handshake_status, now if ping_result and ping_result.get("success") else None, now, connection_id)
        )
        conn.execute(
            "INSERT INTO uc_ai_connection_events VALUES (?,?,?,?,?,?)",
            ("uce_" + uuid.uuid4().hex, connection_id, user.org_id, "handshake_paired", now, json.dumps({
                "webhook_url": webhook_url, "handshake_status": handshake_status, "ping": ping_result
            }))
        )

    return {
        "connection_id": connection_id,
        "handshake_status": handshake_status,
        "webhook_url": webhook_url,
        "websocket_url": extracted["websocket_url"],
        "connection_mode": connection_mode,
        "ping_result": ping_result,
        "code_staged": bool(integration_code),
        "summary": extracted["summary"],
        "message": "Handshake verified and two-way connection active." if handshake_status == "verified_active" else "Connection parameters saved.",
    }
