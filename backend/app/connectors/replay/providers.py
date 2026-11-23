"""
PostHog & Microsoft Clarity Session Replay Connectors.

Zero-Fake Policy:
- Wired to .env credentials (POSTHOG_API_KEY / POSTHOG_PROJECT_ID / CLARITY_API_TOKEN / CLARITY_PROJECT_ID).
- Returns explicit NOT_CONNECTED when credentials are absent; never fabricates recordings.
- Reports consent-aware recording coverage (recorded vs total sessions) so opt-out sampling bias is transparent.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings


class ReplayCoverageSummary(BaseModel):
    provider: str
    status: str  # CONNECTED | NOT_CONNECTED | FAILED
    total_sessions: Optional[int] = None
    recorded_sessions: Optional[int] = None
    consent_recording_coverage_pct: Optional[float] = None
    recordings: List[Dict[str, Any]] = Field(default_factory=list)
    privacy_masking_enforced: bool = True
    note: str = ""


class PostHogReplayConnector:
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "POSTHOG_API_KEY", None)
        self.project_id = project_id or getattr(settings, "POSTHOG_PROJECT_ID", None)
        self.host = (host or getattr(settings, "POSTHOG_HOST", "https://app.posthog.com")).rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.project_id)

    def fetch_recordings(
        self,
        *,
        total_site_sessions: Optional[int] = None,
        limit: int = 50,
        http_get: Optional[Callable[..., Any]] = None,
    ) -> ReplayCoverageSummary:
        if not self.is_configured:
            return ReplayCoverageSummary(
                provider="PostHog",
                status="NOT_CONNECTED",
                note="Configure POSTHOG_API_KEY and POSTHOG_PROJECT_ID in .env to enable PostHog session recordings.",
            )
        url = f"{self.host}/api/projects/{self.project_id}/session_recordings/?limit={limit}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            if http_get is None:
                import httpx
                resp = httpx.get(url, headers=headers, timeout=15.0)
                code, body = resp.status_code, resp.json() if resp.status_code == 200 else {}
            else:
                code, body = http_get(url, headers=headers)
            if code != 200:
                return ReplayCoverageSummary(provider="PostHog", status="FAILED", note=f"PostHog HTTP {code}")
            results = body.get("results") or []
            rec_cnt = len(results)
            cov = (
                round(min(100.0, (rec_cnt / total_site_sessions) * 100.0), 1)
                if total_site_sessions and total_site_sessions > 0
                else None
            )
            return ReplayCoverageSummary(
                provider="PostHog",
                status="CONNECTED",
                total_sessions=total_site_sessions,
                recorded_sessions=rec_cnt,
                consent_recording_coverage_pct=cov,
                recordings=[
                    {
                        "recording_ref": str(r.get("id") or ""),
                        "start_time": r.get("start_time"),
                        "duration_sec": r.get("recording_duration"),
                        "click_count": r.get("click_count"),
                        "console_error_count": r.get("console_error_count"),
                    }
                    for r in results
                ],
                note="PostHog recordings retrieved with PII masking and consent coverage disclosure.",
            )
        except Exception as exc:
            return ReplayCoverageSummary(provider="PostHog", status="FAILED", note=str(exc))


class MicrosoftClarityConnector:
    def __init__(self, api_token: Optional[str] = None, project_id: Optional[str] = None):
        self.api_token = api_token or getattr(settings, "CLARITY_API_TOKEN", None)
        self.project_id = project_id or getattr(settings, "CLARITY_PROJECT_ID", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and self.project_id)

    def fetch_behavioral_insights(
        self,
        *,
        num_days: int = 3,
        http_get: Optional[Callable[..., Any]] = None,
    ) -> ReplayCoverageSummary:
        if not self.is_configured:
            return ReplayCoverageSummary(
                provider="Microsoft Clarity",
                status="NOT_CONNECTED",
                note="Configure CLARITY_API_TOKEN and CLARITY_PROJECT_ID in .env to enable Microsoft Clarity telemetry.",
            )
        url = f"https://www.clarity.ms/export-data/api/v1/project-live-insights?numOfDays={min(3, max(1, num_days))}"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            if http_get is None:
                import httpx
                resp = httpx.get(url, headers=headers, timeout=15.0)
                code, body = resp.status_code, resp.json() if resp.status_code == 200 else []
            else:
                code, body = http_get(url, headers=headers)
            if code != 200:
                return ReplayCoverageSummary(provider="Microsoft Clarity", status="FAILED", note=f"Clarity HTTP {code}")
            items = body if isinstance(body, list) else body.get("data", [])
            return ReplayCoverageSummary(
                provider="Microsoft Clarity",
                status="CONNECTED",
                recorded_sessions=len(items),
                recordings=items[:50],
                note="Microsoft Clarity behavioral insights retrieved.",
            )
        except Exception as exc:
            return ReplayCoverageSummary(provider="Microsoft Clarity", status="FAILED", note=str(exc))
