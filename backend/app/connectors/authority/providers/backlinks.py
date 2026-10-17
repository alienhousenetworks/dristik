"""Ahrefs, Semrush, and Majestic adapters.

Vendor scores keep their vendor names. They are not combined.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from app.connectors.authority.http import ProviderAuthError, ProviderRateLimitError, ProviderTransientError
from app.connectors.authority.models import CollectionResult, ProviderCapabilities, RawPayload, isoformat, utcnow, vendor_metric_label
from app.connectors.authority.providers.base import CollectContext, ExternalDataProvider, not_connected
from app.connectors.authority.providers.records import record
from app.connectors.authority.redact import strip_secrets
from datetime import timedelta


def _follow(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "follow" if value else "nofollow"
    text = str(value).strip().lower()
    if text in {"1", "true", "dofollow", "follow"}:
        return "follow"
    if text in {"0", "false", "nofollow"}:
        return "nofollow"
    if text in {"ugc", "sponsored"}:
        return text
    return text or "unknown"


class _KeyOrOAuthProvider(ExternalDataProvider):
    api_setting: str = ""
    client_setting: str = ""
    secret_setting: str = ""
    enabled_setting: str = ""
    authorize_setting: str = ""
    token_setting: str = ""
    redirect_setting: str = ""

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(getattr(settings, self.enabled_setting))

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        from app.core.config import settings
        key = getattr(settings, self.api_setting, None)
        if key:
            return {"api_key": key}
        return None

    def oauth_application_ready(self) -> bool:
        from app.core.config import settings
        return bool(getattr(settings, self.client_setting, None) and getattr(settings, self.secret_setting, None))

    def build_authorize(self, state: str) -> tuple[str, str]:
        from app.core.config import settings
        redirect = getattr(settings, self.redirect_setting) or settings.external_oauth_redirect_uri()
        query = urlencode({
            "client_id": getattr(settings, self.client_setting) or "",
            "redirect_uri": redirect,
            "response_type": "code",
            "state": state,
            "scope": " ".join(self.scopes),
        })
        return f"{getattr(settings, self.authorize_setting)}?{query}", ""

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        if secret.get("api_key") and not secret.get("code"):
            self._probe_key(transport, secret["api_key"])
            return {"api_key": secret["api_key"]}
        return self._exchange(transport, secret)

    def _exchange(self, transport, secret: Dict[str, Any]) -> Dict[str, Any]:
        from app.core.config import settings
        response = transport.request("POST", getattr(settings, self.token_setting), data={
            "client_id": getattr(settings, self.client_setting) or "",
            "client_secret": getattr(settings, self.secret_setting) or "",
            "code": secret.get("code"),
            "redirect_uri": getattr(settings, self.redirect_setting) or settings.external_oauth_redirect_uri(),
            "grant_type": "authorization_code",
        })
        if response.status_code != 200 or not isinstance(response.payload, dict):
            raise ProviderAuthError(f"{self.display_name} token exchange failed.")
        token = response.payload.get("access_token") or response.payload.get("api_key")
        if not token:
            raise ProviderAuthError(f"{self.display_name} token exchange returned no token.")
        expires_in = int(response.payload.get("expires_in") or 3600)
        return {
            "access_token": response.payload.get("access_token"),
            "refresh_token": response.payload.get("refresh_token"),
            "api_key": response.payload.get("api_key"),
            "expires_at": isoformat(utcnow() + timedelta(seconds=expires_in)) if response.payload.get("access_token") else None,
        }

    def refresh_credentials(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        if not secret.get("refresh_token"):
            return secret
        from app.core.config import settings
        response = transport.request("POST", getattr(settings, self.token_setting), data={
            "client_id": getattr(settings, self.client_setting) or "",
            "client_secret": getattr(settings, self.secret_setting) or "",
            "refresh_token": secret["refresh_token"],
            "grant_type": "refresh_token",
        })
        if response.status_code != 200 or not isinstance(response.payload, dict):
            raise ProviderAuthError(f"{self.display_name} token refresh failed.")
        updated = dict(secret)
        updated["access_token"] = response.payload.get("access_token") or secret.get("access_token")
        updated["expires_at"] = isoformat(utcnow() + timedelta(seconds=int(response.payload.get("expires_in") or 3600)))
        return updated

    def _probe_key(self, transport, api_key: str) -> None:
        return None

    def _token(self, ctx: CollectContext) -> Optional[str]:
        return ctx.access_token or ctx.api_key


class AhrefsProvider(_KeyOrOAuthProvider):
    provider_id = "ahrefs"
    display_name = "Ahrefs"
    auth_mode = "oauth"
    collection_tier = "ADVANCED"
    scopes = ["site-explorer"]
    api_setting = "AHREFS_API_KEY"
    client_setting = "AHREFS_CLIENT_ID"
    secret_setting = "AHREFS_CLIENT_SECRET"
    enabled_setting = "AHREFS_ENABLED"
    authorize_setting = "AHREFS_AUTHORIZE_URL"
    token_setting = "AHREFS_TOKEN_URL"
    redirect_setting = "AHREFS_REDIRECT_URI"
    capabilities = ProviderCapabilities(backlinks=True, referring_domains=True, competitors=True)

    def current_auth_mode(self) -> str:
        return "oauth" if self.oauth_application_ready() else "api_key"

    def _probe_key(self, transport, api_key: str) -> None:
        response = transport.request(
            "GET",
            "https://api.ahrefs.com/v3/site-explorer/domain-rating",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            params={"target": "ahrefs.com", "date": utcnow().date().isoformat()},
        )
        if response.status_code in (401, 403):
            raise ProviderAuthError("Ahrefs rejected this API key.")

    def collect(self, ctx: CollectContext) -> CollectionResult:
        token = self._token(ctx)
        if not token:
            return not_connected(self.provider_id, "Ahrefs is not connected.")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        date = ctx.period_end or utcnow().date().isoformat()
        params = {"target": ctx.domain, "mode": "domain", "date": date, "limit": 100}
        result = CollectionResult(provider=self.provider_id, connection_status="CONNECTED")
        partial: List[str] = []
        stats = _get_json(ctx, "https://api.ahrefs.com/v3/site-explorer/backlinks-stats", headers, {"target": ctx.domain, "mode": "domain", "date": date})
        rating = _get_json(ctx, "https://api.ahrefs.com/v3/site-explorer/domain-rating", headers, {"target": ctx.domain, "date": date})
        links = _get_json(ctx, "https://api.ahrefs.com/v3/site-explorer/all-backlinks", headers, {**params, "select": "url_from,url_to,anchor,is_dofollow,first_seen,last_seen"})
        domains = _get_json(ctx, "https://api.ahrefs.com/v3/site-explorer/refdomains", headers, {**params, "select": "domain,backlinks,first_seen,last_seen,domain_rating"})
        for name, payload in (("backlinks-stats", stats), ("domain-rating", rating), ("all-backlinks", links), ("refdomains", domains)):
            if isinstance(payload, str):
                partial.append(f"{name}: {payload}")
                continue
            if isinstance(payload, dict):
                result.raw_payloads.append(RawPayload(endpoint=name, payload=strip_secrets(payload)))
        if isinstance(stats, dict):
            metrics = stats.get("metrics") or stats
            live = metrics.get("live") if isinstance(metrics.get("live"), dict) else metrics
            result.records.append(record(ctx, record_type="backlink", metric="backlinks", value=_num(live.get("live") or live.get("all_time") or live.get("backlinks")), unit="links", raw_ref="ahrefs.backlinks-stats"))
            result.records.append(record(ctx, record_type="referring_domain", metric="referring_domains", value=_num(live.get("live_refdomains") or live.get("refdomains")), unit="domains", raw_ref="ahrefs.backlinks-stats"))
        if isinstance(rating, dict):
            metrics = rating.get("domain_rating") or (rating.get("metrics") or {})
            value = metrics.get("domain_rating") if isinstance(metrics, dict) else metrics
            result.records.append(record(
                ctx, record_type="referring_domain", metric="domain_rating", value=_num(value), unit="ahrefs_domain_rating",
                metadata={"vendor_metric_label": vendor_metric_label("ahrefs", "domain_rating")},
                raw_ref="ahrefs.domain-rating",
            ))
        if isinstance(links, dict):
            for item in links.get("backlinks") or []:
                result.records.append(_backlink(ctx, "ahrefs", item.get("url_from"), item.get("url_to"), item.get("anchor"), _follow(item.get("is_dofollow")), item.get("first_seen"), item.get("last_seen"), "ahrefs.all-backlinks"))
        if isinstance(domains, dict):
            for item in domains.get("refdomains") or []:
                result.records.append(_refdomain(ctx, "ahrefs", item, "ahrefs.refdomains"))
        result.partial_errors = partial
        result.data_state = _state(result.records, partial)
        result.note = "Ahrefs Domain Rating is an Ahrefs metric. It is not a Google ranking metric."
        return result


class SemrushProvider(_KeyOrOAuthProvider):
    provider_id = "semrush"
    display_name = "Semrush"
    auth_mode = "api_key"
    collection_tier = "ADVANCED"
    scopes = ["backlinks"]
    api_setting = "SEMRUSH_API_KEY"
    client_setting = "SEMRUSH_CLIENT_ID"
    secret_setting = "SEMRUSH_CLIENT_SECRET"
    enabled_setting = "SEMRUSH_ENABLED"
    authorize_setting = "SEMRUSH_AUTHORIZE_URL"
    token_setting = "SEMRUSH_TOKEN_URL"
    redirect_setting = "SEMRUSH_REDIRECT_URI"
    capabilities = ProviderCapabilities(backlinks=True, referring_domains=True, competitors=True, serp=True)

    def current_auth_mode(self) -> str:
        return "oauth" if self.oauth_application_ready() else "api_key"

    def _probe_key(self, transport, api_key: str) -> None:
        response = transport.request("GET", "https://api.semrush.com/analytics/v1/", params={
            "type": "backlinks_overview", "target": "semrush.com", "target_type": "root_domain", "key": api_key,
        })
        if response.status_code in (401, 403) or response.text.upper().startswith("ERROR"):
            raise ProviderAuthError("Semrush rejected this API key.")

    def collect(self, ctx: CollectContext) -> CollectionResult:
        key = self._token(ctx)
        if not key:
            return not_connected(self.provider_id, "Semrush is not connected.")
        result = CollectionResult(provider=self.provider_id, connection_status="CONNECTED")
        partial: List[str] = []
        overview = _semrush_table(ctx, key, "backlinks_overview", ctx.domain)
        links = _semrush_table(ctx, key, "backlinks", ctx.domain, display_limit=100)
        domains = _semrush_table(ctx, key, "backlinks_refdomains", ctx.domain, display_limit=100)
        for name, payload in (("backlinks_overview", overview), ("backlinks", links), ("backlinks_refdomains", domains)):
            if isinstance(payload, str):
                partial.append(f"{name}: {payload}")
            elif payload:
                result.raw_payloads.append(RawPayload(endpoint=name, payload={"rows": payload}))
        if isinstance(overview, list) and overview:
            row = overview[0]
            result.records.append(record(ctx, record_type="backlink", metric="backlinks", value=_num(row.get("total") or row.get("backlinks")), unit="links", raw_ref="semrush.backlinks_overview"))
            result.records.append(record(ctx, record_type="referring_domain", metric="referring_domains", value=_num(row.get("domains_num") or row.get("domains")), unit="domains", raw_ref="semrush.backlinks_overview"))
            result.records.append(record(
                ctx, record_type="referring_domain", metric="authority_score", value=_num(row.get("ascore") or row.get("authority_score")),
                unit="semrush_authority_score", metadata={"vendor_metric_label": vendor_metric_label("semrush", "authority_score")},
                raw_ref="semrush.backlinks_overview",
            ))
            if row.get("follows_num") is not None:
                result.records.append(record(ctx, record_type="backlink", metric="follow_links", value=_num(row.get("follows_num")), unit="links", raw_ref="semrush.backlinks_overview"))
            if row.get("nofollows_num") is not None:
                result.records.append(record(ctx, record_type="backlink", metric="nofollow_links", value=_num(row.get("nofollows_num")), unit="links", raw_ref="semrush.backlinks_overview"))
        if isinstance(links, list):
            for item in links:
                result.records.append(_backlink(ctx, "semrush", item.get("source_url") or item.get("url_from"), item.get("target_url") or item.get("url_to"), item.get("anchor"), _follow(item.get("nofollow") == "0" if "nofollow" in item else item.get("follow")), item.get("first_seen"), item.get("last_seen"), "semrush.backlinks"))
        if isinstance(domains, list):
            for item in domains:
                result.records.append(_refdomain(ctx, "semrush", item, "semrush.backlinks_refdomains"))
        result.partial_errors = partial
        result.data_state = _state(result.records, partial)
        result.note = "Semrush Authority Score is a Semrush metric. It is not a Google ranking metric."
        return result


class MajesticProvider(ExternalDataProvider):
    provider_id = "majestic"
    display_name = "Majestic"
    auth_mode = "api_key"
    collection_tier = "ADVANCED"
    scopes: List[str] = []
    capabilities = ProviderCapabilities(backlinks=True, referring_domains=True)

    def enabled(self) -> bool:
        from app.core.config import settings
        return bool(settings.MAJESTIC_ENABLED)

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        from app.core.config import settings
        if settings.MAJESTIC_API_KEY:
            return {"api_key": settings.MAJESTIC_API_KEY}
        return None

    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        response = transport.request("GET", "https://api.majestic.com/api/json", params={
            "app_api_key": secret.get("api_key"), "cmd": "GetIndexItemInfo", "items": 1, "item0": "majestic.com", "datasource": "fresh",
        })
        if response.status_code in (401, 403):
            raise ProviderAuthError("Majestic rejected this API key.")
        code = ""
        if isinstance(response.payload, dict):
            code = str(response.payload.get("Code") or "")
        if code and code not in {"OK", "0"}:
            raise ProviderAuthError("Majestic rejected this API key.")
        return {"api_key": secret.get("api_key")}

    def collect(self, ctx: CollectContext) -> CollectionResult:
        if not ctx.api_key:
            return not_connected(self.provider_id, "Majestic is not connected.")
        result = CollectionResult(provider=self.provider_id, connection_status="CONNECTED")
        partial: List[str] = []
        summary = _majestic(ctx, "GetIndexItemInfo", {"items": 1, "item0": ctx.domain, "datasource": "fresh"})
        links = _majestic(ctx, "GetBackLinkData", {"item": ctx.domain, "Count": 100, "datasource": "fresh", "Mode": 0})
        domains = _majestic(ctx, "GetRefDomains", {"item0": ctx.domain, "Count": 100, "datasource": "fresh"})
        for name, payload in (("GetIndexItemInfo", summary), ("GetBackLinkData", links), ("GetRefDomains", domains)):
            if isinstance(payload, str):
                partial.append(f"{name}: {payload}")
            elif isinstance(payload, dict):
                result.raw_payloads.append(RawPayload(endpoint=name, payload=strip_secrets(payload)))
        info = _majestic_rows(summary, "Results")
        if info:
            row = info[0]
            result.records.append(record(ctx, record_type="backlink", metric="backlinks", value=_num(row.get("ExtBackLinks") or row.get("BackLinks")), unit="links", raw_ref="majestic.GetIndexItemInfo"))
            result.records.append(record(ctx, record_type="referring_domain", metric="referring_domains", value=_num(row.get("RefDomains")), unit="domains", raw_ref="majestic.GetIndexItemInfo"))
            result.records.append(record(ctx, record_type="referring_domain", metric="trust_flow", value=_num(row.get("TrustFlow")), unit="majestic_trust_flow", metadata={"vendor_metric_label": vendor_metric_label("majestic", "trust_flow")}, raw_ref="majestic.GetIndexItemInfo"))
            result.records.append(record(ctx, record_type="referring_domain", metric="citation_flow", value=_num(row.get("CitationFlow")), unit="majestic_citation_flow", metadata={"vendor_metric_label": vendor_metric_label("majestic", "citation_flow")}, raw_ref="majestic.GetIndexItemInfo"))
        for item in _majestic_rows(links, "BackLinks"):
            result.records.append(_backlink(
                ctx, "majestic", item.get("SourceURL"), item.get("TargetURL"), item.get("AnchorText"),
                "nofollow" if str(item.get("FlagNoFollow")) == "1" else "follow",
                item.get("FirstIndexedDate"), item.get("LastSeenDate"), "majestic.GetBackLinkData",
            ))
        for item in _majestic_rows(domains, "RefDomains") or _majestic_rows(domains, "Results"):
            result.records.append(_refdomain(ctx, "majestic", {
                "domain": item.get("Domain") or item.get("RefDomain"),
                "backlinks": item.get("BackLinks") or item.get("MatchedLinks"),
                "first_seen": item.get("FirstSeen"),
                "last_seen": item.get("LastSeen"),
                "trust_flow": item.get("TrustFlow"),
                "citation_flow": item.get("CitationFlow"),
            }, "majestic.GetRefDomains"))
        result.partial_errors = partial
        result.data_state = _state(result.records, partial)
        result.note = "Majestic Trust Flow and Citation Flow are Majestic metrics. They are not Google ranking metrics."
        return result


def _get_json(ctx: CollectContext, url: str, headers: Dict[str, str], params: Dict[str, Any]):
    try:
        response = ctx.transport.request("GET", url, headers=headers, params=params)
    except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
        raise
    except Exception as exc:
        return str(exc)
    if response.status_code == 403:
        raise ProviderAuthError("Provider rejected the credential.")
    if response.status_code != 200 or not isinstance(response.payload, dict):
        return f"HTTP {response.status_code}"
    return response.payload


def _semrush_table(ctx: CollectContext, key: str, report: str, target: str, display_limit: Optional[int] = None):
    params: Dict[str, Any] = {"type": report, "target": target, "target_type": "root_domain", "key": key}
    if display_limit:
        params["display_limit"] = display_limit
    try:
        response = ctx.transport.request("GET", "https://api.semrush.com/analytics/v1/", params=params)
    except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
        raise
    except Exception as exc:
        return str(exc)
    text = response.text or ""
    if text.upper().startswith("ERROR"):
        return text.splitlines()[0][:200]
    if response.status_code != 200:
        return f"HTTP {response.status_code}"
    return _parse_semicolon(text)


def _parse_semicolon(text: str) -> List[Dict[str, str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    header = [item.strip() for item in lines[0].split(";")]
    rows = []
    for line in lines[1:]:
        cols = [item.strip() for item in line.split(";")]
        rows.append({header[index]: cols[index] if index < len(cols) else "" for index in range(len(header))})
    return rows


def _majestic(ctx: CollectContext, command: str, extra: Dict[str, Any]):
    params = {"app_api_key": ctx.api_key, "cmd": command, **extra}
    try:
        response = ctx.transport.request("GET", "https://api.majestic.com/api/json", params=params)
    except (ProviderAuthError, ProviderRateLimitError, ProviderTransientError):
        raise
    except Exception as exc:
        return str(exc)
    if response.status_code != 200 or not isinstance(response.payload, dict):
        return f"HTTP {response.status_code}"
    return response.payload


def _majestic_rows(payload: Any, table: str) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    tables = payload.get("DataTables") or {}
    block = tables.get(table) or {}
    data = block.get("Data") or []
    return [item for item in data if isinstance(item, dict)]


def _backlink(ctx, provider, source_url, target_url, anchor, rel, first_seen, last_seen, raw_ref):
    return record(
        ctx,
        record_type="backlink",
        metric="backlink",
        value_text=anchor,
        url=target_url,
        evidence_url=source_url,
        metadata={
            "source_url": source_url,
            "target_url": target_url,
            "anchor": anchor,
            "rel": rel,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "provider": provider,
        },
        raw_ref=raw_ref,
        source=provider,
    )


def _refdomain(ctx, provider, item: Dict[str, Any], raw_ref: str):
    domain = item.get("domain") or item.get("Domain")
    meta = {
        "linking_pages": item.get("backlinks") or item.get("links"),
        "first_seen": item.get("first_seen"),
        "last_seen": item.get("last_seen"),
        "provider": provider,
    }
    for metric in ("domain_rating", "trust_flow", "citation_flow"):
        if item.get(metric) is not None:
            meta[metric] = item.get(metric)
            label = vendor_metric_label(provider, metric)
            if label:
                meta["vendor_metric_label"] = label
    return record(
        ctx,
        record_type="referring_domain",
        metric="referring_domain",
        value=_num(item.get("backlinks")),
        value_text=domain,
        unit="linking_pages",
        url=domain,
        metadata=meta,
        raw_ref=raw_ref,
        source=provider,
    )


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _state(records: list, partial: list) -> str:
    if records and partial:
        return "PARTIALLY_MEASURED"
    if records:
        return "MEASURED"
    return "UNAVAILABLE"
