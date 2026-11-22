"""
Dristik Frontier AI Remediation & Roadmap Synthesizer (Phase 5)

Generates tech-stack-aware, evidence-grounded CodePatch / RemediationPatch packs
and dynamic 7/30/90-day + Top-10 execution roadmaps strictly anchored to verified
findings, real crawled HTML/sections, and AI copywriting rewrites.

Every generated patch passes:
1. PatchValidator syntax / AST safety checks
2. JSON-LD validation (when schema patch)
3. Anti-fabrication gate (rejects dummy social links, placeholder image paths,
   example.com URLs, and generic boilerplate copy)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.domain.enums import (
    Category,
    PatchApprovalStatus,
    PatchOperation,
    PatchRiskLevel,
    ReleaseStatus,
    VerificationStatus,
)
from app.domain.models import (
    BusinessProfile,
    CodePatch,
    ExecutiveActionItem,
    ExecutiveTopActionsPlan,
    Finding,
    PageEvidence,
    PageReport,
    RemediationPatch,
    RoadmapItem,
)
from app.remediation.validator import PatchValidator

logger = logging.getLogger("dristik.remediation.ai_synthesizer")

_FORBIDDEN_PATCH_PATTERNS = re.compile(
    r"(/assets/hero-banner\.png|for\s+modern\s+teams|https?://(?:www\.)?example\.com\b|"
    r"your-brand-here|placeholder\.com|lorem\s+ipsum)",
    re.IGNORECASE,
)


def _detect_tech_stack_from_pages(pages: Optional[List[PageEvidence]]) -> Dict[str, Any]:
    html_blob = ""
    hdr_blob = ""
    for p in (pages or [])[:6]:
        hdrs = getattr(p, "response_headers", None) or {}
        if isinstance(hdrs, dict):
            hdr_blob += " ".join(f"{k}:{v}" for k, v in hdrs.items()).lower() + " "
        raw = str(getattr(p, "raw_html", None) or getattr(p, "rendered_html", None) or "")
        html_blob += raw[:20000].lower() + " "
    frameworks: List[str] = []
    if "/_next/" in html_blob or "__next_data__" in html_blob or "next.js" in hdr_blob:
        frameworks.append("nextjs")
    if "wp-content/" in html_blob or "wp-includes/" in html_blob:
        frameworks.append("wordpress")
    if "cdn.shopify.com" in html_blob or "shopify.theme" in html_blob:
        frameworks.append("shopify")
    if "data-wf-domain" in html_blob or "webflow" in html_blob:
        frameworks.append("webflow")
    return {
        "primary_framework": frameworks[0] if frameworks else "static_html",
        "frameworks_detected": frameworks,
    }


def _parse_category(raw: Any, default: Category = Category.TECHNICAL_SEO) -> Category:
    val = str(raw or "").strip().upper()
    for c in Category:
        if c.value.upper() == val or c.name.upper() == val:
            return c
    return default


def _parse_operation(raw: Any) -> PatchOperation:
    val = str(raw or "REPLACE").strip().upper()
    for op in PatchOperation:
        if op.value.upper() == val or op.name.upper() == val:
            return op
    return PatchOperation.REPLACE


def _parse_risk(raw: Any) -> PatchRiskLevel:
    val = str(raw or "REVIEW_REQUIRED").strip().upper()
    for r in PatchRiskLevel:
        if r.value.upper() == val or r.name.upper() == val:
            return r
    return PatchRiskLevel.REVIEW_REQUIRED


def _is_fabricated_snippet(snippet: str, observed_urls: set) -> bool:
    if not snippet or len(snippet.strip()) < 10:
        return True
    if _FORBIDDEN_PATCH_PATTERNS.search(snippet):
        return True
    # Reject invented linkedin/twitter/facebook URLs that were not actually crawled on the site
    for social_match in re.findall(r"https?://(?:www\.)?(?:linkedin|twitter|x|facebook|instagram)\.com/[^\s\"'<>]+", snippet, re.I):
        if social_match.rstrip("/").lower() not in observed_urls:
            return True
    return False


def _validate_jsonld_block(snippet: str) -> bool:
    """Validate JSON-LD payload if snippet contains JSON-LD script or bare JSON."""
    raw = snippet.strip()
    m = re.search(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", raw, re.I | re.S)
    candidate = m.group(1).strip() if m else (raw if raw.startswith("{") else "")
    if not candidate:
        return True
    try:
        parsed = json.loads(candidate)
        return isinstance(parsed, (dict, list)) and ("@context" in parsed or "@graph" in parsed or isinstance(parsed, list))
    except Exception:
        return False


class AiRemediationSynthesizer:
    """Frontier AI synthesizer for tech-stack-aware remediation patches & dynamic roadmaps."""

    def __init__(self, model_router: Any):
        self.model_router = model_router
        self.validator = PatchValidator()

    async def synthesize_patches(
        self,
        *,
        findings: List[Finding],
        business_profile: Optional[BusinessProfile],
        website_url: str,
        pages: Optional[List[PageEvidence]] = None,
        page_reports: Optional[List[PageReport]] = None,
        competitor_context: Optional[Dict[str, Any]] = None,
        max_patches: int = 8,
    ) -> Tuple[List[CodePatch], List[RemediationPatch]]:
        """Synthesize validated, tech-stack-aware CodePatch & RemediationPatch items via Frontier AI."""
        if not self.model_router or not hasattr(self.model_router, "generate_structured"):
            return [], []

        actionable = [
            f for f in (findings or [])
            if not getattr(f, "held_from_executive", False)
        ]
        if not actionable:
            return [], []

        tech_stack = _detect_tech_stack_from_pages(pages)
        sev_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        top_findings = sorted(
            actionable,
            key=lambda f: (
                sev_rank.get(str(getattr(getattr(f, "severity", ""), "value", getattr(f, "severity", ""))).upper(), 0),
                int(getattr(f, "priority", 5) or 5),
            ),
            reverse=True,
        )[:12]

        # Collect real observed social/site URLs for anti-fabrication checking
        observed_urls: set = set()
        for p in (pages or []):
            if getattr(p, "url", None):
                observed_urls.add(p.url.rstrip("/").lower())
            footer = getattr(p, "footer_info", None) or {}
            if isinstance(footer, dict):
                for s_url in (footer.get("social_links") or []):
                    observed_urls.add(str(s_url).rstrip("/").lower())

        copy_hints = []
        for pr in (page_reports or [])[:5]:
            sugg = getattr(getattr(pr, "copywriting", None), "suggested", None)
            if sugg:
                copy_hints.append({
                    "url": pr.url,
                    "suggested_title": getattr(sugg, "title", None),
                    "suggested_meta": getattr(sugg, "meta_description", None),
                    "suggested_h1": getattr(sugg, "h1", None),
                })

        findings_payload = [
            {
                "finding_id": f.finding_id,
                "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "title": (f.title or f.finding or "")[:200],
                "affected_urls": (f.affected_urls or [website_url])[:3],
                "recommendation": (f.recommendation or "")[:260],
            }
            for f in top_findings
        ]
        schema_desc = (
            '{"patches":[{"finding_id":"string (MUST match an input finding_id)",'
            '"title":"string","category":"TECHNICAL_SEO|ON_PAGE_SEO|SCHEMA|GEO|AI_SEARCH|UX_CONVERSION|CONTENT",'
            '"target_url":"string","target_file":"string (appropriate for detected framework)",'
            '"operation":"INSERT_HEAD|REPLACE|APPEND|CREATE_FILE|UPDATE_META",'
            '"risk_level":"SAFE_AUTO|REVIEW_REQUIRED|HIGH_RISK",'
            '"before_snippet":"string (optional observed snippet)",'
            '"after_snippet":"string (exact drop-in HTML, JSON-LD, robots.txt, or framework code)",'
            '"explanation":"string (why this fixes the verified finding)"}]}'
        )
        contract = (
            f"WEBSITE: {website_url}\n"
            f"BRAND: {getattr(business_profile, 'business_name', None) or website_url} | "
            f"INDUSTRY: {getattr(business_profile, 'industry', None) or 'Unknown'}\n"
            f"DETECTED TECH STACK: {json.dumps(tech_stack)}\n"
            f"VERIFIED FINDINGS:\n{json.dumps(findings_payload, indent=2)}\n\n"
            f"APPROVED AI COPY REWRITES (reuse where relevant):\n{json.dumps(copy_hints, indent=2)}\n\n"
            "INSTRUCTIONS:\n"
            f"1. Generate up to {max_patches} production-ready, drop-in remediation patches for the highest-impact findings.\n"
            "2. Match `target_file` and syntax strictly to DETECTED TECH STACK (never output Next.js `layout.tsx` unless nextjs is detected; "
            "use WordPress/Shopify/static HTML conventions otherwise).\n"
            "3. ZERO FABRICATION: Never invent LinkedIn/Twitter URLs, placeholder image paths, example.com domains, prices, or certifications not in the inputs.\n"
            "4. JSON-LD patches must be valid JSON with `@context`: `https://schema.org`."
        )

        try:
            raw = await self.model_router.generate_structured(
                capability="remediation_synthesis",
                agent_role="Principal Full-Stack SEO/GEO/CRO Remediation Engineer",
                task_contract=contract,
                evidence_list=[],
                output_schema_desc=schema_desc,
                max_claims=max_patches,
                allow_fallback=False,
                model_tier="reasoning_model",
            )
        except Exception as exc:
            logger.warning("AI remediation synthesis failed: %s", exc)
            return [], []

        if not isinstance(raw, dict) or str(raw.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
            return [], []

        valid_fids = {f.finding_id: f for f in top_findings}
        code_patches: List[CodePatch] = []
        rem_patches: List[RemediationPatch] = []

        for idx, item in enumerate((raw.get("patches") or [])[:max_patches], start=1):
            if not isinstance(item, dict):
                continue
            fid = str(item.get("finding_id") or "").strip()
            if fid not in valid_fids:
                continue
            after_snip = str(item.get("after_snippet") or "").strip()
            if _is_fabricated_snippet(after_snip, observed_urls):
                logger.info("Rejected fabricated AI patch snippet for %s", fid)
                continue
            if not _validate_jsonld_block(after_snip):
                logger.info("Rejected invalid JSON-LD in AI patch for %s", fid)
                continue

            cat = _parse_category(item.get("category"), default=valid_fids[fid].category)
            target_file = str(item.get("target_file") or "index.html").strip()
            # Guard against Next.js file hallucinations on non-Next.js sites
            if tech_stack["primary_framework"] != "nextjs" and ("layout.tsx" in target_file or "next.config" in target_file):
                target_file = "index.html"
            title = str(item.get("title") or valid_fids[fid].title or f"Fix {fid}").strip()[:180]
            explanation = str(item.get("explanation") or valid_fids[fid].recommendation or "").strip()[:500]
            before_snip = str(item.get("before_snippet") or "").strip() or None
            target_url = str(item.get("target_url") or (valid_fids[fid].affected_urls[0] if valid_fids[fid].affected_urls else website_url)).strip()
            pid = f"ai_patch_{idx:02d}_{uuid.uuid4().hex[:6]}"

            cp = CodePatch(
                patch_id=pid,
                title=title,
                category=cat,
                target_file=target_file,
                before_snippet=before_snip,
                after_snippet=after_snip,
                explanation=explanation,
                release_status=ReleaseStatus.PENDING_APPROVAL,
            )
            val_res = self.validator.validate_patch(cp)
            if not val_res.is_valid:
                logger.info("PatchValidator rejected AI patch %s: %s", pid, val_res.issues)
                continue

            code_patches.append(cp)
            rem_patches.append(
                RemediationPatch(
                    patch_id=pid,
                    finding_id=fid,
                    title=title,
                    category=cat,
                    risk_level=_parse_risk(item.get("risk_level")),
                    target_url=target_url,
                    target_file=target_file,
                    operation=_parse_operation(item.get("operation")),
                    before_snippet=before_snip,
                    after_snippet=after_snip,
                    explanation=explanation,
                    confidence=0.90,
                    approval_status=PatchApprovalStatus.PENDING,
                    verification_status=VerificationStatus.PROVISIONAL,
                    metadata_payload={"synthesized_by": "frontier_ai", "tech_stack": tech_stack["primary_framework"]},
                )
            )

        return code_patches, rem_patches

    async def synthesize_roadmap(
        self,
        *,
        findings: List[Finding],
        business_profile: Optional[BusinessProfile],
        website_url: str,
        narrative: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[List[RoadmapItem], List[RoadmapItem], List[RoadmapItem], ExecutiveTopActionsPlan]]:
        """Synthesize a dynamic Frontier AI 7/30/90-day + Top-10 roadmap strictly anchored to verified findings."""
        if not self.model_router or not hasattr(self.model_router, "generate_structured"):
            return None

        actionable = [f for f in (findings or []) if not getattr(f, "held_from_executive", False)]
        if not actionable:
            return None

        sev_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        ranked = sorted(
            actionable,
            key=lambda f: (
                sev_rank.get(str(getattr(getattr(f, "severity", ""), "value", getattr(f, "severity", ""))).upper(), 0),
                int(getattr(f, "priority", 5) or 5),
            ),
            reverse=True,
        )[:25]
        valid_fids = {f.finding_id: f for f in ranked}

        f_rows = [
            {
                "finding_id": f.finding_id,
                "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "title": (f.title or f.finding or "")[:180],
                "recommendation": (f.recommendation or "")[:240],
                "affected_urls": (f.affected_urls or [])[:3],
                "effort": f.effort,
            }
            for f in ranked
        ]
        schema_desc = (
            '{"roadmap_7_days":[{"title":"string","description":"string","related_finding_id":"string","impact":"High|Medium|Low","effort":"Low|Medium|High","owner_role":"string","estimated_hours":"string","verification_step":"string"}],'
            '"roadmap_30_days":[...],"roadmap_90_days":[...],'
            '"top_10_actions":[{"priority":"P0|P1|P2","action":"string","related_finding_id":"string","impact":"Very High|High|Medium","effort":"Low|Medium|High","expected_outcome":"string","estimated_engineer_hours":3,"dependencies":["string"],"validation":"string"}],'
            '"dependencies_flow":"string"}'
        )
        contract = (
            f"WEBSITE: {website_url}\n"
            f"BRAND: {getattr(business_profile, 'business_name', None) or website_url} | "
            f"MODEL: {getattr(business_profile, 'business_model', None) or 'Unknown'} | "
            f"INDUSTRY: {getattr(business_profile, 'industry', None) or 'Unknown'}\n"
            f"VERIFIED FINDINGS:\n{json.dumps(f_rows, indent=2)}\n\n"
            "Build a tailored 7-day, 30-day, 90-day execution roadmap and prioritized Top-10 Action Plan.\n"
            "STRICT RULES:\n"
            "1. EVERY item MUST cite an exact `related_finding_id` from VERIFIED FINDINGS above.\n"
            "2. NEVER include generic boilerplate actions unrelated to the findings.\n"
            "3. Sequence dependencies logically (e.g. crawl/indexation & hero clarity in 7-day, schema/AEO depth in 30-day, authority/scale in 90-day)."
        )

        try:
            raw = await self.model_router.generate_structured(
                capability="roadmap_synthesis",
                agent_role="Principal Growth & Technical Execution Program Manager",
                task_contract=contract,
                evidence_list=[],
                output_schema_desc=schema_desc,
                max_claims=15,
                allow_fallback=False,
                model_tier="reasoning_model",
            )
        except Exception as exc:
            logger.warning("AI roadmap synthesis failed: %s", exc)
            return None

        if not isinstance(raw, dict) or str(raw.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
            return None

        def _parse_bucket(key: str, timeframe: str, badge: str) -> List[RoadmapItem]:
            out: List[RoadmapItem] = []
            for row in (raw.get(key) or [])[:8]:
                if not isinstance(row, dict):
                    continue
                fid = str(row.get("related_finding_id") or "").strip()
                if fid not in valid_fids:
                    continue
                f_obj = valid_fids[fid]
                title = str(row.get("title") or f_obj.title or "").strip()
                desc = str(row.get("description") or f_obj.recommendation or "").strip()
                if not title:
                    continue
                out.append(
                    RoadmapItem(
                        timeframe=timeframe,
                        title=title[:180],
                        description=desc[:500],
                        impact=str(row.get("impact") or "High"),
                        effort=str(row.get("effort") or "Medium"),
                        category=f_obj.category,
                        related_finding_id=fid,
                        owner_role=str(row.get("owner_role") or "Engineering Lead"),
                        estimated_hours=str(row.get("estimated_hours") or "2–4 hours"),
                        verification_step=str(row.get("verification_step") or f"Re-test finding {fid} via automated verification."),
                        priority_badge=badge,
                    )
                )
            return out

        r7 = _parse_bucket("roadmap_7_days", "7_days", "P0 Blocker")
        r30 = _parse_bucket("roadmap_30_days", "30_days", "P1 Sprint Priority")
        r90 = _parse_bucket("roadmap_90_days", "90_days", "P2 Strategic Architecture")

        top_actions: List[ExecutiveActionItem] = []
        for idx, row in enumerate((raw.get("top_10_actions") or [])[:10], start=1):
            if not isinstance(row, dict):
                continue
            fid = str(row.get("related_finding_id") or "").strip()
            if fid not in valid_fids:
                continue
            f_obj = valid_fids[fid]
            act_title = str(row.get("action") or f_obj.title or "").strip()
            if not act_title:
                continue
            hours_raw = row.get("estimated_engineer_hours")
            try:
                hours_int = max(1, min(40, int(hours_raw)))
            except Exception:
                hours_int = 3
            top_actions.append(
                ExecutiveActionItem(
                    rank=len(top_actions) + 1,
                    priority=str(row.get("priority") or ("P0" if idx <= 3 else ("P1" if idx <= 7 else "P2"))),
                    action=act_title[:180],
                    impact=str(row.get("impact") or "High"),
                    effort=str(row.get("effort") or "Medium"),
                    expected_outcome=str(row.get("expected_outcome") or f_obj.business_impact or f_obj.why_it_matters or "Resolves verified audit finding.")[:260],
                    estimated_engineer_hours=hours_int,
                    dependencies=[str(d) for d in (row.get("dependencies") or [])[:4] if d],
                    validation=str(row.get("validation") or f"Automated retest confirms {fid} is resolved."),
                    category=f_obj.category,
                    related_finding_id=fid,
                )
            )

        if not (r7 or r30 or r90) or not top_actions:
            return None

        top_plan = ExecutiveTopActionsPlan(
            actions=top_actions,
            total_engineer_hours=sum(a.estimated_engineer_hours for a in top_actions),
            dependencies_flow=str(raw.get("dependencies_flow") or " → ".join(a.action for a in top_actions[:4])),
            validation_mode="automated_retest",
        )
        return r7, r30, r90, top_plan
