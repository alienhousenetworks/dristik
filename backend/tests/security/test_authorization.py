"""Role permissions stay on the authorizer."""
from app.identity.authorization import ROLE_PERMISSIONS, Authorizer, UserIdentity
from app.identity.roles import ORG_STAFF_ROLES, UserRole


def test_viewer_cannot_approve_patches():
    viewer = UserIdentity(org_id="org_1", email="viewer@example.com", role=UserRole.VIEWER)
    owner = UserIdentity(org_id="org_1", email="owner@example.com", role=UserRole.OWNER)
    assert Authorizer.can_perform(viewer, "patches:approve") is False
    assert Authorizer.can_perform(owner, "patches:approve") is True
    assert UserRole.ANALYST in ORG_STAFF_ROLES
    assert "patches:approve" not in ROLE_PERMISSIONS[UserRole.VIEWER]
