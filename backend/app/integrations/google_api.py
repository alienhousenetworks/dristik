"""
Live Google API helpers for Search Console and GA4.

A credentials file is not a measurement. These helpers either return the
API payload or raise. Callers must not label a failure as MEASURED.
"""
from __future__ import annotations

import json
import time
from base64 import urlsafe_b64encode
from typing import Any, Dict, List
from urllib.parse import quote

import httpx


_GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
_GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def load_service_account(credentials_path: str) -> Dict[str, Any]:
    with open(credentials_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("type") != "service_account" or not data.get("private_key") or not data.get("client_email"):
        raise ValueError("Credentials file is not a Google service account JSON with client_email and private_key.")
    return data


def _b64(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def service_account_access_token(credentials_path: str, scopes: List[str], timeout: float = 15.0) -> str:
    """Exchange a service-account JWT for an OAuth access token. Raises on failure."""
    account = load_service_account(credentials_path)
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:
        raise RuntimeError(
            "The cryptography package is required to sign Google service-account tokens."
        ) from exc

    now = int(time.time())
    header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode("utf-8"))
    claims = _b64(json.dumps({
        "iss": account["client_email"],
        "scope": " ".join(scopes),
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }).encode("utf-8"))
    signing_input = f"{header}.{claims}".encode("ascii")
    key = serialization.load_pem_private_key(account["private_key"].encode("utf-8"), password=None)
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input.decode("ascii") + "." + _b64(signature)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
    if response.status_code != 200:
        raise RuntimeError(f"Google token exchange failed ({response.status_code}): {response.text[:300]}")
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Google token exchange returned no access_token.")
    return str(token)


def query_search_console(credentials_path: str, domain: str, days: int = 90, timeout: float = 20.0) -> Dict[str, Any]:
    """Query Search Analytics. Raises unless Google returns HTTP 200."""
    token = service_account_access_token(credentials_path, [_GSC_SCOPE], timeout=timeout)
    end = time.strftime("%Y-%m-%d", time.gmtime())
    start = time.strftime("%Y-%m-%d", time.gmtime(time.time() - max(1, days) * 86400))
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query"],
        "rowLimit": 25,
    }
    site_candidates = [f"sc-domain:{domain}", f"https://{domain}/", f"https://{domain}"]
    last_error = "No Search Console property matched this domain."
    with httpx.Client(timeout=timeout) as client:
        for site in site_candidates:
            url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query"
            response = client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                return response.json()
            last_error = f"{site} -> HTTP {response.status_code}: {response.text[:240]}"
    raise RuntimeError(last_error)


def query_ga4(credentials_path: str, property_id: str, timeout: float = 20.0) -> Dict[str, Any]:
    """Run a 30-day GA4 report. Raises unless the Data API returns HTTP 200."""
    token = service_account_access_token(credentials_path, [_GA4_SCOPE], timeout=timeout)
    clean = property_id.strip()
    if clean.startswith("properties/"):
        clean = clean.split("/", 1)[1]
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{clean}:runReport"
    body = {
        "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
            {"name": "conversions"},
            {"name": "engagementRate"},
        ],
        "limit": 1,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        raise RuntimeError(f"GA4 Data API failed ({response.status_code}): {response.text[:300]}")
    return response.json()
