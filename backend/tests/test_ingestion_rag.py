from fastapi.testclient import TestClient


def test_document_ingestion_chunking_and_deduplication(client: TestClient, auth_helper):
    """Document ingestion creates chunks, computes SHA-256 hash, and deduplicates identical uploads."""
    owner, owner_headers = auth_helper("ingest_lead@example.com", "Password123!", "Ingest Lead")

    p_res = client.post("/api/projects", json={"name": "Ingestion Project"}, headers=owner_headers)
    project_id = p_res.json()["id"]

    content = (
        "Stripe Webhook Architecture and Secret Rotation Guide.\n\n"
        "All incoming webhook payloads from api.stripe.com must be validated using the Stripe webhook secret. "
        "The webhook signing secret is stored in AWS Secrets Manager under prod/ecommerce/stripe-webhook-secret. "
        "During high-load flash sales, webhook events trigger an asynchronous SQS background queue worker to prevent HTTP 504 timeouts. "
        "If the webhook queue worker fails 3 consecutive times, messages are dead-lettered to orders-payment-failures-dlq."
    )

    # 1. First Ingestion
    ingest_res1 = client.post(
        f"/api/projects/{project_id}/sources",
        json={
            "title": "Stripe Webhook Architecture",
            "content": content,
            "provider_type": "file_upload",
            "source_type": "runbook",
        },
        headers=owner_headers,
    )
    assert ingest_res1.status_code == 201
    source1 = ingest_res1.json()
    assert source1["content_hash"] is not None
    assert source1["chunk_count"] >= 1
    first_id = source1["id"]

    # 2. Second Ingestion with identical content: deduplication returns existing record without creating duplicate
    ingest_res2 = client.post(
        f"/api/projects/{project_id}/sources",
        json={
            "title": "Stripe Webhook Architecture Duplicate",
            "content": content,
            "provider_type": "file_upload",
            "source_type": "runbook",
        },
        headers=owner_headers,
    )
    assert ingest_res2.status_code == 201
    source2 = ingest_res2.json()
    assert source2["id"] == first_id  # Same record ID, deduplicated

    # 3. List sources
    list_res = client.get(f"/api/projects/{project_id}/sources", headers=owner_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1


def test_rag_question_answering_and_evidence_abstention(client: TestClient, auth_helper):
    """RAG chatbot cites retrieved evidence for supported queries and abstains when evidence is missing."""
    owner, owner_headers = auth_helper("rag_user@example.com", "Password123!", "RAG User")

    p_res = client.post("/api/projects", json={"name": "RAG Verification Project"}, headers=owner_headers)
    project_id = p_res.json()["id"]

    # Ingest technical documentation
    client.post(
        f"/api/projects/{project_id}/sources",
        json={
            "title": "PostgreSQL Failover & Connection Pooling",
            "content": (
                "PostgreSQL Primary connection pooler runs PgBouncer on port 6432. "
                "Max client connections is configured to 500 connections. "
                "Read replicas are located in us-east-1b and us-east-1c with streaming replication lag under 15ms. "
                "Emergency failover is initiated via Patroni using etcd distributed consensus."
            ),
            "provider_type": "file_upload",
            "source_type": "runbook",
        },
        headers=owner_headers,
    )

    # 1. Query with sufficient evidence: Ask about PgBouncer max connections
    ask_res1 = client.post(
        f"/api/projects/{project_id}/ask",
        json={"question": "What is the max client connections for PgBouncer?", "top_k": 3},
        headers=owner_headers,
    )
    assert ask_res1.status_code == 200
    data1 = ask_res1.json()
    assert data1["has_sufficient_evidence"] is True
    assert len(data1["citations"]) >= 1
    assert data1["confidence"] > 0.0
    assert "PgBouncer" in data1["answer"] or "connections" in data1["answer"]

    # 2. Query with NO evidence: Ask about an unmentioned system (e.g. Kubernetes cluster auto-scaler)
    ask_res2 = client.post(
        f"/api/projects/{project_id}/ask",
        json={"question": "How does the Kubernetes HPA auto-scaler scale worker nodes on Azure AKS?", "top_k": 3},
        headers=owner_headers,
    )
    assert ask_res2.status_code == 200
    data2 = ask_res2.json()
    # Should honestly abstain
    assert data2["has_sufficient_evidence"] is False
    assert "could not find" in data2["answer"].lower()
    assert data2["confidence"] == 0.0


def test_ai_assisted_handoff_generation(client: TestClient, auth_helper):
    """AI handoff generator automatically extracts tasks, dependencies, and risks from project sources."""
    owner, owner_headers = auth_helper("ai_lead@example.com", "Password123!", "AI Lead")
    successor, _ = auth_helper("next_lead@example.com", "Password123!", "Next Lead")

    p_res = client.post("/api/projects", json={"name": "AI Generation Project"}, headers=owner_headers)
    project_id = p_res.json()["id"]

    # Ingest Jira issue with deadlock blocker
    client.post(
        f"/api/projects/{project_id}/sources",
        json={
            "title": "ECOM-202: Inventory SKU Concurrency Deadlock",
            "content": (
                "Concurrent checkout carts purchasing high-demand SKUs trigger database deadlock. "
                "Blocked on database lock restructuring. Requires optimistic locking with row versioning."
            ),
            "source_id": "ECOM-202",
            "provider_type": "jira",
            "source_type": "ticket",
        },
        headers=owner_headers,
    )

    # Generate handoff
    gen_res = client.post(
        f"/api/projects/{project_id}/handoffs/generate",
        json={
            "title": "Generated Sprint Handoff",
            "successor_id": successor["id"],
            "target_completion_date": "2026-11-30",
        },
        headers=owner_headers,
    )
    assert gen_res.status_code == 201
    gen_data = gen_res.json()
    assert gen_data["sources_analyzed_count"] >= 1
    assert gen_data["extracted_tasks_count"] >= 1
    assert gen_data["readiness_score"] > 0

    handoff = gen_data["handoff"]
    assert handoff["title"] == "Generated Sprint Handoff"
    assert handoff["status"] == "draft"
    tasks = handoff["summary"]["tasks"]
    assert any("ECOM-202" in t["title"] for t in tasks)
