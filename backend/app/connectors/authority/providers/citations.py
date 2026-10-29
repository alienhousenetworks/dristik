"""Configurable citation collection.

Directories are not treated as authoritative because they exist.
Consistency is calculated against the business profile the user configured.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.connectors.authority.models import CollectionResult, ProviderCapabilities, RawPayload
from app.connectors.authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.connectors.authority.providers.records import record
from app.connectors.authority.redact import strip_secrets


class CitationProvider(ExternalDataProvider):
    provider_id = "citations"
    display_name = "Business directories"
    auth_mode = "api_key"
    collection_tier = "STANDARD"
    scopes: List[str] = []
    capabilities = ProviderCapabilities(citations=True)

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.CITATIONS_ENABLED)

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        from app.core.config import settings
        if not settings.CITATIONS_ENABLED:
            return None
        if settings.CITATIONS_PROVIDER == "dataforseo":
            return None
        if settings.CITATIONS_API_KEY:
            return {"api_key": settings.CITATIONS_API_KEY, "provider_name": settings.CITATIONS_PROVIDER}
        return None

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        return {
            "api_key": secret.get("api_key"),
            "provider_name": secret.get("provider_name"),
        }

    def collect(self, ctx: CollectContext) -> CollectionResult:
        from app.core.config import settings
        if not settings.CITATIONS_ENABLED and not ctx.api_key:
            return not_connected(self.provider_id, "No citation provider is connected.")
        if (settings.CITATIONS_PROVIDER or "").lower() == "dataforseo" and ctx.login and ctx.password:
            return self._dataforseo(ctx)
        if not ctx.api_key or not settings.CITATIONS_BASE_URL:
            return not_connected(
                self.provider_id,
                "No citation provider is connected. Configure CITATIONS_PROVIDER and a base URL, or DataForSEO business listings.",
            )
        response = ctx.transport.request(
            "GET",
            settings.CITATIONS_BASE_URL.rstrip("/") + "/listings",
            headers={"Authorization": f"Bearer {ctx.api_key}", "Accept": "application/json"},
            params={"domain": ctx.domain},
        )
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="UNAVAILABLE", error=f"HTTP {response.status_code}")
        listings = response.payload.get("listings") or []
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            data_state="MEASURED",
            raw_payloads=[RawPayload(endpoint="listings", payload=strip_secrets(response.payload))],
            note="Listing consistency is compared with the business profile you configured. A directory is not treated as authoritative merely because it exists.",
        )
        for item in listings:
            result.records.append(_listing_record(ctx, item, settings.CITATIONS_PROVIDER or "citations"))
        return result

    def _dataforseo(self, ctx: CollectContext) -> CollectionResult:
        response = ctx.transport.request(
            "POST",
            "https://api.dataforseo.com/v3/business_data/business_listings/search/live",
            auth=(ctx.login or "", ctx.password or ""),
            json_body=[{"keyword": ctx.domain, "location_code": 2840, "limit": 20}],
        )
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="UNAVAILABLE", error=f"HTTP {response.status_code}")
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            data_state="MEASURED",
            raw_payloads=[RawPayload(endpoint="business_listings/search/live", payload=strip_secrets(response.payload))],
            note="These listings come from DataForSEO. A directory is not treated as authoritative merely because it exists.",
        )
        for task in response.payload.get("tasks") or []:
            for row in task.get("result") or []:
                for item in row.get("items") or []:
                    result.records.append(_listing_record(ctx, {
                        "name": item.get("title"),
                        "address": item.get("address"),
                        "phone": item.get("phone"),
                        "website": item.get("url") or item.get("domain"),
                        "category": item.get("category"),
                        "listing_url": item.get("url"),
                        "source": item.get("domain") or "dataforseo",
                        "claimed": item.get("is_claimed"),
                    }, "dataforseo"))
        if not result.records:
            result.note = "DataForSEO returned no business listings for this query. " + (result.note or "")
        return result


def _listing_record(ctx: CollectContext, item: Dict[str, Any], source: str):
    return record(
        ctx,
        record_type="business_listing",
        metric="listing",
        value_text=item.get("name") or item.get("business_name"),
        url=item.get("listing_url") or item.get("url"),
        evidence_url=item.get("listing_url") or item.get("url"),
        metadata={
            "business_name": item.get("name") or item.get("business_name"),
            "address": item.get("address"),
            "phone": item.get("phone"),
            "website": item.get("website"),
            "category": item.get("category"),
            "listing_url": item.get("listing_url") or item.get("url"),
            "source_directory": item.get("source") or source,
            "claimed": item.get("claimed"),
        },
        source=source,
        raw_ref=f"{source}.listings",
    )
