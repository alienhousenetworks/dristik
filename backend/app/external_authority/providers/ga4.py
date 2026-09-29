"""Google Analytics 4 Data API.

GA4 is analytics and behavior evidence only. It is not a ranking or
backlink source. Organic scope uses Google's Organic Search channel.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.external_authority.http import ProviderAuthError, ProviderRateLimitError, ProviderTransientError, quota_status
from app.external_authority.models import CollectionResult, ExternalProperty, ProviderCapabilities, RawPayload
from app.external_authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.external_authority.providers.google_oauth import application_client, authorize_url, bearer, exchange_code, pkce_pair, refresh, revoke
from app.external_authority.providers.records import record
from app.external_authority.redact import safe_http_error, strip_secrets

ADMIN_URL = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
DATA_HOST = "https://analyticsdata.googleapis.com/v1beta"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
ATTRIBUTION_NOTE = (
    "GA4 attributes sessions with its own channel grouping. "
    "These figures are analytics evidence, not rankings or backlink authority."
)


class GoogleAnalytics4Provider(ExternalDataProvider):
    provider_id = "google_analytics_4"
    display_name = "Google Analytics 4"
    auth_mode = "oauth"
    collection_tier = "FREE"
    scopes = SCOPES
    capabilities = ProviderCapabilities(analytics=True)

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.GA4_ENABLED)

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
            return not_connected(self.provider_id, "Google Analytics 4 is not connected.")
        headers = bearer(ctx.access_token)
        properties = self._properties(ctx, headers)
        selected = _select_property(properties, ctx.property_id, ctx.domain)
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            properties=properties,
            note=ATTRIBUTION_NOTE,
        )
        if not selected:
            result.data_state = "UNAVAILABLE"
            result.note = "No GA4 property is selected. Choose a property before measuring analytics. " + ATTRIBUTION_NOTE
            return result
        ctx.property_id = selected
        partial: List[str] = []
        current = self._report(ctx, headers, selected, ctx.period_start, ctx.period_end, landing_pages=False)
        pages = self._report(ctx, headers, selected, ctx.period_start, ctx.period_end, landing_pages=True)
        previous = self._report(ctx, headers, selected, ctx.previous_start, ctx.previous_end, landing_pages=False)
        quota = None
        for label, triple, comparison, landing in (
            ("totals", current, "current", False),
            ("landing_pages", pages, "current", True),
            ("previous_totals", previous, "previous", False),
        ):
            payload, error, call_quota = triple
            if call_quota:
                quota = call_quota
            if error:
                partial.append(f"{label}: {error}")
                continue
            if not payload:
                continue
            result.raw_payloads.append(RawPayload(endpoint=label, payload=strip_secrets(payload), http_status=200))
            result.records.extend(_rows(ctx, payload, comparison, landing))
        result.partial_errors = partial
        result.quota_status = quota
        if any(item.metric == "organic_sessions" for item in result.records):
            result.data_state = "PARTIALLY_MEASURED" if partial else "MEASURED"
        elif partial:
            result.data_state = "UNAVAILABLE"
            result.error = "GA4 did not return organic session metrics."
        else:
            result.data_state = "MEASURED"
            result.records.append(record(
                ctx, record_type="search_performance", metric="organic_sessions", value=0, unit="sessions",
                metadata={"channel": "Organic Search", "empty": True, "attribution": ATTRIBUTION_NOTE},
                raw_ref="analyticsdata.runReport",
            ))
        return result

    def _properties(self, ctx: CollectContext, headers: Dict[str, str]) -> List[ExternalProperty]:
        response = ctx.transport.request("GET", ADMIN_URL, headers=headers)
        if response.status_code == 403:
            raise ProviderAuthError("GA4 admin API denied this token.")
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return []
        properties: List[ExternalProperty] = []
        for account in response.payload.get("accountSummaries") or []:
            for prop in account.get("propertySummaries") or []:
                name = str(prop.get("property") or "")
                properties.append(ExternalProperty(
                    property_id=name,
                    provider=self.provider_id,
                    external_property_id=name,
                    label=prop.get("displayName") or name,
                    domain=ctx.domain,
                    metadata={"account": account.get("account"), "account_name": account.get("displayName")},
                ))
        return properties

    def _report(self, ctx, headers, property_name, start, end, landing_pages: bool):
        clean = property_name.split("/")[-1]
        url = f"{DATA_HOST}/properties/{clean}:runReport"
        metrics = [
            {"name": "totalUsers"},
            {"name": "sessions"},
            {"name": "engagementRate"},
            {"name": "conversions"},
            {"name": "totalRevenue"},
        ]
        body: Dict[str, Any] = {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "metrics": metrics,
            "dimensionFilter": {
                "filter": {
                    "fieldName": "sessionDefaultChannelGroup",
                    "stringFilter": {"matchType": "EXACT", "value": "Organic Search"},
                }
            },
            "limit": 100 if landing_pages else 1,
        }
        if landing_pages:
            body["dimensions"] = [{"name": "landingPagePlusQueryString"}]
        else:
            body["dimensions"] = [{"name": "sessionDefaultChannelGroup"}]
        response = self._post(ctx, url, headers, body)
        if response is None:
            return None, "GA4 request failed", None
        if response.status_code == 400 and _mentions_revenue(response.text):
            body["metrics"] = [item for item in metrics if item["name"] != "totalRevenue"]
            response = self._post(ctx, url, headers, body)
            if response and response.status_code == 200:
                payload = response.payload if isinstance(response.payload, dict) else {}
                payload = dict(payload)
                payload["_revenue_unavailable"] = True
                return payload, None, quota_status(response.headers)
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return None, safe_http_error(response.status_code, response.text), quota_status(response.headers)
        return response.payload, None, quota_status(response.headers)

    def _post(self, ctx, url, headers, body):
        try:
            return ctx.transport.request("POST", url, headers=headers, json_body=body)
        except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
            raise
        except Exception:
            return None


def _mentions_revenue(text: str) -> bool:
    return "totalRevenue" in (text or "") or "TOTAL_REVENUE" in (text or "")


def _select_property(properties: List[ExternalProperty], selected: Optional[str], domain: str) -> Optional[str]:
    if selected:
        for item in properties:
            if item.external_property_id == selected or item.external_property_id.endswith("/" + selected):
                return item.external_property_id
        if selected.startswith("properties/"):
            return selected
    if len(properties) == 1:
        return properties[0].external_property_id
    host = domain.lower()
    for item in properties:
        if host and host in (item.label or "").lower():
            return item.external_property_id
    return None


def _rows(ctx: CollectContext, payload: Dict[str, Any], comparison: str, landing: bool):
    headers = [item.get("name") for item in payload.get("metricHeaders") or []]
    built = []
    revenue_missing = bool(payload.get("_revenue_unavailable"))
    for row in payload.get("rows") or []:
        dims = [item.get("value") for item in row.get("dimensionValues") or []]
        metrics = {}
        for name, cell in zip(headers, row.get("metricValues") or []):
            metrics[name] = _num(cell.get("value"))
        meta = {
            "channel": "Organic Search",
            "attribution": ATTRIBUTION_NOTE,
            "dimensions": dims,
            "revenue_unavailable": revenue_missing,
            **metrics,
        }
        if landing and dims:
            meta["page"] = dims[0]
            built.append(record(
                ctx,
                record_type="search_performance",
                metric="organic_landing_page",
                value=metrics.get("sessions"),
                unit="sessions",
                url=dims[0],
                metadata=meta,
                comparison=comparison,
                raw_ref="analyticsdata.runReport",
            ))
            continue
        if not landing:
            continue
    if not landing:
        built.extend(_aggregate_channel(ctx, payload, comparison, revenue_missing))
    if revenue_missing:
        built.append(record(
            ctx,
            record_type="search_performance",
            metric="organic_revenue",
            value=None,
            status="UNAVAILABLE",
            metadata={"reason": "The GA4 property did not return totalRevenue for this query.", "attribution": ATTRIBUTION_NOTE},
            comparison=comparison,
            raw_ref="analyticsdata.runReport",
        ))
    return built


def _aggregate_channel(ctx, payload, comparison, revenue_missing):
    headers = [item.get("name") for item in payload.get("metricHeaders") or []]
    totals = {name: 0.0 for name in headers}
    sessions_for_rate = 0.0
    engagement_weighted = 0.0
    saw = False
    for row in payload.get("rows") or []:
        saw = True
        metrics = {}
        for name, cell in zip(headers, row.get("metricValues") or []):
            metrics[name] = _num(cell.get("value")) or 0.0
        for name, amount in metrics.items():
            if name == "engagementRate":
                sessions = metrics.get("sessions") or 0.0
                engagement_weighted += amount * sessions
                sessions_for_rate += sessions
            else:
                totals[name] = totals.get(name, 0.0) + amount
    if not saw:
        return []
    if sessions_for_rate:
        totals["engagementRate"] = engagement_weighted / sessions_for_rate
    built = []
    meta = {"channel": "Organic Search", "attribution": ATTRIBUTION_NOTE, "revenue_unavailable": revenue_missing}
    for metric, unit, name in (
        ("totalUsers", "users", "organic_users"),
        ("sessions", "sessions", "organic_sessions"),
        ("engagementRate", "ratio", "organic_engagement_rate"),
        ("conversions", "events", "organic_conversions"),
        ("totalRevenue", "currency", "organic_revenue"),
    ):
        if metric not in totals and not (metric == "engagementRate" and sessions_for_rate):
            continue
        if metric not in headers and metric not in totals:
            continue
        if metric not in headers:
            continue
        built.append(record(
            ctx,
            record_type="search_performance",
            metric=name,
            value=totals.get(metric),
            unit=unit,
            metadata=meta,
            comparison=comparison,
            raw_ref="analyticsdata.runReport",
        ))
    return built


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


