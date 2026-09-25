"""
Integration tests for Enterprise Multi-Tenant Workspace & Domain Hierarchy Routes.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_workspace_hierarchy_lifecycle():
    # 1. List workspaces (returns default if none)
    res = client.get("/api/v1/workspaces")
    assert res.status_code == 200
    data = res.json()
    assert len(data["workspaces"]) >= 1

    # 2. Create new workspace
    create_res = client.post("/api/v1/workspaces", json={
        "name": "Acme North America",
        "slug": "acme-na",
    })
    assert create_res.status_code == 200
    ws_data = create_res.json()
    ws_id = ws_data["id"]
    assert ws_data["name"] == "Acme North America"
    assert ws_data["slug"] == "acme-na"

    # 3. Add domain to workspace
    dom_res = client.post(f"/api/v1/workspaces/{ws_id}/domains", json={
        "hostname": "https://acme.com",
        "site_type": "b2b_saas",
        "crawl_frequency": "weekly",
        "max_pages": 1000,
    })
    assert dom_res.status_code == 200
    dom_data = dom_res.json()
    dom_id = dom_data["id"]
    assert dom_data["hostname"] == "acme.com"
    assert dom_data["workspace_id"] == ws_id

    # 4. List domains in workspace
    list_doms = client.get(f"/api/v1/workspaces/{ws_id}/domains")
    assert list_doms.status_code == 200
    assert len(list_doms.json()["domains"]) == 1

    # 5. History endpoint
    hist_res = client.get(f"/api/v1/workspaces/{ws_id}/domains/{dom_id}/history")
    assert hist_res.status_code == 200
    assert hist_res.json()["domain_id"] == dom_id

    # 6. Diff endpoint with insufficient runs returns clean status
    diff_res = client.get(f"/api/v1/workspaces/{ws_id}/domains/{dom_id}/diff")
    assert diff_res.status_code == 200
    assert diff_res.json()["status"] == "INSUFFICIENT_HISTORY"
