"""Google Search Console.

Search Analytics totals are requested without dimensions so headline
clicks are not a sum of a capped row sample. A page missing from that
sample is not treated as deindexed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.external_authority.http import ProviderAuthError, ProviderRateLimitError, ProviderTransientError, quota_status
from app.external_authority.models import CollectionResult, ExternalAccount, ExternalProperty, ProviderCapabilities, RawPayload
from app.external_authority.providers.base import CollectContext, ExternalDataProvider, not_connected, unavailable
from app.external_authority.providers.google_oauth import (
    application_client,
    authorize_url,
    bearer,
    exchange_code,
    pkce_pair,
    refresh,
    revoke,
)
from app.external_authority.providers.records import record
from app.external_authority.redact import safe_http_error, strip_secrets

SITES_URL = "https://www.googleapis.com/webmasters/v3/sites"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


class GoogleSearchConsoleProvider(ExternalDataProvider):
    provider_id = "google_search_console"
    display_name = "Google Search Console"
    auth_mode = "oauth"
    collection_tier = "FREE"
    scopes = SCOPES
    capabilities = ProviderCapabilities(
        search_performance=True,
        indexing=True,
        sitemaps=True,
    )

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.GSC_ENABLED)

    def oauth_application_ready(self) -> bool:
        client_id, client_secret, _ = application_client()
        return bool(client_id and client_secret)

    def build_authorize(self, state: str) -> tuple[str, str]:
        verifier, challenge = pkce_pair()
        return authorize_url(self.scopes, state, challenge), verifier

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        return exchange_code(transport, secret["code"], secret["code_verifier"])

    def disconnect(self, secret: Dict[str, Any], transport: Any) -> None:
        revoke(transport, secret)

    def refresh_credentials(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        return refresh(transport, secret)

    def collect(self, ctx: CollectContext) -> CollectionResult:
        if not ctx.access_token:
            return not_connected(self.provider_id, "Google Search Console is not connected.")
        headers = bearer(ctx.access_token)
        sites = self._sites(ctx, headers)
        if sites is None:
            return unavailable(self.provider_id, "Search Console property list could not be read.")
        properties = [_property_from_site(item) for item in sites]
        selected = _select_site(properties, ctx.domain, ctx.property_id)
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            data_state="MEASURED",
            properties=properties,
            accounts=[ExternalAccount(account_id="google", provider=self.provider_id, external_account_id=ctx.external_account_id or "google", label="Google account")],
        )
        if not selected:
            result.data_state = "UNAVAILABLE"
            result.note = "No verified Search Console property matches this domain. Select a property before measuring search performance."
            return result
        ctx.property_id = selected
        partial: List[str] = []
        quota = None
        for comparison, start, end in (
            ("current", ctx.period_start, ctx.period_end),
            ("previous", ctx.previous_start, ctx.previous_end),
        ):
            total, total_error, total_quota = self._query(ctx, headers, selected, start, end, None)
            if total_quota:
                quota = total_quota
            if total_error:
                partial.append(total_error)
            elif total:
                result.raw_payloads.append(RawPayload(endpoint=f"searchAnalytics/totals/{comparison}", payload=strip_secrets(total), http_status=200))
                result.records.extend(_totals(ctx, total, comparison))
            from app.core.config import settings
            limit = int(settings.EXTERNAL_GSC_ROW_LIMIT or 250)
            for dimension in ("query", "page", "country", "device", "searchAppearance"):
                payload, error, dim_quota = self._query(ctx, headers, selected, start, end, [dimension], limit)
                if dim_quota:
                    quota = dim_quota
                if error:
                    partial.append(f"{dimension}: {error}")
                    continue
                if payload is None:
                    continue
                rows = payload.get("rows") or []
                if len(rows) >= limit:
                    partial.append(f"{dimension} rows reached the collection cap of {limit}.")
                result.records.extend(_dimension_rows(ctx, rows, dimension, comparison))
            if comparison == "current":
                pair, pair_error, _ = self._query(ctx, headers, selected, start, end, ["query", "page"], min(limit, 500))
                if pair_error:
                    partial.append(f"query_page: {pair_error}")
                elif pair:
                    result.records.extend(_dimension_rows(ctx, pair.get("rows") or [], "query_page", comparison))
        sitemaps, sitemap_error = self._sitemaps(ctx, headers, selected)
        if sitemap_error:
            partial.append(sitemap_error)
        elif sitemaps is not None:
            result.raw_payloads.append(RawPayload(endpoint="sitemaps", payload=strip_secrets(sitemaps), http_status=200))
            for item in sitemaps.get("sitemap") or []:
                result.records.append(record(
                    ctx,
                    record_type="search_performance",
                    metric="sitemap",
                    value_text=item.get("path"),
                    url=item.get("path"),
                    metadata={
                        "errors": item.get("errors"),
                        "warnings": item.get("warnings"),
                        "is_pending": item.get("isPending"),
                        "last_submitted": item.get("lastSubmitted"),
                        "contents": item.get("contents"),
                    },
                    raw_ref="webmasters.sitemaps.list",
                ))
        if ctx.inspect_urls and _inspection_enabled():
            for url in ctx.inspect_urls[:10]:
                inspected, error = self._inspect(ctx, headers, selected, url)
                if error:
                    partial.append(error)
                elif inspected:
                    verdict = ((inspected.get("inspectionResult") or {}).get("indexStatusResult") or {})
                    result.records.append(record(
                        ctx,
                        record_type="search_performance",
                        metric="url_inspection",
                        value_text=verdict.get("coverageState") or verdict.get("verdict"),
                        url=url,
                        metadata={"verdict": verdict.get("verdict"), "coverage_state": verdict.get("coverageState"), "indexing_state": verdict.get("indexingState"), "robots_txt_state": verdict.get("robotsTxtState")},
                        raw_ref="searchconsole.urlInspection",
                    ))
        result.partial_errors = partial
        result.quota_status = quota
        if not any(item.metric == "clicks" for item in result.records):
            result.data_state = "UNAVAILABLE" if not partial else "PARTIALLY_MEASURED"
            result.note = "Search Console did not return a totals row for this property."
        elif partial:
            result.data_state = "PARTIALLY_MEASURED"
            result.note = "Some Search Console dimensions were unavailable. Headline totals still come from the totals request. Pages absent from a row sample are not treated as deindexed."
        else:
            result.note = "Measured from the Google Search Console Search Analytics API. Pages absent from a sampled dimension are not treated as deindexed."
        return result

    def _sites(self, ctx: CollectContext, headers: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        response = ctx.transport.request("GET", SITES_URL, headers=headers)
        if response.status_code == 403:
            raise ProviderAuthError("Search Console denied this token.")
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return None
        return list(response.payload.get("siteEntry") or [])

    def _query(self, ctx, headers, site, start, end, dimensions, row_limit: Optional[int] = None):
        body: Dict[str, Any] = {"startDate": start, "endDate": end, "dataState": "final"}
        if dimensions:
            body["dimensions"] = dimensions
            body["rowLimit"] = row_limit or 250
        url = f"{SITES_URL}/{quote(site, safe='')}/searchAnalytics/query"
        try:
            response = ctx.transport.request("POST", url, headers=headers, json_body=body)
        except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
            raise
        except Exception as exc:
            return None, str(exc), None
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return None, safe_http_error(response.status_code, response.text), quota_status(response.headers)
        return response.payload, None, quota_status(response.headers)

    def _sitemaps(self, ctx, headers, site):
        url = f"{SITES_URL}/{quote(site, safe='')}/sitemaps"
        try:
            response = ctx.transport.request("GET", url, headers=headers)
        except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
            raise
        except Exception as exc:
            return None, str(exc)
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return None, safe_http_error(response.status_code, response.text)
        return response.payload, None

    def _inspect(self, ctx, headers, site, page_url):
        try:
            response = ctx.transport.request(
                "POST",
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers=headers,
                json_body={"inspectionUrl": page_url, "siteUrl": site},
            )
        except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
            raise
        except Exception as exc:
            return None, str(exc)
        if response.status_code != 200:
            return None, safe_http_error(response.status_code, response.text)
        return response.payload if isinstance(response.payload, dict) else None, None


def _inspection_enabled() -> bool:
    from app.core.config import settings
    return bool(settings.GSC_URL_INSPECTION_ENABLED)


def _property_from_site(item: Dict[str, Any]) -> ExternalProperty:
    site = str(item.get("siteUrl") or "")
    domain = site.replace("sc-domain:", "").replace("https://", "").replace("http://", "").strip("/")
    return ExternalProperty(
        property_id=site,
        provider="google_search_console",
        external_property_id=site,
        label=site,
        domain=domain,
        metadata={"permission_level": item.get("permissionLevel")},
    )


def _select_site(properties: List[ExternalProperty], domain: str, selected: Optional[str]) -> Optional[str]:
    if selected and any(item.external_property_id == selected for item in properties):
        return selected
    host = domain.lower().removeprefix("www.").strip("/")
    for item in properties:
        site = item.external_property_id
        site_host = (item.domain or "").lower().removeprefix("www.")
        if site == selected or site_host == host or site in {f"sc-domain:{host}", f"https://{host}/", f"http://{host}/"}:
            return site
    return None


def _totals(ctx: CollectContext, payload: Dict[str, Any], comparison: str):
    rows = payload.get("rows") or []
    if not rows:
        return [record(ctx, record_type="search_performance", metric="clicks", value=0, unit="count", comparison=comparison, metadata={"empty": True}, raw_ref="searchAnalytics.query")]
    row = rows[0]
    clicks = float(row.get("clicks") or 0)
    impressions = float(row.get("impressions") or 0)
    ctr = float(row.get("ctr") or 0)
    position = float(row.get("position") or 0)
    return [
        record(ctx, record_type="search_performance", metric="clicks", value=clicks, unit="count", comparison=comparison, raw_ref="searchAnalytics.query"),
        record(ctx, record_type="search_performance", metric="impressions", value=impressions, unit="count", comparison=comparison, raw_ref="searchAnalytics.query"),
        record(ctx, record_type="search_performance", metric="ctr", value=ctr, unit="ratio", comparison=comparison, raw_ref="searchAnalytics.query"),
        record(ctx, record_type="search_performance", metric="average_position", value=position, unit="position", comparison=comparison, raw_ref="searchAnalytics.query"),
    ]


def _dimension_rows(ctx: CollectContext, rows: List[Dict[str, Any]], dimension: str, comparison: str):
    built = []
    for row in rows:
        keys = list(row.get("keys") or [])
        meta: Dict[str, Any] = {
            "clicks": row.get("clicks"),
            "impressions": row.get("impressions"),
            "ctr": row.get("ctr"),
            "position": row.get("position"),
            "dimension": dimension,
        }
        url = None
        if dimension == "query" and keys:
            meta["query"] = keys[0]
        elif dimension == "page" and keys:
            meta["page"] = keys[0]
            url = keys[0]
        elif dimension == "country" and keys:
            meta["country"] = keys[0]
        elif dimension == "device" and keys:
            meta["device"] = keys[0]
        elif dimension == "searchAppearance" and keys:
            meta["search_appearance"] = keys[0]
        elif dimension == "query_page" and len(keys) >= 2:
            meta["query"] = keys[0]
            meta["page"] = keys[1]
            url = keys[1]
        built.append(record(
            ctx,
            record_type="search_performance",
            metric="search_analytics_row",
            metric_type=dimension,
            value=float(row.get("clicks") or 0),
            unit="clicks",
            url=url,
            metadata=meta,
            comparison=comparison,
            raw_ref="searchAnalytics.query",
        ))
    return built
