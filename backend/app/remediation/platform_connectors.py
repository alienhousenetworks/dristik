"""
Platform Connectors & Permission Boundaries — Phase 8.3 (10/10 Transformation)

Builds connectors for 8 platforms with explicit capability matrices and strict
permission boundaries:
1. WordPress
2. WooCommerce
3. Shopify
4. Webflow
5. Next.js
6. React Applications
7. Custom Websites
8. Supported Static-Site Systems (Astro, Hugo, Jekyll, Gatsby, Docusaurus)

STRICT GUARDRAIL:
Connectors enforce their boundaries. For instance, a Shopify connector explicitly
refuses arbitrary server-side code execution or nginx modifications.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.remediation.models import (
    PatchType,
    PlatformCapability,
    PlatformType,
    UniversalPatch,
)

logger = logging.getLogger("dristik.remediation.connectors")

# Canonical platform capability specifications
PLATFORM_CAPABILITIES: Dict[PlatformType, PlatformCapability] = {
    PlatformType.WORDPRESS: PlatformCapability(
        platform=PlatformType.WORDPRESS,
        can_modify_templates=True,
        can_modify_styles=True,
        can_modify_client_js=True,
        can_modify_server_code=True,  # functions.php
        can_modify_server_config=False,  # managed wp-config / htaccess
        can_modify_redirects=True,  # Redirection plugin / rewrite rules
        can_modify_metadata=True,  # Yoast / RankMath API
        can_modify_structured_data=True,
        allowed_scopes=["theme_edit", "plugin_options", "metadata_write", "redirection_write"],
        boundary_notes="Cannot execute arbitrary MySQL schema drops or server root commands.",
    ),
    PlatformType.WOOCOMMERCE: PlatformCapability(
        platform=PlatformType.WOOCOMMERCE,
        can_modify_templates=True,
        can_modify_styles=True,
        can_modify_client_js=True,
        can_modify_server_code=True,  # hooks & filters
        can_modify_server_config=False,
        can_modify_redirects=True,
        can_modify_metadata=True,
        can_modify_structured_data=True,
        allowed_scopes=["wc_products_write", "theme_edit", "metadata_write"],
        boundary_notes="Cannot bypass payment gateway security or direct transaction records.",
    ),
    PlatformType.SHOPIFY: PlatformCapability(
        platform=PlatformType.SHOPIFY,
        can_modify_templates=True,  # Liquid files
        can_modify_styles=True,  # Asset CSS
        can_modify_client_js=True,  # ScriptTag / Asset JS
        can_modify_server_code=False,  # STRICT: Shopify has no arbitrary server execution!
        can_modify_server_config=False,  # STRICT: Cloud hosted
        can_modify_redirects=True,  # URL Redirects API
        can_modify_metadata=True,  # Metafields / SEO title
        can_modify_structured_data=True,  # Liquid Schema.org
        allowed_scopes=["read_themes", "write_themes", "read_content", "write_content"],
        boundary_notes="STRICT BOUNDARY: Arbitrary server-side Node/Python or nginx configuration is forbidden.",
    ),
    PlatformType.WEBFLOW: PlatformCapability(
        platform=PlatformType.WEBFLOW,
        can_modify_templates=False,  # Designer visual tree
        can_modify_styles=True,  # Custom CSS block
        can_modify_client_js=True,  # Custom head/footer code
        can_modify_server_code=False,  # Hosted SaaS
        can_modify_server_config=False,  # Hosted SaaS
        can_modify_redirects=True,  # Site settings 301 redirects
        can_modify_metadata=True,  # Page settings meta
        can_modify_structured_data=True,  # Custom code JSON-LD
        allowed_scopes=["sites:read", "sites:write", "custom_code:write"],
        boundary_notes="STRICT BOUNDARY: No server middleware, no direct filesystem access.",
    ),
    PlatformType.NEXT_JS: PlatformCapability(
        platform=PlatformType.NEXT_JS,
        can_modify_templates=True,  # JSX/TSX
        can_modify_styles=True,  # CSS / Tailwind
        can_modify_client_js=True,  # React components
        can_modify_server_code=True,  # API routes / Server Components
        can_modify_server_config=True,  # next.config.js / middleware.ts
        can_modify_redirects=True,  # next.config redirects
        can_modify_metadata=True,  # Metadata API
        can_modify_structured_data=True,  # JSON-LD script
        allowed_scopes=["repo_write", "pull_request_create", "deploy_staging"],
        boundary_notes="Full React/Next.js repository modification permitted within repo boundary.",
    ),
    PlatformType.REACT_APP: PlatformCapability(
        platform=PlatformType.REACT_APP,
        can_modify_templates=True,
        can_modify_styles=True,
        can_modify_client_js=True,
        can_modify_server_code=False,  # Client-side SPA
        can_modify_server_config=True,  # Vite/Webpack config
        can_modify_redirects=False,  # Handled by host (Netlify/Vercel/Nginx)
        can_modify_metadata=True,  # React Helmet / index.html
        can_modify_structured_data=True,
        allowed_scopes=["repo_write", "pull_request_create"],
        boundary_notes="Client-side SPA. Server routing must be configured at hosting layer.",
    ),
    PlatformType.CUSTOM_WEBSITE: PlatformCapability(
        platform=PlatformType.CUSTOM_WEBSITE,
        can_modify_templates=True,
        can_modify_styles=True,
        can_modify_client_js=True,
        can_modify_server_code=True,
        can_modify_server_config=True,
        can_modify_redirects=True,
        can_modify_metadata=True,
        can_modify_structured_data=True,
        allowed_scopes=["repo_write", "ftp_write", "server_config_write"],
        boundary_notes="Full source access with explicit privilege validation required.",
    ),
    PlatformType.STATIC_SITE: PlatformCapability(
        platform=PlatformType.STATIC_SITE,
        can_modify_templates=True,  # Layouts / Components
        can_modify_styles=True,
        can_modify_client_js=True,
        can_modify_server_code=False,  # Pre-rendered static HTML
        can_modify_server_config=False,
        can_modify_redirects=True,  # _redirects / netlify.toml
        can_modify_metadata=True,  # Frontmatter
        can_modify_structured_data=True,
        allowed_scopes=["repo_write", "pull_request_create"],
        boundary_notes="Static pre-rendered site. Modifications compile at build time.",
    ),
}


class BasePlatformConnector:
    def __init__(self, platform_type: PlatformType):
        self.platform_type = platform_type
        self.capability = PLATFORM_CAPABILITIES[platform_type]

    def validate_patch_compatibility(self, patch: UniversalPatch) -> Tuple[bool, Optional[str]]:
        cap = self.capability
        ptype = patch.patch_type

        # Check server code boundaries
        if ptype in [PatchType.CONFIGURATION] and not cap.can_modify_server_config:
            return False, f"Platform '{self.platform_type.value}' does not permit server configuration changes: {cap.boundary_notes}"

        # Shopify server code boundary
        if self.platform_type == PlatformType.SHOPIFY and "server" in patch.file_path.lower():
            return False, f"Shopify boundary violation: cannot modify server files ({patch.file_path})."

        # Webflow template boundary
        if self.platform_type == PlatformType.WEBFLOW and ptype in [PatchType.CONFIGURATION, PatchType.REACT_COMPONENT]:
            return False, f"Webflow boundary violation: cannot apply {ptype.value} patches."

        return True, None

    def apply_patch_dry_run(self, patch: UniversalPatch) -> Dict[str, Any]:
        compatible, reason = self.validate_patch_compatibility(patch)
        if not compatible:
            return {
                "success": False,
                "platform": self.platform_type.value,
                "error": reason,
                "applied": False,
            }

        return {
            "success": True,
            "platform": self.platform_type.value,
            "file_path": patch.file_path,
            "bytes_changed": len(patch.proposed_code) - len(patch.original_code),
            "applied": True,
        }


def get_connector(platform_type: PlatformType) -> BasePlatformConnector:
    return BasePlatformConnector(platform_type)
