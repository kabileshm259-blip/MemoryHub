import uuid
from fastapi.testclient import TestClient


def test_handoff_creation_and_retrieval(client: TestClient, auth_helper):
    """Authenticated project members can create and retrieve handoffs in draft state."""
    owner, owner_headers = auth_helper("handoff_owner@example.com", "Password123!", "Handoff Owner")

    # Create project
    p_res = client.post("/api/projects", json={"name": "Handoff Project Alpha"}, headers=owner_headers)
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # Create draft handoff
    create_res = client.post(
        f"/api/projects/{project_id}/handoffs",
        json={
            "title": "Core Checkout Service Handoff",
            "summary": {
                "executive_summary": "Handover documentation for checkout payment gateway microservice.",
                "key_responsibilities": ["Primary maintenance of checkout services", "Sentry alert triage"],
                "tasks": [
                    {
                        "id": "task_1",
                        "title": "Rotate Stripe webhook secret",
                        "description": "Update AWS secret prod/ecommerce/stripe and verify pod reload.",
                        "status": "todo",
                        "priority": "high",
                        "deadline": "2026-11-15",
                    }
                ],
                "dependencies": [
                    {
                        "id": "dep_1",
                        "name": "Stripe PaymentIntents API",
                        "type": "api",
                        "description": "External payment tokenization endpoint.",
                        "criticality": "high",
                        "contact_or_link": "https://dashboard.stripe.com",
                    }
                ],
                "risks": [
                    {
                        "id": "risk_1",
                        "category": "operational",
                        "title": "Webhook dropouts during network blips",
                        "severity": "medium",
                        "impact": "Delayed order confirmation.",
                        "mitigation": "Enable exponential backoff retry in SQS queue.",
                        "status": "identified",
                    }
                ],
                "resources": [
                    {
                        "id": "res_1",
                        "title": "Payment Runbook",
                        "type": "runbook",
                        "url_or_path": "https://wiki.company.internal/runbooks/payments",
                        "notes": "Emergency failover procedures.",
                    }
                ],
            },
        },
        headers=owner_headers,
    )
    assert create_res.status_code == 201
    handoff = create_res.json()
    assert handoff["title"] == "Core Checkout Service Handoff"
    assert handoff["status"] == "draft"
    assert "readiness_score" in handoff["summary"]
    # Score should be calculated with explainable breakdown
    score_data = handoff["summary"]["readiness_score"]
    assert score_data["score"] > 0
    assert "breakdown" in score_data

    # Retrieve handoff by ID
    get_res = client.get(f"/api/projects/{project_id}/handoffs/{handoff['id']}", headers=owner_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == handoff["id"]


def test_handoff_lifecycle_transitions_and_guards(client: TestClient, auth_helper):
    """Verify strict handoff state transitions: draft -> in_review -> approved -> acknowledged."""
    owner, owner_headers = auth_helper("boss_lead@example.com", "Password123!", "Lead Boss")
    successor, succ_headers = auth_helper("succ_engineer@example.com", "Password123!", "Successor Eng")

    # Create project and add successor as editor
    p_res = client.post("/api/projects", json={"name": "Lifecycle Project"}, headers=owner_headers)
    project_id = p_res.json()["id"]

    client.post(
        f"/api/projects/{project_id}/members",
        json={"email": "succ_engineer@example.com", "role": "editor"},
        headers=owner_headers,
    )

    # 1. Create draft handoff designating successor
    create_res = client.post(
        f"/api/projects/{project_id}/handoffs",
        json={
            "title": "DevOps Infrastructure Handoff",
            "summary": {
                "successor_id": successor["id"],
                "successor_name": successor["display_name"],
                "key_responsibilities": ["Kubernetes cluster upgrades"],
                "tasks": [{"id": "t1", "title": "Upgrade EKS cluster to 1.30", "status": "todo", "priority": "high"}],
            },
        },
        headers=owner_headers,
    )
    assert create_res.status_code == 201
    handoff_id = create_res.json()["id"]

    # 2. Invalid transition: draft cannot jump directly to approved (must go to in_review first)
    invalid_jump = client.post(
        f"/api/projects/{project_id}/handoffs/{handoff_id}/status",
        json={"status": "approved"},
        headers=owner_headers,
    )
    assert invalid_jump.status_code == 400

    # 3. Transition: draft -> in_review
    review_res = client.post(
        f"/api/projects/{project_id}/handoffs/{handoff_id}/status",
        json={"status": "in_review", "comment": "Ready for initial successor review."},
        headers=owner_headers,
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "in_review"

    # 4. Successor adds review comment
    comment_res = client.post(
        f"/api/projects/{project_id}/handoffs/{handoff_id}/comments",
        json={"content": "Reviewed tasks. Please ensure rollback scripts are documented.", "comment_type": "comment"},
        headers=succ_headers,
    )
    assert comment_res.status_code == 201
    assert comment_res.json()["author_name"] == "Successor Eng"

    # 5. Successor approves handoff
    approve_res = client.post(
        f"/api/projects/{project_id}/handoffs/{handoff_id}/status",
        json={"status": "approved", "comment": "Requirements clear, approved."},
        headers=succ_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    # 6. Successor formally acknowledges receipt
    ack_res = client.post(
        f"/api/projects/{project_id}/handoffs/{handoff_id}/acknowledge",
        headers=succ_headers,
    )
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "acknowledged"
    assert len(ack_data["acknowledgements"]) == 1
    assert ack_data["acknowledgements"][0]["user_id"] == successor["id"]

    # Verify score reflects acknowledgement bonus
    updated_score = ack_data["summary"]["readiness_score"]["breakdown"]["successor_readiness"]
    assert updated_score == 20  # Full 20 points (10 for assigned + 10 for acknowledged)
