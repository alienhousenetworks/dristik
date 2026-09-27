"""
One-click OAuth for connectors that publish a consent screen.

A provider is usable only when its client id and secret are set.
No token is invented, and saving a token does not invent metrics.
"""
import base64
import hashlib
import hmac
import html
import json
import urllib.parse
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx

from app.connectors.base.models import ConnectorCredentials
from app.connectors.store import connector_store
from app.core.config import settings
from app.domain.enums import ConnectorType

router = APIRouter()

_PUBLIC_BASE = "http://localhost:8000/api/v1/connectors/oauth/callback"


def _setting(name: str) -> str:
    return (getattr(settings, name, None) or "").strip()


def _callback() -> str:
    return _setting("OAUTH_REDIRECT_URI") or _PUBLIC_BASE


PROVIDERS: Dict[str, Dict[str, Any]] = {
    "google_search_console": {
        "label": "Google Search Console",
        "connector": ConnectorType.GOOGLE_SEARCH_CONSOLE,
        "client_id": "GOOGLE_CLIENT_ID",
        "client_secret": "GOOGLE_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/webmasters.readonly openid email profile",
        "extra": {"access_type": "offline", "prompt": "consent"},
    },
    "google_analytics_4": {
        "label": "Google Analytics",
        "connector": ConnectorType.GOOGLE_ANALYTICS_4,
        "client_id": "GOOGLE_CLIENT_ID",
        "client_secret": "GOOGLE_CLIENT_SECRET",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/analytics.readonly openid email",
        "extra": {"access_type": "offline", "prompt": "consent"},
    },
    "github": {
        "label": "GitHub",
        "connector": ConnectorType.GITHUB,
        "client_id": "GITHUB_CLIENT_ID",
        "client_secret": "GITHUB_CLIENT_SECRET",
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "scope": "repo read:user",
    },
    "shopify": {
        "label": "Shopify",
        "connector": ConnectorType.SHOPIFY,
        "client_id": "SHOPIFY_CLIENT_ID",
        "client_secret": "SHOPIFY_CLIENT_SECRET",
        "scope": "read_content,read_themes",
        "needs_shop": True,
    },
    "webflow": {
        "label": "Webflow",
        "connector": ConnectorType.WEBFLOW,
        "client_id": "WEBFLOW_CLIENT_ID",
        "client_secret": "WEBFLOW_CLIENT_SECRET",
        "authorize": "https://webflow.com/oauth/authorize",
        "token": "https://api.webflow.com/oauth/access_token",
        "scope": "sites:read custom_code:read custom_code:write",
    },
    "hubspot": {
        "label": "HubSpot",
        "connector": ConnectorType.CRM,
        "client_id": "HUBSPOT_CLIENT_ID",
        "client_secret": "HUBSPOT_CLIENT_SECRET",
        "authorize": "https://app.hubspot.com/oauth/authorize",
        "token": "https://api.hubapi.com/oauth/v1/token",
        "scope": "oauth crm.objects.contacts.read crm.objects.deals.read",
    },
    "salesforce": {
        "label": "Salesforce",
        "connector": ConnectorType.CRM,
        "client_id": "SALESFORCE_CLIENT_ID",
        "client_secret": "SALESFORCE_CLIENT_SECRET",
        "authorize": "https://login.salesforce.com/services/oauth2/authorize",
        "token": "https://login.salesforce.com/services/oauth2/token",
        "scope": "api refresh_token",
    },
    "stripe": {
        "label": "Stripe",
        "connector": ConnectorType.CRM,
        "client_id": "STRIPE_CLIENT_ID",
        "client_secret": "STRIPE_CLIENT_SECRET",
        "authorize": "https://connect.stripe.com/oauth/authorize",
        "token": "https://connect.stripe.com/oauth/token",
        "scope": "read_only",
    },
    "wordpress": {
        "label": "WordPress.com",
        "connector": ConnectorType.WORDPRESS,
        "client_id": "WORDPRESS_CLIENT_ID",
        "client_secret": "WORDPRESS_CLIENT_SECRET",
        "authorize": "https://public-api.wordpress.com/oauth2/authorize",
        "token": "https://public-api.wordpress.com/oauth2/token",
        "scope": "global",
    },
}


def _sign(payload: Dict[str, str]) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    secret = (settings.AUTH_SECRET or "dristik").encode()
    sig = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def _unsign(state: str) -> Dict[str, str]:
    try:
        raw, sig = state.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="OAuth state is invalid.") from exc
    secret = (settings.AUTH_SECRET or "dristik").encode()
    expected = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=400, detail="OAuth state signature does not match.")
    data = json.loads(base64.urlsafe_b64decode(raw.encode()))
    if not isinstance(data, dict) or "provider" not in data:
        raise HTTPException(status_code=400, detail="OAuth state is missing the provider.")
    return {str(k): str(v) for k, v in data.items()}


def _configured(spec: Dict[str, Any]) -> bool:
    return bool(_setting(spec["client_id"]) and _setting(spec["client_secret"]))


def provider_status() -> Dict[str, Any]:
    redirect_uri = _callback()
    out = {}
    for key, spec in PROVIDERS.items():
        out[key] = {
            "label": spec["label"],
            "configured": _configured(spec),
            "client_id_env": spec["client_id"],
            "client_secret_env": spec["client_secret"],
            "redirect_uri": redirect_uri,
            "needs_shop": bool(spec.get("needs_shop")),
        }
    return {"redirect_uri": redirect_uri, "providers": out}


def _shop_host(shop: str) -> str:
    host = shop.replace("https://", "").replace("http://", "").split("/")[0].strip().lower()
    if host and "." not in host:
        host = f"{host}.myshopify.com"
    if not host.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Shopify sign-in needs a storename.myshopify.com address.")
    return host


def _authorize_url(provider: str, state: str, shop: str) -> str:
    spec = PROVIDERS[provider]
    client_id = _setting(spec["client_id"])
    redirect_uri = _callback()
    if spec.get("needs_shop"):
        host = _shop_host(shop)
        query = urllib.parse.urlencode({
            "client_id": client_id,
            "scope": spec["scope"],
            "redirect_uri": redirect_uri,
            "state": state,
        })
        return f"https://{host}/admin/oauth/authorize?{query}"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": spec["scope"],
        "state": state,
    }
    params.update(spec.get("extra") or {})
    return f"{spec['authorize']}?{urllib.parse.urlencode(params)}"


async def _exchange(provider: str, code: str, shop: str) -> Dict[str, Any]:
    spec = PROVIDERS[provider]
    client_id = _setting(spec["client_id"])
    client_secret = _setting(spec["client_secret"])
    redirect_uri = _callback()
    if spec.get("needs_shop"):
        host = _shop_host(shop)
        url = f"https://{host}/admin/oauth/access_token"
        body = {"client_id": client_id, "client_secret": client_secret, "code": code}
    else:
        url = spec["token"]
        body = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, data=body, headers=headers)
    if not response.is_success:
        raise HTTPException(status_code=400, detail="The provider rejected the authorization code. No connector was saved.")
    try:
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="The provider did not return a token. No connector was saved.") from exc
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="No access token was returned. No connector was saved.")
    return data


def _page(title: str, body: str, script: str = "") -> HTMLResponse:
    safe_title = html.escape(title)
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html><head><title>{safe_title}</title></head>
<body style="font-family: Georgia, serif; color: #111; background: #fff; padding: 48px;">
  <h1 style="font-weight: 400;">{safe_title}</h1>
  <p>{body}</p>
  {script}
</body></html>""")


@router.get("/oauth/providers")
def list_oauth_providers():
    return provider_status()


@router.get("/oauth/{provider}/authorize")
def oauth_authorize(
    provider: str,
    domain: str = "",
    shop: str = "",
    property_id: str = "",
    repository: str = "",
):
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise HTTPException(status_code=404, detail="This connector has no OAuth sign-in.")
    if not _configured(spec):
        raise HTTPException(
            status_code=503,
            detail=f"Set {spec['client_id']} and {spec['client_secret']} in the backend env, then restart.",
        )
    state = _sign({
        "provider": provider,
        "domain": domain,
        "shop": shop,
        "property_id": property_id,
        "repository": repository,
    })
    return RedirectResponse(_authorize_url(provider, state, shop))


@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    shop: Optional[str] = None,
):
    if error:
        return _page("Sign-in cancelled", html.escape(error))
    if not code or not state or code.startswith("mock_"):
        return _page("Sign-in failed", "The consent screen did not return a real authorization code.")
    saved = _unsign(state)
    provider = saved["provider"]
    spec = PROVIDERS.get(provider)
    if spec is None or not _configured(spec):
        return _page("Sign-in failed", "This OAuth provider is not configured.")
    shop_host = shop or saved.get("shop") or ""
    token_data = await _exchange(provider, code, shop_host)
    target = saved.get("domain") or shop_host or saved.get("repository") or spec["label"]
    stored = {
        "type": "oauth2",
        "provider": provider,
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token") or "",
        "property_id": saved.get("property_id") or "",
        "shop": shop_host,
        "repository": saved.get("repository") or "",
    }
    creds = ConnectorCredentials(
        provider=spec["connector"],
        api_url=target if str(target).startswith("http") else f"https://{target}",
        api_key=json.dumps(stored),
        github_token=token_data.get("access_token") if provider == "github" else None,
        repository=saved.get("repository") or None,
    )
    connector_store.add_integration(
        provider=spec["connector"],
        name=f"{spec['label']} ({target})",
        target_url=creds.api_url or target,
        credentials=creds,
        repository=saved.get("repository") or None,
        settings={"auth_mode": "oauth2", "oauth_provider": provider},
    )
    safe_target = html.escape(str(target))
    script = """
    <script>
      try {
        if (window.opener && !window.opener.closed) {
          window.opener.postMessage({ type: 'OAUTH_SUCCESS', provider: %s }, '*');
          setTimeout(function () { window.close(); }, 900);
        }
      } catch (e) {}
    </script>
    """ % json.dumps(provider)
    return _page(
        "Signed in",
        f"The {html.escape(spec['label'])} token for <strong>{safe_target}</strong> is saved. "
        "Search, session, and revenue numbers stay blank until a live query returns them.",
        script,
    )
