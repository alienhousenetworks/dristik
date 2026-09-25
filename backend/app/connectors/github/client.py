"""
Dristik AI GitHub API Client
Manages authentication, repository inspection, branch creation, file commits, and Pull Requests.
"""
import httpx
from typing import Dict, Any, Optional
from app.connectors.base.models import ConnectorCredentials, ConnectorHealth
from app.domain.enums import ConnectorType, ConnectorHealthStatus

class GitHubClient:
    def __init__(self, credentials: ConnectorCredentials):
        self.credentials = credentials
        self.repo = credentials.repository or "example/website"
        self.token = credentials.github_token or ""
        self.default_branch = credentials.branch or "main"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Dristik-AI-Connector/3.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def test_health(self) -> ConnectorHealth:
        """Pings repository to confirm access token permissions."""
        if not self.repo or "/" not in self.repo:
            return ConnectorHealth(
                provider=ConnectorType.GITHUB,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message="Repository must be specified in format 'owner/repo'",
            )

        if not self.token:
            return ConnectorHealth(
                provider=ConnectorType.GITHUB,
                status=ConnectorHealthStatus.UNAUTHORIZED,
                authenticated=False,
                message=f"GitHub personal access token is required to access repository '{self.repo}'.",
            )

        try:
            url = f"https://api.github.com/repos/{self.repo}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorHealth(
                        provider=ConnectorType.GITHUB,
                        status=ConnectorHealthStatus.CONNECTED,
                        authenticated=True,
                        version="GitHub API v3",
                        permissions_granted=["repo:read", "pull_requests:write"],
                        message=f"Connected to repository '{data.get('full_name', self.repo)}' ({data.get('default_branch', 'main')})",
                    )
                elif resp.status_code in [401, 403]:
                    return ConnectorHealth(
                        provider=ConnectorType.GITHUB,
                        status=ConnectorHealthStatus.UNAUTHORIZED,
                        authenticated=False,
                        message="Invalid GitHub Personal Access Token or insufficient permissions",
                    )
                else:
                    return ConnectorHealth(
                        provider=ConnectorType.GITHUB,
                        status=ConnectorHealthStatus.ERROR,
                        authenticated=False,
                        message=f"GitHub API returned unexpected status HTTP {resp.status_code}",
                    )
        except Exception as e:
            return ConnectorHealth(
                provider=ConnectorType.GITHUB,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message=f"Failed to connect to repository '{self.repo}': {str(e)}",
            )
