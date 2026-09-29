"""Named external collection jobs.

Execution, retries, and idempotency live on ExternalAuthorityService.
A failed provider inside one job does not fail the crawl audit.
"""
from app.external_authority.registry import JOB_PROVIDERS

JOB_NAMES = (
    "sync_gsc_data",
    "sync_ga4_data",
    "sync_bing_data",
    "sync_backlinks",
    "sync_gbp_data",
    "sync_brand_mentions",
    "sync_citations",
    "sync_serp",
)


def providers_for(job_type: str) -> list[str]:
    return list(JOB_PROVIDERS.get(job_type, []))
