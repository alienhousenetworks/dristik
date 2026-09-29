"""Brand mention collection.

Sentiment is stored only when a connected provider returns it and
BRAND_MENTIONS_SENTIMENT_ENABLED is on. It is never inferred here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.external_authority.models import CollectionResult, ProviderCapabilities, RawPayload, isoformat
from app.external_authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.external_authority.providers.records import record
from app.external_authority.redact import strip_secrets


class BrandMentionProvider(ExternalDataProvider):
    provider_id = "brand_mentions"
    display_name = "Brand mentions"
    auth_mode = "api_key"
    collection_tier = "STANDARD"
    scopes: list = []
    capabilities = ProviderCapabilities(brand_mentions=True, sentiment=False)

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.BRAND_MENTIONS_ENABLED)

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        from app.core.config import settings
        if settings.BRAND_MENTIONS_ENABLED and settings.BRAND_MENTIONS_API_KEY:
            return {"api_key": settings.BRAND_MENTIONS_API_KEY}
        return None

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        return {"api_key": secret.get("api_key")}

    def collect(self, ctx: CollectContext) -> CollectionResult:
        from app.core.config import settings
        provider_name = (settings.BRAND_MENTIONS_PROVIDER or "").lower()
        if provider_name == "dataforseo" and ctx.login and ctx.password:
            return self._dataforseo(ctx)
        if not ctx.api_key or not settings.BRAND_MENTIONS_BASE_URL:
            return not_connected(self.provider_id, "No brand mention provider is connected.")
        response = ctx.transport.request(
            "GET",
            settings.BRAND_MENTIONS_BASE_URL.rstrip("/") + "/mentions",
            headers={"Authorization": f"Bearer {ctx.api_key}", "Accept": "application/json"},
            params={"domain": ctx.domain, "brand": " ".join(ctx.brand_terms)},
        )
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="UNAVAILABLE", error=f"HTTP {response.status_code}")
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            data_state="MEASURED",
            raw_payloads=[RawPayload(endpoint="mentions", payload=strip_secrets(response.payload))],
            note="Mention class is taken from the provider payload. Sentiment is not inferred.",
        )
        for item in response.payload.get("mentions") or []:
            result.records.append(_mention(ctx, item, provider_name or "brand_mentions"))
        return result

    def _dataforseo(self, ctx: CollectContext) -> CollectionResult:
        keyword = " ".join(ctx.brand_terms) or ctx.domain
        response = ctx.transport.request(
            "POST",
            "https://api.dataforseo.com/v3/content_analysis/search/live",
            auth=(ctx.login or "", ctx.password or ""),
            json_body=[{"keyword": keyword, "limit": 20}],
        )
        if response.status_code != 200 or not isinstance(response.payload, dict):
            return CollectionResult(provider=self.provider_id, connection_status="CONNECTED", data_state="UNAVAILABLE", error=f"HTTP {response.status_code}")
        result = CollectionResult(
            provider=self.provider_id,
            connection_status="CONNECTED",
            data_state="MEASURED",
            raw_payloads=[RawPayload(endpoint="content_analysis/search/live", payload=strip_secrets(response.payload))],
            note="Mentions come from DataForSEO content analysis. Sentiment is not inferred.",
        )
        for task in response.payload.get("tasks") or []:
            for row in task.get("result") or []:
                for item in row.get("items") or []:
                    links = item.get("links") or []
                    result.records.append(_mention(ctx, {
                        "url": item.get("url"),
                        "domain": item.get("domain"),
                        "published_at": item.get("date_published"),
                        "snippet": item.get("snippet") or item.get("main_domain"),
                        "linked": bool(links),
                        "target_url": links[0] if links and isinstance(links[0], str) else None,
                        "brand": keyword,
                    }, "dataforseo"))
        return result


def _mention(ctx: CollectContext, item: Dict[str, Any], source: str):
    from app.core.config import settings
    mention_class = _class_for(item, ctx.domain)
    meta = {
        "mention_url": item.get("url"),
        "source_domain": item.get("domain"),
        "published_at": item.get("published_at") or item.get("publication_date"),
        "discovered_at": isoformat(ctx.now),
        "brand": item.get("brand") or " ".join(ctx.brand_terms),
        "mention_class": mention_class,
        "linked": mention_class == "LINKED",
        "target_url": item.get("target_url"),
        "context": item.get("snippet") or item.get("context"),
        "category": item.get("category"),
    }
    if settings.BRAND_MENTIONS_SENTIMENT_ENABLED and item.get("sentiment") is not None:
        meta["sentiment"] = item.get("sentiment")
        meta["sentiment_source"] = source
    return record(
        ctx,
        record_type="brand_mention",
        metric="mention",
        value_text=mention_class,
        url=item.get("target_url") or item.get("url"),
        evidence_url=item.get("url"),
        metadata=meta,
        source=source,
        raw_ref=f"{source}.mentions",
        confidence=0.9 if mention_class != "UNVERIFIED" else 0.4,
        status="MEASURED" if mention_class != "UNVERIFIED" else "UNVERIFIED",
        evidence_basis="DIRECT_PROVIDER_EVIDENCE" if mention_class != "UNVERIFIED" else "UNVERIFIED",
    )


def _class_for(item: Dict[str, Any], domain: str) -> str:
    explicit = str(item.get("mention_class") or "").upper()
    if explicit in {"LINKED", "UNLINKED", "POTENTIAL_ENTITY", "UNVERIFIED"}:
        return explicit
    if not item.get("url"):
        return "UNVERIFIED"
    target = str(item.get("target_url") or "")
    if item.get("linked") is True or (target and domain and domain in target):
        return "LINKED"
    if item.get("entity") is True and not item.get("brand"):
        return "POTENTIAL_ENTITY"
    if item.get("snippet") or item.get("context") or item.get("brand"):
        return "UNLINKED"
    return "UNVERIFIED"
