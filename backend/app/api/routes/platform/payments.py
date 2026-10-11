"""
Dristik AI Payment & Razorpay Gateway Integration
Handles order creation, signature verification, and plan catalog management for India & global pricing.
"""
import hmac
import hashlib
import time
import uuid
import httpx
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/payments", tags=["Payments & Pricing"])

# ============================================================================
# Pricing Model & Catalog
# ============================================================================

AUDIT_PLANS = [
    {
        "id": "free_scan",
        "name": "Dristik Free Scan",
        "tier": "free_scan",
        "category": "one_time",
        "price_inr": 0,
        "price_display": "₹0",
        "price_usd": 0,
        "badge": "Free 1-Page Teaser",
        "description": "Instant single-page audit showing your Honest 3-Scores, top 3 bottlenecks, and 1 competitor insight.",
        "popular": False,
        "deliverables": [
            "1-Page Instant Diagnostic Crawl",
            "Honest 3-Scores: Human Experience, Google Search, AI Citation",
            "Top 3 Critical Bottlenecks identified",
            "1 Head-to-Head Competitor Insight",
            "Immediate CTA to unlock full 35-capability intelligence audit"
        ],
        "limits": {
            "max_pages": 1,
            "ai_scenarios": 1,
            "competitor_analysis": False,
            "remediation_code_patches": False,
            "executive_story_deck": False
        }
    },
    {
        "id": "starter",
        "name": "Dristik Starter",
        "tier": "starter",
        "category": "one_time",
        "price_inr": 1499,
        "price_display": "₹1,499",
        "price_usd": 19,
        "badge": "Entry Baseline",
        "description": "Essential crawl & technical baseline for early-stage sites and landing pages.",
        "popular": False,
        "deliverables": [
            "Up to 3 pages crawled & analyzed",
            "Core Technical SEO & Crawlability check",
            "Basic Content Clarity & Meta hygiene",
            "Initial GEO & AI Extractability Score",
            "Standard findings export",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ],
        "limits": {
            "max_pages": 3,
            "ai_scenarios": 1,
            "competitor_analysis": False,
            "remediation_code_patches": False,
            "executive_story_deck": False
        }
    },
    {
        "id": "professional",
        "name": "Dristik Professional",
        "tier": "professional",
        "category": "one_time",
        "price_inr": 3499,
        "price_display": "₹3,499",
        "price_usd": 49,
        "badge": "Growing Startups",
        "description": "Full-spectrum autonomous website intelligence with verified DOM evidence and 7/30/90-day remediation roadmap.",
        "popular": False,
        "deliverables": [
            "Full website crawl (up to 10 key pages)",
            "Deep Technical SEO + DOM Schema verification",
            "Content Intelligence & ICP Alignment",
            "Generative Engine Optimization (GEO) Readiness",
            "AI-Search Discoverability Matrix (Perplexity, GPT, Claude)",
            "UX/CRO Friction & Value Proposition scoring",
            "Concrete Evidence-Backed Findings with DOM locators",
            "7 / 30 / 90-Day Step-by-Step Remediation Roadmap",
            "Executive Story Report & Printable PDF",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ],
        "limits": {
            "max_pages": 10,
            "ai_scenarios": 3,
            "competitor_analysis": False,
            "remediation_code_patches": True,
            "executive_story_deck": True
        }
    },
    {
        "id": "diagnostic",
        "name": "Dristik Diagnostic Sprint",
        "tier": "diagnostic",
        "category": "one_time",
        "price_inr": 4999,
        "price_display": "₹4,999",
        "price_usd": 69,
        "badge": "Recommended Flagship",
        "description": "Full-spectrum autonomous website intelligence + Developer Patch Pack (ZIP) + Re-Query before/after citation readiness.",
        "popular": True,
        "deliverables": [
            "Full multi-page crawl with Evidence Graph 2.0 locators (15 pages)",
            "Theory of Constraints single bottleneck + 'What to ignore this month'",
            "The 6 Commercial Inquiries AI evaluation (Identity, ICP, Pricing, Alts, Trust, ROI)",
            "Re-Query Before → After Citation Readiness matrix with score gain",
            "Developer Patch Pack: schema.jsonld, metadata.html, semantic faq.html, llms.txt, robots.txt",
            "Character-safe copy assistant (Title 50-60, Meta 140-160, Hero 40-60w)",
            "Honest 3-Scores: Human, Google, AI Citation (Evidence-backed)",
            "WhatsApp-shareable C-suite 1-pager & Institutional printable deck",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ],
        "limits": {
            "max_pages": 15,
            "ai_scenarios": 6,
            "competitor_analysis": False,
            "remediation_code_patches": True,
            "executive_story_deck": True
        }
    },
    {
        "id": "business",
        "name": "Dristik Business Intelligence",
        "tier": "business",
        "category": "one_time",
        "price_inr": 9999,
        "price_display": "₹9,999",
        "price_usd": 129,
        "badge": "Growth & Scaleups",
        "description": "Deep 35-page competitive matrix, advanced AI evaluation, claim contradiction detection, and patch specifications.",
        "popular": False,
        "deliverables": [
            "Comprehensive deep crawl (up to 35 pages)",
            "3-Way Competitor Positioning & Market Gap Matrix",
            "Advanced Multi-Persona AI-Search Scenarios",
            "Cross-Page Claim & Pricing Contradiction Detection",
            "Direct Universal Remediation Patches (WordPress + GitHub PR ready)",
            "Consultant-Grade Strategy Presentation",
            "Before / After Remediation Validation Scan",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ],
        "limits": {
            "max_pages": 35,
            "ai_scenarios": 8,
            "competitor_analysis": True,
            "remediation_code_patches": True,
            "executive_story_deck": True
        }
    },
    {
        "id": "diagnostic_bakeoff",
        "name": "Competitor Intelligence & Bake-Off",
        "tier": "diagnostic_bakeoff",
        "category": "one_time",
        "price_inr": 14999,
        "price_display": "₹14,999",
        "price_usd": 189,
        "badge": "Sales Battlecard",
        "description": "Everything in Diagnostic Sprint + Head-to-Head 3-Competitor Bake-Off across all commercial queries.",
        "popular": False,
        "deliverables": [
            "Everything in Dristik Diagnostic Sprint (up to 50 pages)",
            "Head-to-head 3-Competitor Bake-Off on Commercial Questions",
            "Side-by-side sales comparative battlecard table (Who the AI answers for)",
            "Agency white-label PDF licensing (no Dristik branding)",
            "14-Day Post-Patch Re-Query Verification Scan included",
            "Direct analyst review & remediation architecture session",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ],
        "limits": {
            "max_pages": 50,
            "ai_scenarios": 12,
            "competitor_analysis": True,
            "remediation_code_patches": True,
            "executive_story_deck": True
        }
    },
    {
        "id": "growth",
        "name": "Growth Intelligence Platform",
        "tier": "growth",
        "category": "one_time",
        "price_inr": 24999,
        "price_display": "₹24,999",
        "price_usd": 319,
        "badge": "Mid-Market Hero",
        "description": "Comprehensive mid-market audit covering 100 pages, developer patch pack, executive story report, and historical comparison.",
        "popular": False,
        "deliverables": [
            "Deep site crawl (up to 100 pages)",
            "Full 5-competitor automated discovery and gap analysis",
            "AI search scenarios across ChatGPT, Perplexity, Gemini, Claude",
            "Developer remediation PR pack & live WordPress sync",
            "Executive presentation deck & business impact ROI attribution",
            "Historical comparison & delta scoring vs previous runs"
        ],
        "limits": {
            "max_pages": 100,
            "ai_scenarios": 15,
            "competitor_analysis": True,
            "remediation_code_patches": True,
            "executive_story_deck": True
        }
    },
    {
        "id": "enterprise",
        "name": "Dristik Enterprise Custom",
        "tier": "enterprise",
        "category": "one_time",
        "price_inr": 49999,
        "price_display": "₹49,999+",
        "price_usd": 649,
        "badge": "Enterprise & Portfolios",
        "description": "Large-scale intelligence matrix for high-traffic portals, enterprise governance, dedicated webhook feeds, and custom SLAs.",
        "popular": False,
        "deliverables": [
            "Enterprise-scale crawling (200+ pages across multiple subdomains)",
            "Custom intelligence vectors & ICP persona modeling",
            "Multi-market GEO readiness & global AI discoverability",
            "White-label executive board reports for clients/agencies",
            "Custom API integration, automated webhook feeds & GitHub PR pipelines",
            "Direct senior analyst review, architecture session & Enterprise SLA",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ],
        "limits": {
            "max_pages": 200,
            "ai_scenarios": 25,
            "competitor_analysis": True,
            "remediation_code_patches": True,
            "executive_story_deck": True
        }
    }
]

MONITORING_PLANS = [
    {
        "id": "monitoring-starter",
        "name": "Sentinel Radar",
        "tier": "starter_monitoring",
        "category": "recurring",
        "price_inr": 1499,
        "price_display": "₹1,499 / mo",
        "price_usd": 19,
        "billing_period": "month",
        "badge": "Bi-Weekly Radar",
        "description": "Continuous bi-weekly audits, regression alerts, and search health monitoring.",
        "deliverables": [
            "Bi-weekly autonomous website audits",
            "SEO & GEO regression detection alerts",
            "AI discoverability score tracking",
            "Change-log impact analysis",
            "Email executive summary digests"
        ]
    },
    {
        "id": "monthly_pulse",
        "name": "AI Citation Monitoring",
        "tier": "monthly_pulse",
        "category": "recurring",
        "price_inr": 3999,
        "price_display": "₹3,999 / mo",
        "price_usd": 49,
        "billing_period": "month",
        "popular": True,
        "badge": "Core Hero Retainer",
        "description": "20–40 saved commercial buyer prompts tracked continuously across ChatGPT & Perplexity with change-log diffs.",
        "deliverables": [
            "20–40 saved buyer prompts tracked across ChatGPT Search & Perplexity Pro",
            "Monthly crawl change-log diff (H1, meta, schema, pricing visibility)",
            "Citation readiness regression alerts & delta comparison vs last run",
            "Monthly strategic delta board digest",
            "WhatsApp & Email executive alerts",
            "Direct Commercial Purchase Receipt (Flat 0% Tax)"
        ]
    },
    {
        "id": "monitoring-growth",
        "name": "Intelligence Radar",
        "tier": "growth_monitoring",
        "category": "recurring",
        "price_inr": 7999,
        "price_display": "₹7,999 / mo",
        "price_usd": 99,
        "billing_period": "month",
        "popular": False,
        "badge": "Recommended Retainer",
        "description": "Weekly deep audits, AI search citation tracking, and competitive shift detection.",
        "deliverables": [
            "Weekly deep website & competitor scans",
            "Perplexity, ChatGPT & Claude citation tracking",
            "Real-time technical regression Slack/Email webhooks",
            "Monthly strategic executive roadmap update",
            "Continuous priority matrix alignment"
        ]
    },
    {
        "id": "monitoring-agency",
        "name": "Agency Multi-Domain Guard",
        "tier": "agency_monitoring",
        "category": "recurring",
        "price_inr": 14999,
        "price_display": "₹14,999 / mo",
        "price_usd": 189,
        "billing_period": "month",
        "badge": "Agencies & Portfolios",
        "description": "Multi-property real-time intelligence radar with white-label exports and priority engineering support.",
        "deliverables": [
            "Up to 5 client domains monitored continuously",
            "Custom AI search query benchmarking",
            "Automated pull-request ready remediation patches",
            "White-label client PDF export decks",
            "Dedicated Slack channel with Dristik AI specialists"
        ]
    },
    {
        "id": "monitoring-enterprise",
        "name": "Enterprise Continuous Monitoring",
        "tier": "enterprise_monitoring",
        "category": "recurring",
        "price_inr": 25000,
        "price_display": "₹25,000+ / mo",
        "price_usd": 329,
        "billing_period": "month",
        "badge": "Enterprise Mission Critical",
        "description": "High-frequency multi-domain monitoring, custom webhooks, dedicated Slack channel, and guaranteed SLA.",
        "deliverables": [
            "Unlimited subdomain continuous monitoring",
            "Real-time regression webhooks & automated GitHub PR generation",
            "Custom enterprise buyer query benchmarking",
            "Dedicated Slack channel and quarterly strategy reviews",
            "Guaranteed 99.9% uptime and enterprise SLA"
        ]
    }
]

# ============================================================================
# Request / Response Schemas
# ============================================================================

class CreateOrderRequest(BaseModel):
    plan_id: str = Field(..., description="ID of the plan selected (e.g. professional, business)")
    target_url: str = Field(..., description="Target website URL to audit")
    customer_name: Optional[str] = Field(default="Dristik Client")
    customer_email: Optional[str] = Field(default="client@example.com")
    customer_phone: Optional[str] = Field(default=None)
    company_name: Optional[str] = Field(default=None)
    gstin: Optional[str] = Field(default=None)

class OrderResponse(BaseModel):
    order_id: str
    amount_inr: int
    amount_paise: int
    currency: str
    key_id: str
    plan_id: str
    plan_name: str
    target_url: str
    is_test_mode: bool
    gst_amount_inr: int = 0
    total_amount_inr: int
    upi_intent_url: str = ""
    upi_qr_data: str = ""
    sac_code: str = ""

class GstInvoiceRequest(BaseModel):
    order_id: str
    customer_name: str
    customer_email: str
    company_name: Optional[str] = None
    gstin: Optional[str] = None
    state_code: Optional[str] = None
    address: Optional[str] = None

class GstInvoiceResponse(BaseModel):
    invoice_number: str
    invoice_date: str
    sac_code: str
    order_id: str
    plan_name: str
    target_url: str
    base_amount_inr: int
    is_inter_state: bool
    cgst_amount_inr: int
    sgst_amount_inr: int
    igst_amount_inr: int
    total_amount_inr: int
    total_in_words: str
    seller_details: Dict[str, str]
    buyer_details: Dict[str, Any]


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str
    target_url: str
    customer_email: Optional[str] = None

class VoucherResponse(BaseModel):
    success: bool
    voucher_code: str
    plan_id: str
    plan_name: str
    target_url: str
    payment_id: str
    timestamp: float
    message: str

from app.payments.store import get_payment_store, OrderRecord

# ============================================================================
# Endpoints
# ============================================================================

@router.get("/config")
async def get_payment_config():
    """Returns Razorpay public key configuration and status."""
    has_keys = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    return {
        "razorpay_key_id": settings.RAZORPAY_KEY_ID or "",
        "is_configured": has_keys,
        "is_test_mode": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_ID.startswith("rzp_test_")),
        "currency": settings.RAZORPAY_CURRENCY,
        "brand_name": "Dristik AI",
        "brand_theme_color": "#06b6d4"
    }

@router.get("/plans")
async def get_plans():
    """Returns the full catalog of Dristik audit and continuous monitoring tiers."""
    from app.commercial.plans import PLANNING_NOTE, SUBSCRIPTION_HYPOTHESES

    return {
        "one_time_audits": AUDIT_PLANS,
        "continuous_monitoring": MONITORING_PLANS,
        "subscription_hypotheses": SUBSCRIPTION_HYPOTHESES,
        "subscription_hypotheses_note": PLANNING_NOTE,
        "default_flagship": "diagnostic",
        "currency": "INR",
        "gst_rate": 0.0,
        "value_proposition": "Investigates your website like a dedicated cross-functional team of technical, SEO, GEO, AI-search, and business analysts—with verified evidence for every conclusion."
    }

@router.post("/create-order", response_model=OrderResponse)
async def create_order(req: CreateOrderRequest):
    """
    Creates a Razorpay Order ID.
    Communicates directly with the live Razorpay Orders API.
    Fails closed if payment gateway is not configured or if the gateway returns an error.
    """
    # Find matching plan
    all_plans = AUDIT_PLANS + MONITORING_PLANS
    plan = next((p for p in all_plans if p["id"] == req.plan_id), None)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{req.plan_id}' not found in catalog."
        )

    base_price = plan["price_inr"]
    total_inr = base_price
    total_paise = total_inr * 100

    # Live Razorpay Gateway Execution
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                    json={
                        "amount": total_paise,
                        "currency": "INR",
                        "receipt": f"dristik_rcpt_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                        "notes": {
                            "plan_id": plan["id"],
                            "target_url": req.target_url,
                            "customer_email": req.customer_email or "",
                            "company": req.company_name or ""
                        }
                    },
                    timeout=10.0
                )
                if res.status_code in (200, 201):
                    data = res.json()
                    order_id = data["id"]
                    upi_intent = f"upi://pay?pa=dristik@icici&pn=Dristik+AI&am={total_inr}&cu=INR&tn={order_id}"
                    
                    # Persist verified order in payment store
                    order_rec = OrderRecord(
                        order_id=order_id,
                        plan_id=plan["id"],
                        plan_name=plan["name"],
                        amount_inr=base_price,
                        amount_paise=total_paise,
                        currency="INR",
                        target_url=req.target_url,
                        customer_name=req.customer_name,
                        customer_email=req.customer_email,
                        company_name=req.company_name,
                        gstin=req.gstin,
                        status="created"
                    )
                    get_payment_store().save_order(order_rec)

                    return OrderResponse(
                        order_id=order_id,
                        amount_inr=base_price,
                        amount_paise=total_paise,
                        currency="INR",
                        key_id=settings.RAZORPAY_KEY_ID,
                        plan_id=plan["id"],
                        plan_name=plan["name"],
                        target_url=req.target_url,
                        is_test_mode=settings.RAZORPAY_KEY_ID.startswith("rzp_test_"),
                        gst_amount_inr=0,
                        total_amount_inr=total_inr,
                        upi_intent_url=upi_intent,
                        upi_qr_data=upi_intent,
                        sac_code=""
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"PAYMENT_FAILED: Razorpay order creation failed ({res.status_code}): {res.text}"
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"PAYMENT_FAILED: Gateway communication error: {str(e)}"
            )

    # If test mode is explicitly allowed in non-production environments
    if settings.ALLOW_PAYMENT_TEST_MOCKS and settings.ENVIRONMENT.lower() != "production":
        mock_order_id = f"order_test_{uuid.uuid4().hex[:12]}"
        order_rec = OrderRecord(
            order_id=mock_order_id,
            plan_id=plan["id"],
            plan_name=plan["name"],
            amount_inr=base_price,
            amount_paise=total_paise,
            currency="INR",
            target_url=req.target_url,
            customer_name=req.customer_name,
            customer_email=req.customer_email,
            company_name=req.company_name,
            gstin=req.gstin,
            status="created"
        )
        get_payment_store().save_order(order_rec)

        upi_intent = f"upi://pay?pa=dristik@icici&pn=Dristik+AI&am={total_inr}&cu=INR&tn={mock_order_id}"
        return OrderResponse(
            order_id=mock_order_id,
            amount_inr=base_price,
            amount_paise=total_paise,
            currency="INR",
            key_id="rzp_test_mock_isolated",
            plan_id=plan["id"],
            plan_name=plan["name"],
            target_url=req.target_url,
            is_test_mode=True,
            gst_amount_inr=0,
            total_amount_inr=total_inr,
            upi_intent_url=upi_intent,
            upi_qr_data=upi_intent,
            sac_code=""
        )

    # Fail closed: No Razorpay credentials configured
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="PAYMENT_NOT_CONFIGURED: Razorpay payment gateway credentials are not configured on this server."
    )

@router.post("/verify-payment", response_model=VoucherResponse)
async def verify_payment(req: VerifyPaymentRequest):
    """
    Verifies Razorpay HMAC signature against persisted order records.
    Never accepts unverified signatures or mock payment IDs in production.
    Returns a verified Dristik Audit Voucher entitlement.
    """
    store = get_payment_store()
    persisted_order = store.get_order(req.razorpay_order_id)

    # If test mode is explicitly allowed in non-production environments
    is_test_env = settings.ALLOW_PAYMENT_TEST_MOCKS and settings.ENVIRONMENT.lower() != "production"

    if not persisted_order:
        if not is_test_env:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PAYMENT_VERIFICATION_FAILED: Order ID does not match any active persisted order."
            )

    all_plans = AUDIT_PLANS + MONITORING_PLANS
    plan = next((p for p in all_plans if p["id"] == req.plan_id), None)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{req.plan_id}' not found in catalog."
        )

    if persisted_order and persisted_order.plan_id != req.plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PAYMENT_VERIFICATION_FAILED: Verified order is for plan '{persisted_order.plan_id}', not '{req.plan_id}'."
        )

    # Check for prohibited mock signatures
    if req.razorpay_signature.startswith("mock_sig_") or req.razorpay_payment_id.startswith("pay_mock_"):
        if not is_test_env:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PAYMENT_VERIFICATION_FAILED: Mock signatures and simulated payments are strictly prohibited in production."
            )

    # HMAC Signature Verification
    if settings.RAZORPAY_KEY_SECRET:
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != req.razorpay_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PAYMENT_VERIFICATION_FAILED: Razorpay HMAC payment signature verification failed."
            )
    else:
        if not is_test_env:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PAYMENT_NOT_CONFIGURED: RAZORPAY_KEY_SECRET is not configured for signature verification."
            )

    max_pages = plan.get("limits", {}).get("max_pages", 1)

    # Mark order as paid and issue persisted entitlement voucher
    store.mark_order_paid(req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature)
    voucher = store.issue_voucher(
        order_id=req.razorpay_order_id,
        plan_id=req.plan_id,
        target_url=req.target_url,
        payment_id=req.razorpay_payment_id,
        max_pages=max_pages
    )

    return VoucherResponse(
        success=True,
        voucher_code=voucher.voucher_code,
        plan_id=req.plan_id,
        plan_name=plan["name"],
        target_url=req.target_url,
        payment_id=req.razorpay_payment_id,
        timestamp=voucher.created_at,
        message="Payment verified successfully. Dristik Intelligence Audit unlocked!"
    )

@router.post("/invoice", response_model=GstInvoiceResponse)
async def generate_gst_invoice(req: GstInvoiceRequest):
    """
    Generates a formal Commercial Purchase Receipt for business expense accounting.
    Exempt / Unregistered under Section 22 of CGST Act (0% GST charged).
    Must originate from a verified persisted order record.
    """
    store = get_payment_store()
    order = store.get_order(req.order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"INVOICE_DATA_UNAVAILABLE: No verified order found for order ID '{req.order_id}'."
        )

    all_plans = AUDIT_PLANS + MONITORING_PLANS
    plan = next((p for p in all_plans if p["id"] == order.plan_id), None)
    plan_name = plan["name"] if plan else order.plan_name
    base_inr = order.amount_inr

    inv_num = f"RCPT-DRK-2026-{uuid.uuid4().hex[:6].upper()}"
    inv_date = time.strftime("%d-%m-%Y")

    return GstInvoiceResponse(
        invoice_number=inv_num,
        invoice_date=inv_date,
        sac_code="",
        order_id=order.order_id,
        plan_name=plan_name,
        target_url=order.target_url,
        base_amount_inr=base_inr,
        is_inter_state=False,
        cgst_amount_inr=0,
        sgst_amount_inr=0,
        igst_amount_inr=0,
        total_amount_inr=base_inr,
        total_in_words=f"INR {base_inr:,} Only",
        seller_details={
            "legal_name": "Dristik AI (Independent Software Studio)",
            "tax_status": "Exempt / Unregistered under Section 22 of CGST Act · 0% GST Charged",
            "receipt_type": "Commercial Purchase & Expense Receipt",
            "jurisdiction": "India",
            "address": "Bangalore, Karnataka, India"
        },
        buyer_details={
            "customer_name": req.customer_name or order.customer_name or "Valued Customer",
            "customer_email": req.customer_email or order.customer_email or "",
            "company_name": req.company_name or order.company_name or req.customer_name or "Commercial Customer",
            "tax_id": req.gstin or order.gstin or "B2B / Direct Customer",
            "state_code": req.state_code or "General",
            "address": req.address or "India"
        }
    )


