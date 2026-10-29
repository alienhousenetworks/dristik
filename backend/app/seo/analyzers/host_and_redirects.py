"""
Dristik AI Canonical & Host-Variant Redirection Prober
Probes the 4 origin permutations:
1. http://domain
2. https://domain
3. http://www.domain
4. https://www.domain

Verifies proper 301 consolidation to a single canonical destination in 1 hop.
Detects redirect chains (>1 hop), redirect loops, and terminal 4xx/5xx responses.
"""
from __future__ import annotations
import asyncio
import logging
from urllib.parse import urlparse
from typing import Dict, List, Optional, Set, Any, Tuple
import httpx
from app.domain.models import RedirectHop, HostVariantProbeResult, RedirectAuditReport

logger = logging.getLogger("dristik.analyzers.host_and_redirects")


class HostRedirectProber:
    @staticmethod
    def _clean_domain(domain_or_url: str) -> str:
        raw = domain_or_url.strip().lower()
        if "://" in raw:
            parsed = urlparse(raw)
            raw = parsed.netloc
        raw = raw.split(":")[0]
        if raw.startswith("www."):
            raw = raw[4:]
        return raw

    @classmethod
    async def _probe_single_origin(
        cls,
        origin_url: str,
        client: Optional[httpx.AsyncClient] = None,
        max_hops: int = 8,
    ) -> HostVariantProbeResult:
        """
        Follows redirects step-by-step to record every hop and detect loops or errors.
        """
        hops: List[RedirectHop] = []
        current_url = origin_url
        visited: Set[str] = set()
        error_msg: Optional[str] = None
        status_code = 0

        owns_client = False
        if client is None:
            client = httpx.AsyncClient(
                timeout=4.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DristikAuditBot/2.0)"},
                follow_redirects=False,
            )
            owns_client = True

        try:
            for _ in range(max_hops):
                if current_url in visited:
                    error_msg = f"Redirect loop detected at '{current_url}'"
                    break
                visited.add(current_url)

                try:
                    resp = await client.get(current_url)
                except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
                    error_msg = f"Connection error reaching '{current_url}': {str(e)}"
                    break

                status_code = resp.status_code
                loc = resp.headers.get("location") or resp.headers.get("Location")

                hops.append(RedirectHop(
                    status=status_code,
                    url=current_url,
                    location=loc
                ))

                if 300 <= status_code < 400 and loc:
                    # Resolve relative redirect locations
                    if loc.startswith("/"):
                        parsed_cur = urlparse(current_url)
                        current_url = f"{parsed_cur.scheme}://{parsed_cur.netloc}{loc}"
                    else:
                        current_url = loc
                else:
                    # Terminal non-redirect response
                    break
        finally:
            if owns_client:
                await client.aclose()

        final_dest = hops[-1].url if hops else origin_url
        hop_count = max(0, len(hops) - 1)

        return HostVariantProbeResult(
            origin_url=origin_url,
            final_destination=final_dest,
            status_code=status_code,
            hops=hops,
            hop_count=hop_count,
            proper_canonical_redirect=False,  # Evaluated sitewide in probe_domain
            error=error_msg
        )

    @classmethod
    async def probe_domain(
        cls,
        domain_or_url: str,
        client: Optional[httpx.AsyncClient] = None,
        canonical_target: Optional[str] = None,
    ) -> RedirectAuditReport:
        apex = cls._clean_domain(domain_or_url)
        target_domain = apex

        # 4 Origin Permutations
        origins = {
            "http_apex": f"http://{apex}",
            "https_apex": f"https://{apex}",
            "http_www": f"http://www.{apex}",
            "https_www": f"https://www.{apex}",
        }

        tasks = [cls._probe_single_origin(url, client=client) for url in origins.values()]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results: Dict[str, HostVariantProbeResult] = {}
        for key, res in zip(origins.keys(), results_list):
            if isinstance(res, Exception):
                results[key] = HostVariantProbeResult(
                    origin_url=origins[key],
                    final_destination=origins[key],
                    status_code=0,
                    error=str(res)
                )
            else:
                results[key] = res

        # Determine canonical destination
        destinations = [r.final_destination.rstrip("/") for r in results.values() if r.final_destination and r.status_code in (200, 301, 302)]
        if not canonical_target:
            if destinations:
                # Majority destination or https:// preferred
                canonical_target = max(set(destinations), key=destinations.count)
            else:
                canonical_target = f"https://{apex}"

        clean_canon = canonical_target.rstrip("/")

        # Evaluate proper 301 redirection
        proper_redirect_count = 0
        has_chain_gt_1 = False
        has_loop = False
        redirects_4xx = False
        chains: List[Dict[str, Any]] = []

        for key, probe in results.items():
            final_clean = (probe.final_destination or "").rstrip("/")
            if probe.hop_count > 1:
                has_chain_gt_1 = True
            if probe.error and "loop" in probe.error.lower():
                has_loop = True
            if probe.status_code >= 400:
                redirects_4xx = True

            is_canonical = (probe.origin_url.rstrip("/") == clean_canon)
            if is_canonical:
                probe.proper_canonical_redirect = (probe.status_code == 200 or probe.hop_count == 0)
            else:
                is_proper_redirect = (
                    final_clean == clean_canon
                    and probe.hop_count == 1
                    and len(probe.hops) >= 2
                    and probe.hops[0].status == 301
                )
                probe.proper_canonical_redirect = is_proper_redirect
                if is_proper_redirect:
                    proper_redirect_count += 1

            chains.append({
                "origin": probe.origin_url,
                "destination": probe.final_destination,
                "status_code": probe.status_code,
                "hop_count": probe.hop_count,
                "hops": [{"status": h.status, "url": h.url, "location": h.location} for h in probe.hops],
                "error": probe.error
            })

        # Perfect consolidation: 3 of 4 redirect in 1 hop to the canonical 4th
        proper_consolidation = (proper_redirect_count >= 3 and not has_chain_gt_1 and not has_loop and not redirects_4xx)

        summary = (
            f"Canonical destination: '{clean_canon}'. "
            f"301 Consolidation: {'Optimal (3/3 non-canonical variants 301-redirect in 1 hop)' if proper_consolidation else f'{proper_redirect_count}/3 properly consolidated'}. "
            f"Chains > 1 hop: {has_chain_gt_1}, Loops: {has_loop}, 4xx errors: {redirects_4xx}."
        )

        return RedirectAuditReport(
            target_domain=target_domain,
            canonical_destination=clean_canon,
            host_variants=results,
            proper_301_consolidation=proper_consolidation,
            has_chain_gt_1_hop=has_chain_gt_1,
            has_redirect_loop=has_loop,
            redirects_to_4xx=redirects_4xx,
            chains_recorded=chains,
            summary=summary
        )


async def probe_host_and_redirects(
    domain_or_url: str,
    client: Optional[httpx.AsyncClient] = None,
    canonical_target: Optional[str] = None
) -> RedirectAuditReport:
    return await HostRedirectProber.probe_domain(domain_or_url, client=client, canonical_target=canonical_target)
