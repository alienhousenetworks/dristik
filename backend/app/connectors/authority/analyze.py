"""Findings and the external authority report.

Missing providers become coverage gaps. They do not become negative SEO
findings. Vendor metrics keep their vendor names. No universal score.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from app.connectors.authority.models import (
    PERIOD_LABELS,
    ExternalFinding,
    ExternalRecord,
    stable_id,
    vendor_metric_label,
)
from app.connectors.authority.registry import all_providers

GA4_NOTE = (
    "GA4 attributes sessions with its own channel grouping. "
    "These figures are analytics and behavior evidence, not rankings or backlink authority."
)
NOT_DEINDEXED = (
    "A page that does not appear in this Search Analytics sample is not treated as deindexed."
)


def build_report(
    *,
    project_id: str,
    domain: str,
    period_days: int,
    connections: List[Dict[str, Any]],
    snapshots: Dict[str, Dict[str, Any]],
    records_by_provider: Dict[str, List[ExternalRecord]],
    history: List[Dict[str, Any]],
    brand: Dict[str, Any],
    competitors: List[Dict[str, Any]],
    local_profile: Dict[str, Any],
    crawl_observations: Optional[Dict[str, Any]] = None,
    competitor_records: Optional[Dict[str, List[ExternalRecord]]] = None,
) -> Dict[str, Any]:
    applicability = (local_profile or {}).get("applicability") or "UNKNOWN"
    coverage = coverage_matrix(connections, snapshots, applicability)
    own_records = [record for rows in records_by_provider.values() for record in rows]
    findings: List[ExternalFinding] = []
    findings.extend(_search_findings(project_id, domain, period_days, own_records, brand))
    findings.extend(_analytics_findings(project_id, domain, period_days, own_records))
    findings.extend(_backlink_findings(project_id, domain, period_days, own_records, coverage))
    findings.extend(_mention_findings(project_id, domain, period_days, own_records, coverage))
    findings.extend(_local_findings(project_id, domain, period_days, own_records, coverage, applicability))
    citation = _citation_summary(own_records, local_profile)
    findings.extend(citation["findings"])
    entity = _entity_signals(project_id, domain, own_records, crawl_observations or {}, coverage, local_profile)
    competitor_section = _competitor_section(
        project_id, domain, period_days, own_records, competitors, competitor_records or {}, coverage,
    )
    findings.extend(competitor_section["findings"])
    sections = _sections(own_records, citation, entity, competitor_section, coverage)
    pillars = _pillars(coverage, sections)
    return {
        "title": "External Authority & Entity Intelligence",
        "project_id": project_id,
        "domain": domain,
        "period_days": period_days,
        "period_label": PERIOD_LABELS.get(period_days, f"{period_days} days"),
        "universal_authority_score": None,
        "score_note": "Dristik does not calculate a universal authority score. Vendor metrics are shown with the vendor's name.",
        "coverage": coverage,
        "pillars": pillars,
        "sections": sections,
        "findings": [item.model_dump() for item in findings],
        "entity_signals": entity,
        "citation_summary": citation["summary"],
        "competitor_gap": competitor_section["gaps"],
        "trends": _trends(history),
        "data_sources": _audit_sources(coverage),
        "notes": [
            NOT_DEINDEXED,
            "Crawl depth does not limit this pillar. External metrics appear only when a provider returned them.",
        ],
    }


def coverage_matrix(connections: List[Dict[str, Any]], snapshots: Dict[str, Dict[str, Any]], applicability: str) -> List[Dict[str, Any]]:
    by_provider = {row["provider"]: row for row in connections}
    matrix = []
    for provider in all_providers():
        if not provider.enabled():
            matrix.append({
                "provider": provider.provider_id,
                "display_name": provider.display_name,
                "connection_status": "NOT_CONNECTED",
                "data_state": "NOT_CONNECTED",
                "capabilities": provider.capabilities.model_dump(),
                "auth_mode": provider.current_auth_mode(),
                "tier": provider.collection_tier,
                "note": "This provider is disabled in the environment.",
            })
            continue
        if provider.provider_id == "google_business_profile" and applicability == "NON_LOCAL_BUSINESS":
            matrix.append(_coverage_row(provider, "NOT_APPLICABLE", "NOT_APPLICABLE", None, "Not applicable for a non-local business. This is not an SEO failure."))
            continue
        connection = by_provider.get(provider.provider_id)
        snapshot = snapshots.get(provider.provider_id)
        app_ready = bool(provider.application_credentials()) or provider.oauth_application_ready()
        if connection and connection.get("status") == "CONNECTED":
            connection_status = "CONNECTED"
        elif provider.application_credentials():
            connection_status = "CONNECTED"
        else:
            connection_status = "NOT_CONNECTED"
        if connection_status != "CONNECTED":
            data_state = "NOT_CONNECTED"
            note = "Not connected."
            if provider.provider_id == "google_business_profile" and applicability == "UNKNOWN":
                note = "Applicability is unknown and Google Business Profile is not connected. This is not an SEO failure."
        elif not snapshot:
            data_state = "UNAVAILABLE"
            note = "Connected, but no snapshot has been collected for this period."
        else:
            data_state = snapshot.get("data_state") or "UNAVAILABLE"
            note = (snapshot.get("summary") or {}).get("note")
        matrix.append(_coverage_row(provider, connection_status, data_state, connection, note, app_ready))
    return matrix


def _coverage_row(provider, connection_status, data_state, connection, note, app_ready=False):
    return {
        "provider": provider.provider_id,
        "display_name": provider.display_name,
        "connection_status": connection_status,
        "data_state": data_state,
        "capabilities": provider.capabilities.model_dump(),
        "auth_mode": provider.current_auth_mode(),
        "tier": provider.collection_tier,
        "account": (connection or {}).get("account_label"),
        "property": (connection or {}).get("property_label") or (connection or {}).get("property_id"),
        "oauth_application_ready": provider.oauth_application_ready(),
        "application_credential_present": bool(provider.application_credentials()) or app_ready,
        "note": note,
    }


def _search_findings(project_id, domain, period_days, records, brand) -> List[ExternalFinding]:
    findings: List[ExternalFinding] = []
    current_clicks = _value(records, "clicks", "current", provider="google_search_console")
    previous_clicks = _value(records, "clicks", "previous", provider="google_search_console")
    impressions = _value(records, "impressions", "current", provider="google_search_console")
    ctr = _value(records, "ctr", "current", provider="google_search_console")
    position = _value(records, "average_position", "current", provider="google_search_console")
    period = _period(period_days, records, "google_search_console")
    if current_clicks is not None and previous_clicks not in (None, 0):
        change = (current_clicks - previous_clicks) / previous_clicks
        if change <= -0.20:
            findings.append(_finding(
                project_id, domain, "search_authority", "HIGH", "google_search_console", "DIRECT_PROVIDER_EVIDENCE",
                "clicks", current_clicks, previous_clicks, period, "PERIOD_VERIFIED",
                f"Organic search clicks declined {abs(change):.0%} over the selected comparison period.",
                f"Google Search Console measured {int(current_clicks)} clicks in this {PERIOD_LABELS.get(period_days)} window and {int(previous_clicks)} clicks in the previous window.",
                "Compare the two Search Analytics totals requests for the connected property.",
                "Review the queries and pages that lost clicks in this same window before changing titles or internal links.",
                "Organic clicks are lower than the previous comparison window.",
            ))
        elif change >= 0.20:
            findings.append(_finding(
                project_id, domain, "search_authority", "INFO", "google_search_console", "DIRECT_PROVIDER_EVIDENCE",
                "clicks", current_clicks, previous_clicks, period, "PERIOD_VERIFIED",
                f"Organic search clicks increased {change:.0%} over the selected comparison period.",
                f"Google Search Console measured {int(current_clicks)} clicks versus {int(previous_clicks)} in the previous window.",
                "Compare the two Search Analytics totals requests.",
                "Keep the pages and queries that gained clicks visible in the next report period.",
                "Organic clicks are higher than the previous comparison window.",
                data_state="MEASURED",
            ))
    terms = [item for item in [brand.get("name"), *(brand.get("aliases") or [])] if item]
    query_rows = _rows(records, "search_analytics_row", "query", "google_search_console")
    if query_rows and terms:
        branded = [row for row in query_rows if _branded(row.metadata.get("query"), terms)]
        branded_clicks = sum(float(row.metadata.get("clicks") or 0) for row in branded)
        other_clicks = sum(float(row.metadata.get("clicks") or 0) for row in query_rows) - branded_clicks
        findings.append(_finding(
            project_id, domain, "search_authority", "INFO", "google_search_console", "INFERRED",
            "branded_clicks", branded_clicks, None, period, "EXTERNAL_INFERRED",
            f"Among returned queries, {int(branded_clicks)} clicks matched configured brand terms and {int(other_clicks)} did not.",
            "Brand matching is a case-insensitive substring check against the configured brand name and aliases. It is not Google's branded-query classifier.",
            "Recompute the split from the stored query rows and the saved brand terms.",
            "Use the non-branded query list to see demand that does not already contain the brand.",
            "The split describes the returned query rows.",
            data_state="INFERRED",
        ))
    elif query_rows and not terms:
        findings.append(_finding(
            project_id, domain, "search_authority", "INFO", "google_search_console", "UNVERIFIED",
            "branded_clicks", None, None, period, "EXTERNAL_INFERRED",
            "Branded and non-branded queries were not split because no brand name or alias is configured.",
            "Dristik does not guess a brand from the domain name.",
            "Configure a brand name and aliases, then sync Search Console again.",
            "Add the public brand name and aliases in the integrations settings.",
            "The branded split is unmeasured.",
            data_state="UNVERIFIED",
        ))
    if query_rows and ctr:
        flagged = _low_ctr(query_rows, float(ctr))
        if flagged:
            findings.append(_finding(
                project_id, domain, "search_authority", "MEDIUM", "google_search_console", "INFERRED",
                "low_ctr_queries", len(flagged), None, period, "EXTERNAL_INFERRED",
                f"{len(flagged)} high-impression queries have CTR substantially below the site's comparable query baseline.",
                "The query clicks, impressions, and CTR are Search Console measurements. The baseline comparison is Dristik's rule: impressions at least 100 and at least the median, and CTR below half of the property CTR.",
                "Recompute the rule from the stored query rows and the totals CTR.",
                "Inspect the titles and descriptions of the listed queries before rewriting the pages.",
                "These queries receive impressions with a weaker click rate than the property baseline.",
                data_state="INFERRED",
            ))
    low_position = [
        row for row in query_rows
        if float(row.metadata.get("impressions") or 0) >= 100 and float(row.metadata.get("position") or 0) > 10
    ]
    if low_position:
        findings.append(_finding(
            project_id, domain, "search_authority", "MEDIUM", "google_search_console", "INFERRED",
            "high_impression_low_position_queries", len(low_position), None, period, "EXTERNAL_INFERRED",
            f"{len(low_position)} queries have at least 100 impressions and an average position worse than 10.",
            "Position and impressions are Search Console measurements. Calling them an opportunity is an inference, not a ranking promise.",
            "Read position and impressions from the stored query rows.",
            "Compare the ranking URL for each query with the page you want to rank.",
            "Visibility exists below the first page of results for these queries.",
            data_state="INFERRED",
        ))
    page_changes = _page_click_changes(records)
    if page_changes["lost"] or page_changes["gained"]:
        findings.append(_finding(
            project_id, domain, "search_authority", "MEDIUM", "google_search_console", "DIRECT_PROVIDER_EVIDENCE",
            "page_click_change", len(page_changes["lost"]), len(page_changes["gained"]), period, "PERIOD_VERIFIED",
            f"{len(page_changes['lost'])} pages lost organic clicks and {len(page_changes['gained'])} pages gained organic clicks between the two windows.",
            "Both windows come from Search Console page rows. A page absent from one sample is not included.",
            "Match page URLs across the current and previous page rows.",
            "Open the pages that lost clicks and compare their queries in the same window.",
            "Click movement is measurable for pages present in both samples.",
        ))
    cannibal = _cannibalization(records)
    if cannibal:
        findings.append(_finding(
            project_id, domain, "search_authority", "MEDIUM", "google_search_console", "INFERRED",
            "query_page_overlap", len(cannibal), None, period, "EXTERNAL_INFERRED",
            f"{len(cannibal)} queries have at least two URLs with 50 or more impressions in this sample.",
            "This can indicate competing URLs. It is not proof of a ranking penalty. " + NOT_DEINDEXED,
            "Group stored query-and-page rows by query.",
            "Choose one primary URL per query and align internal links toward it.",
            "More than one URL is visible for the same query in this sample.",
            data_state="INFERRED",
        ))
    inspections = [row for row in records if row.metric == "url_inspection" and row.provider == "google_search_console"]
    bad = [row for row in inspections if _inspection_failed(row)]
    if bad:
        findings.append(_finding(
            project_id, domain, "search_authority", "HIGH", "google_search_console", "DIRECT_PROVIDER_EVIDENCE",
            "url_inspection", len(bad), None, period, "PROVIDER_VERIFIED",
            f"URL Inspection returned a non-indexed verdict for {len(bad)} submitted URL(s).",
            "Only URLs sent to the URL Inspection API are included. " + NOT_DEINDEXED,
            "Read the stored coverage state from the URL Inspection response.",
            "Open the inspected URL in Search Console and follow the coverage reason Google returned.",
            "Google's inspection verdict says these URLs are not indexed.",
        ))
    if current_clicks is None and impressions is None and ctr is None and position is None:
        pass
    return findings


def _analytics_findings(project_id, domain, period_days, records) -> List[ExternalFinding]:
    findings = []
    sessions = _value(records, "organic_sessions", "current", provider="google_analytics_4")
    previous = _value(records, "organic_sessions", "previous", provider="google_analytics_4")
    conversions = _value(records, "organic_conversions", "current", provider="google_analytics_4")
    previous_conversions = _value(records, "organic_conversions", "previous", provider="google_analytics_4")
    period = _period(period_days, records, "google_analytics_4")
    if sessions is not None and previous not in (None, 0) and conversions is not None and previous_conversions is not None:
        session_change = (sessions - previous) / previous
        conversion_change = 0 if previous_conversions == 0 else (conversions - previous_conversions) / previous_conversions
        if session_change >= 0.15 and conversion_change <= 0.02:
            findings.append(_finding(
                project_id, domain, "search_authority", "MEDIUM", "google_analytics_4", "INFERRED",
                "organic_sessions", sessions, previous, period, "EXTERNAL_INFERRED",
                "Organic sessions grew without a matching increase in key events.",
                f"Sessions changed by {session_change:.0%} and key events changed by {conversion_change:.0%}. {GA4_NOTE}",
                "Compare the two GA4 organic totals rows.",
                "Check the landing pages that gained sessions and whether their key events are tagged.",
                "More organic sessions did not bring a matching key-event increase in this window.",
                data_state="INFERRED",
            ))
    pages = [row for row in records if row.metric == "organic_landing_page" and row.provider == "google_analytics_4" and row.metadata.get("comparison") == "current"]
    weak = []
    rates = []
    for row in pages:
        sessions_n = float(row.metadata.get("sessions") or row.value or 0)
        conversions_n = float(row.metadata.get("conversions") or 0)
        if sessions_n <= 0:
            continue
        rate = conversions_n / sessions_n
        rates.append(rate)
        if sessions_n >= 50:
            weak.append((row, rate, sessions_n))
    if weak and rates:
        ordered = sorted(rates)
        median = ordered[len(ordered) // 2]
        below = [item for item in weak if item[1] < median * 0.5]
        if below and median > 0:
            findings.append(_finding(
                project_id, domain, "search_authority", "MEDIUM", "google_analytics_4", "INFERRED",
                "landing_page_conversion", len(below), None, period, "EXTERNAL_INFERRED",
                f"{len(below)} organic landing pages have a key-event rate below half the median of measured landing pages.",
                GA4_NOTE + " The median comparison is Dristik's rule, not a GA4 benchmark.",
                "Divide key events by sessions on each stored landing-page row.",
                "Review the landing pages with sessions and few key events before changing their rankings.",
                "These pages receive organic sessions and convert below the site's own landing-page median.",
                data_state="INFERRED",
            ))
    gsc_pages = {row.url: row for row in _rows(records, "search_analytics_row", "page", "google_search_console") if row.url}
    joined = []
    for row in pages:
        match = gsc_pages.get(row.url)
        if not match:
            continue
        impressions = float(match.metadata.get("impressions") or 0)
        engagement = float(row.metadata.get("engagementRate") or 0)
        if impressions >= 100 and engagement < 0.4:
            joined.append(row.url)
    if joined:
        findings.append(_finding(
            project_id, domain, "search_authority", "MEDIUM", "google_analytics_4", "INFERRED",
            "impression_engagement", len(joined), None, period, "EXTERNAL_INFERRED",
            f"{len(joined)} URLs have Search Console impressions and GA4 organic engagement below 0.4.",
            "The impressions come from Search Console and the engagement rate comes from GA4. " + GA4_NOTE,
            "Join stored page rows on the URL.",
            "Read the page against the query that earned the impressions.",
            "The URL is visible in search and the organic sessions on it engage below 0.4.",
            data_state="INFERRED",
        ))
    total_revenue = 0.0
    revenue_pages = []
    for row in pages:
        rev = float(row.metadata.get("totalRevenue") or row.metadata.get("purchaseRevenue") or 0.0)
        if rev > 0:
            total_revenue += rev
            revenue_pages.append((row.url or row.metadata.get("page") or "Landing Page", rev))

    if total_revenue > 0:
        revenue_pages.sort(key=lambda x: x[1], reverse=True)
        top_page, top_rev = revenue_pages[0]
        share = top_rev / total_revenue
        findings.append(_finding(
            project_id, domain, "search_authority", "INFO", "google_analytics_4", "DIRECT_PROVIDER_EVIDENCE",
            "organic_revenue_impact", total_revenue, None, period, "PROVIDER_VERIFIED",
            f"Organic search generated an attributed {total_revenue:,.2f} in revenue across {len(revenue_pages)} landing page(s).",
            f"Top landing page '{top_page}' accounted for {share:.1%} ({top_rev:,.2f}) of all attributed organic search revenue. {GA4_NOTE}",
            "Sum stored landing-page revenue metrics from GA4.",
            "Prioritize technical SEO health and ranking protection for top revenue-generating landing pages.",
            f"Measured organic revenue impact is {total_revenue:,.2f}.",
            data_state="MEASURED",
        ))
    return findings


def _backlink_findings(project_id, domain, period_days, records, coverage) -> List[ExternalFinding]:
    findings = []
    providers = [row for row in coverage if row["capabilities"].get("backlinks") and row["provider"] != "bing_webmaster"]
    connected = [row for row in providers if row["data_state"] in {"MEASURED", "PARTIALLY_MEASURED", "INFERRED"}]
    period = {"days": period_days, "label": PERIOD_LABELS.get(period_days)}
    if not connected:
        findings.append(_finding(
            project_id, domain, "link_authority", "INFO", "backlinks", "UNVERIFIED",
            "referring_domains", None, None, period, "PROVIDER_VERIFIED",
            "Backlink authority could not be measured because no backlink data provider is connected.",
            "Ahrefs, Semrush, Majestic, and DataForSEO were not available for this period. This is a coverage gap, not a measurement of weak authority.",
            "Connect one backlink provider and collect a snapshot.",
            "Connect a backlink provider before drawing a conclusion about referring domains.",
            "No backlink provider returned data.",
            data_state="NOT_CONNECTED",
        ))
    else:
        findings.extend(_vendor_link_findings(project_id, domain, period_days, records, period))
    for row in records:
        if row.metric == "bing_link_count" and row.value is not None:
            findings.append(_finding(
                project_id, domain, "link_authority", "INFO", "bing_webmaster", "DIRECT_PROVIDER_EVIDENCE",
                "bing_link_count", row.value, None, period, "PROVIDER_VERIFIED",
                f"Bing Webmaster link count is {row.value:g}.",
                "This is Bing Webmaster's own link count. It is not Ahrefs Domain Rating, Semrush Authority Score, or Majestic Trust Flow.",
                "Read the stored bing_link_count record.",
                "Use a dedicated backlink provider when you need referring domains and anchor text.",
                "Bing reported this link count for the connected site.",
                vendor_metric_label="Bing Webmaster link count",
            ))
    return findings


def _vendor_link_findings(project_id, domain, period_days, records, period) -> List[ExternalFinding]:
    findings = []
    for row in records:
        if row.metric == "bing_link_count":
            continue
        label = vendor_metric_label(row.provider, row.metric)
        if not label or row.value is None:
            continue
        findings.append(_finding(
            project_id, domain, "link_authority", "INFO", row.provider, "DIRECT_PROVIDER_EVIDENCE",
            row.metric, row.value, None, _period(period_days, records, row.provider), "PROVIDER_VERIFIED",
            f"{label} is {row.value:g} for this domain in the {row.provider} dataset.",
            f"{label} is a {row.provider} metric. It is not a Google ranking factor and it is not combined with other vendors.",
            f"Read the stored {row.metric} record from {row.provider}.",
            "Use the underlying referring domains and links when deciding what to do.",
            f"{label} was returned by the provider.",
            vendor_metric_label=label,
        ))
    lost = [row for row in records if row.metric in {"lost_referring_domains", "lost_backlinks"} and row.value]
    for row in lost:
        if float(row.value or 0) <= 0:
            continue
        findings.append(_finding(
            project_id, domain, "link_authority", "MEDIUM" if float(row.value) >= 10 else "INFO", row.provider, "DIRECT_PROVIDER_EVIDENCE",
            row.metric, row.value, None, _period(period_days, records, row.provider), "PERIOD_VERIFIED",
            f"{int(row.value)} {row.metric.replace('_', ' ')} were reported by {row.provider} for the selected period.",
            "This count is the provider's lost-link figure. It is not inferred by comparing incomplete samples.",
            f"Read the {row.metric} field stored from {row.provider}.",
            "Export the provider's lost-link list and check which target URLs were affected.",
            "The provider reported links or referring domains as lost in this period.",
        ))
    anchors = [row for row in records if row.metric == "backlink" and row.metadata.get("anchor")]
    if len(anchors) >= 20:
        counts: Dict[str, int] = defaultdict(int)
        for row in anchors:
            counts[str(row.metadata.get("anchor")).strip().lower()] += 1
        top_anchor, top_count = max(counts.items(), key=lambda item: item[1])
        if top_count / len(anchors) >= 0.6:
            findings.append(_finding(
                project_id, domain, "link_authority", "MEDIUM", anchors[0].provider, "INFERRED",
                "anchor_concentration", top_count, len(anchors), period, "EXTERNAL_INFERRED",
                f"The anchor “{top_anchor}” accounts for {top_count} of {len(anchors)} stored backlink rows.",
                "This uses the stored sample from the provider, not the provider's full index. It is not a Google penalty claim.",
                "Count anchors on stored backlink rows.",
                "Review the source URLs that use this anchor before treating the pattern as a problem.",
                "Anchor text in the stored sample is concentrated.",
                data_state="INFERRED",
            ))
    return findings


def _mention_findings(project_id, domain, period_days, records, coverage) -> List[ExternalFinding]:
    mentions = [row for row in records if row.record_type == "brand_mention"]
    connected = any(row["provider"] == "brand_mentions" and row["connection_status"] == "CONNECTED" for row in coverage)
    if not mentions and not connected:
        return [_finding(
            project_id, domain, "brand_authority", "INFO", "brand_mentions", "UNVERIFIED",
            "mentions", None, None, {"days": period_days}, "PROVIDER_VERIFIED",
            "Brand mentions could not be measured because no brand mention provider is connected.",
            "Unlinked and linked mentions are not inferred from the crawl.",
            "Connect a brand mention provider.",
            "Connect a provider before reporting brand mention coverage.",
            "Mention coverage is unmeasured.",
            data_state="NOT_CONNECTED",
        )]
    linked = sum(1 for row in mentions if row.value_text == "LINKED")
    unlinked = sum(1 for row in mentions if row.value_text == "UNLINKED")
    if not mentions:
        return []
    return [_finding(
        project_id, domain, "brand_authority", "INFO", mentions[0].provider, "DIRECT_PROVIDER_EVIDENCE",
        "mentions", len(mentions), None, _period(period_days, records, mentions[0].provider), "PROVIDER_VERIFIED",
        f"The connected provider returned {len(mentions)} mentions, {linked} linked and {unlinked} unlinked.",
        "Classes are LINKED, UNLINKED, POTENTIAL_ENTITY, or UNVERIFIED. Sentiment is omitted unless the provider returned it.",
        "Count stored brand mention rows by class.",
        "Review unlinked mentions on relevant publications before requesting links.",
        "These counts are the provider's returned mentions.",
    )]


def _local_findings(project_id, domain, period_days, records, coverage, applicability) -> List[ExternalFinding]:
    if applicability == "NON_LOCAL_BUSINESS":
        return [_finding(
            project_id, domain, "entity_local_authority", "INFO", "google_business_profile", "DIRECT_PROVIDER_EVIDENCE",
            "applicability", None, None, {"days": period_days}, "ACCOUNT_VERIFIED",
            "Google Business Profile is not applicable for this business. This is not an SEO failure.",
            "The business was configured as NON_LOCAL_BUSINESS.",
            "Read the saved local-business applicability.",
            "Leave this pillar out of the SEO defect list.",
            "Local profile data is not applicable.",
            data_state="NOT_APPLICABLE",
        )]
    metrics = [row for row in records if row.record_type == "business_profile_metric"]
    if not metrics:
        return []
    calls = _value(records, "calls")
    clicks = _value(records, "website_clicks")
    directions = _value(records, "direction_requests")
    return [_finding(
        project_id, domain, "entity_local_authority", "INFO", "google_business_profile", "DIRECT_PROVIDER_EVIDENCE",
        "business_profile", clicks, None, _period(period_days, records, "google_business_profile"), "PERIOD_VERIFIED",
        "Google Business Profile returned location metrics for this period.",
        f"Website clicks {clicks}, calls {calls}, direction requests {directions}.",
        "Sum the stored Business Profile daily metrics.",
        "Compare the next period against this snapshot.",
        "The profile returned measured interactions.",
    )]


def _citation_summary(records: List[ExternalRecord], profile: Dict[str, Any]) -> Dict[str, Any]:
    listings = [row for row in records if row.record_type == "business_listing"]
    expected = [item.lower() for item in profile.get("expected_directories") or []]
    canonical = {
        "name": _norm(profile.get("name")),
        "address": _norm(profile.get("address")),
        "phone": _digits(profile.get("phone")),
        "website": _host(profile.get("website") or ""),
        "category": _norm(profile.get("category")),
    }
    checked = []
    mismatches = []
    for row in listings:
        meta = row.metadata or {}
        fields = {
            "name": _norm(meta.get("business_name")),
            "address": _norm(meta.get("address")),
            "phone": _digits(meta.get("phone")),
            "website": _host(str(meta.get("website") or "")),
            "category": _norm(meta.get("category")),
        }
        compared = 0
        matched = 0
        issues = []
        for key, expected_value in canonical.items():
            observed = fields.get(key)
            if not expected_value or not observed:
                continue
            compared += 1
            if expected_value == observed:
                matched += 1
            else:
                issues.append(key)
        source = str(meta.get("source_directory") or "")
        checked.append({"source": source, "listing_url": meta.get("listing_url"), "issues": issues, "compared": compared, "matched": matched})
        if issues:
            mismatches.append({"source": source, "issues": issues, "listing_url": meta.get("listing_url")})
    present = {_host(item["source"]) for item in checked}
    missing = [item for item in expected if item not in present and not any(item in source for source in present)]
    duplicates = _duplicates(listings)
    ratio = None
    compared_total = sum(item["compared"] for item in checked)
    matched_total = sum(item["matched"] for item in checked)
    if compared_total:
        ratio = matched_total / compared_total
    summary = {
        "listings": len(listings),
        "nap_consistency": ratio,
        "missing_listings": missing,
        "duplicate_listings": duplicates,
        "mismatches": mismatches,
        "note": "Consistency is measured only against the business profile you configured. A directory is not an authority source merely because it exists.",
    }
    findings = []
    if mismatches:
        findings.append(ExternalFinding(
            finding_id=stable_id("ext_", "citations", "nap"),
            pillar="entity_local_authority",
            severity="MEDIUM",
            source="citations",
            provider="citations",
            evidence_basis="INFERRED",
            metric="nap_consistency",
            observed_value=ratio,
            period={},
            confidence=0.8,
            scope="EXTERNAL_INFERRED",
            impact="Some configured fields differ from the saved business profile.",
            recommendation="Correct the differing phone, address, URL, name, or category at the listed source.",
            verification_method="Compare each stored listing with the saved NAP profile.",
            title=f"{len(mismatches)} directory listings differ from the configured business profile.",
            description=summary["note"],
            data_state="INFERRED",
        ))
    if missing:
        findings.append(ExternalFinding(
            finding_id=stable_id("ext_", "citations", "missing"),
            pillar="entity_local_authority",
            severity="INFO",
            source="citations",
            provider="citations",
            evidence_basis="INFERRED",
            metric="missing_listings",
            observed_value=len(missing),
            period={},
            confidence=0.7,
            scope="EXTERNAL_INFERRED",
            impact="The configured directory list has sources with no stored listing.",
            recommendation="Confirm whether a listing should exist before treating the directory as required.",
            verification_method="Compare configured expected directories with stored listing source hosts.",
            title=f"{len(missing)} configured directories have no stored listing.",
            description="Missing means absent from the directories you configured. A directory is not authoritative merely because it exists.",
            data_state="INFERRED",
        ))
    if duplicates:
        findings.append(ExternalFinding(
            finding_id=stable_id("ext_", "citations", "duplicates"),
            pillar="entity_local_authority",
            severity="MEDIUM",
            source="citations",
            provider="citations",
            evidence_basis="INFERRED",
            metric="duplicate_listings",
            observed_value=len(duplicates),
            period={},
            confidence=0.7,
            scope="EXTERNAL_INFERRED",
            impact="More than one stored listing shares a directory, phone, and address.",
            recommendation="Review the duplicate listing URLs and keep the record the business controls.",
            verification_method="Group stored listings by directory host, phone, and address.",
            title=f"{len(duplicates)} directory sources have more than one stored listing for the same phone and address.",
            description="Duplicates are counted only inside the stored citation sample.",
            data_state="INFERRED",
        ))
    return {"summary": summary, "findings": findings}


def _entity_signals(project_id, domain, records, crawl, coverage, local_profile) -> List[Dict[str, Any]]:
    signals = []
    schema_types = crawl.get("schema_types") or []
    if "Organization" in schema_types or "LocalBusiness" in schema_types:
        signals.append(_signal("organization_schema", "OBSERVED", "Organization or LocalBusiness schema was present on a crawled page.", "crawl"))
    else:
        signals.append(_signal("organization_schema", "UNKNOWN", "Organization schema was not observed in the pages passed to this report. That is not a sitewide absence claim.", "crawl"))
    same_as = crawl.get("same_as") or []
    if same_as:
        signals.append(_signal("same_as", "OBSERVED", f"{len(same_as)} sameAs URLs were present in crawled structured data.", "crawl", {"urls": same_as}))
    else:
        signals.append(_signal("same_as", "UNKNOWN", "No sameAs URLs were passed from the crawl.", "crawl"))
    if any(row.record_type == "business_profile_metric" for row in records):
        signals.append(_signal("google_business_profile", "VERIFIED", "A Google Business Profile location returned performance metrics.", "google_business_profile"))
    elif local_profile.get("applicability") == "NON_LOCAL_BUSINESS":
        signals.append(_signal("google_business_profile", "UNKNOWN", "Google Business Profile is not applicable.", "google_business_profile"))
    else:
        signals.append(_signal("google_business_profile", "UNKNOWN", "No Business Profile metrics were collected.", "google_business_profile"))
    graphs = [row for row in records if row.metric == "knowledge_graph_reference"]
    if graphs:
        signals.append(_signal("knowledge_graph_reference", "VERIFIED", "A connected SERP provider returned a knowledge graph element.", graphs[0].provider, {"title": graphs[0].value_text, "url": graphs[0].url}))
    else:
        signals.append(_signal("knowledge_graph_reference", "UNKNOWN", "Google Knowledge Graph presence was not measured. No connected SERP provider returned a knowledge graph element.", "serp"))
    if any(row.record_type == "brand_mention" for row in records):
        signals.append(_signal("brand_mentions", "OBSERVED", "A connected provider returned brand mentions.", "brand_mentions"))
    if crawl.get("publisher_name") and crawl.get("business_name") and _norm(crawl.get("publisher_name")) == _norm(crawl.get("business_name")):
        signals.append(_signal("publisher_consistency", "OBSERVED", "The crawled publisher name matches the business name passed with the crawl.", "crawl"))
    signals.append(_signal("identity_scope", "UNKNOWN", "External identity signals are limited to connected providers and the pages supplied with this report.", "dristik"))
    return signals


def _competitor_section(project_id, domain, period_days, records, competitors, competitor_records, coverage) -> Dict[str, Any]:
    gaps = []
    findings = []
    our_refs = _latest_metric(records, "referring_domains")
    for competitor in competitors:
        comp_domain = competitor.get("domain")
        name = competitor.get("name") or comp_domain
        if not comp_domain:
            continue
        theirs = competitor_records.get(comp_domain) or []
        their_refs = _latest_metric(theirs, "referring_domains")
        if our_refs and their_refs and our_refs["provider"] == their_refs["provider"]:
            difference = their_refs["value"] - our_refs["value"]
            statement = (
                f"Our domain has {int(our_refs['value'])} referring domains while {name} has {int(their_refs['value'])} "
                f"in the {our_refs['provider']} dataset for this period. The difference is {int(difference)} referring domains. "
                "This is a measured difference in that provider's dataset. It does not say which domain is better."
            )
            gaps.append({
                "competitor": name,
                "domain": comp_domain,
                "metric": "referring_domains",
                "provider": our_refs["provider"],
                "our_value": our_refs["value"],
                "their_value": their_refs["value"],
                "difference": difference,
                "statement": statement,
            })
            findings.append(_finding(
                project_id, domain, "market_authority", "INFO", our_refs["provider"], "DIRECT_PROVIDER_EVIDENCE",
                "referring_domains", our_refs["value"], their_refs["value"], {"days": period_days}, "DOMAIN_VERIFIED",
                statement,
                "Both counts come from the same provider and period. No quality ranking is applied.",
                "Subtract the stored referring-domain totals.",
                "Use the provider's referring-domain list if you want to see which domains differ.",
                "The two domains have different referring-domain counts in this dataset.",
            ))
        elif our_refs and not their_refs:
            gaps.append({
                "competitor": name,
                "domain": comp_domain,
                "metric": "referring_domains",
                "statement": f"Referring domains for {name} were not collected, so no difference is reported.",
            })
    serp = [row for row in records if row.metric == "serp_presence"]
    if serp:
        domains = sorted({row.metadata.get("competitor_domain") or row.value_text for row in serp if row.metadata.get("competitor_domain") or row.value_text})
        gaps.append({
            "metric": "serp_presence",
            "provider": serp[0].provider,
            "observed_domains": domains,
            "statement": f"{serp[0].provider} returned {len(serp)} organic results for the tracked query. This is one SERP snapshot, not a visibility score.",
        })
    if not competitors and not serp:
        gaps.append({"statement": "No competitor domains are configured and no SERP provider returned competitor rows."})
    return {"gaps": gaps, "findings": findings}


def _sections(records, citation, entity, competitor_section, coverage) -> Dict[str, Any]:
    def totals(provider, metric):
        return _value(records, metric, "current", provider=provider)

    gsc = {
        "organic_clicks": totals("google_search_console", "clicks"),
        "impressions": totals("google_search_console", "impressions"),
        "ctr": totals("google_search_console", "ctr"),
        "average_position": totals("google_search_console", "average_position"),
        "bing_clicks": totals("bing_webmaster", "bing_clicks"),
        "bing_impressions": totals("bing_webmaster", "bing_impressions"),
    }
    backlinks = {}
    for provider in ("ahrefs", "semrush", "majestic", "dataforseo"):
        links = totals(provider, "backlinks")
        refs = totals(provider, "referring_domains")
        if links is None and refs is None:
            continue
        backlinks[provider] = {"backlinks": links, "referring_domains": refs}
        for metric in ("domain_rating", "authority_score", "trust_flow", "citation_flow"):
            value = totals(provider, metric)
            if value is not None:
                backlinks[provider][metric] = {"value": value, "label": vendor_metric_label(provider, metric)}
    bing_links = totals("bing_webmaster", "bing_link_count")
    if bing_links is not None:
        backlinks["bing_webmaster"] = {
            "backlinks": bing_links,
            "referring_domains": None,
            "label": "Bing Webmaster link count",
        }
    mentions = [row for row in records if row.record_type == "brand_mention"]
    brand = {
        "mentions": len(mentions),
        "linked": sum(1 for row in mentions if row.value_text == "LINKED"),
        "unlinked": sum(1 for row in mentions if row.value_text == "UNLINKED"),
        "potential_entity": sum(1 for row in mentions if row.value_text == "POTENTIAL_ENTITY"),
        "unverified": sum(1 for row in mentions if row.value_text == "UNVERIFIED"),
    }
    local = {
        "search_impressions": _sum_metrics(records, "search_impressions_"),
        "maps_impressions": _sum_metrics(records, "maps_impressions_"),
        "website_clicks": totals("google_business_profile", "website_clicks"),
        "calls": totals("google_business_profile", "calls"),
        "direction_requests": totals("google_business_profile", "direction_requests"),
    }
    return {
        "search_performance": gsc,
        "backlink_profile": backlinks,
        "referring_domains": {provider: values.get("referring_domains") for provider, values in backlinks.items()},
        "brand_mentions": brand,
        "entity_signals": entity,
        "local_authority": local,
        "competitor_gap": competitor_section["gaps"],
        "data_coverage": coverage,
        "analytics": {
            "organic_users": totals("google_analytics_4", "organic_users"),
            "organic_sessions": totals("google_analytics_4", "organic_sessions"),
            "organic_engagement_rate": totals("google_analytics_4", "organic_engagement_rate"),
            "organic_conversions": totals("google_analytics_4", "organic_conversions"),
            "organic_revenue": totals("google_analytics_4", "organic_revenue"),
            "note": GA4_NOTE,
        },
        "citation_summary": citation["summary"],
    }


def _pillars(coverage, sections) -> Dict[str, Any]:
    def state_for(providers: Iterable[str]) -> str:
        rows = [row for row in coverage if row["provider"] in providers]
        states = [row["data_state"] for row in rows]
        if any(state == "MEASURED" for state in states) and any(state in {"UNAVAILABLE", "NOT_CONNECTED", "PARTIALLY_MEASURED"} for state in states):
            if any(state in {"MEASURED", "PARTIALLY_MEASURED"} for state in states):
                return "PARTIALLY_MEASURED" if any(state != "MEASURED" for state in states) else "MEASURED"
        if any(state == "MEASURED" for state in states):
            return "MEASURED"
        if any(state == "PARTIALLY_MEASURED" for state in states):
            return "PARTIALLY_MEASURED"
        if states and all(state == "NOT_APPLICABLE" for state in states):
            return "NOT_APPLICABLE"
        if any(state == "NOT_CONNECTED" for state in states):
            return "NOT_CONNECTED"
        return "UNAVAILABLE"

    return {
        "search_authority": {"sources": ["google_search_console", "bing_webmaster"], "data_state": state_for(["google_search_console", "bing_webmaster"]), "summary": sections["search_performance"]},
        "link_authority": {"sources": ["ahrefs", "semrush", "majestic", "dataforseo"], "data_state": state_for(["ahrefs", "semrush", "majestic", "dataforseo"]), "summary": sections["backlink_profile"]},
        "brand_authority": {"sources": ["brand_mentions", "citations"], "data_state": state_for(["brand_mentions", "citations"]), "summary": sections["brand_mentions"]},
        "entity_local_authority": {"sources": ["google_business_profile", "citations"], "data_state": state_for(["google_business_profile", "citations"]), "summary": {"local": sections["local_authority"], "entity": sections["entity_signals"]}},
        "market_authority": {"sources": ["serpapi", "dataforseo"], "data_state": state_for(["serpapi", "dataforseo"]), "summary": sections["competitor_gap"]},
    }


def _trends(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for snap in history:
        grouped[(snap.get("provider"), snap.get("period_days"))].append(snap)
    trends = []
    for (provider, period), snaps in grouped.items():
        snaps = sorted(snaps, key=lambda item: item.get("collected_at") or "")
        if len(snaps) < 2:
            continue
        previous, current = snaps[-2], snaps[-1]
        prev_totals = (previous.get("summary") or {}).get("totals") or {}
        cur_totals = (current.get("summary") or {}).get("totals") or {}
        for metric, value in cur_totals.items():
            before = prev_totals.get(metric)
            if not isinstance(value, (int, float)) or not isinstance(before, (int, float)):
                continue
            direction = "flat"
            if value > before:
                direction = "growth"
            elif value < before:
                direction = "decline"
            trends.append({
                "provider": provider,
                "metric": metric,
                "period_days": period,
                "period_label": PERIOD_LABELS.get(period, str(period)),
                "previous": before,
                "current": value,
                "direction": direction,
                "previous_collected_at": previous.get("collected_at"),
                "current_collected_at": current.get("collected_at"),
            })
    return trends


def _audit_sources(coverage: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows = [{"source": "Website Crawl", "state": "INCLUDED", "detail": "Crawl depth is independent of external authority."}]
    labels = {
        "google_search_console": "Google Search Console",
        "google_analytics_4": "Google Analytics",
        "bing_webmaster": "Bing Webmaster",
        "ahrefs": "Backlink Provider",
        "semrush": "Backlink Provider",
        "majestic": "Backlink Provider",
        "dataforseo": "Backlink Provider",
        "google_business_profile": "Google Business",
        "brand_mentions": "Brand Mentions",
    }
    seen = set()
    for row in coverage:
        label = labels.get(row["provider"])
        if not label or label in seen and row["connection_status"] != "CONNECTED":
            continue
        if label in seen and row["connection_status"] == "CONNECTED":
            rows = [item for item in rows if item["source"] != label]
        seen.add(label)
        state = "CONNECTED" if row["connection_status"] == "CONNECTED" else row["data_state"]
        rows.append({"source": label, "state": state, "detail": row.get("note") or ""})
    return rows


def _finding(project_id, domain, pillar, severity, provider, basis, metric, observed, previous, period, scope, title, description, verification, recommendation, impact, data_state="MEASURED", vendor_metric_label=None) -> ExternalFinding:
    return ExternalFinding(
        finding_id=stable_id("ext_", project_id, domain, provider, metric, title[:80]),
        pillar=pillar,
        severity=severity,
        source=provider,
        provider=provider,
        evidence_basis=basis,
        metric=metric,
        observed_value=observed,
        previous_value=previous,
        period=period,
        confidence=0.95 if basis == "DIRECT_PROVIDER_EVIDENCE" else 0.7 if basis == "INFERRED" else 0.4,
        scope=scope,
        impact=impact,
        recommendation=recommendation,
        verification_method=verification,
        title=title,
        description=description,
        data_state="UNAVAILABLE" if data_state == "UNVERIFIED" else data_state,
        vendor_metric_label=vendor_metric_label,
    )


def _value(records, metric, comparison="current", provider=None):
    for row in records:
        if row.metric != metric:
            continue
        if provider and row.provider != provider:
            continue
        if (row.metadata or {}).get("comparison", "current") != comparison:
            continue
        if row.value is None or row.status == "UNAVAILABLE":
            continue
        return row.value
    return None


def _rows(records, metric, dimension, provider):
    return [
        row for row in records
        if row.metric == metric and row.provider == provider and row.metric_type == dimension and (row.metadata or {}).get("comparison", "current") == "current"
    ]


def _period(period_days, records, provider):
    for row in records:
        if row.provider == provider and row.period_start:
            return {"start": row.period_start, "end": row.period_end, "days": period_days, "label": PERIOD_LABELS.get(period_days)}
    return {"days": period_days, "label": PERIOD_LABELS.get(period_days)}


def _branded(query: Optional[str], terms: List[str]) -> bool:
    text = (query or "").lower()
    return any(term.lower() in text for term in terms if term)


def _low_ctr(rows: List[ExternalRecord], site_ctr: float) -> List[ExternalRecord]:
    impressions = sorted(float(row.metadata.get("impressions") or 0) for row in rows)
    median = impressions[len(impressions) // 2] if impressions else 0
    threshold = max(100, median)
    return [
        row for row in rows
        if float(row.metadata.get("impressions") or 0) >= threshold and float(row.metadata.get("ctr") or 0) < site_ctr * 0.5
    ]


def _page_click_changes(records: List[ExternalRecord]) -> Dict[str, List[str]]:
    current = {}
    previous = {}
    for row in records:
        if row.metric != "search_analytics_row" or row.metric_type != "page" or row.provider != "google_search_console" or not row.url:
            continue
        target = current if (row.metadata or {}).get("comparison") == "current" else previous
        target[row.url] = float(row.metadata.get("clicks") or 0)
    lost, gained = [], []
    for url, clicks in current.items():
        if url not in previous:
            continue
        before = previous[url]
        if before < 10 and clicks < 10:
            continue
        if before == 0:
            continue
        change = (clicks - before) / before
        if change <= -0.2 and abs(clicks - before) >= 10:
            lost.append(url)
        elif change >= 0.2 and abs(clicks - before) >= 10:
            gained.append(url)
    return {"lost": lost, "gained": gained}


def _cannibalization(records: List[ExternalRecord]) -> List[str]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    for row in records:
        if row.metric != "search_analytics_row" or row.metric_type != "query_page":
            continue
        if (row.metadata or {}).get("comparison") != "current":
            continue
        query = row.metadata.get("query")
        impressions = float(row.metadata.get("impressions") or 0)
        if query and impressions >= 50:
            grouped[query].append(impressions)
    return [query for query, impressions in grouped.items() if len(impressions) >= 2]


def _inspection_failed(row: ExternalRecord) -> bool:
    text = " ".join([
        str(row.value_text or ""),
        str((row.metadata or {}).get("coverage_state") or ""),
        str((row.metadata or {}).get("verdict") or ""),
    ]).lower()
    return any(token in text for token in ("not indexed", "url is unknown", "fail", "excluded"))


def _latest_metric(records: List[ExternalRecord], metric: str) -> Optional[Dict[str, Any]]:
    matches = [row for row in records if row.metric == metric and row.value is not None and (row.metadata or {}).get("comparison", "current") == "current"]
    if not matches:
        return None
    row = matches[-1]
    return {"provider": row.provider, "value": float(row.value)}


def _sum_metrics(records: List[ExternalRecord], prefix: str) -> Optional[float]:
    values = [row.value for row in records if row.metric.startswith(prefix) and row.value is not None and row.provider == "google_business_profile"]
    if not values:
        return None
    return float(sum(values))


def _signal(name: str, status: str, detail: str, source: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"signal": name, "status": status, "detail": detail, "source": source, "metadata": extra or {}}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _digits(value: Any) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def _host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.")


def _duplicates(listings: List[ExternalRecord]) -> List[Dict[str, str]]:
    seen = defaultdict(list)
    for row in listings:
        meta = row.metadata or {}
        key = (_host(str(meta.get("source_directory") or "")), _digits(meta.get("phone")), _norm(meta.get("address")))
        seen[key].append(meta.get("listing_url") or "")
    return [{"source": key[0], "listing_url": urls[0]} for key, urls in seen.items() if key[0] and len(urls) > 1]
