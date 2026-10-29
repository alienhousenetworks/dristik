"""Google Business Profile.

Applicability is explicit. A non-local business is NOT_APPLICABLE,
which is not an SEO failure.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.connectors.authority.http import ProviderAuthError, ProviderRateLimitError, ProviderTransientError
from app.connectors.authority.models import CollectionResult, ExternalProperty, ProviderCapabilities, RawPayload
from app.connectors.authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.connectors.authority.providers.google_oauth import application_client, authorize_url, bearer, exchange_code, pkce_pair, refresh, revoke
from app.connectors.authority.providers.records import record
from app.connectors.authority.redact import strip_secrets

SCOPES = ["https://www.googleapis.com/auth/business.manage"]
METRICS = [
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
    "WEBSITE_CLICKS",
    "CALL_CLICKS",
    "BUSINESS_DIRECTION_REQUESTS",
    "BUSINESS_BOOKINGS",
    "BUSINESS_FOOD_MENU_CLICKS",
]
METRIC_NAMES = {
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH": "search_impressions_desktop",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": "search_impressions_mobile",
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS": "maps_impressions_desktop",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS": "maps_impressions_mobile",
    "WEBSITE_CLICKS": "website_clicks",
    "CALL_CLICKS": "calls",
    "BUSINESS_DIRECTION_REQUESTS": "direction_requests",
    "BUSINESS_BOOKINGS": "bookings",
    "BUSINESS_FOOD_MENU_CLICKS": "menu_interactions",
}


class GoogleBusinessProfileProvider(ExternalDataProvider):
    provider_id = "google_business_profile"
    display_name = "Google Business Profile"
    auth_mode = "oauth"
    collection_tier = "FREE"
    scopes = SCOPES
    capabilities = ProviderCapabilities(business_profile=True)

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.GBP_ENABLED)

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
        if ctx.applicability == "NON_LOCAL_BUSINESS":
            return CollectionResult(
                provider=self.provider_id,
                connection_status="NOT_APPLICABLE",
                data_state="NOT_APPLICABLE",
                note="Google Business Profile is not applicable for this business. This is not an SEO failure.",
            )
        if not ctx.access_token:
            note = "Google Business Profile is not connected."
            if ctx.applicability == "UNKNOWN":
                note += " Applicability is unknown, so this is not treated as an SEO failure."
            return not_connected(self.provider_id, note)
        headers = bearer(ctx.access_token)
        accounts = ctx.transport.request("GET", "https://mybusinessaccountmanagement.googleapis.com/v1/accounts", headers=headers)
        if accounts.status_code == 403:
            raise ProviderAuthError("Google Business Profile denied this token.")
        if accounts.status_code != 200 or not isinstance(accounts.payload, dict):
            return CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="UNAVAILABLE", error=f"HTTP {accounts.status_code}")
        properties: List[ExternalProperty] = []
        result = CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="MEASURED")
        partial: List[str] = []
        for account in accounts.payload.get("accounts") or []:
            name = account.get("name")
            if not name:
                continue
            locations = ctx.transport.request(
                "GET",
                f"https://mybusinessbusinessinformation.googleapis.com/v1/{name}/locations",
                headers=headers,
                params={"readMask": "name,title,storefrontAddress,websiteUri,phoneNumbers"},
            )
            if locations.status_code != 200 or not isinstance(locations.payload, dict):
                partial.append(f"locations for {name} were unavailable")
                continue
            for location in locations.payload.get("locations") or []:
                loc_name = location.get("name")
                properties.append(ExternalProperty(
                    property_id=loc_name,
                    provider=self.provider_id,
                    external_property_id=loc_name,
                    label=location.get("title"),
                    domain=ctx.domain,
                    metadata={"website": location.get("websiteUri"), "account": name},
                ))
                if ctx.property_id and loc_name != ctx.property_id:
                    continue
                series = self._metrics(ctx, headers, loc_name)
                if isinstance(series, str):
                    partial.append(series)
                    continue
                result.raw_payloads.append(RawPayload(endpoint=loc_name, payload=strip_secrets(series)))
                result.records.extend(_sum_metrics(ctx, series, loc_name, location.get("title")))
        result.properties = properties
        result.partial_errors = partial
        if not result.records and partial:
            result.data_state = "UNAVAILABLE"
        elif partial:
            result.data_state = "PARTIALLY_MEASURED"
        elif not result.records:
            result.data_state = "MEASURED"
            result.note = "The connected Business Profile account returned no location metrics for this period."
        else:
            result.note = "Measured from the Google Business Profile Performance API."
        return result

    def _metrics(self, ctx, headers, location_name: str):
        start = _date(ctx.period_start)
        end = _date(ctx.period_end)
        try:
            response = ctx.transport.request(
                "POST",
                f"https://businessprofileperformance.googleapis.com/v1/{location_name}:fetchMultiDailyMetricsTimeSeries",
                headers=headers,
                json_body={"dailyMetrics": METRICS, "dailyRange": {"startDate": start, "endDate": end}},
            )
        except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
            raise
        except Exception as exc:
            return str(exc)
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return f"performance HTTP {response.status_code}"
        return response.payload


def _date(iso_day: str) -> Dict[str, int]:
    year, month, day = [int(part) for part in iso_day.split("-")[:3]]
    return {"year": year, "month": month, "day": day}


def _sum_metrics(ctx: CollectContext, payload: Dict[str, Any], location_name: str, title: str):
    built = []
    series_groups = payload.get("multiDailyMetricTimeSeries") or []
    for group in series_groups:
        for series in group.get("dailyMetricTimeSeries") or []:
            metric = series.get("dailyMetric")
            total = 0.0
            for point in (series.get("timeSeries") or {}).get("datedValues") or []:
                try:
                    total += float(point.get("value") or 0)
                except (TypeError, ValueError):
                    continue
            built.append(record(
                ctx,
                record_type="business_profile_metric",
                metric=METRIC_NAMES.get(metric, str(metric or "unknown").lower()),
                value=total,
                unit="count",
                url=location_name,
                metadata={"location": location_name, "title": title, "daily_metric": metric},
                raw_ref="businessprofileperformance.fetchMultiDailyMetricsTimeSeries",
            ))
    return built
