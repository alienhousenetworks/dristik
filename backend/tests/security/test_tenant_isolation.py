"""A run the caller does not own is not found."""
import pytest
from fastapi import HTTPException

from app.identity.authorization import UserIdentity
from app.identity.roles import UserRole
from app.tenancy.isolation import require_analysis


def test_missing_run_is_not_found():
    owner = UserIdentity(org_id="org_1", email="owner@example.com", role=UserRole.OWNER)
    with pytest.raises(HTTPException) as caught:
        require_analysis("run_does_not_exist", owner)
    assert caught.value.status_code == 404
