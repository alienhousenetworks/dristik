from urllib.parse import urlparse, urlunparse

def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    return urlunparse((scheme, netloc, path, "", "", ""))
