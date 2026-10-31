"""
Dristik AI WordPress Site Structure & SEO Discovery.

Discovers real WordPress pages, posts, REST API namespaces,
and indicators of installed SEO integrations.
"""

from typing import Any, Dict, List, Optional

import httpx

from app.connectors.wordpress.client import WordPressClient


class WordPressDiscovery:
    def __init__(self, client: WordPressClient):
        self.client = client

    @staticmethod
    def _extract_title(item: Dict[str, Any]) -> str:
        """Extract the rendered title from a WordPress resource."""
        title = item.get("title", {})

        if isinstance(title, dict):
            return str(title.get("rendered", ""))

        return str(title or "")

    @staticmethod
    def _extract_namespace_info(
        namespaces: List[str],
    ) -> Dict[str, Any]:
        """Identify SEO and WooCommerce indicators from REST namespaces."""
        seo_plugins = {
            "yoast": ("yoast", "yoast/v1", "yoast/v2"),
            "rank_math": ("rankmath", "rankmath/v1"),
            "aioseo": ("aioseo", "aioseo/v1"),
        }

        detected_seo_handler = None

        for handler, indicators in seo_plugins.items():
            if any(
                namespace == indicator
                or namespace.startswith(indicator + "/")
                for namespace in namespaces
                for indicator in indicators
            ):
                detected_seo_handler = handler
                break

        woocommerce_detected = any(
            namespace == "wc/v3"
            or namespace.startswith("wc/v3/")
            for namespace in namespaces
        )

        return {
            "detected_seo_handler": detected_seo_handler,
            "woocommerce_detected": woocommerce_detected,
        }

    async def _fetch_resources(
        self,
        endpoint: str,
        resource_type: str,
        errors: List[str],
    ) -> Dict[str, Any]:
        """
        Fetch up to 10 pages or posts.

        Returns actual resource data and the total reported by WordPress,
        when available.
        """
        try:
            response = await self.client.get(
                endpoint,
                params={
                    "per_page": 10,
                    "_fields": "id,date,slug,link,title,status,parent",
                },
            )

            if response.status_code != 200:
                errors.append(
                    f"{resource_type}: WordPress returned HTTP "
                    f"{response.status_code}."
                )
                return {"items": [], "total": None}

            data = response.json()

            if not isinstance(data, list):
                errors.append(
                    f"{resource_type}: unexpected response format."
                )
                return {"items": [], "total": None}

            items = []

            for item in data:
                if not isinstance(item, dict):
                    continue

                items.append(
                    {
                        "id": item.get("id"),
                        "title": self._extract_title(item),
                        "slug": item.get("slug"),
                        "url": item.get("link"),
                        "status": item.get("status"),
                        "date": item.get("date"),
                        "parent": item.get("parent"),
                    }
                )

            total_header = response.headers.get("X-WP-Total")

            try:
                total = int(total_header) if total_header is not None else None
            except (ValueError, TypeError):
                total = None

            if total is None:
                # This is the number returned in this response, not necessarily
                # the total number of resources on the site.
                total = len(items) if len(items) < 10 else None

            return {"items": items, "total": total}

        except httpx.TimeoutException:
            errors.append(f"{resource_type}: request timed out.")

        except httpx.RequestError as exc:
            errors.append(
                f"{resource_type}: connection error ({type(exc).__name__})."
            )

        except ValueError:
            errors.append(
                f"{resource_type}: WordPress returned invalid JSON."
            )

        return {"items": [], "total": None}

    async def discover(self) -> Dict[str, Any]:
        """
        Discover WordPress pages, posts, REST namespaces, and SEO indicators.

        Discovery is read-only. It does not modify the WordPress site.
        """
        errors: List[str] = []

        result: Dict[str, Any] = {
            "site_url": self.client.base_url,
            "cms": "WordPress",
            "version": None,
            "detected_seo_handler": None,
            "total_pages_found": None,
            "total_posts_found": None,
            "woocommerce_detected": False,
            "rest_api_available": False,
            "namespaces": [],
            "capabilities": [
                "read_pages",
                "read_posts",
            ],
            "sample_pages": [],
            "sample_posts": [],
            "discovery_errors": errors,
        }

        if not self.client.base_url:
            errors.append("WordPress URL is required.")
            return result

        # Step 1: Discover REST API namespaces.
        try:
            response = await self.client.get("/wp-json/")

            if response.status_code == 200:
                data = response.json()

                if isinstance(data, dict):
                    result["rest_api_available"] = True

                    namespaces = data.get("namespaces", [])

                    if isinstance(namespaces, list):
                        result["namespaces"] = [
                            namespace
                            for namespace in namespaces
                            if isinstance(namespace, str)
                        ]

                    info = data.get("site", {})

                    if isinstance(info, dict):
                        result["version"] = info.get("version")

                    result.update(
                        self._extract_namespace_info(result["namespaces"])
                    )

            else:
                errors.append(
                    "REST API root returned HTTP "
                    f"{response.status_code}."
                )

        except httpx.TimeoutException:
            errors.append("REST API root request timed out.")

        except httpx.RequestError as exc:
            errors.append(
                f"REST API root connection error ({type(exc).__name__})."
            )

        except ValueError:
            errors.append("REST API root returned invalid JSON.")

        # Step 2: Discover actual pages.
        pages_result = await self._fetch_resources(
            "/wp-json/wp/v2/pages",
            "Pages",
            errors,
        )

        result["sample_pages"] = pages_result["items"]
        result["total_pages_found"] = pages_result["total"]

        # Step 3: Discover actual posts.
        posts_result = await self._fetch_resources(
            "/wp-json/wp/v2/posts",
            "Posts",
            errors,
        )

        result["sample_posts"] = posts_result["items"]
        result["total_posts_found"] = posts_result["total"]

        # Avoid claiming that SEO metadata can be updated merely because
        # the REST API is reachable. That requires separate verification.
        if result["detected_seo_handler"]:
            result["capabilities"].append("seo_handler_detected")

        return result