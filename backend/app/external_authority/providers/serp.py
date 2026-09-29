"""SERP and DataForSEO collection.

DataForSEO uses an API login and API password, which are that vendor's
credentials, not a Google or website password. SerpAPI is API-key only.
Neither result is stored as a universal authority score.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.external_authority.http import ProviderAuthError, ProviderRateLimitError, ProviderTransientError
from app.external_authority.models import CollectionResult, ProviderCapabilities, RawPayload
from app.external_authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.external_authority.providers.records import record
from app.external_authority.redact import strip_secrets


class DataForSeoProvider(ExternalDataProvider):
    provider_id = "dataforseo"
    display_name = "DataForSEO"
    auth_mode = "basic"
    collection_tier = "ADVANCED"
    scopes: List[str] = []
    capabilities = ProviderCapabilities(
        backlinks=True,
        referring_domains=True,
        serp=True,
        competitors=True,
        citations=True,
        brand_mentions=True,
    )

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.DATAFORSEO_ENABLED)

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        from app.core.config import settings
        if settings.DATAFORSEO_LOGIN and settings.DATAFORSEO_PASSWORD and settings.DATAFORSEO_ENABLED:
            return {"login": settings.DATAFORSEO_LOGIN, "password": settings.DATAFORSEO_PASSWORD}
        return None

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        response = transport.request(
            "POST",
            "https://api.dataforseo.com/v3/appendix/user_data",
            auth=(secret.get("login") or "", secret.get("password") or ""),
            json_body=[],
        )
        if response.status_code in (401, 403):
            raise ProviderAuthError("DataForSEO rejected these API credentials.")
        return {"login": secret.get("login"), "password": secret.get("password")}

    def collect(self, ctx: CollectContext) -> CollectionResult:
        if not ctx.login or not ctx.password:
            return not_connected(self.provider_id, "DataForSEO is not connected.")
        result = CollectionResult(provider=self.provider_id, connection_status="CONNECTED")
        partial: List[str] = []
        if ctx.mode in {"default", "backlinks"}:
            payload = _post(ctx, "/v3/backlinks/summary/live", [{"target": ctx.domain, "internal_list_limit": 10}])
            if isinstance(payload, str):
                partial.append(payload)
            else:
                result.raw_payloads.append(RawPayload(endpoint="backlinks/summary/live", payload=strip_secrets(payload)))
                row = _first_result(payload)
                if row:
                    result.records.append(record(ctx, record_type="backlink", metric="backlinks", value=_num(row.get("backlinks")), unit="links", raw_ref="dataforseo.backlinks.summary"))
                    result.records.append(record(ctx, record_type="referring_domain", metric="referring_domains", value=_num(row.get("referring_domains")), unit="domains", raw_ref="dataforseo.backlinks.summary"))
                    if row.get("referring_domains_nofollow") is not None:
                        result.records.append(record(ctx, record_type="backlink", metric="nofollow_referring_domains", value=_num(row.get("referring_domains_nofollow")), unit="domains", raw_ref="dataforseo.backlinks.summary"))
        if ctx.mode in {"default", "serp"}:
            payload = _post(ctx, "/v3/serp/google/organic/live/advanced", [{
                "keyword": ctx.domain,
                "location_code": 2840,
                "language_code": "en",
                "depth": 10,
            }])
            if isinstance(payload, str):
                partial.append(payload)
            else:
                result.raw_payloads.append(RawPayload(endpoint="serp/google/organic/live/advanced", payload=strip_secrets(payload)))
                for item in _serp_items(payload):
                    if item.get("type") == "organic":
                        result.records.append(record(
                            ctx,
                            record_type="competitor_signal",
                            metric="serp_presence",
                            value=_num(item.get("rank_group")),
                            value_text=item.get("domain"),
                            url=item.get("url"),
                            metadata={"competitor_domain": item.get("domain"), "title": item.get("title"), "keyword": ctx.domain},
                            raw_ref="dataforseo.serp",
                        ))
                    if item.get("type") == "knowledge_graph":
                        result.records.append(record(
                            ctx,
                            record_type="entity_signal",
                            metric="knowledge_graph_reference",
                            value_text=item.get("title"),
                            url=item.get("url"),
                            evidence_url=item.get("url"),
                            metadata={"signal": "knowledge_graph_reference", "title": item.get("title"), "description": item.get("description")},
                            status="MEASURED",
                            raw_ref="dataforseo.serp.knowledge_graph",
                        ))
        result.partial_errors = partial
        result.data_state = "PARTIALLY_MEASURED" if partial and result.records else "MEASURED" if result.records else "UNAVAILABLE"
        result.note = "DataForSEO backlink counts are DataForSEO measurements. They are not a Google authority score."
        return result


class SerpApiProvider(ExternalDataProvider):
    provider_id = "serpapi"
    display_name = "SerpAPI"
    auth_mode = "api_key"
    collection_tier = "ADVANCED"
    scopes: List[str] = []
    capabilities = ProviderCapabilities(serp=True, competitors=True)

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.SERPAPI_ENABLED)

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        from app.core.config import settings
        if settings.SERPAPI_ENABLED and settings.SERPAPI_KEY:
            return {"api_key": settings.SERPAPI_KEY}
        return None

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        response = transport.request("GET", "https://serpapi.com/account.json", params={"api_key": secret.get("api_key")})
        if response.status_code in (401, 403):
            raise ProviderAuthError("SerpAPI rejected this API key.")
        return {"api_key": secret.get("api_key")}

    def collect(self, ctx: CollectContext) -> CollectionResult:
        if not ctx.api_key:
            return not_connected(self.provider_id, "SerpAPI is not connected.")
        response = ctx.transport.request("GET", "https://serpapi.com/search.json", params={
            "engine": "google", "q": ctx.domain, "api_key": ctx.api_key, "num": 10,
        })
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="UNAVAILABLE", error=f"HTTP {response.status_code}")
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            data_state="MEASURED",
            raw_payloads=[RawPayload(endpoint="search", payload=strip_secrets(response.payload))],
            note="SERP presence is a snapshot of one query. It is not a ranking authority score.",
        )
        for item in response.payload.get("organic_results") or []:
            result.records.append(record(
                ctx,
                record_type="competitor_signal",
                metric="serp_presence",
                value=_num(item.get("position")),
                value_text=item.get("displayed_link") or item.get("link"),
                url=item.get("link"),
                metadata={"competitor_domain": item.get("displayed_link"), "title": item.get("title"), "keyword": ctx.domain},
                raw_ref="serpapi.search",
            ))
        graph = response.payload.get("knowledge_graph")
        if isinstance(graph, dict):
            result.records.append(record(
                ctx,
                record_type="entity_signal",
                metric="knowledge_graph_reference",
                value_text=graph.get("title"),
                url=graph.get("website") or graph.get("source", {}).get("link") if isinstance(graph.get("source"), dict) else None,
                metadata={"signal": "knowledge_graph_reference", "title": graph.get("title"), "description": graph.get("description")},
                raw_ref="serpapi.knowledge_graph",
            ))
        return result


def _post(ctx: CollectContext, path: str, body: List[Dict[str, Any]]):
    try:
        response = ctx.transport.request(
            "POST",
            f"https://api.dataforseo.com{path}",
            json_body=body,
            auth=(ctx.login or "", ctx.password or ""),
        )
    except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
        raise
    except Exception as exc:
        return str(exc)
    if response.status_code != 200 or not isinstance(response.payload, dict):
        return f"HTTP {response.status_code}"
    return response.payload


def _first_result(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for task in payload.get("tasks") or []:
        if task.get("status_code") not in (20000, None) and task.get("status_code") != 20000:
            continue
        for row in task.get("result") or []:
            if isinstance(row, dict):
                return row
    return None


def _serp_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for task in payload.get("tasks") or []:
        for row in task.get("result") or []:
            for item in row.get("items") or []:
                if isinstance(item, dict):
                    items.append(item)
    return items


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
