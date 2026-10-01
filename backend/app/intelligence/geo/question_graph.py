"""
Scaled 50-Question Answerability Engine (Dynamic Question Graph).
Layer 1 Extractability: What Dristik can prove deterministically from the website itself.

Generates a website-specific 50-question benchmark graph across 8 key buyer intent dimensions:
1. Entity Identity (5 questions)
2. Core Capabilities & Services (10 questions)
3. Target Audience & ICP (5 questions)
4. Pricing & Commercial Terms (7 questions)
5. Security, Trust & Compliance (8 questions)
6. Comparative & Differentiators (5 questions)
7. Implementation & Onboarding (5 questions)
8. High-Intent Purchase Actions (5 questions)

Evaluates whether each question is directly answerable from first-party crawled evidence:
Status: SUPPORTED | PARTIAL | UNSUPPORTED | CONFLICTING
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.domain.models import BusinessProfile, PageEvidence, GeoQuestionEvidence


QUESTION_TEMPLATES = [
    # -------------------------------------------------------------
    # 1. Entity Identity (5)
    # -------------------------------------------------------------
    {
        "key": "identity_what",
        "category": "Entity Identity",
        "template": "What is {brand} and what does it do?",
        "needles": ["we are", "is a", "is an", "platform", "provider of", "specializes in", "founded", "company that"],
    },
    {
        "key": "identity_leadership",
        "category": "Entity Identity",
        "template": "Who founded or leads {brand}, and when was it established?",
        "needles": ["founded in", "founded by", "founder", "ceo", "leadership team", "established in", "our story", "executive team"],
    },
    {
        "key": "identity_headquarters",
        "category": "Entity Identity",
        "template": "Where is {brand} headquartered and where does it operate?",
        "needles": ["headquartered in", "based in", "offices in", "locations", "address", "global presence", "registered office"],
    },
    {
        "key": "identity_category",
        "category": "Entity Identity",
        "template": "What specific business category or industry does {brand} belong to?",
        "needles": ["software", "agency", "consulting", "platform", "saas", "technology", "solution", "service provider"],
    },
    {
        "key": "identity_mission",
        "category": "Entity Identity",
        "template": "What is {brand}'s core mission and company purpose?",
        "needles": ["our mission", "we believe", "our vision", "our purpose", "core values", "why we built"],
    },

    # -------------------------------------------------------------
    # 2. Core Capabilities & Services (10)
    # -------------------------------------------------------------
    {
        "key": "caps_primary_offerings",
        "category": "Core Capabilities & Services",
        "template": "What primary products or services does {brand} deliver?",
        "needles": ["services", "products", "offerings", "features", "capabilities", "solutions", "what we do", "modules"],
    },
    {
        "key": "caps_tech_stack",
        "category": "Core Capabilities & Services",
        "template": "What technologies, architectures, or frameworks does {brand} use?",
        "needles": ["python", "react", "fastapi", "aws", "cloud", "api", "node", "kubernetes", "ai", "llm", "technology stack", "built with"],
    },
    {
        "key": "caps_custom_integrations",
        "category": "Core Capabilities & Services",
        "template": "Does {brand} provide custom integrations or a developer API?",
        "needles": ["api", "rest api", "sdk", "webhook", "webhooks", "integrations", "integrate with", "zapier", "slack", "salesforce"],
    },
    {
        "key": "caps_key_deliverables",
        "category": "Core Capabilities & Services",
        "template": "What are the tangible deliverables or outcomes provided by {brand}?",
        "needles": ["deliverables", "deliver", "outcomes", "results", "reports", "codebase", "dashboards", "milestones"],
    },
    {
        "key": "caps_how_it_works",
        "category": "Core Capabilities & Services",
        "template": "How does {brand}'s product or service work step-by-step?",
        "needles": ["how it works", "step 1", "step 2", "workflow", "process", "methodology", "pipeline", "getting started"],
    },
    {
        "key": "caps_deployment_model",
        "category": "Core Capabilities & Services",
        "template": "Can {brand} be deployed in cloud, on-premise, or hybrid environments?",
        "needles": ["cloud", "on-premise", "on premise", "self-hosted", "saas", "hybrid", "aws", "private cloud", "soc 2 compliant cloud"],
    },
    {
        "key": "caps_problem_solved",
        "category": "Core Capabilities & Services",
        "template": "What specific business pain points or operational bottlenecks does {brand} solve?",
        "needles": ["solve", "pain point", "challenge", "automate", "eliminate", "reduce overhead", "bottleneck", "replace"],
    },
    {
        "key": "caps_automation",
        "category": "Core Capabilities & Services",
        "template": "Does {brand} support automated workflows or real-time processing?",
        "needles": ["automation", "automated", "real-time", "real time", "instant", "scheduled", "background jobs", "ai powered"],
    },
    {
        "key": "caps_maintenance_support",
        "category": "Core Capabilities & Services",
        "template": "What ongoing maintenance, updates, or technical support are included with {brand}?",
        "needles": ["maintenance", "support", "updates", "upgrades", "sla", "24/7", "technical assistance", "dedicated manager"],
    },
    {
        "key": "caps_prerequisites",
        "category": "Core Capabilities & Services",
        "template": "What are the technical prerequisites or system requirements to use {brand}?",
        "needles": ["prerequisites", "requirements", "compatible with", "browser", "operating system", "minimum", "dependencies"],
    },

    # -------------------------------------------------------------
    # 3. Target Audience & ICP (5)
    # -------------------------------------------------------------
    {
        "key": "icp_target_customer",
        "category": "Target Audience & ICP",
        "template": "Who is {brand}'s ideal customer profile (ICP)?",
        "needles": ["built for", "designed for", "ideal for", "our customers", "who we serve", "for teams", "for organizations"],
    },
    {
        "key": "icp_enterprise_suitability",
        "category": "Target Audience & ICP",
        "template": "Is {brand} suitable for enterprise-scale organizations?",
        "needles": ["enterprise", "enterprises", "large organizations", "fortune 500", "scale", "unlimited seats", "sso"],
    },
    {
        "key": "icp_smb_startup_suitability",
        "category": "Target Audience & ICP",
        "template": "Does {brand} support early-stage startups and small businesses?",
        "needles": ["startups", "smb", "small business", "founders", "early-stage", "growing teams", "starter"],
    },
    {
        "key": "icp_buyer_roles",
        "category": "Target Audience & ICP",
        "template": "Which buyer personas or department roles purchase {brand}?",
        "needles": ["cto", "cio", "developers", "engineering leads", "product managers", "founders", "marketers", "finance"],
    },
    {
        "key": "icp_verticals",
        "category": "Target Audience & ICP",
        "template": "Which specific industry verticals or sectors does {brand} serve?",
        "needles": ["industries", "healthcare", "fintech", "ecommerce", "saas", "retail", "manufacturing", "education", "legal"],
    },

    # -------------------------------------------------------------
    # 4. Pricing & Commercial Terms (7)
    # -------------------------------------------------------------
    {
        "key": "price_cost",
        "category": "Pricing & Commercial Terms",
        "template": "How much does {brand} cost?",
        "needles": ["pricing", "price", "costs", "$", "€", "£", "₹", "/mo", "/month", "/year", "starting at", "contact sales"],
    },
    {
        "key": "price_tiers",
        "category": "Pricing & Commercial Terms",
        "template": "Does {brand} offer transparent pricing tiers or packaged plans?",
        "needles": ["starter", "pro", "enterprise", "plan", "tiers", "basic", "premium", "unlimited", "packages"],
    },
    {
        "key": "price_free_trial",
        "category": "Pricing & Commercial Terms",
        "template": "Does {brand} provide a free trial, free tier, or proof of concept?",
        "needles": ["free trial", "try for free", "free plan", "14-day trial", "no credit card required", "free tier", "poc"],
    },
    {
        "key": "price_setup_fees",
        "category": "Pricing & Commercial Terms",
        "template": "Are there implementation fees, onboarding costs, or hidden add-ons for {brand}?",
        "needles": ["setup fee", "onboarding fee", "implementation fee", "hidden fees", "no setup fee", "add-on", "one-time fee"],
    },
    {
        "key": "price_billing_cycle",
        "category": "Pricing & Commercial Terms",
        "template": "What billing intervals (monthly vs annual) does {brand} support?",
        "needles": ["billed monthly", "billed annually", "monthly billing", "annual billing", "yearly", "pay as you go", "subscription"],
    },
    {
        "key": "price_volume_discounts",
        "category": "Pricing & Commercial Terms",
        "template": "Does {brand} offer custom enterprise pricing or high-volume discounts?",
        "needles": ["volume discount", "custom pricing", "enterprise pricing", "quote", "talk to sales", "volume tiers"],
    },
    {
        "key": "price_refund_cancellation",
        "category": "Pricing & Commercial Terms",
        "template": "What is {brand}'s cancellation or refund policy?",
        "needles": ["cancel anytime", "refund policy", "money-back guarantee", "cancellation", "30-day guarantee", "terms of service"],
    },

    # -------------------------------------------------------------
    # 5. Security, Trust & Compliance (8)
    # -------------------------------------------------------------
    {
        "key": "trust_data_security",
        "category": "Security, Trust & Compliance",
        "template": "Can customers trust {brand} with confidential or sensitive data?",
        "needles": ["security", "encryption", "aes-256", "tls", "data protection", "secure", "safe", "privacy"],
    },
    {
        "key": "trust_compliance_standards",
        "category": "Security, Trust & Compliance",
        "template": "Does {brand} publish SOC 2, ISO 27001, HIPAA, or GDPR compliance?",
        "needles": ["soc 2", "soc2", "iso 27001", "hipaa", "gdpr", "ccpa", "pci", "compliant", "compliance"],
    },
    {
        "key": "trust_data_privacy",
        "category": "Security, Trust & Compliance",
        "template": "How does {brand} handle customer data privacy and retention?",
        "needles": ["privacy policy", "data retention", "we do not sell your data", "anonymized", "gdpr compliant", "subprocessors"],
    },
    {
        "key": "trust_testimonials",
        "category": "Security, Trust & Compliance",
        "template": "What customer testimonials, case studies, or social proof does {brand} publish?",
        "needles": ["case study", "case studies", "testimonials", "what our clients say", "success stories", "reviews", "rating"],
    },
    {
        "key": "trust_client_logos",
        "category": "Security, Trust & Compliance",
        "template": "Who are verified clients, logos, or partners of {brand}?",
        "needles": ["trusted by", "our partners", "customers include", "used by", "companies rely on", "partnered with"],
    },
    {
        "key": "trust_uptime_sla",
        "category": "Security, Trust & Compliance",
        "template": "Does {brand} offer an SLA or guaranteed uptime percentage?",
        "needles": ["sla", "99.9%", "99.99%", "uptime", "service level agreement", "high availability", "status page"],
    },
    {
        "key": "trust_support_channels",
        "category": "Security, Trust & Compliance",
        "template": "What customer support channels (email, phone, Slack, chat) are available for {brand}?",
        "needles": ["live chat", "email support", "phone support", "dedicated slack", "help center", "ticket", "response time"],
    },
    {
        "key": "trust_third_party_audits",
        "category": "Security, Trust & Compliance",
        "template": "Does {brand} maintain third-party security audits or penetration tests?",
        "needles": ["penetration test", "third-party audit", "security whitepaper", "audited by", "pen test", "bug bounty"],
    },

    # -------------------------------------------------------------
    # 6. Comparative & Differentiators (5)
    # -------------------------------------------------------------
    {
        "key": "diff_alternatives",
        "category": "Comparative & Differentiators",
        "template": "How does {brand} compare to alternatives and direct competitors?",
        "needles": ["vs ", "versus", "alternative", "compared to", "unlike competitors", "competitor", "comparison"],
    },
    {
        "key": "diff_core_moat",
        "category": "Comparative & Differentiators",
        "template": "What is {brand}'s competitive moat or unique value proposition?",
        "needles": ["why choose us", "our advantage", "unique", "differentiator", "only platform that", "patented", "proprietary"],
    },
    {
        "key": "diff_traditional_vs_brand",
        "category": "Comparative & Differentiators",
        "template": "Why should buyers choose {brand} over traditional approaches?",
        "needles": ["traditional", "legacy", "outdated", "faster than", "10x", "modern approach", "next generation"],
    },
    {
        "key": "diff_limitations",
        "category": "Comparative & Differentiators",
        "template": "What known limitations or trade-offs does {brand} disclose?",
        "needles": ["not suitable for", "limitations", "prerequisites", "requires", "dependencies", "best suited for"],
    },
    {
        "key": "diff_migration",
        "category": "Comparative & Differentiators",
        "template": "How easy is it to migrate data or switch to {brand} from a legacy tool?",
        "needles": ["migration", "migrate", "switch from", "import data", "easy migration", "seamless transition", "export"],
    },

    # -------------------------------------------------------------
    # 7. Implementation & Onboarding (5)
    # -------------------------------------------------------------
    {
        "key": "impl_setup_time",
        "category": "Implementation & Onboarding",
        "template": "How long does it take to onboard or implement {brand}?",
        "needles": ["minutes", "setup in", "onboarding time", "days", "weeks", "instant setup", "deploy in", "quickstart"],
    },
    {
        "key": "impl_engineering_effort",
        "category": "Implementation & Onboarding",
        "template": "How much developer or IT effort is required to install {brand}?",
        "needles": ["no code", "low code", "simple install", "npm install", "one line of code", "developer friendly", "api integration"],
    },
    {
        "key": "impl_business_roi",
        "category": "Implementation & Onboarding",
        "template": "What quantifiable business ROI or cost savings does {brand} claim?",
        "needles": ["roi", "save hours", "cost reduction", "% faster", "% increase", "payback period", "revenue growth"],
    },
    {
        "key": "impl_dedicated_success",
        "category": "Implementation & Onboarding",
        "template": "Does {brand} provide dedicated account managers or customer success engineers?",
        "needles": ["customer success", "account manager", "onboarding specialist", "dedicated engineer", "white-glove"],
    },
    {
        "key": "impl_documentation",
        "category": "Implementation & Onboarding",
        "template": "Where can users access {brand}'s API reference, guides, and documentation?",
        "needles": ["documentation", "docs", "api reference", "knowledge base", "guides", "tutorial", "quickstart"],
    },

    # -------------------------------------------------------------
    # 8. High-Intent Purchase Actions (5)
    # -------------------------------------------------------------
    {
        "key": "intent_schedule_demo",
        "category": "High-Intent Purchase Actions",
        "template": "How can prospective buyers schedule a demo or contact {brand}'s sales team?",
        "needles": ["book a demo", "schedule demo", "request demo", "contact sales", "talk to an expert", "get in touch"],
    },
    {
        "key": "intent_self_serve",
        "category": "High-Intent Purchase Actions",
        "template": "Can buyers sign up and start using {brand} self-service without talking to sales?",
        "needles": ["sign up", "get started", "start free", "create account", "instant access", "register"],
    },
    {
        "key": "intent_status_changelog",
        "category": "High-Intent Purchase Actions",
        "template": "Does {brand} publish a public changelog, product updates, or system status page?",
        "needles": ["changelog", "status page", "release notes", "what's new", "updates", "roadmap"],
    },
    {
        "key": "intent_global_currencies",
        "category": "High-Intent Purchase Actions",
        "template": "Does {brand} support international currencies, invoicing, and global payment methods?",
        "needles": ["invoicing", "credit card", "stripe", "wire transfer", "usd", "eur", "gbp", "inr", "currencies"],
    },
    {
        "key": "intent_next_steps",
        "category": "High-Intent Purchase Actions",
        "template": "What is the immediate next step to begin working with {brand}?",
        "needles": ["get started today", "start now", "contact us", "download", "install", "request quote"],
    },
]


class QuestionGraphResult(BaseModel):
    total_questions: int = 50
    supported_count: int = 0
    partial_count: int = 0
    unsupported_count: int = 0
    conflicting_count: int = 0
    answerability_score: float = 0.0  # 0 to 100
    headline: str = ""
    category_scores: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    questions: List[GeoQuestionEvidence] = Field(default_factory=list)
    summary: str = ""


class GeoQuestionGraphEngine:
    """
    Evaluates 50 structured buyer intent questions against crawled content.
    """

    def __init__(self, brand_name: str = ""):
        self.brand_name = brand_name

    def _clean_snippet(self, raw: str) -> str:
        s = re.sub(r"\s+", " ", raw).strip()
        # If snippet starts with a lowercase word fragment, trim to the next full sentence or clean boundary
        if len(s) > 20 and s[0].islower() and " " in s:
            first_period = s.find(". ")
            if 0 < first_period < len(s) - 20:
                s = s[first_period + 2:].strip()
        return s

    def _synthesize_answer(
        self,
        status: str,
        brand: str,
        cat: str,
        q_key: str,
        snippet: Optional[str],
        price_amounts: set[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        category_recommendations = {
            "Entity Identity": f"Publish an authoritative 'About' page or structured FAQ explicitly stating {brand}'s exact business category, founding year, leadership, headquarters, and core mission.",
            "Core Capabilities & Services": f"Provide structured service/product documentation detailing {brand}'s primary features, supported technical integrations, deployment models, and tangible client deliverables.",
            "Target Audience & ICP": f"Explicitly list target customer profiles, ideal organization sizes (e.g. enterprise vs startups), and served verticals in hero headers or solution pages.",
            "Pricing & Commercial Terms": f"Publish a dedicated /pricing page with transparent tiers, free trial availability, setup fees, billing intervals, or an explicit enterprise quotation pathway.",
            "Security, Trust & Compliance": f"Deploy a /security or trust center publishing compliance certifications (SOC 2, ISO 27001, GDPR), data encryption policies, and verified client testimonials.",
            "Comparative & Differentiators": f"Create comparison or 'Why {brand}' assets detailing competitive differentiators, advantages over legacy methods, and seamless migration assistance.",
            "Implementation & Onboarding": f"Document expected onboarding timelines, developer effort requirements, documentation links, and customer support availability (SLA, chat, email).",
            "High-Intent Purchase Actions": f"Ensure clear, prominent conversion calls-to-action (schedule a demo, self-service register, contact sales) are visible on all primary pages.",
        }
        rec = category_recommendations.get(cat, f"Publish clear, extractable content answering this question directly on {brand}'s website.")

        if status == "SUPPORTED":
            clean = self._clean_snippet(snippet or "")
            ans = f"According to {brand}'s crawled pages: \"{clean}\""
            return ans, None
        elif status == "PARTIAL":
            clean = self._clean_snippet(snippet or "") if snippet else ""
            if clean:
                ans = f"Partially addressed on {brand}'s website: \"{clean}\" (lacks full standalone depth)."
            else:
                ans = f"Partially mentioned on {brand}'s website: Related keywords were found, but no standalone answer block exists."
            return ans, rec
        elif status == "CONFLICTING":
            ans = f"Conflicting data found across crawled pages: {', '.join(list(price_amounts)[:3])}."
            rec_conf = f"Standardize all public references to pricing across all pages for {brand} to eliminate AI engine confusion."
            return ans, rec_conf
        else:  # UNSUPPORTED
            ans = f"No direct answer found on crawled pages. AI search engines and agents cannot answer this question from first-party evidence."
            return ans, rec

    def _page_hits(self, pages: List[PageEvidence], pattern: re.Pattern) -> List[Tuple[str, str]]:
        hits = []
        for p in pages:
            blob = " ".join([
                p.title or "",
                " ".join(p.h1 or []),
                " ".join(p.h2 or []),
                " ".join(p.h3 or []),
                (p.body_text or "")[:4000],
            ])
            m = pattern.search(blob)
            if m:
                start = max(0, m.start() - 60)
                end = min(len(blob), m.end() + 140)
                snippet = blob[start:end].strip()
                hits.append((p.url, snippet[:240]))
        return hits

    def evaluate_graph(
        self,
        pages: List[PageEvidence],
        brand_name: str = "",
        website_url: str = "",
        profile: Optional[BusinessProfile] = None
    ) -> QuestionGraphResult:
        brand = (
            brand_name
            or (profile.business_name if profile and profile.business_name not in ["Unknown", "Unknown Business", ""] else "")
            or self.brand_name
            or (urlparse(website_url or (pages[0].url if pages else "")).netloc.replace("www.", "").split(".")[0].capitalize())
            or "the company"
        )

        all_corpus = " ".join([
            f"{p.title or ''} {' '.join(p.h1 or [])} {' '.join(p.h2 or [])} {(p.body_text or '')[:3000]}"
            for p in pages
        ]).lower()

        evaluated_questions: List[GeoQuestionEvidence] = []
        category_stats: Dict[str, Dict[str, int]] = {}

        # Price conflict check
        pricing_re = re.compile(r"(?:₹|rs\.?\s?|inr\s?|\$|€|£)\s*[\d,]+(?:\.\d+)?|\b\d{2,6}\s*/\s*(?:mo|month|yr|year)\b", re.I)
        price_amounts = {m.group(0).lower().replace(" ", "") for m in pricing_re.finditer(all_corpus)}
        pricing_conflicted = len(price_amounts) >= 3

        for tpl in QUESTION_TEMPLATES:
            q_key = tpl["key"]
            cat = tpl["category"]
            needles = tpl["needles"]
            rendered_q = tpl["template"].format(brand=brand)

            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "supported": 0, "partial": 0, "unsupported": 0, "conflicting": 0}
            category_stats[cat]["total"] += 1

            # Compile pattern
            pattern = re.compile("|".join(re.escape(n) for n in needles if n.strip()), re.I)
            hits = self._page_hits(pages, pattern) if needles else []

            # Determine status
            status = "UNSUPPORTED"
            why = "No direct evidence found on crawled pages."
            evidence_url = None
            evidence_snippet = None

            if q_key == "price_cost" and pricing_conflicted:
                status = "CONFLICTING"
                why = f"Conflicting price values detected across pages: {', '.join(list(price_amounts)[:3])}."
                if hits:
                    evidence_url, evidence_snippet = hits[0]
            elif hits and len(hits) >= 2:
                status = "SUPPORTED"
                why = "Explicit, extractable answers found across crawled pages."
                evidence_url, evidence_snippet = hits[0]
            elif hits:
                # Check snippet density
                snippet_text = hits[0][1]
                if len(snippet_text.split()) >= 12:
                    status = "SUPPORTED"
                    why = "Self-contained answer snippet found in first-party text."
                else:
                    status = "PARTIAL"
                    why = "Keywords mentioned, but statement lacks full standalone depth."
                evidence_url, evidence_snippet = hits[0]
            else:
                # Check if needles appear anywhere in corpus
                found_needles = [n for n in needles if n in all_corpus]
                if found_needles:
                    status = "PARTIAL"
                    why = f"Mentions related terms ({', '.join(found_needles[:2])}) but no distinct answer block."
                else:
                    status = "UNSUPPORTED"
                    why = f"The crawled website does not contain information to answer this buyer question."

            category_stats[cat][status.lower()] += 1

            ans, rec_ans = self._synthesize_answer(
                status=status,
                brand=brand,
                cat=cat,
                q_key=q_key,
                snippet=evidence_snippet,
                price_amounts=price_amounts,
            )

            evaluated_questions.append(GeoQuestionEvidence(
                question_key=q_key,
                question=rendered_q,
                category=cat,
                status=status,
                answer=ans,
                answer_snippet=evidence_snippet,
                evidence_url=evidence_url,
                evidence_snippet=evidence_snippet,
                why=why,
                recommended_answer=rec_ans,
            ))

        total_q = len(evaluated_questions)
        supp_count = sum(1 for q in evaluated_questions if q.status == "SUPPORTED")
        part_count = sum(1 for q in evaluated_questions if q.status == "PARTIAL")
        unsup_count = sum(1 for q in evaluated_questions if q.status == "UNSUPPORTED")
        conf_count = sum(1 for q in evaluated_questions if q.status == "CONFLICTING")

        # Answerability score: 100% for supported, 50% for partial, 0% for unsupported/conflicting
        ans_score = min(100.0, max(0.0, ((supp_count * 1.0) + (part_count * 0.50)) / total_q * 100.0))

        headline = (
            f"{supp_count} of {total_q} high-intent buyer questions are directly answerable from first-party content"
            f"{f' ({part_count} partial)' if part_count else ''}"
            f"{f' ({conf_count} conflicting)' if conf_count else ''}."
        )

        category_scores: Dict[str, Dict[str, Any]] = {}
        for cat, stats in category_stats.items():
            c_tot = stats["total"]
            c_sup = stats["supported"]
            c_part = stats["partial"]
            c_pct = round(((c_sup + 0.5 * c_part) / max(1, c_tot)) * 100.0, 1)
            category_scores[cat] = {
                "score_pct": c_pct,
                "supported": c_sup,
                "partial": c_part,
                "unsupported": stats["unsupported"],
                "conflicting": stats["conflicting"],
                "total": c_tot,
            }

        return QuestionGraphResult(
            total_questions=total_q,
            supported_count=supp_count,
            partial_count=part_count,
            unsupported_count=unsup_count,
            conflicting_count=conf_count,
            answerability_score=round(ans_score, 1),
            headline=headline,
            category_scores=category_scores,
            questions=evaluated_questions,
            summary=f"Evaluated {total_q} dynamic buyer intent questions. Answerability score: {ans_score:.1f}% ({supp_count}/{total_q} fully supported).",
        )


question_graph_engine = GeoQuestionGraphEngine()
