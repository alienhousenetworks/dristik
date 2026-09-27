"""
Unit tests for Canonical & Host-Variant Redirection Prober.
"""
import pytest
import httpx
from app.analyzers.host_and_redirects import HostRedirectProber


@pytest.mark.asyncio
async def test_proper_canonical_301_consolidation():
    """
    Test standard best-practice configuration:
    - https://acme.com is canonical (200 OK)
    - http://acme.com -> 301 -> https://acme.com
    - http://www.acme.com -> 301 -> https://acme.com
    - https://www.acme.com -> 301 -> https://acme.com
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url).rstrip("/")
        if url == "https://acme.com":
            return httpx.Response(200, text="OK")
        elif url in ("http://acme.com", "http://www.acme.com", "https://www.acme.com"):
            return httpx.Response(301, headers={"Location": "https://acme.com"})
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        report = await HostRedirectProber.probe_domain("acme.com", client=client, canonical_target="https://acme.com")

        assert report.proper_301_consolidation is True
        assert report.has_chain_gt_1_hop is False
        assert report.has_redirect_loop is False
        assert report.redirects_to_4xx is False
        assert len(report.host_variants) == 4

        # Non-canonical variants must have 1 hop
        assert report.host_variants["http_apex"].hop_count == 1
        assert report.host_variants["http_www"].hop_count == 1
        assert report.host_variants["https_www"].hop_count == 1
        assert report.host_variants["https_apex"].hop_count == 0


@pytest.mark.asyncio
async def test_detects_redirect_chain_gt_1_hop():
    """
    Test multi-hop chain defect:
    http://acme.com -> 301 -> http://www.acme.com -> 301 -> https://www.acme.com
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url).rstrip("/")
        if url == "http://acme.com":
            return httpx.Response(301, headers={"Location": "http://www.acme.com"})
        elif url == "http://www.acme.com":
            return httpx.Response(301, headers={"Location": "https://www.acme.com"})
        elif url == "https://www.acme.com":
            return httpx.Response(200, text="OK")
        elif url == "https://acme.com":
            return httpx.Response(301, headers={"Location": "https://www.acme.com"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        report = await HostRedirectProber.probe_domain("acme.com", client=client, canonical_target="https://www.acme.com")

        assert report.has_chain_gt_1_hop is True
        assert report.proper_301_consolidation is False
        assert report.host_variants["http_apex"].hop_count >= 2


@pytest.mark.asyncio
async def test_detects_redirect_loop():
    """
    Test redirect loop defect:
    https://acme.com -> 301 -> https://www.acme.com -> 301 -> https://acme.com
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url).rstrip("/")
        if url in ("http://acme.com", "https://acme.com"):
            return httpx.Response(301, headers={"Location": "https://www.acme.com"})
        elif url in ("http://www.acme.com", "https://www.acme.com"):
            return httpx.Response(301, headers={"Location": "https://acme.com"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        report = await HostRedirectProber.probe_domain("acme.com", client=client)

        assert report.has_redirect_loop is True
        assert report.proper_301_consolidation is False


@pytest.mark.asyncio
async def test_detects_redirect_to_4xx():
    """
    Test redirecting to broken 4xx terminal page.
    """
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url).rstrip("/")
        if url == "http://acme.com":
            return httpx.Response(301, headers={"Location": "https://acme.com/missing"})
        elif url == "https://acme.com/missing":
            return httpx.Response(404, text="Not Found")
        return httpx.Response(200, text="OK")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        report = await HostRedirectProber.probe_domain("acme.com", client=client)

        assert report.redirects_to_4xx is True
        assert report.proper_301_consolidation is False
