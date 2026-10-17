"""Domain errors.

Shared HTTP exceptions stay defined in app.core.exceptions and are re-exported
so domain code has one import path. Pillar lookup errors are domain-specific.
"""
from app.core.exceptions import (
    AuthenticationException,
    CrawlerException,
    DristikException,
    EntityNotFoundException,
)

__all__ = [
    "AuthenticationException",
    "CrawlerException",
    "DomainError",
    "DristikException",
    "EntityNotFoundException",
    "PillarNotFound",
    "UnmeasuredDependency",
]


class DomainError(DristikException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code=status_code)


class PillarNotFound(DomainError):
    def __init__(self, pillar_id: str):
        super().__init__(f"Pillar '{pillar_id}' is not registered.", status_code=404)
        self.pillar_id = pillar_id


class UnmeasuredDependency(DomainError):
    """A caller asked for a metric whose source is not connected."""

    def __init__(self, metric: str, source: str):
        super().__init__(f"{metric} is unmeasured because {source} is not connected.", status_code=409)
        self.metric = metric
        self.source = source
