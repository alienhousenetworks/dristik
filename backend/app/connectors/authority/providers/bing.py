"""Bing Webmaster Tools via Microsoft OAuth and the JSON API.

The retired SOAP API is not called. Link counts are Bing's own figures
and are labeled as such.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from app.connectors.authority.http import ProviderAuthError, ProviderRateLimitError, ProviderTransientError
from app.connectors.authority.models import CollectionResult, ExternalProperty, ProviderCapabilities, RawPayload, isoformat, utcnow
from app.connectors.authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.connectors.authority.providers.records import record
from app.connectors.authority.redact import strip_secrets
from datetime import timedelta

API = "https://ssl.bing.com/webmaster/api.svc/json"


class BingWebmasterProvider(ExternalDataProvider):
    provider_id = "bing_webmaster"
    display_name = "Bing Webmaster Tools"
    auth_mode = "oauth"
    collection_tier = "FREE"
    scopes: List[str] = []
    capabilities = ProviderCapabilities(
        search_performance=True,
        indexing=True,
        crawl_stats=True,
        backlinks=True,
        referring_domains=False,
    )

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.BING_WEBMASTER_ENABLED)

    def _settings(self):
        from app.core.config import settings
        return settings

    def oauth_application_ready(self) -> bool:
        settings = self._settings()
        return bool(settings.BING_OAUTH_CLIENT_ID and settings.BING_OAUTH_CLIENT_SECRET)

    def build_authorize(self, state: str) -> tuple[str, str]:
        settings = self._settings()
        redirect = settings.BING_OAUTH_REDIRECT_URI or settings.external_oauth_redirect_uri()
        query = urlencode({
            "client_id": settings.BING_OAUTH_CLIENT_ID or "",
            "response_type": "code",
            "redirect_uri": redirect,
            "response_mode": "query",
            "scope": settings.BING_OAUTH_SCOPE,
            "state": state,
        })
        return f"{settings.BING_OAUTH_AUTHORIZE_URL}?{query}", ""

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        return self._token(transport, {
            "client_id": self._settings().BING_OAUTH_CLIENT_ID or "",
            "client_secret": self._settings().BING_OAUTH_CLIENT_SECRET or "",
            "code": secret["code"],
            "redirect_uri": self._settings().BING_OAUTH_REDIRECT_URI or self._settings().external_oauth_redirect_uri(),
            "grant_type": "authorization_code",
        })

    def refresh_credentials(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        if not secret.get("refresh_token"):
            raise ProviderAuthError("Bing refresh token is not available.")
        refreshed = self._token(transport, {
            "client_id": self._settings().BING_OAUTH_CLIENT_ID or "",
            "client_secret": self._settings().BING_OAUTH_CLIENT_SECRET or "",
            "refresh_token": secret["refresh_token"],
            "grant_type": "refresh_token",
        })
        refreshed["refresh_token"] = secret.get("refresh_token")
        return refreshed

    def _token(self, transport, data: Dict[str, str]) -> Dict[str, Any]:
        response = transport.request("POST", self._settings().BING_OAUTH_TOKEN_URL, data=data)
        if response.status_code != 200 or not isinstance(response.payload, dict) or not response.payload.get("access_token"):
            raise ProviderAuthError("Bing token exchange failed.")
        expires_in = int(response.payload.get("expires_in") or 3600)
        return {
            "access_token": response.payload.get("access_token"),
            "refresh_token": response.payload.get("refresh_token"),
            "expires_at": isoformat(utcnow() + timedelta(seconds=expires_in)),
            "token_type": response.payload.get("token_type") or "Bearer",
        }

    def collect(self, ctx: CollectContext) -> CollectionResult:
        if not ctx.access_token:
            return not_connected(self.provider_id, "Bing Webmaster Tools is not connected.")
        headers = {"Authorization": f"Bearer {ctx.access_token}", "Accept": "application/json"}
        sites_payload = self._get(ctx, "GetUserSites", headers, None)
        sites = _as_list(sites_payload)
        properties = []
        for site in sites:
            url = site.get("Url") or site.get("url") or ""
            properties.append(ExternalProperty(
                property_id=url,
                provider=self.provider_id,
                external_property_id=url,
                label=url,
                domain=_host(url),
            ))
        selected = ctx.property_id or _match(properties, ctx.domain)
        result = CollectionResult(provider=self.provider_id, connection_status="CONNECTED", properties=properties)
        if not selected:
            result.data_state = "UNAVAILABLE"
            result.note = "No Bing Webmaster site matches this domain."
            return result
        ctx.property_id = selected
        partial: List[str] = []
        calls = {
            "GetQueryStats": "query",
            "GetRankAndTrafficStats": "traffic",
            "GetCrawlStats": "crawl",
            "GetLinkCounts": "links",
        }
        for method, kind in calls.items():
            try:
                payload = self._get(ctx, method, headers, selected)
            except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
                raise
            except Exception as exc:
                partial.append(f"{method}: {exc}")
                continue
            if payload is None:
                partial.append(f"{method} returned no data")
                continue
            result.raw_payloads.append(RawPayload(endpoint=method, payload=strip_secrets(payload if isinstance(payload, dict) else {"rows": payload}), http_status=200))
            result.records.extend(_normalize(ctx, kind, payload))
        result.partial_errors = partial
        result.data_state = "PARTIALLY_MEASURED" if partial and result.records else "MEASURED" if result.records else "UNAVAILABLE"
        result.note = "Bing Webmaster figures are Bing's own measurements. Link counts are not Ahrefs, Semrush, or Majestic metrics."
        return result

    def _get(self, ctx, method: str, headers: Dict[str, str], site: Optional[str]):
        params = {"siteUrl": site} if site else None
        response = ctx.transport.request("GET", f"{API}/{method}", headers=headers, params=params)
        if response.status_code == 403:
            raise ProviderAuthError("Bing Webmaster denied this token.")
        if response.status_code != 200:
            raise RuntimeError(f"{method} HTTP {response.status_code}")
        payload = response.payload
        if isinstance(payload, dict) and "d" in payload:
            return payload["d"]
        return payload


def _as_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("results", "Result", "Sites"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
        return [payload]
    return []


def _host(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").strip("/").lower()


def _match(properties: List[ExternalProperty], domain: str) -> Optional[str]:
    host = domain.lower().removeprefix("www.")
    for item in properties:
        if _host(item.domain or "").removeprefix("www.") == host:
            return item.external_property_id
    return None


def _normalize(ctx: CollectContext, kind: str, payload: Any):
    rows = _as_list(payload)
    built = []
    if kind == "traffic":
        clicks = sum(float(row.get("Clicks") or row.get("clicks") or 0) for row in rows)
        impressions = sum(float(row.get("Impressions") or row.get("impressions") or 0) for row in rows)
        built.append(record(ctx, record_type="search_performance", metric="bing_clicks", value=clicks, unit="count", source="bing_webmaster", raw_ref="GetRankAndTrafficStats"))
        built.append(record(ctx, record_type="search_performance", metric="bing_impressions", value=impressions, unit="count", source="bing_webmaster", raw_ref="GetRankAndTrafficStats"))
    elif kind == "query":
        for row in rows:
            built.append(record(
                ctx,
                record_type="search_performance",
                metric="bing_query",
                value=float(row.get("Clicks") or row.get("clicks") or 0),
                unit="clicks",
                value_text=row.get("Query") or row.get("query"),
                metadata={
                    "query": row.get("Query") or row.get("query"),
                    "clicks": row.get("Clicks") or row.get("clicks"),
                    "impressions": row.get("Impressions") or row.get("impressions"),
                    "position": row.get("AvgImpressionPosition") or row.get("position"),
                },
                source="bing_webmaster",
                raw_ref="GetQueryStats",
            ))
    elif kind == "crawl":
        crawled = sum(float(row.get("CrawledPages") or row.get("crawled") or 0) for row in rows)
        errors = sum(float(row.get("CrawlErrors") or row.get("errors") or 0) for row in rows)
        built.append(record(ctx, record_type="search_performance", metric="bing_crawled_pages", value=crawled, unit="pages", source="bing_webmaster", raw_ref="GetCrawlStats"))
        built.append(record(ctx, record_type="search_performance", metric="bing_crawl_errors", value=errors, unit="pages", source="bing_webmaster", raw_ref="GetCrawlStats"))
    elif kind == "links":
        inbound = 0.0
        for row in rows:
            inbound += float(row.get("InboundLinkCount") or row.get("links") or row.get("Count") or 0)
        built.append(record(
            ctx,
            record_type="backlink",
            metric="bing_link_count",
            value=inbound,
            unit="links",
            metadata={"vendor_metric_label": "Bing Webmaster link count"},
            source="bing_webmaster",
            raw_ref="GetLinkCounts",
        ))
    return built
