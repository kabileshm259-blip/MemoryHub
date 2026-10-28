from fastapi.testclient import TestClient


def test_integrations_and_ecommerce_demo_seeder(client: TestClient, auth_helper):
    """Integrations can be configured, synchronized, and seeded with the E-Commerce demo dataset."""
    owner, owner_headers = auth_helper("integ_owner@example.com", "Password123!", "Integ Owner")

    p_res = client.post("/api/projects", json={"name": "E-Commerce Modernization Workspace"}, headers=owner_headers)
    project_id = p_res.json()["id"]

    # 1. Add Jira connection
    jira_res = client.post(
        f"/api/projects/{project_id}/integrations",
        json={
            "provider_type": "jira",
            "display_name": "Jira Cloud E-Commerce",
            "provider_metadata": {"domain": "company.atlassian.net", "project_key": "ECOM"},
        },
        headers=owner_headers,
    )
    assert jira_res.status_code == 201
    jira_id = jira_res.json()["id"]

    # 2. Add Slack connection
    slack_res = client.post(
        f"/api/projects/{project_id}/integrations",
        json={
            "provider_type": "slack",
            "display_name": "Engineering Slack Workspace",
            "provider_metadata": {"workspace_id": "T012345", "channels": ["#ops-checkout", "#dev-backend"]},
        },
        headers=owner_headers,
    )
    assert slack_res.status_code == 201

    # 3. List integrations
    list_res = client.get(f"/api/projects/{project_id}/integrations", headers=owner_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2

    # 4. Trigger sync on Jira connection
    sync_res = client.post(f"/api/projects/{project_id}/integrations/{jira_id}/sync", headers=owner_headers)
    assert sync_res.status_code == 200
    assert sync_res.json()["status"] == "success"

    # 5. Seed full E-Commerce Platform Modernization demo dataset
    seed_res = client.post(f"/api/projects/{project_id}/integrations/seed-demo", headers=owner_headers)
    assert seed_res.status_code == 200
    seed_data = seed_res.json()
    assert seed_data["records_ingested"] >= 5
    assert seed_data["scenario"] == "E-Commerce Platform Modernization"

    # Verify sources table has the 5 seeded records (ECOM-101, ECOM-102, ECOM-103, Slack thread, Runbook)
    sources_res = client.get(f"/api/projects/{project_id}/sources", headers=owner_headers)
    assert sources_res.status_code == 200
    sources = sources_res.json()["items"]
    titles = [s["title"] for s in sources]
    assert any("ECOM-101" in t for t in titles)
    assert any("ECOM-102" in t for t in titles)
    assert any("Runbook" in t for t in titles)


def test_unified_search_and_notifications(client: TestClient, auth_helper):
    """Unified search finds projects, handoffs, and sources; notification service tracks unread alerts."""
    owner, owner_headers = auth_helper("search_boss@example.com", "Password123!", "Search Boss")

    p_res = client.post("/api/projects", json={"name": "Searchable Core Banking"}, headers=owner_headers)
    project_id = p_res.json()["id"]

    # Ingest source
    client.post(
        f"/api/projects/{project_id}/sources",
        json={
            "title": "Ledger Database Sharding Protocol",
            "content": "Ledger transactions are sharded across 16 PostgreSQL database nodes using consistent hashing.",
            "provider_type": "file_upload",
            "source_type": "document",
        },
        headers=owner_headers,
    )

    # Create handoff
    client.post(
        f"/api/projects/{project_id}/handoffs",
        json={
            "title": "Ledger Sharding Transition",
            "summary": {
                "executive_summary": "Quarterly handoff for banking transaction sharding operations.",
                "tasks": [{"id": "t1", "title": "Audit shard rebalancing script", "status": "todo", "priority": "high"}],
            },
        },
        headers=owner_headers,
    )

    # 1. Project-scoped search for "sharding"
    search_res = client.get(f"/api/projects/{project_id}/search?q=sharding", headers=owner_headers)
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert s_data["total_matches"] >= 2
    types_found = {item["entity_type"] for item in s_data["results"]}
    assert "source" in types_found or "handoff" in types_found

    # 2. Global search
    global_res = client.get("/api/search?q=Banking", headers=owner_headers)
    assert global_res.status_code == 200
    assert global_res.json()["total_matches"] >= 1

    # 3. Notifications API
    notif_res = client.get("/api/notifications", headers=owner_headers)
    assert notif_res.status_code == 200
    assert "unread_count" in notif_res.json()
