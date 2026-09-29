"""External authority stays measured, encrypted, and fail-open."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.enums import BusinessIntent, Category, Severity
from app.domain.models import BusinessProfile, Finding
from app.evidence.store import EvidenceStore
from app.external_authority.audit_bridge import build_audit_attachment
from app.external_authority.crypto import EncryptionKeyMissing
from app.external_authority.http import HttpResponse, ProviderAuthError, ProviderRateLimitError
from app.external_authority.models import ExternalRecord, isoformat
from app.external_authority.service import ExternalAuthorityService, reset_service
from app.external_authority.store import ExternalStore
from app.scoring.engine import ScoringEngine

FIXED = datetime(2026, 9, 29, tzinfo=timezone.utc)
PROJECT = "org_test"
DOMAIN = "example.com"
SECRET_KEY = "unit-test-external-key"
API_KEY = "super-secret-ahrefs-key"


class ScriptedTransport:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def request(self, method, url, headers=None, params=None, json_body=None, data=None, auth=None, timeout=None):
        self.calls.append((method, url, json_body, params))
        result = self.handler(method, url, json_body, params, data)
        if isinstance(result, Exception):
            raise result
        return result


def _blank_provider_env(monkeypatch):
    for name in (
        "AHREFS_API_KEY",
        "AHREFS_CLIENT_ID",
        "AHREFS_CLIENT_SECRET",
        "SEMRUSH_API_KEY",
        "SEMRUSH_CLIENT_ID",
        "SEMRUSH_CLIENT_SECRET",
        "MAJESTIC_API_KEY",
        "SERPAPI_KEY",
        "BRAND_MENTIONS_API_KEY",
        "BRAND_MENTIONS_BASE_URL",
        "CITATIONS_API_KEY",
        "CITATIONS_BASE_URL",
        "BING_OAUTH_CLIENT_ID",
        "BING_OAUTH_CLIENT_SECRET",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
    ):
        monkeypatch.setattr(settings, name, None)
    monkeypatch.setattr(settings, "DATAFORSEO_ENABLED", False)
    monkeypatch.setattr(settings, "SERPAPI_ENABLED", False)
    monkeypatch.setattr(settings, "BRAND_MENTIONS_ENABLED", False)
    monkeypatch.setattr(settings, "BRAND_MENTIONS_SENTIMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CITATIONS_ENABLED", False)
    monkeypatch.setattr(settings, "GSC_ENABLED", True)
    monkeypatch.setattr(settings, "GA4_ENABLED", True)
    monkeypatch.setattr(settings, "GBP_ENABLED", True)
    monkeypatch.setattr(settings, "AHREFS_ENABLED", True)
    monkeypatch.setattr(settings, "EXTERNAL_INTEGRATION_ENCRYPTION_KEY", SECRET_KEY)
    monkeypatch.setattr(settings, "OAUTH_DEBUG_LOG_TOKENS", True)


def _service(tmp_path, handler=None, when=FIXED):
    store = ExternalStore(str(tmp_path / "external.db"))
    transport = ScriptedTransport(handler or (lambda *args: HttpResponse(404, None, "missing", {})))
    clock = {"now": when}

    def current():
        return clock["now"]

    service = ExternalAuthorityService(store, transport, clock=current)
    service._clock_box = clock  # type: ignore[attr-defined]
    return service, transport


def _install(monkeypatch, service):
    import app.external_authority.service as module
    monkeypatch.setattr(module, "_SERVICE", service)


def _connect_token(service, provider, token="ya29.test-token"):
    service.store.upsert_connection(
        {
            "project_id": PROJECT,
            "provider": provider,
            "status": "CONNECTED",
            "auth_mode": "oauth",
            "token_status": "valid",
            "credential_source": "account",
        },
        secret={"access_token": token, "refresh_token": "refresh-secret"},
    )


def _ok(payload, text=None):
    return HttpResponse(200, payload, text if text is not None else "", {})


@pytest.fixture
def env(tmp_path, monkeypatch):
    _blank_provider_env(monkeypatch)
    monkeypatch.setattr(settings, "EXTERNAL_AUTHORITY_DB_PATH", str(tmp_path / "external.db"))
    reset_service()
    yield
    reset_service()


def test_zero_providers_are_coverage_gaps_not_failures(env, tmp_path, monkeypatch):
    service, _transport = _service(tmp_path)
    _install(monkeypatch, service)
    report = service.report(PROJECT, DOMAIN, 28)
    blob = str(report)
    assert report["universal_authority_score"] is None
    assert "poor" not in blob.lower()
    assert "low authority" not in blob.lower()
    states = {row["provider"]: row["data_state"] for row in report["coverage"]}
    assert states["google_search_console"] == "NOT_CONNECTED"
    assert states["ahrefs"] == "NOT_CONNECTED"
    assert any("could not be measured" in item["title"] for item in report["findings"])
    attachment = build_audit_attachment(project_id=PROJECT, domain=DOMAIN, evidence_store=EvidenceStore("run_test"))
    assert attachment["domain_findings"] == []
    assert attachment["report"]["universal_authority_score"] is None


def test_gsc_decline_does_not_invent_deindexing(env, tmp_path):
    def handler(method, url, body, params, data):
        if method == "GET" and url.endswith("/sites"):
            return _ok({"siteEntry": [{"siteUrl": "sc-domain:example.com", "permissionLevel": "siteOwner"}]})
        if "searchAnalytics/query" in url:
            if body and body.get("dimensions") == ["query"]:
                return _ok({"rows": [
                    {"keys": ["example shoes"], "clicks": 4, "impressions": 500, "ctr": 0.008, "position": 14},
                    {"keys": ["other query"], "clicks": 10, "impressions": 40, "ctr": 0.25, "position": 2},
                ]})
            if not body or not body.get("dimensions"):
                clicks = 66 if body.get("startDate") == "2026-09-01" else 100
                return _ok({"rows": [{"clicks": clicks, "impressions": 1000, "ctr": 0.066, "position": 11}]})
            return _ok({"rows": []})
        if url.endswith("/sitemaps"):
            return _ok({"sitemap": [{"path": "https://example.com/sitemap.xml", "errors": 0, "warnings": 0}]})
        return HttpResponse(404, None, "missing", {})

    service, _transport = _service(tmp_path, handler)
    _connect_token(service, "google_search_console")
    outcome = service.collect_provider(PROJECT, "google_search_console", "https://www.example.com/path", 28)
    assert outcome["data_state"] == "MEASURED"
    report = service.report(PROJECT, DOMAIN, 28)
    titles = " ".join(item["title"] for item in report["findings"])
    assert "declined 34%" in titles
    assert "deindexed" not in titles.lower()
    assert any("not treated as deindexed" in note for note in report["notes"])
    assert any(item["evidence_basis"] == "UNVERIFIED" and "brand" in item["title"].lower() for item in report["findings"])
    assert report["sections"]["search_performance"]["organic_clicks"] == 66


def test_gsc_empty_dataset_is_measured_zero(env, tmp_path):
    def handler(method, url, body, params, data):
        if method == "GET" and url.endswith("/sites"):
            return _ok({"siteEntry": [{"siteUrl": "sc-domain:example.com"}]})
        if "searchAnalytics/query" in url:
            return _ok({"rows": []})
        if url.endswith("/sitemaps"):
            return _ok({"sitemap": []})
        return HttpResponse(404, None, "missing", {})

    service, _transport = _service(tmp_path, handler)
    _connect_token(service, "google_search_console")
    outcome = service.collect_provider(PROJECT, "google_search_console", DOMAIN, 28)
    assert outcome["data_state"] == "MEASURED"
    report = service.report(PROJECT, DOMAIN, 28)
    assert report["sections"]["search_performance"]["organic_clicks"] == 0
    assert "poor" not in str(report).lower()


def test_gsc_partial_dimension_does_not_fail_totals(env, tmp_path):
    def handler(method, url, body, params, data):
        if method == "GET" and url.endswith("/sites"):
            return _ok({"siteEntry": [{"siteUrl": "sc-domain:example.com"}]})
        if "searchAnalytics/query" in url and body and body.get("dimensions") == ["query"]:
            return HttpResponse(400, {"error": "dimension"}, "dimension unavailable", {})
        if "searchAnalytics/query" in url:
            return _ok({"rows": [{"clicks": 10, "impressions": 20, "ctr": 0.5, "position": 4}]})
        if url.endswith("/sitemaps"):
            return _ok({"sitemap": []})
        return HttpResponse(404, None, "missing", {})

    service, _transport = _service(tmp_path, handler)
    _connect_token(service, "google_search_console")
    outcome = service.collect_provider(PROJECT, "google_search_console", DOMAIN, 28)
    assert outcome["data_state"] == "PARTIALLY_MEASURED"
    assert outcome["partial_errors"]


def test_ga4_is_analytics_not_rankings(env, tmp_path):
    def handler(method, url, body, params, data):
        if "accountSummaries" in url:
            return _ok({"accountSummaries": [{"account": "accounts/1", "displayName": "Example", "propertySummaries": [{"property": "properties/123", "displayName": "example.com"}]}]})
        start = (body or {}).get("dateRanges", [{}])[0].get("startDate")
        sessions = "80" if start == "2026-09-01" else "40"
        conversions = "2"
        return _ok({
            "metricHeaders": [
                {"name": "totalUsers"}, {"name": "sessions"}, {"name": "engagementRate"},
                {"name": "conversions"}, {"name": "totalRevenue"},
            ],
            "rows": [{
                "dimensionValues": [{"value": "/pricing" if body and body.get("dimensions") else "Organic Search"}],
                "metricValues": [{"value": "70"}, {"value": sessions}, {"value": "0.2"}, {"value": conversions}, {"value": "0"}],
            }],
        })

    service, _transport = _service(tmp_path, handler)
    _connect_token(service, "google_analytics_4")
    outcome = service.collect_provider(PROJECT, "google_analytics_4", DOMAIN, 28)
    assert outcome["data_state"] == "MEASURED"
    report = service.report(PROJECT, DOMAIN, 28)
    text = str(report["findings"])
    assert "not rankings" in report["sections"]["analytics"]["note"]
    assert "grew without a matching increase" in text
    assert "backlink authority" not in " ".join(item["title"] for item in report["findings"] if item["provider"] == "google_analytics_4").lower()


def test_bing_json_api_and_labeled_link_count(env, tmp_path):
    def handler(method, url, body, params, data):
        if url.endswith("/GetUserSites"):
            return _ok({"d": [{"Url": "https://example.com/"}]})
        if url.endswith("/GetRankAndTrafficStats"):
            return _ok({"d": [{"Clicks": 12, "Impressions": 90}]})
        if url.endswith("/GetQueryStats"):
            return _ok({"d": [{"Query": "example", "Clicks": 3, "Impressions": 20}]})
        if url.endswith("/GetCrawlStats"):
            return _ok({"d": [{"CrawledPages": 8, "CrawlErrors": 1}]})
        if url.endswith("/GetLinkCounts"):
            return _ok({"d": [{"InboundLinkCount": 15}]})
        return HttpResponse(404, None, "missing", {})

    service, transport = _service(tmp_path, handler)
    _connect_token(service, "bing_webmaster")
    outcome = service.collect_provider(PROJECT, "bing_webmaster", DOMAIN, 28)
    assert outcome["data_state"] == "MEASURED"
    assert all("api.svc/json" in call[1] for call in transport.calls)
    report = service.report(PROJECT, DOMAIN, 28)
    assert report["sections"]["search_performance"]["bing_clicks"] == 12
    assert any(item.get("vendor_metric_label") == "Bing Webmaster link count" for item in report["findings"])


def test_backlink_vendors_keep_their_names_and_do_not_combine(env, tmp_path):
    service, _transport = _service(tmp_path)
    now = isoformat(FIXED)
    service.save_competitors(PROJECT, [{"name": "Competitor A", "domain": "https://competitor.example"}])
    snapshots = {
        "ahrefs": [
            ExternalRecord(record_id="rec_refs", record_type="referring_domain", project_id=PROJECT, provider="ahrefs", source="ahrefs", domain=DOMAIN, metric="referring_domains", value=184, collected_at=now, metadata={"comparison": "current"}),
            ExternalRecord(record_id="rec_dr", record_type="referring_domain", project_id=PROJECT, provider="ahrefs", source="ahrefs", domain=DOMAIN, metric="domain_rating", value=42, collected_at=now, metadata={"comparison": "current"}),
            ExternalRecord(record_id="rec_lost", record_type="referring_domain", project_id=PROJECT, provider="ahrefs", source="ahrefs", domain=DOMAIN, metric="lost_referring_domains", value=42, collected_at=now, metadata={"comparison": "current"}),
        ],
        "semrush": [
            ExternalRecord(record_id="rec_sem", record_type="referring_domain", project_id=PROJECT, provider="semrush", source="semrush", domain=DOMAIN, metric="authority_score", value=38, collected_at=now, metadata={"comparison": "current"}),
        ],
        "majestic": [
            ExternalRecord(record_id="rec_maj", record_type="referring_domain", project_id=PROJECT, provider="majestic", source="majestic", domain=DOMAIN, metric="trust_flow", value=27, collected_at=now, metadata={"comparison": "current"}),
        ],
    }
    for provider, records in snapshots.items():
        service.store.upsert_connection({"project_id": PROJECT, "provider": provider, "status": "CONNECTED", "auth_mode": "api_key", "token_status": "valid"}, secret=None)
        service.store.save_snapshot(
            project_id=PROJECT,
            provider=provider,
            domain=DOMAIN,
            period_days=28,
            period_start="2026-09-01",
            period_end="2026-09-29",
            data_state="MEASURED",
            summary={"totals": {row.metric: row.value for row in records}},
            idempotency_key=f"{PROJECT}|{provider}|{DOMAIN}|28|2026-09-29|default",
            records=records,
            raw_payloads=[],
            collected_at=now,
        )
    service.store.save_snapshot(
        project_id=PROJECT,
        provider="ahrefs",
        domain="competitor.example",
        period_days=28,
        period_start="2026-09-01",
        period_end="2026-09-29",
        data_state="MEASURED",
        summary={"totals": {"referring_domains": 421}},
        idempotency_key=f"{PROJECT}|ahrefs|competitor.example|28|2026-09-29|default",
        records=[ExternalRecord(record_id="rec_comp", record_type="referring_domain", project_id=PROJECT, provider="ahrefs", source="ahrefs", domain="competitor.example", metric="referring_domains", value=421, collected_at=now, metadata={"comparison": "current"})],
        raw_payloads=[],
        collected_at=now,
    )
    report = service.report(PROJECT, DOMAIN, 28)
    titles = " ".join(item["title"] for item in report["findings"])
    assert report["universal_authority_score"] is None
    assert "Ahrefs Domain Rating" in titles
    assert "Semrush Authority Score" in titles
    assert "Majestic Trust Flow" in titles
    assert "42 lost referring domains" in titles
    assert "Our domain has 184 referring domains while Competitor A has 421" in titles
    assert "does not say which domain is better" in titles
    assert "universal" not in titles.lower()


def test_tokens_are_encrypted_and_absent_from_reports(env, tmp_path):
    service, transport = _service(tmp_path, lambda *args: _ok({"domain_rating": 1}))
    service.connect_api_key(PROJECT, "ahrefs", {"api_key": API_KEY}, DOMAIN)
    cipher = service.store.ciphertext_for(PROJECT, "ahrefs")
    assert cipher
    assert API_KEY not in cipher
    assert "access_token" not in str(service.health(PROJECT))
    assert API_KEY not in str(service.report(PROJECT, DOMAIN, 28))
    service.disconnect(PROJECT, "ahrefs")
    assert service.store.ciphertext_for(PROJECT, "ahrefs") is None
    assert transport.calls


def test_rate_limit_retries_and_auth_failure_is_isolated(env, tmp_path):
    state = {"limited": True}

    def handler(method, url, body, params, data):
        if "ahrefs.com" in url and state["limited"]:
            raise ProviderRateLimitError("slow down", retry_after=2)
        if "ahrefs.com" in url:
            return _ok({"metrics": {"live": {"live": 3, "live_refdomains": 4}}, "domain_rating": {"domain_rating": 10}, "backlinks": [], "refdomains": []})
        return HttpResponse(404, None, "missing", {})

    service, _transport = _service(tmp_path, handler)
    state["limited"] = False
    service.connect_api_key(PROJECT, "ahrefs", {"api_key": API_KEY}, DOMAIN)
    state["limited"] = True
    jobs = service.enqueue(PROJECT, DOMAIN, ["sync_backlinks"], [28])
    first = service.run_due_jobs()
    assert first[0]["status"] == "queued"
    state["limited"] = False
    service._clock_box["now"] = FIXED + timedelta(seconds=10)  # type: ignore[attr-defined]
    second = service.run_due_jobs()
    assert second[0]["status"] == "succeeded"
    assert jobs

    def deny(method, url, body, params, data):
        if "ahrefs.com" in url:
            raise ProviderAuthError("expired")
        return HttpResponse(404, None, "missing", {})

    service.transport.handler = deny
    service.store.upsert_connection({"project_id": PROJECT, "provider": "ahrefs", "status": "CONNECTED", "auth_mode": "api_key", "token_status": "valid"}, secret={"api_key": API_KEY})
    service.enqueue(PROJECT, DOMAIN, ["sync_backlinks"], [7], force=True)
    outcome = service.run_due_jobs()
    assert outcome[0]["status"] == "partial"
    health = {row["provider_id"]: row for row in service.health(PROJECT)}
    assert health["ahrefs"]["token_status"] == "expired"
    assert health["semrush"]["connection_status"] == "NOT_CONNECTED"


def test_cache_skips_repeat_collection(env, tmp_path):
    def handler(method, url, body, params, data):
        if url.endswith("/sites"):
            return _ok({"siteEntry": [{"siteUrl": "sc-domain:example.com"}]})
        if "searchAnalytics" in url:
            return _ok({"rows": [{"clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3}]})
        if url.endswith("/sitemaps"):
            return _ok({"sitemap": []})
        return HttpResponse(404, None, "missing", {})

    service, transport = _service(tmp_path, handler)
    _connect_token(service, "google_search_console")
    first = service.collect_provider(PROJECT, "google_search_console", DOMAIN, 28)
    calls = len(transport.calls)
    second = service.collect_provider(PROJECT, "google_search_console", DOMAIN, 28)
    assert first["cached"] is False
    assert second["cached"] is True
    assert len(transport.calls) == calls


def test_historical_periods_and_trends(env, tmp_path):
    clicks = {"value": 100}

    def handler(method, url, body, params, data):
        if url.endswith("/sites"):
            return _ok({"siteEntry": [{"siteUrl": "sc-domain:example.com"}]})
        if "searchAnalytics" in url and (not body or not body.get("dimensions")):
            return _ok({"rows": [{"clicks": clicks["value"], "impressions": 10, "ctr": 0.1, "position": 5}]})
        if "searchAnalytics" in url:
            return _ok({"rows": []})
        if url.endswith("/sitemaps"):
            return _ok({"sitemap": []})
        return HttpResponse(404, None, "missing", {})

    service, _transport = _service(tmp_path, handler)
    _connect_token(service, "google_search_console")
    created = service.enqueue(PROJECT, DOMAIN, ["sync_gsc_data"], [7, 28, 90, 365])
    assert len(created) == 4
    again = service.enqueue(PROJECT, DOMAIN, ["sync_gsc_data"], [7, 28, 90, 365])
    assert [job["job_id"] for job in again] == [job["job_id"] for job in created]
    service.collect_provider(PROJECT, "google_search_console", DOMAIN, 28, force=True)
    clicks["value"] = 140
    service._clock_box["now"] = FIXED + timedelta(days=40)  # type: ignore[attr-defined]
    service.collect_provider(PROJECT, "google_search_console", DOMAIN, 28, force=True)
    report = service.report(PROJECT, DOMAIN, 28)
    assert any(item["direction"] == "growth" and item["metric"] == "clicks" for item in report["trends"])


def test_gbp_not_applicable_and_citation_nap(env, tmp_path, monkeypatch):
    service, transport = _service(tmp_path)
    service.save_local_business(PROJECT, {"applicability": "NON_LOCAL_BUSINESS", "name": "Example", "expected_directories": []})
    outcome = service.collect_provider(PROJECT, "google_business_profile", DOMAIN, 28)
    assert outcome["data_state"] == "NOT_APPLICABLE"
    assert transport.calls == []
    report = service.report(PROJECT, DOMAIN, 28)
    gbp = next(row for row in report["coverage"] if row["provider"] == "google_business_profile")
    assert gbp["data_state"] == "NOT_APPLICABLE"
    assert any("not an SEO failure" in item["title"] for item in report["findings"])
    kg = next(item for item in report["entity_signals"] if item["signal"] == "knowledge_graph_reference")
    assert kg["status"] == "UNKNOWN"
    assert "not measured" in kg["detail"]

    monkeypatch.setattr(settings, "CITATIONS_ENABLED", True)
    monkeypatch.setattr(settings, "CITATIONS_PROVIDER", "directories")
    monkeypatch.setattr(settings, "CITATIONS_BASE_URL", "https://citations.test")
    monkeypatch.setattr(settings, "BRAND_MENTIONS_ENABLED", True)
    monkeypatch.setattr(settings, "BRAND_MENTIONS_PROVIDER", "mentions")
    monkeypatch.setattr(settings, "BRAND_MENTIONS_BASE_URL", "https://mentions.test")

    def handler(method, url, body, params, data):
        if url.endswith("/listings"):
            return _ok({"listings": [
                {"name": "Example", "address": "1 Main", "phone": "555-0100", "website": "https://example.com", "category": "Cafe", "listing_url": "https://directory.test/a", "source": "directory.test"},
                {"name": "Example", "address": "1 Main", "phone": "555-0199", "website": "https://example.com", "category": "Cafe", "listing_url": "https://directory.test/b", "source": "directory.test"},
            ]})
        if url.endswith("/mentions"):
            return _ok({"mentions": [
                {"url": "https://news.test/story", "domain": "news.test", "mention_class": "LINKED", "target_url": "https://example.com/about", "snippet": "Example launched"},
                {"url": "https://blog.test/note", "domain": "blog.test", "mention_class": "UNLINKED", "snippet": "Example was mentioned"},
            ]})
        return HttpResponse(404, None, "missing", {})

    service.transport.handler = handler
    service.save_local_business(PROJECT, {
        "applicability": "LOCAL_BUSINESS",
        "name": "Example",
        "address": "1 Main",
        "phone": "555-0100",
        "website": "https://example.com",
        "category": "Cafe",
        "expected_directories": ["missing.directory"],
    })
    service.connect_api_key(PROJECT, "citations", {"api_key": "citation-key"}, DOMAIN)
    service.connect_api_key(PROJECT, "brand_mentions", {"api_key": "mention-key"}, DOMAIN)
    service.save_brand(PROJECT, "Example", [])
    assert service.collect_provider(PROJECT, "citations", DOMAIN, 28)["data_state"] == "MEASURED"
    assert service.collect_provider(PROJECT, "brand_mentions", DOMAIN, 28)["data_state"] == "MEASURED"
    report = service.report(PROJECT, DOMAIN, 28)
    titles = " ".join(item["title"] for item in report["findings"])
    assert "differ from the configured business profile" in titles
    assert "missing.directory" in str(report["citation_summary"]["missing_listings"])
    assert report["sections"]["brand_mentions"]["linked"] == 1
    assert report["sections"]["brand_mentions"]["unlinked"] == 1
    assert "sentiment" not in str(report["sections"]["brand_mentions"]).lower()
    assert "citation-key" not in str(report)
    assert "mention-key" not in str(report)


def test_missing_encryption_key_refuses_plaintext(env, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXTERNAL_INTEGRATION_ENCRYPTION_KEY", None)
    service, _transport = _service(tmp_path)
    with pytest.raises(EncryptionKeyMissing):
        service.connect_api_key(PROJECT, "majestic", {"api_key": API_KEY}, DOMAIN)


def test_external_category_does_not_change_the_composite_score(env):
    profile = BusinessProfile(business_name="Example", primary_intent=BusinessIntent.LEAD_GENERATION)
    base = [Finding(
        finding_id="f1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing title",
        description="The homepage title is empty.",
        recommendation="Add a title.",
    )]
    extra = base + [Finding(
        finding_id="f2",
        category=Category.EXTERNAL_AUTHORITY,
        severity=Severity.HIGH,
        title="Organic search clicks declined 34% over the selected comparison period.",
        description="Measured.",
        recommendation="Review the queries.",
    )]
    engine = ScoringEngine()
    assert engine.calculate_scores(base, profile).overall_score == engine.calculate_scores(extra, profile).overall_score


def test_http_api_hides_secrets_and_reports_not_connected(env, tmp_path, monkeypatch):
    service, _transport = _service(tmp_path)
    _install(monkeypatch, service)
    from app.main import app
    with TestClient(app) as client:
        report = client.get("/api/v1/external-authority/report", params={"domain": DOMAIN, "project_id": PROJECT})
        assert report.status_code == 200
        body = report.json()
        assert body["universal_authority_score"] is None
        assert any(row["data_state"] == "NOT_CONNECTED" for row in body["coverage"])
        health = client.get("/api/v1/external-authority/health", params={"project_id": PROJECT})
        assert health.status_code == 200
        assert "token_ciphertext" not in health.text
        monkeypatch.setattr(settings, "EXTERNAL_INTEGRATION_ENCRYPTION_KEY", None)
        denied = client.post("/api/v1/external-authority/connect", json={"provider": "majestic", "api_key": API_KEY, "project_id": PROJECT, "domain": DOMAIN})
        assert denied.status_code == 503
        assert API_KEY not in denied.text
