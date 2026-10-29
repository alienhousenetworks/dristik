"""Dristik Connect Copilot & Conversational Bridge.

Powers the interactive chatbot in the AI Connection section for:
1. Guiding connection setup and answering capability questions.
2. Automatically parsing and ingesting pasted external AI responses in-chat.
3. Live bidirectional messaging with connected external AI endpoints.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.api.routes.integrations import universal_connect as uc
from app.api.routes.integrations import ai_onboarding as onboarding
from app.api.routes.integrations import provider_adapters as providers

router = APIRouter(prefix="/connect/chat", tags=["Dristik Connect Chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ConnectChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=50000)
    connection_id: str | None = Field(default=None, max_length=100)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)


def _detect_handshake_content(text: str) -> bool:
    return any(
        marker in text.lower()
        for marker in [
            "json:dristik-connection",
            "webhook_url",
            "connection_mode",
            "supported_capabilities",
            "ready to pair with dristik",
        ]
    ) or bool(re.search(r"(?i)\b(?:webhook|callback)\s*[:=]\s*['\"]?https?://", text))


@router.post("")
async def chat_with_connect(body: ConnectChatRequest, user: UserIdentity = Depends(get_current_user)):
    user_msg = body.message.strip()
    now = time.time()

    # 1. Check if user pasted an AI handshake response into the chat
    if _detect_handshake_content(user_msg):
        # Determine target connection
        target_conn_id = body.connection_id
        if not target_conn_id:
            with uc._db() as conn:
                row = conn.execute(
                    "SELECT id FROM uc_ai_connections WHERE org_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
                    (user.org_id,),
                ).fetchone()
                if row:
                    target_conn_id = row["id"]

        if target_conn_id:
            try:
                ingest_res = await onboarding.pair_ai_connection(
                    target_conn_id,
                    onboarding.HandshakeIngestRequest(raw_response=user_msg, auto_verify_ping=True),
                    user,
                )
                status_str = "Verified Active (200 OK)" if ingest_res["handshake_status"] == "verified_active" else ingest_res["handshake_status"]
                reply = (
                    f"🎉 **AI Connection Ingested & Configured!**\n\n"
                    f"- **Connection ID:** `{target_conn_id}`\n"
                    f"- **Mode:** `{ingest_res['connection_mode']}`\n"
                    f"- **Webhook URL:** `{ingest_res['webhook_url'] or 'Not provided (MCP Client mode)'}`\n"
                    f"- **Handshake Status:** **{status_str}**\n"
                    f"- **Bridge Code:** {'Staged safely for review' if ingest_res.get('code_staged') else 'Not required (Direct credentials used)'}\n\n"
                    f"{ingest_res['message']} You can now exchange tasks, stream audit reports, and chat bidirectional."
                )
                return {
                    "role": "assistant",
                    "content": reply,
                    "action": "handshake_ingested",
                    "connection_id": target_conn_id,
                    "handshake": ingest_res,
                }
            except Exception as exc:
                return {
                    "role": "assistant",
                    "content": f"⚠️ I detected connection parameters in your message, but pairing encountered an issue: {exc}. Please verify the target connection is active.",
                    "action": "handshake_error",
                }

    # 2. If target connection is specified, check for direct bridge messaging
    if body.connection_id:
        with uc._db() as conn:
            conn_row = conn.execute(
                "SELECT * FROM uc_ai_connections WHERE id=? AND org_id=?",
                (body.connection_id, user.org_id),
            ).fetchone()

        if conn_row and conn_row["webhook_url"]:
            # Deliver outbound message to external AI webhook
            webhook = conn_row["webhook_url"]
            headers = json.loads(conn_row["outbound_headers_json"] or "{}")
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0), follow_redirects=False) as client:
                    payload = {
                        "event": "dristik_user_message",
                        "sender": user.email,
                        "connection_email": conn_row["connection_email"],
                        "message": user_msg,
                        "timestamp": now,
                    }
                    resp = await client.post(webhook, json=payload, headers={"Content-Type": "application/json", **headers})
                    if resp.status_code < 400:
                        data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"response": resp.text}
                        ai_reply = data.get("response") or data.get("message") or resp.text or "Message received by external AI."
                        # Log event
                        uc._log_connection_event(
                            body.connection_id, user.org_id, "chat_message_dispatched",
                            direction="outbound", method="POST", summary=f"Dispatched message to {webhook}",
                            arguments={"message": user_msg[:200]}, status="success"
                        )
                        return {
                            "role": "assistant",
                            "content": f"**[{conn_row['name']}]:** {ai_reply}",
                            "action": "external_ai_response",
                            "connection_id": body.connection_id,
                        }
            except Exception as exc:
                # Fallback to assistant acknowledging outbound attempt
                pass

    # 3. Intelligent Connect Copilot Guidance
    lower = user_msg.lower()
    if "claude" in lower:
        guidance = (
            "To connect **Claude Desktop** or **Claude Code**:\n\n"
            "1. In Dristik Connect, click **Generate credentials** with provider `Claude`.\n"
            "2. In your `claude_desktop_config.json`, add the Dristik MCP server block.\n"
            "3. Put your one-time API key in the `Authorization: Bearer <KEY>` header.\n"
            "4. Copy the **Onboarding Prompt** into Claude. When Claude replies with its connection details, paste Claude's response right here in this chat to complete the bidirectional link!"
        )
    elif "grok" in lower or "xai" in lower:
        guidance = (
            "To connect **Grok (xAI)**:\n\n"
            "1. Generate Dristik credentials for `Grok`.\n"
            "2. Grok can either connect via direct MCP JSON-RPC (`/api/v1/mcp`) or you can register your xAI API key under **Model Provider Credentials**.\n"
            "3. Copy the Grok Onboarding Prompt into Grok. Paste Grok's reply back here to establish the two-way bridge."
        )
    elif "chatgpt" in lower or "gpt" in lower:
        guidance = (
            "To connect **ChatGPT (Custom GPT / Actions)**:\n\n"
            "1. Under ChatGPT Custom GPT Actions, use Dristik's MCP gateway URL.\n"
            "2. Set Authentication to Bearer API key.\n"
            "3. Provide the Onboarding Prompt to your GPT. Paste its confirmation block here to pair."
        )
    elif "delete" in lower or "revoke" in lower:
        guidance = (
            "**Managing Connections:**\n\n"
            "- To revoke an active connection, click **Revoke** on its card. Its key will immediately stop working.\n"
            "- Once revoked, click **Delete** (trash icon) to permanently purge it from your tenant database.\n"
            "- Use **Clean up revoked** at the top of the connections list to remove all revoked credentials in 1 click."
        )
    elif "agent" in lower or "105" in lower or "specialist" in lower:
        guidance = (
            "Dristik operates **105 Specialist Agents** across 12 intelligence domains, including:\n\n"
            "- **Technical SEO & Canonical Crawl:** Crawl budget, robots, redirect loop analyzers.\n"
            "- **GEO (Generative Engine Optimization):** Citation visibility across ChatGPT, Perplexity, Claude & Gemini.\n"
            "- **AEO (Answer Engine Optimization):** 40–60 word extractability, schema authority, direct answers.\n"
            "- **Conversion & UX Intelligence:** High-converting layout and authority signals.\n\n"
            "Connected external AIs can invoke any authorized specialist agent via `dristik_audit_start` and inspect blackboard memory."
        )
    else:
        guidance = (
            "👋 **Dristik Connect Copilot is ready.**\n\n"
            "I can help you:\n"
            "1. **Pair an External AI:** Generate credentials, copy the specialized prompt to Claude/Grok/ChatGPT, and paste their reply directly here.\n"
            "2. **Auto-Verify Handshakes:** I automatically extract webhook URLs and test live two-way pings.\n"
            "3. **Orchestrate Audits:** Ask questions about Dristik's 105 specialist agents, DAG pipeline, or MCP tool suite."
        )

    return {
        "role": "assistant",
        "content": guidance,
        "action": "copilot_guidance",
    }
