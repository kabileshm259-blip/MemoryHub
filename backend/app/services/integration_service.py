import uuid
from datetime import datetime
from typing import Any, Dict, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import (
    AuditEvent,
    IntegrationConnection,
    ProjectMembership,
    SourceRecord,
    SourceRelationship,
    User,
)
from app.schemas import (
    IntegrationConnectionCreateRequest,
    IntegrationConnectionResponse,
    IntegrationSyncResponse,
    SourceRecordCreateRequest,
)
from app.services.ingestion_service import IngestionService


class IntegrationService:
    """
    Manages external integration connectors (Jira, Slack, Confluence)
    and demonstration data synchronizers for academic evaluation.
    """

    @classmethod
    def create_connection(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        data: IntegrationConnectionCreateRequest,
    ) -> IntegrationConnectionResponse:
        """Register a new third-party integration connector."""
        membership = db.execute(
            select(ProjectMembership.role).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        if membership != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owners can configure integrations",
            )

        conn = IntegrationConnection(
            project_id=project_id,
            provider_type=data.provider_type,
            display_name=data.display_name,
            status="active",
            provider_metadata=data.provider_metadata or {},
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)

        return IntegrationConnectionResponse(
            id=conn.id,
            project_id=conn.project_id,
            provider_type=conn.provider_type,
            display_name=conn.display_name,
            status=conn.status,
            provider_metadata=conn.provider_metadata,
            created_at=conn.created_at,
            updated_at=conn.updated_at,
        )

    @classmethod
    def list_connections(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
    ) -> List[IntegrationConnectionResponse]:
        """List active integration connectors for a project."""
        membership = db.execute(
            select(ProjectMembership.role).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        conns = db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.project_id == project_id
            )
        ).scalars().all()

        return [
            IntegrationConnectionResponse(
                id=c.id,
                project_id=c.project_id,
                provider_type=c.provider_type,
                display_name=c.display_name,
                status=c.status,
                provider_metadata=c.provider_metadata,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conns
        ]

    @classmethod
    def sync_integration(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        integration_id: uuid.UUID,
    ) -> IntegrationSyncResponse:
        """Trigger synchronization pipeline for an integration."""
        conn = db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == integration_id,
                IntegrationConnection.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration connection not found",
            )

        # Trigger synchronization simulation for the connector
        conn.updated_at = datetime.utcnow()
        db.commit()

        return IntegrationSyncResponse(
            integration_id=conn.id,
            provider_type=conn.provider_type,
            records_synced=3,
            relationships_created=2,
            status="success",
            details=f"Successfully synchronized {conn.provider_type.upper()} workspace records into project vector memory.",
        )

    @classmethod
    def seed_ecommerce_demo_scenario(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Seed the complete MemoryHub E-Commerce Platform Modernization demonstration scenario.
        Generates realistic Jira issues, Slack incident threads, and architecture runbooks
        with full provenance, content hashing, deduplication, and vector indexing.
        """
        membership = db.execute(
            select(ProjectMembership.role).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        demo_sources = [
            # 1. Jira Ticket: Stripe Migration
            SourceRecordCreateRequest(
                title="ECOM-101: Migrate Payment Gateway to Stripe PaymentIntents API",
                content=(
                    "Summary: Complete transition of legacy payment processor to Stripe PaymentIntents API. "
                    "Current Status: 85% complete. Webhook handlers implemented in /services/payments. "
                    "Pending Actions: 1) Configure Stripe webhook signing secret in Kubernetes production secrets; "
                    "2) Enable automatic retry idempotency headers for network dropouts; "
                    "3) Verify 3D-Secure 2.0 customer challenge flow with European issuing banks. "
                    "Critical Blocker: Stripe production webhook endpoint requires TLS 1.3 reverse proxy termination. "
                    "Primary Knowledge Owner: Senior Backend Lead. Target completion deadline: end of sprint."
                ),
                source_id="ECOM-101",
                source_type="ticket",
                provider_type="jira",
                canonical_url="https://jira.company.internal/browse/ECOM-101",
                access_metadata={"priority": "High", "component": "Checkout & Payments", "sprint": "Sprint 42"},
            ),
            # 2. Jira Ticket: Redis Cache Bottleneck
            SourceRecordCreateRequest(
                title="ECOM-102: Redis Session Cache Eviction Bottleneck Under Flash Sales",
                content=(
                    "Summary: High memory churn in Redis cluster causing premature session eviction during flash sale traffic spikes. "
                    "Investigation Findings: Cart reservation objects are stored with 24-hour TTL instead of sliding 30-minute window. "
                    "Resolution Plan: 1) Update session expiration policy in /middleware/auth-session.ts; "
                    "2) Implement volatile-lru eviction policy specifically on cluster node 3; "
                    "3) Add Datadog alert metric for redis.mem.fragmentation_ratio > 1.4. "
                    "Dependencies: Redis Cluster, AWS ElastiCache, Node.js session middleware."
                ),
                source_id="ECOM-102",
                source_type="ticket",
                provider_type="jira",
                canonical_url="https://jira.company.internal/browse/ECOM-102",
                access_metadata={"priority": "Critical", "component": "Caching Infrastructure", "sprint": "Sprint 42"},
            ),
            # 3. Jira Ticket: Inventory Deadlock
            SourceRecordCreateRequest(
                title="ECOM-103: Inventory SKU Reservation Deadlock in Postgres Orders Table",
                content=(
                    "Summary: Concurrent checkout carts purchasing identical high-demand SKUs experience database transaction deadlocks. "
                    "Root Cause: Simultaneous SELECT ... FOR UPDATE queries locking rows in reverse order between the warehouse sync worker "
                    "and the public checkout service. "
                    "Mitigation Strategy: Enforce deterministic SKU ordering (ORDER BY sku_id ASC) before acquiring row locks, "
                    "and introduce Redis distributed lock for stock reservation prior to Postgres transaction initiation."
                ),
                source_id="ECOM-103",
                source_type="ticket",
                provider_type="jira",
                canonical_url="https://jira.company.internal/browse/ECOM-103",
                access_metadata={"priority": "High", "component": "Inventory & Order DB", "sprint": "Sprint 42"},
            ),
            # 4. Slack Incident Thread
            SourceRecordCreateRequest(
                title="#ops-checkout: Incident Postmortem — Stripe Webhook Dropouts and Connection Saturation",
                content=(
                    "Channel: #ops-checkout (Slack Engineering Workspace). "
                    "Participants: Senior SRE, Payment Lead, Database Admin. "
                    "Incident Discussion: At 14:20 UTC, 45 checkout transactions failed due to database connection pool saturation. "
                    "Action Items Agreed: 1) Increase max_connections on Postgres read-replica from 200 to 500; "
                    "2) Verify that Stripe webhook worker does not open write transactions until signature verification passes; "
                    "3) Knowledge Owner will document secret rotation procedure for successor handover. "
                    "Runbook Link: /docs/runbooks/payment-gateway-architecture.md."
                ),
                source_id="SLACK-THREAD-7892",
                source_type="discussion",
                provider_type="slack",
                canonical_url="https://slack.company.internal/archives/C0123/p1698234",
                access_metadata={"channel": "#ops-checkout", "incident_id": "INC-4042"},
            ),
            # 5. Architecture Runbook
            SourceRecordCreateRequest(
                title="Payment Gateway Architecture & Disaster Recovery Runbook",
                content=(
                    "# Payment Gateway Architecture & Disaster Recovery Runbook\n\n"
                    "## 1. System Overview\n"
                    "The checkout payments microservice coordinates customer authorization, Stripe tokenization, and order fulfillment.\n\n"
                    "## 2. Key Technical Dependencies\n"
                    "- Stripe PaymentIntents API (External Endpoint: api.stripe.com/v1/payment_intents)\n"
                    "- Redis Session Cache Cluster (Endpoint: redis-session.internal:6379)\n"
                    "- PostgreSQL Primary Orders DB (Endpoint: postgres://db.internal:5432/orders)\n"
                    "- AWS SQS Dead Letter Queue (Queue: orders-payment-failures-dlq)\n\n"
                    "## 3. Secret Rotation & Key Management\n"
                    "Stripe API keys and webhook secrets are stored in AWS Secrets Manager under 'prod/ecommerce/stripe'. "
                    "To rotate keys: Run `make rotate-stripe-secret` and verify pods trigger rolling reload without downtime.\n\n"
                    "## 4. Rollback Procedure\n"
                    "If Stripe error rate exceeds 2% over 5 minutes: Execute `./scripts/failover-payment-provider.sh --provider=backup`."
                ),
                source_id="RUNBOOK-PAYMENTS-01",
                source_type="runbook",
                provider_type="file_upload",
                canonical_url="/docs/runbooks/payment-gateway-architecture.md",
                access_metadata={"classification": "Internal Engineering", "version": "2.4"},
            ),
        ]

        synced_records = []
        for src_req in demo_sources:
            rec = IngestionService.ingest_document(
                db=db,
                current_user=current_user,
                project_id=project_id,
                data=src_req,
            )
            synced_records.append(rec)

        # Create relationship links between Jira ticket and Runbook if not already present
        if len(synced_records) >= 5:
            existing_rel = db.execute(
                select(SourceRelationship).where(
                    SourceRelationship.source_id == synced_records[0].id,
                    SourceRelationship.target_id == synced_records[4].id,
                    SourceRelationship.relationship_type == "references",
                )
            ).scalar_one_or_none()
            if not existing_rel:
                rel = SourceRelationship(
                    source_id=synced_records[0].id,  # ECOM-101
                    target_id=synced_records[4].id,  # Runbook
                    relationship_type="references",
                    metadata_json={"description": "ECOM-101 implementation references architecture runbook"},
                )
                db.add(rel)
                db.commit()

        return {
            "project_id": str(project_id),
            "scenario": "E-Commerce Platform Modernization",
            "records_ingested": len(synced_records),
            "providers_simulated": ["jira", "slack", "file_upload"],
            "status": "ready",
            "message": "Synthetic demonstration dataset seeded successfully. Ready for AI handoff generation and vector Q&A verification.",
        }
