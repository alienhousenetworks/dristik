"""
Dristik AI WordPress REST API & Plugin Bridge Client.

Supports WordPress Application Passwords and the Dristik plugin bridge.
"""

import base64
import time
from typing import Any, Dict, Optional

import httpx

from app.connectors.base.models import ConnectorCredentials, ConnectorHealth
from app.domain.enums import ConnectorType, ConnectorHealthStatus


class WordPressClient:
    """HTTP client for communicating with a WordPress site."""

    def __init__(self, credentials: ConnectorCredentials):
        self.credentials = credentials
        self.base_url = (credentials.api_url or "").rstrip("/")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers from the supplied credentials."""
        headers = {"User-Agent": "Dristik-AI-Connector/3.0"}

        if self.credentials.api_key:
            headers["X-Dristik-Plugin-Key"] = self.credentials.api_key

        elif self.credentials.username and self.credentials.app_password:
            user_pass = (
                f"{self.credentials.username}:{self.credentials.app_password}"
            )
            token = base64.b64encode(user_pass.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        return headers

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Make a GET request to a WordPress endpoint.

        TLS certificate verification remains enabled by default.
        HTTP errors are returned as responses so callers can interpret them.
        Network errors and timeouts raise httpx exceptions.
        """
        if not self.base_url:
            raise ValueError("WordPress URL is required")

        url = f"{self.base_url}/{path.lstrip('/')}"

        async with httpx.AsyncClient(timeout=8.0) as client:
            return await client.get(
                url,
                headers=self._get_auth_headers(),
                params=params,
            )

    async def test_health(self) -> ConnectorHealth:
        """
        Check WordPress connectivity and attempt to verify authentication.

        A successful public REST response alone does not prove authentication.
        """
        if not self.base_url:
            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message="WordPress URL is required",
            )

        started_at = time.perf_counter()

        try:
            # First, check whether the Dristik plugin bridge is available.
            plugin_response = await self.get("/wp-json/dristik/v1/site")

            if plugin_response.status_code == 200:
                try:
                    data = plugin_response.json()
                except ValueError:
                    data = {}

                if not isinstance(data, dict):
                    data = {}

                # Only report permissions explicitly returned by the plugin.
                reported_permissions = data.get("permissions_granted", [])
                if not isinstance(reported_permissions, list):
                    reported_permissions = []

                latency_ms = (time.perf_counter() - started_at) * 1000

                return ConnectorHealth(
                    provider=ConnectorType.WORDPRESS,
                    status=ConnectorHealthStatus.CONNECTED,
                    authenticated=True,
                    latency_ms=latency_ms,
                    version=data.get("plugin_version"),
                    permissions_granted=[
                        permission
                        for permission in reported_permissions
                        if isinstance(permission, str)
                    ],
                    message=(
                        "Connected to the Dristik WordPress plugin endpoint. "
                        "Only explicitly reported permissions are listed."
                    ),
                )

            # Next, check an endpoint that requires WordPress permissions.
            settings_response = await self.get("/wp-json/wp/v2/settings")

            latency_ms = (time.perf_counter() - started_at) * 1000

            if settings_response.status_code == 200:
                return ConnectorHealth(
                    provider=ConnectorType.WORDPRESS,
                    status=ConnectorHealthStatus.CONNECTED,
                    authenticated=True,
                    latency_ms=latency_ms,
                    version="WordPress REST API",
                    permissions_granted=["read_settings"],
                    message=(
                        "WordPress REST API is reachable and the supplied "
                        "request can access the settings endpoint."
                    ),
                )

            if settings_response.status_code in (401, 403):
                return ConnectorHealth(
                    provider=ConnectorType.WORDPRESS,
                    status=ConnectorHealthStatus.UNAUTHORIZED,
                    authenticated=False,
                    latency_ms=latency_ms,
                    version="WordPress REST API",
                    message=(
                        "WordPress REST API is reachable, but authentication "
                        "or permission to access settings could not be verified."
                    ),
                )

            if settings_response.status_code == 404:
                # Settings may be unavailable or the REST route may be disabled.
                # Check the public REST root before concluding the site is down.
                root_response = await self.get("/wp-json/")

                latency_ms = (time.perf_counter() - started_at) * 1000

                if root_response.status_code == 200:
                    return ConnectorHealth(
                        provider=ConnectorType.WORDPRESS,
                        status=ConnectorHealthStatus.DEGRADED,
                        authenticated=False,
                        latency_ms=latency_ms,
                        version="WordPress REST API",
                        message=(
                            "WordPress REST API is reachable, but the settings "
                            "endpoint is unavailable. Authentication remains "
                            "unverified."
                        ),
                    )

            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                latency_ms=latency_ms,
                message=(
                    "WordPress returned HTTP "
                    f"{settings_response.status_code} while checking the "
                    "settings endpoint."
                ),
            )

        except httpx.TimeoutException:
            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.UNAVAILABLE,
                authenticated=False,
                latency_ms=(time.perf_counter() - started_at) * 1000,
                message="WordPress connection timed out.",
            )

        except httpx.RequestError as exc:
            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.UNAVAILABLE,
                authenticated=False,
                latency_ms=(time.perf_counter() - started_at) * 1000,
                message=f"Could not reach the WordPress site: {exc}",
            )

        except ValueError as exc:
            return ConnectorHealth(
                provider=ConnectorType.WORDPRESS,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                latency_ms=(time.perf_counter() - started_at) * 1000,
                message=str(exc),
            )