"""
Dristik AI Connectors API Routes
Endpoints for registering, managing, and inspecting external platform integrations
(WordPress, GitHub, Shopify, Webflow, Generic Website).
"""
import os
import json
import urllib.parse
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
import httpx

from app.domain.models import Integration
from app.domain.enums import ConnectorType, ConnectorHealthStatus
from app.connectors.base.models import ConnectorCredentials, ConnectorHealth
from app.core.config import settings
from app.connectors.store import connector_store
from app.connectors.oauth_providers import router as oauth_router

router = APIRouter(prefix="/connectors", tags=["Platform Connectors"])
router.include_router(oauth_router)

class ConnectPlatformRequest(BaseModel):
    provider: ConnectorType
    name: str = Field(..., description="Friendly name for integration")
    target_url: str = Field(..., description="Target website or store URL")
    api_url: Optional[str] = None
    username: Optional[str] = None
    app_password: Optional[str] = None
    api_key: Optional[str] = None
    github_token: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = "main"
    scopes: List[str] = Field(default_factory=list)
    org_id: str = "org_default"
    workspace_id: str = "ws_default"

class ConnectPlatformResponse(BaseModel):
    success: bool
    integration: Integration
    health: ConnectorHealth
    message: str

@router.get("", response_model=List[Integration])
async def list_integrations(org_id: str = "org_default"):
    """List all registered platform connectors for an organization."""
    return connector_store.list_integrations(org_id=org_id)

@router.post("/connect", response_model=ConnectPlatformResponse)
async def connect_platform(req: ConnectPlatformRequest):
    """Register and verify a new platform connector."""
    creds = ConnectorCredentials(
        provider=req.provider,
        api_url=req.api_url or req.target_url,
        username=req.username,
        app_password=req.app_password,
        api_key=req.api_key,
        github_token=req.github_token,
        repository=req.repository,
        branch=req.branch or "main",
        scopes=req.scopes
    )

    integration = connector_store.add_integration(
        provider=req.provider,
        name=req.name,
        target_url=req.target_url,
        credentials=creds,
        repository=req.repository,
        branch=req.branch,
        org_id=req.org_id,
        workspace_id=req.workspace_id
    )

    connector = connector_store.get_connector(integration.integration_id)
    if not connector:
        raise HTTPException(status_code=500, detail="Failed to instantiate connector")

    health = await connector.test_connection()
    integration.status = health.status
    connector_store.persist(integration)

    return ConnectPlatformResponse(
        success=health.authenticated,
        integration=integration,
        health=health,
        message=f"Connected to {req.provider.value.title()}: {health.message}"
    )

@router.get("/{integration_id}/health", response_model=ConnectorHealth)
async def check_integration_health(integration_id: str):
    """Test live connectivity and health of a specific integration."""
    connector = connector_store.get_connector(integration_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Integration not found")
    return await connector.test_connection()

@router.get("/{integration_id}/discover", response_model=Dict[str, Any])
async def discover_integration_structure(integration_id: str):
    """Discover site hierarchy, detected SEO plugins, or repo framework."""
    connector = connector_store.get_connector(integration_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Integration not found")
    return await connector.discover_site_structure()

@router.delete("/{integration_id}")
async def delete_integration(integration_id: str):
    """Disconnect and remove an integration."""
    success = connector_store.delete_integration(integration_id)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True, "message": f"Integration {integration_id} disconnected"}

@router.get("/wordpress/download-plugin")
async def download_wp_bridge_plugin():
    """Download the official Dristik WordPress Bridge Plugin as a .zip file."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    php_code = """<?php
/**
 * Plugin Name: Dristik AI SEO & GEO Bridge
 * Plugin URI: https://dristik.ai
 * Description: Secure bridge allowing Dristik AI to read pages and inject Schema.org JSON-LD, metadata, and robots.txt directives.
 * Version: 1.0.0
 * Author: Dristik AI
 * License: GPL-2.0+
 */

if (!defined('ABSPATH')) exit;

class Dristik_Bridge_Plugin {
    const OPTION_KEY = 'dristik_bridge_api_key';

    public function __construct() {
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('rest_api_init', array($this, 'register_rest_routes'));
    }

    public function add_admin_menu() {
        add_options_page('Dristik AI Bridge', 'Dristik AI Bridge', 'manage_options', 'dristik-bridge', array($this, 'render_settings_page'));
    }

    public function render_settings_page() {
        if (!current_user_can('manage_options')) return;
        $key = get_option(self::OPTION_KEY);
        if (!$key) {
            $key = 'dstk_live_' . bin2hex(random_bytes(16));
            update_option(self::OPTION_KEY, $key);
        }
        ?>
        <div class="wrap">
            <h1>Dristik AI SEO &amp; GEO Bridge</h1>
            <p>Use this API Key in your Dristik Audit Dashboard to establish a secure 2-way connection without needing Application Passwords.</p>
            <table class="form-table">
                <tr>
                    <th scope="row">Bridge API Key</th>
                    <td>
                        <input type="text" readonly value="<?php echo esc_attr($key); ?>" class="regular-text" style="font-family: monospace; font-size: 14px;" onclick="this.select();" />
                        <p class="description">Copy and paste this key into Dristik &gt; Connectors &gt; WordPress.</p>
                    </td>
                </tr>
            </table>
        </div>
        <?php
    }

    public function register_rest_routes() {
        register_rest_route('dristik/v1', '/site', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_site_info'),
            'permission_callback' => array($this, 'verify_key')
        ));
    }

    public function verify_key($request) {
        $header = $request->get_header('x-dristik-plugin-key');
        $stored = get_option(self::OPTION_KEY);
        return ($header && $stored && hash_equals($stored, $header));
    }

    public function get_site_info() {
        return array(
            'status' => 'connected',
            'plugin_version' => '1.0.0',
            'site_url' => get_site_url(),
            'site_name' => get_bloginfo('name'),
            'permissions_granted' => array('read_seo', 'update_schema', 'update_metadata', 'update_robots')
        );
    }
}

new Dristik_Bridge_Plugin();
"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dristik-bridge/dristik-bridge.php", php_code)
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=dristik-bridge.zip"}
    )

# =========================================================================
# Google Search Console 1-Click OAuth Flow
# =========================================================================
class GoogleOAuthQuickConnectRequest(BaseModel):
    domain: str
    property_url: Optional[str] = None
    account_email: Optional[str] = None

def _get_gsc_redirect_uri(request: Optional[Request] = None) -> str:
    configured = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI") or settings.GOOGLE_OAUTH_REDIRECT_URI
    if configured:
        if "localhost" in configured and request:
            host = request.headers.get("x-forwarded-host") or request.headers.get("host")
            if host and not host.startswith("localhost") and not host.startswith("127.0.0.1"):
                scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
                return f"{scheme}://{host}/api/v1/connectors/google/oauth/callback"
        return configured
    if request:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if host:
            scheme = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
            return f"{scheme}://{host}/api/v1/connectors/google/oauth/callback"
    return "http://localhost:8000/api/v1/connectors/google/oauth/callback"


@router.get("/google/oauth/status")
async def google_oauth_status(request: Request):
    """Returns whether Google OAuth credentials are configured on the server."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID") or settings.GOOGLE_CLIENT_ID
    redirect_uri = _get_gsc_redirect_uri(request)
    return {
        "configured": bool(client_id),
        "client_id": (client_id[:8] + "...") if client_id else None,
        "redirect_uri": redirect_uri
    }

@router.get("/google/oauth/authorize")
async def google_oauth_authorize(request: Request, domain: str = "example.com"):
    """
    Initiates 1-click Google OAuth 2.0 flow for Google Search Console.
    Redirects to Google Accounts consent screen if GOOGLE_CLIENT_ID is configured,
    or completes seamless instant-consent in local development mode.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID") or settings.GOOGLE_CLIENT_ID
    redirect_uri = _get_gsc_redirect_uri(request)
    clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    if client_id:
        scope = urllib.parse.quote("https://www.googleapis.com/auth/webmasters.readonly openid email profile")
        state = urllib.parse.quote(clean_domain)
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
            f"response_type=code&"
            f"scope={scope}&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={state}"
        )
        return RedirectResponse(auth_url)

    raise HTTPException(
        status_code=503,
        detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET. Mock consent codes are not issued.",
    )

@router.get("/google/oauth/callback", response_class=HTMLResponse)
async def google_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Handles Google OAuth redirect, exchanges code for tokens, and notifies window.opener.
    """
    target_domain = state or "example.com"
    target_domain = target_domain.replace("https://", "").replace("http://", "").split("/")[0]

    if error:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Google Authorization Failed</title></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 48px; background: #efe8dc; color: #1f3d36;">
            <div style="max-width: 480px; margin: 0 auto; background: #fbf7ee; border: 1px solid #dcd2c0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
                <div style="font-size: 32px; margin-bottom: 12px;">✕</div>
                <h2 style="margin: 0 0 8px; font-size: 20px;">Authorization Cancelled</h2>
                <p style="color: #666; font-size: 14px; margin-bottom: 24px;">{error}</p>
                <button onclick="window.close()" style="background: #1f3d36; color: #fbf7ee; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600;">Close Window</button>
            </div>
        </body>
        </html>
        """, status_code=400)

    client_id = os.environ.get("GOOGLE_CLIENT_ID") or settings.GOOGLE_CLIENT_ID
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or settings.GOOGLE_CLIENT_SECRET
    redirect_uri = _get_gsc_redirect_uri(request)

    def _oauth_error(message: str) -> HTMLResponse:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Google Authorization Failed</title></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 48px; background: #efe8dc; color: #1f3d36;">
            <div style="max-width: 480px; margin: 0 auto; background: #fbf7ee; border: 1px solid #dcd2c0; border-radius: 12px; padding: 32px;">
                <h2 style="margin: 0 0 8px; font-size: 20px;">Authorization Failed</h2>
                <p style="color: #666; font-size: 14px;">{message}</p>
            </div>
        </body>
        </html>
        """, status_code=400)

    if not code or code.startswith("mock_"):
        return _oauth_error("Mock OAuth codes are rejected. Complete the Google consent screen.")
    if not client_id or not client_secret:
        return _oauth_error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required to exchange this code.")

    user_email = ""
    tokens = None
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            if not token_res.is_success:
                return _oauth_error("Google rejected the authorization code. No connector was saved.")
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return _oauth_error("Google did not return an access token. No connector was saved.")
            tokens = {
                "type": "oauth2",
                "domain": target_domain,
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token") or "",
                "email": "",
            }
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_res.is_success:
                user_email = userinfo_res.json().get("email") or ""
                tokens["email"] = user_email
    except Exception as exc:
        return _oauth_error(f"Token exchange failed: {exc}")

    if not tokens or not tokens.get("access_token"):
        return _oauth_error("No access token was returned. No connector was saved.")

    # Save to connector store
    creds = ConnectorCredentials(
        provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
        api_url=f"https://{target_domain}",
        api_key=json.dumps(tokens)
    )
    integration = connector_store.add_integration(
        provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
        name=f"Google Search Console ({target_domain})",
        target_url=f"https://{target_domain}",
        credentials=creds,
        settings={"auth_mode": "oauth2", "email": user_email}
    )
    integration.status = ConnectorHealthStatus.CONNECTED
    connector_store.persist(integration)
    try:
        from app.integrations.google_connectors import gsc_connector
        gsc_connector._connected = True
    except Exception:
        pass

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Search Console Connected</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 48px; background: #efe8dc; color: #1f3d36;">
        <div style="max-width: 480px; margin: 0 auto; background: #fbf7ee; border: 1px solid #dcd2c0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <div style="font-size: 36px; margin-bottom: 12px; color: #137547;">✓</div>
            <h2 style="margin: 0 0 8px; font-size: 22px; font-weight: 700;">Google Search Console Connected!</h2>
            <p style="color: #4a5568; font-size: 13px; line-height: 1.5; margin-bottom: 20px;">
                Successfully authorized property for <strong>{target_domain}</strong> via Google OAuth (<code>{user_email}</code>).
            </p>
            <p id="close-msg" style="color: #718096; font-size: 12px;">This window will close automatically...</p>
            <button id="close-btn" onclick="window.close()" style="display: none; margin-top: 14px; background: #137547; color: #fff; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">Return to App</button>
        </div>
        <script>
            (function() {{
                var payload = {{
                    type: 'GSC_OAUTH_SUCCESS',
                    domain: '{target_domain}',
                    email: '{user_email}',
                    timestamp: Date.now()
                }};
                var isPopup = (window.opener && !window.opener.closed) || (window.name && window.name.indexOf('popup') !== -1);

                // 1. Post to opener if available
                try {{
                    if (window.opener && !window.opener.closed) {{
                        window.opener.postMessage(payload, '*');
                    }}
                }} catch (e) {{}}

                // 2. BroadcastChannel: Works across tabs/windows without opener
                try {{
                    var bc = new BroadcastChannel('dristik_gsc_auth');
                    bc.postMessage(payload);
                    bc.close();
                }} catch (e) {{}}

                // 3. localStorage fallback: fires storage events
                try {{
                    localStorage.setItem('dristik_gsc_auth_sync', JSON.stringify(payload));
                }} catch (e) {{}}

                if (isPopup) {{
                    setTimeout(function() {{ window.close(); }}, 800);
                    setTimeout(function() {{
                        var btn = document.getElementById('close-btn');
                        if (btn) btn.style.display = 'inline-block';
                        var msg = document.getElementById('close-msg');
                        if (msg) msg.textContent = 'Authorization complete. You can return to Dristik.';
                    }}, 1600);
                }} else {{
                    setTimeout(function() {{
                        window.location.href = '/?tab=search_console&gsc_connected=true';
                    }}, 600);
                }}
            }})();
        </script>
    </body>
    </html>
    """)

@router.post("/google/oauth/quick-connect")
async def google_oauth_quick_connect(req: GoogleOAuthQuickConnectRequest):
    """Refuses to mint tokens. OAuth must go through Google's consent screen."""
    raise HTTPException(
        status_code=400,
        detail="Instant OAuth is disabled. Open /api/v1/connectors/google/oauth/authorize after setting GOOGLE_CLIENT_ID.",
    )

