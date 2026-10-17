"""Subscription hypotheses.

These ranges are for buyer interviews. They are not checkout prices and they
do not replace the existing one-time audit catalog.
"""

SUBSCRIPTION_HYPOTHESES = [
    {
        "id": "hypothesis_free",
        "name": "Free",
        "purchasable": False,
        "status": "hypothesis",
        "price_inr_monthly_range": [0, 0],
        "buyer": "Acquisition",
        "includes": [
            "Bounded public grader",
            "Limited audit preview",
            "Shareable preliminary report",
        ],
    },
    {
        "id": "hypothesis_pro",
        "name": "Pro",
        "purchasable": False,
        "status": "hypothesis",
        "price_inr_monthly_range": [2000, 8000],
        "buyer": "Single-site customer",
        "includes": [
            "Scheduled audits",
            "Historical comparisons",
            "Prioritized findings",
            "Limited AI visibility tracking",
        ],
    },
    {
        "id": "hypothesis_agency",
        "name": "Agency",
        "purchasable": False,
        "status": "hypothesis",
        "price_inr_monthly_range": [15000, 60000],
        "buyer": "Initial growth wedge",
        "includes": [
            "Multi-client workspaces",
            "White-label reports",
            "Client sharing",
            "Remediation workflows",
            "Pooled usage allowances",
        ],
    },
    {
        "id": "hypothesis_enterprise",
        "name": "Enterprise",
        "purchasable": False,
        "status": "hypothesis",
        "price_inr_annual_range": [500000, 3000000],
        "buyer": "Sales-led",
        "includes": [
            "Contracted usage",
            "Advanced access controls",
            "Integrations and governance",
            "Negotiated service levels",
        ],
    },
]

PLANNING_NOTE = (
    "These ranges are hypotheses to test with buyers. They are not a forecast, "
    "not a checkout price, and not a claim of market validation. "
    "Gross margin is (revenue - direct service costs) / revenue. "
    "Direct costs include hosting, crawl infrastructure, paid datasets, "
    "AI inference and search, and storage."
)
