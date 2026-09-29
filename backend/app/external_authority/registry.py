"""Provider registry. The authority engine depends on this list, not on one vendor."""
from __future__ import annotations

from typing import Dict, List

from app.external_authority.providers.backlinks import AhrefsProvider, MajesticProvider, SemrushProvider
from app.external_authority.providers.base import ExternalDataProvider
from app.external_authority.providers.bing import BingWebmasterProvider
from app.external_authority.providers.citations import CitationProvider
from app.external_authority.providers.ga4 import GoogleAnalytics4Provider
from app.external_authority.providers.gbp import GoogleBusinessProfileProvider
from app.external_authority.providers.gsc import GoogleSearchConsoleProvider
from app.external_authority.providers.mentions import BrandMentionProvider
from app.external_authority.providers.serp import DataForSeoProvider, SerpApiProvider

_PROVIDERS: Dict[str, ExternalDataProvider] = {
    provider.provider_id: provider
    for provider in (
        GoogleSearchConsoleProvider(),
        GoogleAnalytics4Provider(),
        BingWebmasterProvider(),
        AhrefsProvider(),
        SemrushProvider(),
        MajesticProvider(),
        DataForSeoProvider(),
        SerpApiProvider(),
        GoogleBusinessProfileProvider(),
        CitationProvider(),
        BrandMentionProvider(),
    )
}

JOB_PROVIDERS = {
    "sync_gsc_data": ["google_search_console"],
    "sync_ga4_data": ["google_analytics_4"],
    "sync_bing_data": ["bing_webmaster"],
    "sync_backlinks": ["ahrefs", "semrush", "majestic", "dataforseo"],
    "sync_gbp_data": ["google_business_profile"],
    "sync_brand_mentions": ["brand_mentions"],
    "sync_citations": ["citations"],
    "sync_serp": ["serpapi", "dataforseo"],
}


def get_provider(provider_id: str) -> ExternalDataProvider:
    try:
        return _PROVIDERS[provider_id]
    except KeyError as exc:
        raise KeyError(f"Unknown external provider '{provider_id}'") from exc


def all_providers() -> List[ExternalDataProvider]:
    return list(_PROVIDERS.values())
