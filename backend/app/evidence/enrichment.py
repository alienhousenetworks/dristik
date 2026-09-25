"""
External Ground Truth Evidence Enrichment Engine
Fetches live deterministic external telemetry (DNS, SSL/TLS, HTTP Security Headers, CruX)
and registers external evidence items (ext_NNN) into EvidenceStore for cross-agent corroboration.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from app.domain.enums import MetricProvenanceState
from app.evidence.models import Evidence
from app.evidence.store import EvidenceStore

logger = logging.getLogger(__name__)


class ExternalEvidenceEnricher:
    """
    Enriches an audit by collecting empirical external ground truth.
    Writes external evidence entries directly via EvidenceStore.add_external_evidence().
    """

    def __init__(self, timeout_sec: float = 6.0):
        self.timeout_sec = timeout_sec

    def _clean_hostname(self, target: str) -> str:
        clean = target.strip()
        if not clean.startswith("http://") and not clean.startswith("https://"):
            clean = "https://" + clean
        parsed = urlparse(clean)
        return parsed.hostname or clean.split("/")[0]

    async def enrich_domain(self, target: str, evidence_store: EvidenceStore) -> List[Evidence]:
        """
        Executes external enrichment across DNS, SSL/TLS, Security Headers, CruX, and Firmographic sources.
        Appends ext_NNN items into evidence_store.
        """
        hostname = self._clean_hostname(target)
        enriched: List[Evidence] = []

        # 1. Empirical DNS Resolution
        dns_ev = await self._resolve_dns(hostname, evidence_store)
        if dns_ev:
            enriched.append(dns_ev)

        # 2. Empirical SSL/TLS Telemetry
        ssl_ev = await self._inspect_ssl_tls(hostname, evidence_store)
        if ssl_ev:
            enriched.append(ssl_ev)

        # 3. HTTP Security Headers
        headers_ev = await self._inspect_security_headers(hostname, evidence_store)
        if headers_ev:
            enriched.append(headers_ev)

        # 4. Google CruX CWV Ground Truth
        crux_ev = await self._fetch_crux_telemetry(hostname, evidence_store)
        if crux_ev:
            enriched.append(crux_ev)

        # 5. Firmographic registries and public entity resolution
        firmographic_evs = await self._fetch_firmographic_stubs(hostname, evidence_store)
        enriched.extend(firmographic_evs)
        wiki_ev = await self._fetch_wikidata(hostname, evidence_store)
        if wiki_ev:
            enriched.append(wiki_ev)

        logger.info(f"[Enrichment] Registered {len(enriched)} external evidence items for {hostname}")
        return enriched

    async def _resolve_dns(self, hostname: str, evidence_store: EvidenceStore) -> Optional[Evidence]:
        try:
            addr_info = await asyncio.wait_for(
                asyncio.to_thread(socket.getaddrinfo, hostname, 443, proto=socket.IPPROTO_TCP),
                timeout=self.timeout_sec
            )
            ips = sorted(list({info[4][0] for info in addr_info if info[4]}))
            return evidence_store.add_external_evidence(
                source="dns",
                claim=f"Domain {hostname} resolves to authoritative IP addresses: {', '.join(ips[:4])}",
                raw_value={
                    "status": "MEASURED",
                    "provenance": MetricProvenanceState.MEASURED.value,
                    "hostname": hostname,
                    "ip_addresses": ips,
                },
                confidence_basis="authoritative_dns_resolution",
                url=f"https://{hostname}",
            )
        except Exception as e:
            logger.warning(f"[Enrichment] DNS resolution failed for {hostname}: {e}")
            return evidence_store.add_external_evidence(
                source="dns",
                claim=f"DNS resolution query for {hostname} failed: {e}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "error": str(e)},
                confidence_basis="authoritative_dns_resolution",
                url=f"https://{hostname}",
            )

    async def _inspect_ssl_tls(self, hostname: str, evidence_store: EvidenceStore) -> Optional[Evidence]:
        def _fetch_cert():
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=self.timeout_sec) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    return cert, cipher, version

        try:
            cert, cipher, version = await asyncio.wait_for(
                asyncio.to_thread(_fetch_cert),
                timeout=self.timeout_sec + 1.0
            )
            issuer = dict(x[0] for x in cert.get("issuer", ()))
            issuer_cn = issuer.get("commonName") or issuer.get("organizationName") or "Verified CA"
            not_after = cert.get("notAfter", "Unknown")

            return evidence_store.add_external_evidence(
                source="ssl_tls",
                claim=f"SSL/TLS verified with valid certificate issued by {issuer_cn}, expires {not_after}. Protocol: {version}.",
                raw_value={
                    "status": "MEASURED",
                    "provenance": MetricProvenanceState.MEASURED.value,
                    "issuer": issuer_cn,
                    "expires_at": not_after,
                    "protocol_version": version,
                    "cipher_suite": cipher[0] if cipher else None,
                },
                confidence_basis="live_tls_handshake",
                url=f"https://{hostname}",
            )
        except Exception as e:
            logger.warning(f"[Enrichment] SSL/TLS handshake failed for {hostname}: {e}")
            return evidence_store.add_external_evidence(
                source="ssl_tls",
                claim=f"SSL/TLS certificate verification failed or unavailable: {e}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "error": str(e)},
                confidence_basis="live_tls_handshake",
                url=f"https://{hostname}",
            )

    async def _inspect_security_headers(self, hostname: str, evidence_store: EvidenceStore) -> Optional[Evidence]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec, follow_redirects=True) as client:
                res = await client.get(f"https://{hostname}", headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
                hsts = res.headers.get("Strict-Transport-Security")
                csp = res.headers.get("Content-Security-Policy")
                xfo = res.headers.get("X-Frame-Options")
                xcto = res.headers.get("X-Content-Type-Options")

                features = []
                if hsts:
                    features.append("HSTS enforced")
                if csp:
                    features.append("CSP active")
                if xfo:
                    features.append(f"X-Frame-Options ({xfo})")
                if xcto:
                    features.append("X-Content-Type-Options nosniff")

                summary = ", ".join(features) if features else "No advanced HTTP security headers active"

                return evidence_store.add_external_evidence(
                    source="security_headers",
                    claim=f"HTTP Security Headers on {hostname}: {summary}.",
                    raw_value={
                        "status": "MEASURED",
                        "provenance": MetricProvenanceState.MEASURED.value,
                        "hsts": hsts,
                        "csp": bool(csp),
                        "x_frame_options": xfo,
                        "x_content_type_options": xcto,
                        "status_code": res.status_code,
                    },
                    confidence_basis="live_http_response_headers",
                    url=f"https://{hostname}",
                )
        except Exception as e:
            logger.warning(f"[Enrichment] Security headers inspection failed for {hostname}: {e}")
            return evidence_store.add_external_evidence(
                source="security_headers",
                claim=f"HTTP security headers could not be inspected: {e}",
                raw_value={"status": "UNAVAILABLE", "provenance": MetricProvenanceState.UNAVAILABLE.value, "error": str(e)},
                confidence_basis="live_http_response_headers",
                url=f"https://{hostname}",
            )

    async def _fetch_crux_telemetry(self, hostname: str, evidence_store: EvidenceStore) -> Optional[Evidence]:
        from app.core.config import settings
        api_key = settings.CRUX_API_KEY or os.getenv("CRUX_API_KEY") or settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return evidence_store.add_external_evidence(
                source="crux",
                claim="Google Chrome User Experience Report (CrUX) connector not configured.",
                raw_value={
                    "status": "NOT_CONFIGURED",
                    "provenance": MetricProvenanceState.NOT_CONFIGURED.value,
                    "reason": "CRUX_API_KEY or GOOGLE_API_KEY is not set in environment.",
                },
                confidence_basis="connector_unconfigured",
                url=f"https://{hostname}",
            )

        endpoint = f"https://chromeuxreport.googleapis.com/v1/records:queryRecord?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.post(endpoint, json={"origin": f"https://{hostname}"})
                if res.status_code == 200:
                    data = res.json()
                    metrics = data.get("record", {}).get("metrics", {})
                    lcp = metrics.get("largest_contentful_paint", {}).get("percentiles", {}).get("p75")
                    cls = metrics.get("cumulative_layout_shift", {}).get("percentiles", {}).get("p75")
                    inp = metrics.get("interaction_to_next_paint", {}).get("percentiles", {}).get("p75")

                    return evidence_store.add_external_evidence(
                        source="crux",
                        claim=f"CrUX 75th percentile real-user telemetry: LCP={lcp}ms, CLS={cls}, INP={inp}ms.",
                        raw_value={
                            "status": "MEASURED",
                            "provenance": MetricProvenanceState.MEASURED.value,
                            "lcp_p75": lcp,
                            "cls_p75": cls,
                            "inp_p75": inp,
                        },
                        confidence_basis="google_crux_api",
                        url=f"https://{hostname}",
                    )
                else:
                    if res.status_code == 404:
                        status = "INSUFFICIENT_TRAFFIC_FOR_CRUX"
                        provenance = MetricProvenanceState.UNAVAILABLE.value
                        claim = "Chrome UX Report has no 28-day field dataset for this origin."
                    elif res.status_code in (401, 403):
                        status = "FAILED"
                        provenance = MetricProvenanceState.FAILED.value
                        claim = "CrUX API rejected the key. Field data was not measured."
                    else:
                        status = "FAILED"
                        provenance = MetricProvenanceState.FAILED.value
                        claim = f"CrUX API returned HTTP {res.status_code}. Field data was not measured."
                    return evidence_store.add_external_evidence(
                        source="crux",
                        claim=claim,
                        raw_value={
                            "status": status,
                            "provenance": provenance,
                            "http_status": res.status_code,
                        },
                        confidence_basis="google_crux_api",
                        url=f"https://{hostname}",
                    )
        except Exception as e:
            logger.warning(f"[Enrichment] CrUX fetch error: {e}")
            return evidence_store.add_external_evidence(
                source="crux",
                claim=f"CrUX telemetry query failed: {e}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "error": str(e)},
                confidence_basis="google_crux_api",
                url=f"https://{hostname}",
            )

    def _external_key(self, env_var: str) -> Optional[str]:
        from app.core.config import settings
        return getattr(settings, env_var, None) or os.getenv(env_var)

    def _not_configured(self, evidence_store: EvidenceStore, hostname: str, source: str, name: str, env_var: str) -> Evidence:
        return evidence_store.add_external_evidence(
            source=source,
            claim=f"{name} connector not configured.",
            raw_value={
                "status": "NOT_CONFIGURED",
                "provenance": MetricProvenanceState.NOT_CONFIGURED.value,
                "source": source,
                "reason": f"{env_var} not configured in environment.",
            },
            confidence_basis="connector_unconfigured",
            url=f"https://{hostname}",
        )

    async def _fetch_firmographic_stubs(self, hostname: str, evidence_store: EvidenceStore) -> List[Evidence]:
        """
        One ext_ token per registry. Missing keys are NOT_CONFIGURED.
        A present key is queried. A partner API we cannot call honestly is UNAVAILABLE, never a fabricated profile.
        """
        items: List[Evidence] = []
        clearbit = self._external_key("CLEARBIT_API_KEY")
        if not clearbit:
            items.append(self._not_configured(evidence_store, hostname, "clearbit", "Clearbit Company API", "CLEARBIT_API_KEY"))
        else:
            items.append(await self._query_clearbit(hostname, clearbit, evidence_store))

        builtwith = self._external_key("BUILTWITH_API_KEY")
        if not builtwith:
            items.append(self._not_configured(evidence_store, hostname, "builtwith", "BuiltWith technology profile", "BUILTWITH_API_KEY"))
        else:
            items.append(await self._query_builtwith(hostname, builtwith, evidence_store))

        crunchbase = self._external_key("CRUNCHBASE_API_KEY")
        if not crunchbase:
            items.append(self._not_configured(evidence_store, hostname, "crunchbase", "Crunchbase organization lookup", "CRUNCHBASE_API_KEY"))
        else:
            items.append(await self._query_crunchbase(hostname, crunchbase, evidence_store))

        for source, env_var, name, reason in (
            ("linkedin", "LINKEDIN_API_KEY", "LinkedIn company profile", "LinkedIn company data requires a partner OAuth flow. A static key is not a measurement."),
            ("g2", "G2_API_KEY", "G2 review profile", "G2 does not provide a documented domain lookup in this build. Reviews are not invented."),
        ):
            if not self._external_key(env_var):
                items.append(self._not_configured(evidence_store, hostname, source, name, env_var))
            else:
                items.append(evidence_store.add_external_evidence(
                    source=source,
                    claim=reason,
                    raw_value={
                        "status": "UNAVAILABLE",
                        "provenance": MetricProvenanceState.UNAVAILABLE.value,
                        "source": source,
                        "reason": reason,
                    },
                    confidence_basis="connector_not_a_measurement",
                    url=f"https://{hostname}",
                ))
        return items

    async def _query_clearbit(self, hostname: str, api_key: str, evidence_store: EvidenceStore) -> Evidence:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.get(
                    "https://company.clearbit.com/v2/companies/find",
                    params={"domain": hostname},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if res.status_code == 404:
                return evidence_store.add_external_evidence(
                    source="clearbit",
                    claim=f"Clearbit has no company record for {hostname}.",
                    raw_value={"status": "NOT_FOUND", "provenance": MetricProvenanceState.UNAVAILABLE.value, "source": "clearbit"},
                    confidence_basis="clearbit_company_api",
                    url=f"https://{hostname}",
                )
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}")
            data = res.json()
            name = data.get("name")
            metrics = data.get("metrics") or {}
            return evidence_store.add_external_evidence(
                source="clearbit",
                claim=f"Clearbit company record: {name or hostname}.",
                raw_value={
                    "status": "MEASURED",
                    "provenance": MetricProvenanceState.MEASURED.value,
                    "source": "clearbit",
                    "name": name,
                    "employees": metrics.get("employees"),
                    "category": (data.get("category") or {}).get("industry"),
                },
                confidence_basis="clearbit_company_api",
                url=f"https://{hostname}",
            )
        except Exception as exc:
            return evidence_store.add_external_evidence(
                source="clearbit",
                claim=f"Clearbit lookup failed: {exc}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "source": "clearbit", "error": str(exc)},
                confidence_basis="clearbit_company_api",
                url=f"https://{hostname}",
            )

    async def _query_builtwith(self, hostname: str, api_key: str, evidence_store: EvidenceStore) -> Evidence:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.get(
                    "https://api.builtwith.com/v21/api.json",
                    params={"KEY": api_key, "LOOKUP": hostname},
                )
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}")
            data = res.json()
            technologies: List[str] = []
            for result in data.get("Results") or []:
                for path in result.get("Result", {}).get("Paths") or []:
                    for tech in path.get("Technologies") or []:
                        if tech.get("Name"):
                            technologies.append(str(tech["Name"]))
            technologies = sorted(set(technologies))[:25]
            if not technologies:
                return evidence_store.add_external_evidence(
                    source="builtwith",
                    claim=f"BuiltWith returned no technologies for {hostname}.",
                    raw_value={"status": "NO_MATCH", "provenance": MetricProvenanceState.UNAVAILABLE.value, "source": "builtwith"},
                    confidence_basis="builtwith_api",
                    url=f"https://{hostname}",
                )
            return evidence_store.add_external_evidence(
                source="builtwith",
                claim=f"BuiltWith technologies observed: {', '.join(technologies[:8])}.",
                raw_value={
                    "status": "MEASURED",
                    "provenance": MetricProvenanceState.MEASURED.value,
                    "source": "builtwith",
                    "technologies": technologies,
                },
                confidence_basis="builtwith_api",
                url=f"https://{hostname}",
            )
        except Exception as exc:
            return evidence_store.add_external_evidence(
                source="builtwith",
                claim=f"BuiltWith lookup failed: {exc}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "source": "builtwith", "error": str(exc)},
                confidence_basis="builtwith_api",
                url=f"https://{hostname}",
            )

    async def _query_crunchbase(self, hostname: str, api_key: str, evidence_store: EvidenceStore) -> Evidence:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.get(
                    "https://api.crunchbase.com/api/v4/autocompletes",
                    params={"query": hostname, "collection_ids": "organizations", "limit": 1, "user_key": api_key},
                )
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}")
            entities = (res.json().get("entities") or [])
            if not entities:
                return evidence_store.add_external_evidence(
                    source="crunchbase",
                    claim=f"Crunchbase autocomplete returned no organization for {hostname}.",
                    raw_value={"status": "NO_MATCH", "provenance": MetricProvenanceState.UNAVAILABLE.value, "source": "crunchbase"},
                    confidence_basis="crunchbase_autocomplete",
                    url=f"https://{hostname}",
                )
            entity = entities[0]
            name = (entity.get("identifier") or {}).get("value") or entity.get("value")
            return evidence_store.add_external_evidence(
                source="crunchbase",
                claim=f"Crunchbase organization match: {name or hostname}.",
                raw_value={
                    "status": "MEASURED",
                    "provenance": MetricProvenanceState.MEASURED.value,
                    "source": "crunchbase",
                    "name": name,
                    "permalink": (entity.get("identifier") or {}).get("permalink"),
                },
                confidence_basis="crunchbase_autocomplete",
                url=f"https://{hostname}",
            )
        except Exception as exc:
            return evidence_store.add_external_evidence(
                source="crunchbase",
                claim=f"Crunchbase lookup failed: {exc}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "source": "crunchbase", "error": str(exc)},
                confidence_basis="crunchbase_autocomplete",
                url=f"https://{hostname}",
            )

    async def _fetch_wikidata(self, hostname: str, evidence_store: EvidenceStore) -> Optional[Evidence]:
        safe_host = hostname.lower().strip(".")
        if not safe_host or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for ch in safe_host):
            return None
        query = (
            "SELECT ?item ?itemLabel ?official WHERE {"
            " ?item wdt:P856 ?official ."
            f' FILTER(CONTAINS(LCASE(STR(?official)), "{safe_host}"))'
            ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
            "} LIMIT 1"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.get(
                    "https://query.wikidata.org/sparql",
                    params={"query": query, "format": "json"},
                    headers={"Accept": "application/sparql-results+json", "User-Agent": "Dristik-Intelligence-Bot/2.0"},
                )
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}")
            bindings = res.json().get("results", {}).get("bindings") or []
            if not bindings:
                return evidence_store.add_external_evidence(
                    source="wikidata",
                    claim=f"Wikidata has no entity whose official website contains {safe_host}.",
                    raw_value={"status": "NO_ENTITY", "provenance": MetricProvenanceState.UNAVAILABLE.value, "source": "wikidata"},
                    confidence_basis="wikidata_sparql",
                    url=f"https://{hostname}",
                )
            row = bindings[0]
            label = (row.get("itemLabel") or {}).get("value")
            item = (row.get("item") or {}).get("value")
            official = (row.get("official") or {}).get("value")
            return evidence_store.add_external_evidence(
                source="wikidata",
                claim=f"Wikidata entity {label or item} lists official website {official}.",
                raw_value={
                    "status": "MEASURED",
                    "provenance": MetricProvenanceState.MEASURED.value,
                    "source": "wikidata",
                    "label": label,
                    "item": item,
                    "official_website": official,
                },
                confidence_basis="wikidata_sparql",
                url=f"https://{hostname}",
            )
        except Exception as exc:
            logger.warning("[Enrichment] Wikidata lookup failed for %s: %s", hostname, exc)
            return evidence_store.add_external_evidence(
                source="wikidata",
                claim=f"Wikidata lookup failed: {exc}",
                raw_value={"status": "FAILED", "provenance": MetricProvenanceState.FAILED.value, "source": "wikidata", "error": str(exc)},
                confidence_basis="wikidata_sparql",
                url=f"https://{hostname}",
            )
