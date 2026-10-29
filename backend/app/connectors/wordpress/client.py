"""
Dristik AI WordPress REST API & Plugin Bridge Client
Supports standard WP Application Passwords and the Dristik WP Plugin API bridge.
"""
import base64
import httpx
from typing import Dict, Any, Optional
from app.connectors.base.models import ConnectorCredentials, ConnectorHealth
from app.domain.enums import ConnectorType, ConnectorHealthStatus

class WordPressClient:
    """
    HTTP client for communicating with a WordPress site securely.
    """

    def __init__(self, credentials: ConnectorCredentials):
        self.credentials = credentials
        self.base_url = (credentials.api_url or "").rstrip("/")

    def _get_auth_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "Dristik-AI-Connector/3.0"}
        if self.credentials.api_key:
            headers["X-Dristik-Plugin-Key"] = self.credentials.api_key
        elif self.credentials.username and self.credentials.app_password:
            user_pass = f"{self.credentials.username}:{self.credentials.app_password}"
            token = base64.b64encode(user_pass.encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers

    async def test_health(self) -> ConnectorHealth:
        """Ping WordPress REST root /wp-json/ or Dristik Plugin endpoint."""
        if not self.base_url:
            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message="WordPress URL is required",
            )
        try:
            # 1. Try Dristik WordPress Bridge Plugin endpoint first
            plugin_endpoint = f"{self.base_url}/wp-json/dristik/v1/site"
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                resp = await client.get(plugin_endpoint, headers=self._get_auth_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorHealth(
                        provider=ConnectorType.WORDPRESS,
                        status=ConnectorHealthStatus.CONNECTED,
                        authenticated=True,
                        version=data.get("plugin_version", "3.0.0"),
                        permissions_granted=["read_seo", "update_schema", "update_metadata", "update_robots"],
                        message="Connected via Dristik WordPress Plugin Bridge (Full 2-Way)",
                    )

            # 2. Fallback to native WP-JSON API
            wp_root = f"{self.base_url}/wp-json/wp/v2/settings"
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                resp = await client.get(wp_root, headers=self._get_auth_headers())
                if resp.status_code in [200, 401, 403]:
                    authed = resp.status_code == 200
                    return ConnectorHealth(
                        provider=ConnectorType.WORDPRESS,
                        status=ConnectorHealthStatus.CONNECTED if authed else ConnectorHealthStatus.UNAUTHORIZED,
                        authenticated=authed,
                        version="WP Core REST",
                        permissions_granted=["read_pages", "read_posts"] if authed else [],
                        message="Connected via Native WordPress REST API" if authed else "WordPress accessible, authentication required",
                    )

            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message=f"WordPress endpoint {self.base_url} did not respond with valid REST API endpoints.",
            )
        except Exception as e:
            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message=f"Failed to connect to WordPress site '{self.base_url}': {str(e)}",
            )
