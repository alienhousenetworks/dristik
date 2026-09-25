import pytest
from app.tenancy.manager import tenant_manager
from app.domain.enums import DataResidency

def test_tenant_creation_and_domain_isolation():
    org_a = tenant_manager.register_organization(
        name="Acme Corp",
        slug="acme",
        allowed_domains=["acme.com", "app.acme.com"],
        budget_limit_usd=100.0
    )
    
    org_b = tenant_manager.register_organization(
        name="Globex Inc",
        slug="globex",
        allowed_domains=["globex.io"],
        budget_limit_usd=50.0
    )

    # Validate Acme domain access
    assert tenant_manager.validate_tenant_access(org_a.org_id, "https://acme.com/pricing") is True
    assert tenant_manager.validate_tenant_access(org_a.org_id, "https://app.acme.com/login") is True
    
    # Acme should NOT be allowed to audit Globex domain under its policy
    assert tenant_manager.validate_tenant_access(org_a.org_id, "https://globex.io") is False
    
    # Globex should NOT be allowed to audit Acme domain
    assert tenant_manager.validate_tenant_access(org_b.org_id, "https://acme.com") is False

def test_tenant_budget_hard_stop():
    org = tenant_manager.register_organization(
        name="Budget Limited Org",
        slug="budget-org",
        budget_limit_usd=10.0
    )

    assert tenant_manager.validate_tenant_access(org.org_id, "https://example.com") is True
    
    # Simulate spending over budget
    tenant_manager.record_cost(org.org_id, 12.50)
    
    # Should fail closed
    assert tenant_manager.validate_tenant_access(org.org_id, "https://example.com") is False

def test_tenant_soft_delete_and_legal_hold():
    org = tenant_manager.register_organization(
        name="Compliance Org",
        slug="compliance",
        budget_limit_usd=200.0
    )

    # Place legal hold
    org.is_legal_hold = True
    with pytest.raises(PermissionError):
        tenant_manager.soft_delete_organization(org.org_id)

    # Remove legal hold and soft delete
    org.is_legal_hold = False
    assert tenant_manager.soft_delete_organization(org.org_id) is True
    assert tenant_manager.get_organization(org.org_id) is None
