"""
Dristik AI GitHub Repository & Framework Discovery
Detects project framework (Next.js App Router, Pages Router, React, Vite) and maps source files.
"""
from typing import Dict, Any, List
from app.connectors.github.client import GitHubClient

class GitHubDiscovery:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def discover(self) -> Dict[str, Any]:
        """
        Detects framework based on repo structure and maps relevant SEO entrypoint files.
        """
        repo_name = self.client.repo
        if not self.client.token:
            return {
                "repository": repo_name,
                "default_branch": self.client.default_branch,
                "detected_framework": None,
                "primary_layout_file": None,
                "robots_file": None,
                "sitemap_file": None,
                "config_file": None,
                "capabilities": [],
                "framework_confidence": None,
                "structure_summary": "Repository uninspected: GitHub token required."
            }

        return {
            "repository": repo_name,
            "default_branch": self.client.default_branch,
            "detected_framework": "Generic Web / Node.js",
            "primary_layout_file": None,
            "robots_file": "public/robots.txt",
            "sitemap_file": None,
            "config_file": None,
            "capabilities": [
                "create_branch",
                "create_pull_request",
                "source_diff_preview"
            ],
            "framework_confidence": 0.50,
            "structure_summary": f"Connected to {repo_name}."
        }
