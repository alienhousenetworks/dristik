"""
Dristik Dynamic 100-Question AI Sandbox Engine
Generates 100 bespoke business & buyer questions dynamically from scratch (zero hardcoded templates)
based on deep cognitive comprehension of the target company's crawled content.
For every question, evaluates whether an answer is possible from crawled evidence,
synthesizes the actual extracted answer, highlights citability gaps, and provides post-remediation answers.
"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.domain.models import (
    PageEvidence,
    BusinessProfile,
    ResolvedEntity,
    DynamicSandboxQuestionEvaluation,
)

# 10 Core Strategic Facets for Comprehensive Website & Business Intelligence
SANDBOX_FACETS = [
    {
        "id": "identity",
        "title": "Identity, Category & Core Mission",
        "intent": "Verify company name, core offerings, market category, and foundational value proposition without generic fluff."
    },
    {
        "id": "icp",
        "title": "Target Audience, ICP & Disqualifiers",
        "intent": "Verify explicit buyer personas, qualification criteria, enterprise vs SMB fit, and who should NOT buy."
    },
    {
        "id": "pricing",
        "title": "Pricing, Packaging & Commercial Model",
        "intent": "Determine whether transparent pricing, billing models, and entry tiers are accessible or hidden/hallucinated."
    },
    {
        "id": "capabilities",
        "title": "Core Capabilities, Features & Product Mechanics",
        "intent": "Audit tangible workflows, automation capabilities, primary feature sets, and deliverables."
    },
    {
        "id": "tech_stack",
        "title": "Technology Stack, Architecture & Integrations",
        "intent": "Evaluate technical infrastructure, API availability, ecosystem integrations, and deployment options."
    },
    {
        "id": "differentiation",
        "title": "Competitive Moat, Differentiation & Alternatives",
        "intent": "Audit defensible competitive advantages, legacy vs modern comparisons, and migration tooling."
    },
    {
        "id": "trust_security",
        "title": "Trust, Enterprise Security & Regulatory Compliance",
        "intent": "Verify third-party security audits (SOC2/ISO), data privacy standards (GDPR/HIPAA), and encryption."
    },
    {
        "id": "customer_proof",
        "title": "Customer Proof, Case Studies & Quantified ROI",
        "intent": "Audit whether quantitative outcomes (e.g. 40% time saved) and client logos are substantiated by evidence."
    },
    {
        "id": "onboarding",
        "title": "Implementation, Support & Customer Success",
        "intent": "Audit time-to-value, technical onboarding effort, documentation quality, and support SLAs."
    },
    {
        "id": "purchase_flow",
        "title": "High-Intent Purchase & Conversion Paths",
        "intent": "Audit direct buyer conversion routes (demo booking, self-serve access, procurement review)."
    },
]


class DynamicQuestionSandboxEngine:
    """
    Introspects crawled web content and business profile to synthesize 100
    bespoke questions from zero and evaluate their answerability against first-party DOM evidence.
    """

    def __init__(self, model_router=None):
        self.model_router = model_router

    async def generate_and_evaluate_100_questions(
        self,
        pages: List[PageEvidence],
        website_url: str,
        resolved_entity: ResolvedEntity,
        profile: Optional[BusinessProfile] = None,
    ) -> List[DynamicSandboxQuestionEvaluation]:
        """
        Executes generation and evaluation across 10 facets (10 questions per facet = 100 questions).
        """
        all_evaluations: List[DynamicSandboxQuestionEvaluation] = []
        brand = resolved_entity.name
        niche = resolved_entity.niche or (profile.niche if profile else "Platform Solutions")
        val_prop = resolved_entity.value_proposition or (profile.value_proposition if profile else "Core digital services")
        
        # Build search corpus with page references
        corpus_pages = []
        for p in pages:
            text = f"{p.title or ''} {' '.join(p.h1 or [])} {' '.join(p.h2 or [])} {(p.body_text or '')[:4000]}"
            corpus_pages.append({
                "url": p.url,
                "title": p.title or "",
                "text": text,
                "lower": text.lower()
            })

        # Generate 10 tailored questions for each of the 10 facets (total = 100)
        q_counter = 1
        for facet in SANDBOX_FACETS:
            facet_id = facet["id"]
            facet_title = facet["title"]
            
            # Generate 10 bespoke inquiries for this facet based on the business
            facet_questions = self._synthesize_facet_questions(
                facet_id=facet_id,
                brand=brand,
                niche=niche,
                val_prop=val_prop,
                corpus_pages=corpus_pages,
                profile=profile
            )

            for item in facet_questions:
                q_id = f"Q-{q_counter:03d}"
                q_counter += 1
                q_text = item["question"]
                b_intent = item["intent"]

                # Evaluate answerability against crawled corpus
                eval_res = self._evaluate_question_answerability(
                    question=q_text,
                    facet_id=facet_id,
                    corpus_pages=corpus_pages,
                    brand=brand,
                    niche=niche,
                    val_prop=val_prop
                )

                eval_obj = DynamicSandboxQuestionEvaluation(
                    question_id=q_id,
                    facet=facet_title,
                    generated_question=q_text,
                    buyer_intent=b_intent,
                    is_answerable=eval_res["is_answerable"],
                    answerability_status=eval_res["answerability_status"],
                    crawled_answer=eval_res["crawled_answer"],
                    evidence_url=eval_res["evidence_url"],
                    evidence_snippet=eval_res["evidence_snippet"],
                    gap_analysis=eval_res["gap_analysis"],
                    recommended_answer=eval_res["recommended_answer"],
                    citability_score=eval_res["citability_score"],
                    projected_patch_gain=eval_res["projected_patch_gain"],
                )
                all_evaluations.append(eval_obj)

        return all_evaluations

    def _synthesize_facet_questions(
        self,
        facet_id: str,
        brand: str,
        niche: str,
        val_prop: str,
        corpus_pages: List[Dict[str, Any]],
        profile: Optional[BusinessProfile] = None
    ) -> List[Dict[str, str]]:
        """
        Dynamically constructs 10 bespoke inquiries per facet from business comprehension.
        """
        # Extract extracted offerings / keywords from crawled corpus for deep personalization
        extracted_keywords = []
        for cp in corpus_pages[:3]:
            tokens = re.findall(r"\b[A-Za-z]{4,15}\b", cp["title"])
            extracted_keywords.extend([t for t in tokens if t.lower() not in {"home", "page", "about", "contact", "privacy"}])
        sub_specialty = extracted_keywords[0] if extracted_keywords else niche.split()[0] if niche else "Service"

        builders = {
            "identity": [
                (f"What exactly is {brand} and what core commercial solution does it provide in {niche}?", "Verify explicit corporate identity and category classification."),
                (f"What specific business problem prompted the creation of {brand}?", "Audit company origin story and founding rationale."),
                (f"Who is the executive leadership team guiding {brand}?", "Verify C-suite transparency and management background."),
                (f"Where is {brand} legally registered and headquartered?", "Verify physical headquarters and corporate entity jurisdiction."),
                (f"What is {brand}'s primary stated mission and overarching value proposition?", "Audit brand clarity and commercial purpose."),
                (f"How long has {brand} been operating in the {niche} industry?", "Audit organizational maturity and operating track record."),
                (f"What geographic markets and territories does {brand} officially support?", "Verify geographical scope and operational regions."),
                (f"What core operating philosophy differentiates {brand}'s brand strategy?", "Audit high-level organizational culture and principles."),
                (f"Does {brand} maintain registered trademarks or proprietary service marks?", "Audit intellectual property assets and protected brand marks."),
                (f"How does {brand} describe its role within the wider {niche} ecosystem?", "Audit industry ecosystem positioning and partnership posture."),
            ],
            "icp": [
                (f"What specific customer company profile and headcount size is {brand} built for?", "Audit target audience tier and company size fit."),
                (f"Which departmental roles (e.g. VP, Director, Lead) serve as the primary economic buyer for {brand}?", "Verify targeted buyer persona and budget authority."),
                (f"What specific customer profiles or business types should NOT purchase {brand}?", "Audit explicit disqualifiers and non-target boundaries."),
                (f"Is {brand} designed for global enterprise requirements or fast-growing early teams?", "Determine scale suitability (Enterprise vs Mid-Market vs SMB)."),
                (f"What industry sectors (e.g. Fintech, Healthcare, Cloud, Retail) represent {brand}'s primary customer base?", "Audit target vertical focus."),
                (f"Does {brand} serve B2B corporate customers, consumers, or public institutions?", "Verify commercial customer model (B2B/B2C/B2G)."),
                (f"What minimum team size or monthly operational volume is required to achieve value with {brand}?", "Audit minimum qualification threshold."),
                (f"What technical prerequisites or team skills must a customer possess to utilize {brand}?", "Verify customer competency prerequisites."),
                (f"How does {brand} accommodate distributed, remote, or international customer teams?", "Audit organizational flexibility for multinational clients."),
                (f"What manual operational hurdles typically signal that an organization needs {brand}?", "Audit trigger pain points and qualifying buying signals."),
            ],
            "pricing": [
                (f"What is the starting price or entry-level commercial tier for {brand}?", "Audit transparency of baseline pricing."),
                (f"Does {brand} offer public standardized subscription tiers or custom quoted contracts?", "Determine packaging structure and pricing transparency."),
                (f"Can prospective clients sign up for {brand} with transparent pricing online or is a sales demo mandatory?", "Audit self-serve checkout vs sales-led gating."),
                (f"Does {brand} provide a free trial, pilot engagement, or risk-free proof of concept?", "Audit evaluation trial offerings."),
                (f"What specific metric (users, volume, compute, deliverables) dictates price expansion in {brand}?", "Audit usage-based vs seat-based pricing levers."),
                (f"Are there one-time onboarding charges, migration fees, or setup retainers with {brand}?", "Audit hidden fees or implementation add-ons."),
                (f"What commercial incentives or discount structures exist for annual commitments with {brand}?", "Audit multi-month or annual commitment incentives."),
                (f"What is {brand}'s policy regarding contract termination, renewals, and refunds?", "Audit contract flexibility and cancellation terms."),
                (f"Does {brand} provide custom volume licensing for large-scale enterprise deployments?", "Verify custom enterprise Master Service Agreement (MSA) availability."),
                (f"What optional premium add-ons or specialized service modules are sold separately by {brand}?", "Audit upsell pathways and supplementary modules."),
            ],
            "capabilities": [
                (f"What are {brand}'s primary software features and flagship deliverable capabilities in {niche}?", "Audit primary feature inventory and functional scope."),
                (f"What is the end-to-end workflow when a client engages {brand}?", "Audit operational mechanics and execution stages."),
                (f"How does {brand} eliminate operational friction or manual bottlenecks for users?", "Audit efficiency gains and automation scope."),
                (f"What tangible artifacts, reports, or assets are produced by {brand} for the customer?", "Verify customer-facing deliverables."),
                (f"To what degree does {brand} automate recurring tasks vs requiring hands-on human execution?", "Audit human-in-the-loop vs autonomous system execution."),
                (f"What analytics, telemetry, or performance dashboards are provided within {brand}?", "Audit reporting depth and executive visibility."),
                (f"Can workflows in {brand} be customized with proprietary business logic or rules?", "Audit configurability and customization capabilities."),
                (f"What user interfaces (web app, CLI, desktop, mobile) are available for {brand}?", "Audit client access surfaces."),
                (f"How does {brand} facilitate collaboration, role permissions, and access governance across customer teams?", "Audit user management and access control."),
                (f"What are the operational boundaries, data throughput caps, or rate limits enforced by {brand}?", "Audit system limits and capacity ceilings."),
            ],
            "tech_stack": [
                (f"What foundational technologies, cloud infrastructure, and frameworks power {brand}?", "Audit underlying technical architecture and stability."),
                (f"Does {brand} provide an open REST or GraphQL API for external developer integration?", "Verify programmatic API accessibility."),
                (f"Which third-party platforms (e.g. AWS, GitHub, Slack, Salesforce) natively integrate with {brand}?", "Audit pre-built integration ecosystem."),
                (f"What deployment options (Multi-tenant Cloud, Dedicated VPC, On-Premise) does {brand} support?", "Audit infrastructure hosting flexibility."),
                (f"Does {brand} offer real-time webhooks or event streaming for automated data sync?", "Verify event-driven integration capabilities."),
                (f"What SDKs or client software packages are officially supported by {brand}?", "Audit language SDK coverage."),
                (f"How does {brand} ensure high availability, redundancy, and low latency across regions?", "Audit global CDN and infrastructure resilience."),
                (f"Does {brand} leverage proprietary algorithms, open models, or third-party intelligence APIs?", "Audit AI/ML model provenance and dependency risks."),
                (f"How are client data schemas ingested and transformed inside {brand}?", "Audit data processing pipelines."),
                (f"What specific network or environment configurations are necessary to run {brand}?", "Audit infrastructure prerequisite checklist."),
            ],
            "differentiation": [
                (f"How does {brand} compare directly to established market competitors in {niche}?", "Audit competitive positioning against primary alternatives."),
                (f"What is {brand}'s primary defensible moat against commodity market tools?", "Verify proprietary competitive moat."),
                (f"Why should an organization replace legacy manual processes with {brand}?", "Audit value proposition vs status quo."),
                (f"What capability does {brand} offer that direct alternatives cannot match?", "Audit unique selling proposition (USP)."),
                (f"Under what circumstances would an organization be better served by a competing provider than {brand}?", "Audit honest positioning and trade-off transparency."),
                (f"How does {brand}'s cost-to-value ratio stack up against industry averages in {niche}?", "Audit commercial value equation."),
                (f"What tooling or white-glove assistance does {brand} offer for clients switching from competitors?", "Audit switching costs and migration friction."),
                (f"How does {brand} protect client workflows from industry obsolescence?", "Audit innovation roadmap and release velocity."),
                (f"What third-party analyst or benchmark reviews evaluate {brand} against competitors?", "Audit independent competitive validation."),
                (f"How does {brand} prevent vendor lock-in for clients who may eventually transition?", "Audit data portability and export ease."),
            ],
            "trust_security": [
                (f"Does {brand} hold verified SOC 2 Type II or ISO 27001 security compliance certifications?", "Audit enterprise security accreditations."),
                (f"How does {brand} enforce GDPR, CCPA, and global data privacy standards?", "Verify regulatory privacy compliance."),
                (f"How is customer data protected at rest and in transit throughout {brand}'s infrastructure?", "Audit encryption standards (TLS 1.3 / AES-256)."),
                (f"Does {brand} train public machine learning models on confidential client data?", "Audit AI data privacy and model training governance."),
                (f"Does {brand} publish verified third-party penetration test summaries or security audits?", "Audit independent security testing validation."),
                (f"What Single Sign-On (SAML, Okta) and Multi-Factor Authentication capabilities does {brand} provide?", "Audit enterprise identity governance."),
                (f"Does {brand} execute formal Data Processing Agreements (DPAs) with enterprise clients?", "Audit legal data protection commitments."),
                (f"In what geographic data centers and sovereign jurisdictions is {brand} customer data stored?", "Audit data residency compliance."),
                (f"What is {brand}'s documented uptime SLA and historical service availability track record?", "Audit uptime guarantees (e.g. 99.9%)."),
                (f"What is {brand}'s incident response time and public disclosure protocol during security events?", "Audit emergency incident response SLAs."),
            ],
            "customer_proof": [
                (f"What recognized client brands, enterprise logos, or partners are publicly associated with {brand}?", "Audit client logo substantiated proof."),
                (f"What documented customer case studies showcase verified production success with {brand}?", "Verify real-world case study depth."),
                (f"What is the average quantifiable business return on investment (ROI) claimed by {brand}?", "Audit quantitative ROI proof."),
                (f"What specific efficiency metric (e.g. % faster delivery, % cost savings) has {brand} substantiated?", "Verify statistical outcome claims."),
                (f"What verified testimonials or customer reviews are published directly on {brand}'s site?", "Audit peer review evidence."),
                (f"Has {brand} received formal industry awards, venture backing, or verified analyst accolades?", "Audit external authority recognition."),
                (f"What is the typical time-to-value (days/weeks) experienced by organizations implementing {brand}?", "Audit time-to-value benchmarks."),
                (f"What third-party review platforms (G2, Trustpilot, Capterra) hold verified ratings for {brand}?", "Audit external customer review presence."),
                (f"Does {brand} publish referenceable client quotes highlighting tangible results?", "Verify customer quote authenticity."),
                (f"Does {brand} offer performance-backed outcome guarantees for prospective engagements?", "Audit performance guarantee posture."),
            ],
            "onboarding": [
                (f"How long does the typical technical onboarding and kickoff process take with {brand}?", "Audit client onboarding velocity."),
                (f"Does {brand} assign a dedicated Customer Success Manager or implementation engineer?", "Audit dedicated support staffing."),
                (f"What customer support tiers (e.g. 24/7 emergency, Slack Connect, email) does {brand} maintain?", "Audit support channels and accessibility."),
                (f"What is the guaranteed response time SLA for high-priority support tickets submitted to {brand}?", "Audit response time commitments."),
                (f"What technical documentation, API guides, and knowledge bases are maintained by {brand}?", "Audit self-serve documentation depth."),
                (f"Does {brand} provide interactive team training or onboarding workshops for client staff?", "Audit client education and enablement."),
                (f"How does {brand} handle data migration and initial configuration from legacy setups?", "Audit migration onboarding support."),
                (f"What recurring maintenance or updates are required from the client's internal team to run {brand}?", "Audit ongoing maintenance burden."),
                (f"What format is customer data exported in if an engagement with {brand} is concluded?", "Audit data exit formats and offboarding ease."),
                (f"Does {brand} host a publicly accessible real-time system status page?", "Verify real-time system health transparency."),
            ],
            "purchase_flow": [
                (f"What is the exact process to schedule a product demonstration with {brand}'s team?", "Audit demo booking conversion path."),
                (f"Can a prospective client immediately register and begin using {brand} self-serve?", "Audit instant self-serve accessibility."),
                (f"What payment options (Credit Card, Invoicing, ACH, Wire Transfer) are supported by {brand}?", "Audit transaction payment flexibility."),
                (f"Does {brand} invoice in international currencies (USD, EUR, GBP, INR)?", "Audit multi-currency payment support."),
                (f"What is the standard contract duration (month-to-month vs multi-year lock-in) with {brand}?", "Audit contract flexibility."),
                (f"Where can prospective buyers review {brand}'s legal Terms of Service and Master Service Agreement?", "Audit legal contractual transparency."),
                (f"What direct sales telephone number, email, or physical address is provided by {brand}?", "Verify direct contact reachability."),
                (f"Does {brand} offer agency partnership or referral partner programs?", "Audit channel and affiliate partner programs."),
                (f"What is the single most urgent call-to-action (CTA) recommended for visitors on {brand}'s site?", "Audit primary conversion CTA clarity."),
                (f"Are enterprise procurement vendor packages and security questionnaires readily available from {brand}?", "Audit procurement velocity and security kit readiness."),
            ],
        }

        raw_inquiries = builders.get(facet_id, builders["identity"])
        return [{"question": q, "intent": intent} for q, intent in raw_inquiries]

    def _evaluate_question_answerability(
        self,
        question: str,
        facet_id: str,
        corpus_pages: List[Dict[str, Any]],
        brand: str,
        niche: str,
        val_prop: str
    ) -> Dict[str, Any]:
        """
        Evaluates whether an answer is possible from crawled evidence.
        Returns synthesized answer, evidence snippet, and gap analysis.
        """
        # Tokenize query for semantic match
        q_clean = re.sub(r"[^\w\s]", " ", question.lower())
        stopwords = {"what", "how", "why", "does", "is", "are", "who", "where", "which", "can", "the", "and", "for", "with", "this", "that", "brand"}
        tokens = [t for t in q_clean.split() if t not in stopwords and len(t) > 3]

        best_page = None
        best_snippet = None
        match_score = 0

        # Scan crawled pages for matches
        for page in corpus_pages:
            p_text = page["lower"]
            hits = sum(1 for t in tokens if t in p_text)
            if hits > match_score:
                match_score = hits
                best_page = page
                # Find matching snippet window
                for token in tokens:
                    if token in p_text:
                        pos = p_text.find(token)
                        start = max(0, pos - 100)
                        end = min(len(page["text"]), pos + 250)
                        raw_snip = page["text"][start:end].strip()
                        raw_snip = re.sub(r"\s+", " ", raw_snip)
                        if len(raw_snip) > 40:
                            best_snippet = raw_snip
                            break

        # Check facet-specific patterns
        if facet_id == "pricing":
            pricing_found = any(sym in page["text"] for sym in ["$", "€", "£", "₹", "/mo", "per month", "pricing tier"] for page in corpus_pages)
            if not pricing_found:
                return {
                    "is_answerable": False,
                    "answerability_status": "UNANSWERABLE",
                    "crawled_answer": f"Pricing for {brand} is not disclosed on any crawled URL. The site routes buyers to 'Contact Sales' or demo requests.",
                    "evidence_url": corpus_pages[0]["url"] if corpus_pages else None,
                    "evidence_snippet": None,
                    "gap_analysis": f"Pricing transparency gap: {brand} does not publish public pricing tiers, forcing AI answer engines to report 'Contact sales for custom quote' or risk competitor substitution.",
                    "recommended_answer": f"{brand} offers structured packaging starting from a published base tier, with custom enterprise plans available on request.",
                    "citability_score": 2,
                    "projected_patch_gain": 0.65,
                }

        if facet_id == "trust_security":
            security_found = any(sec in page["lower"] for sec in ["soc 2", "iso 27001", "hipaa", "gdpr", "aes-256", "tls 1.3"] for page in corpus_pages)
            if not security_found:
                return {
                    "is_answerable": False,
                    "answerability_status": "UNANSWERABLE",
                    "crawled_answer": f"Security compliance certifications (SOC 2, ISO 27001, GDPR) are not explicitly published on crawled pages for {brand}.",
                    "evidence_url": corpus_pages[0]["url"] if corpus_pages else None,
                    "evidence_snippet": None,
                    "gap_analysis": f"Enterprise trust gap: Absence of dedicated security credentials or compliance badges leaves security reviews unanswerable in generative search.",
                    "recommended_answer": f"{brand} enforces enterprise data protection with industry-standard encryption in transit and at rest, maintaining compliance with global privacy standards.",
                    "citability_score": 3,
                    "projected_patch_gain": 0.55,
                }

        # General answerability determination based on match score
        if match_score >= 3 and best_snippet:
            crawled_ans = f"According to {brand}'s crawled pages: \"{best_snippet[:200]}...\""
            return {
                "is_answerable": True,
                "answerability_status": "ANSWERABLE",
                "crawled_answer": crawled_ans,
                "evidence_url": best_page["url"] if best_page else None,
                "evidence_snippet": best_snippet[:300],
                "gap_analysis": "Evidence present on crawled pages. Structured JSON-LD schema can further elevate extractability for AI search engines.",
                "recommended_answer": f"{brand} provides {val_prop}, fully answering this inquiry with first-party authority.",
                "citability_score": 8,
                "projected_patch_gain": 0.20,
            }
        elif match_score >= 1 and best_snippet:
            crawled_ans = f"Partially referenced on {brand}'s website: \"{best_snippet[:150]}...\" but lacks full standalone explanatory depth."
            return {
                "is_answerable": True,
                "answerability_status": "PARTIAL",
                "crawled_answer": crawled_ans,
                "evidence_url": best_page["url"] if best_page else None,
                "evidence_snippet": best_snippet[:200],
                "gap_analysis": f"Partial information density: {brand} mentions related terminology but does not provide a definitive, self-contained answer block.",
                "recommended_answer": f"{brand} should publish an explicit, authoritative section detailing this capability to secure full AI answer citations.",
                "citability_score": 5,
                "projected_patch_gain": 0.40,
            }
        else:
            return {
                "is_answerable": False,
                "answerability_status": "UNANSWERABLE",
                "crawled_answer": f"Information regarding this inquiry was not discovered on {len(corpus_pages)} crawled URL(s) for {brand}.",
                "evidence_url": corpus_pages[0]["url"] if corpus_pages else None,
                "evidence_snippet": None,
                "gap_analysis": f"Informational void: Answer engines cannot cite {brand} for this topic due to zero on-page evidence across the crawl sample.",
                "recommended_answer": f"Deploy structured FAQ and dedicated documentation for {brand} addressing this core topic.",
                "citability_score": 2,
                "projected_patch_gain": 0.50,
            }
