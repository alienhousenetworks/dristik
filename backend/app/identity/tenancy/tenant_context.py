"""Current organization for the active call."""
from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Optional

current_org_id: ContextVar[Optional[str]] = ContextVar("dristik_org_id", default=None)


def set_current_org(org_id: Optional[str]) -> Token:
    return current_org_id.set(org_id)


def reset_current_org(token: Token) -> None:
    current_org_id.reset(token)


def get_current_org() -> Optional[str]:
    return current_org_id.get()
