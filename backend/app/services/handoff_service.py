import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import (
    AuditEvent,
    Handoff,
    HandoffAcknowledgement,
    HandoffComment,
    Notification,
    Project,
    ProjectMembership,
    User,
)
from app.schemas import (
    HandoffCommentCreateRequest,
    HandoffCommentResponse,
    HandoffCreateRequest,
    HandoffListResponse,
    HandoffResponse,
    HandoffStatusType,
    HandoffUpdateRequest,
    ReadinessBreakdown,
    ReadinessScoreData,
    RecommendationItem,
)


class ReadinessScoringEngine:
    """
    Explainable Readiness Scoring Engine (0-100 score).
    Evaluates 5 operational dimensions:
    - Task Clarity & Status (25%)
    - Technical Dependencies Documented (20%)
    - Risk & Blocker Mitigation (20%)
    - Runbooks & Resources Complete (15%)
    - Successor Assignment & Acknowledgement (20%)
    """

    @classmethod
    def calculate_readiness(
        cls, summary: Dict[str, Any], is_acknowledged: bool = False
    ) -> ReadinessScoreData:
        tasks = summary.get("tasks", [])
        dependencies = summary.get("dependencies", [])
        risks = summary.get("risks", [])
        resources = summary.get("resources", [])
        successor_id = summary.get("successor_id")

        missing_items: List[str] = []
        recommendations: List[RecommendationItem] = []

        # 1. Task Clarity (0-25)
        task_points = 0
        if not tasks:
            missing_items.append("No operational handover tasks defined.")
            recommendations.append(
                RecommendationItem(
                    priority="high",
                    action="Add handover tasks with deadlines and priority levels.",
                    reason="Outgoing employee responsibilities must be explicitly tracked.",
                )
            )
        else:
            task_points += 10  # Base points for having tasks
            # Check completeness of task fields
            complete_tasks = sum(
                1
                for t in tasks
                if t.get("status") and t.get("priority") and (t.get("deadline") or t.get("description"))
            )
            ratio = complete_tasks / len(tasks)
            task_points += int(15 * ratio)

            # Check for unresolved blockers
            blocked_tasks = [t for t in tasks if t.get("status") == "blocked"]
            if blocked_tasks:
                task_points = max(5, task_points - 5)
                missing_items.append(f"{len(blocked_tasks)} tasks currently marked as BLOCKED.")
                recommendations.append(
                    RecommendationItem(
                        priority="high",
                        action="Resolve or reassign blocked handover items.",
                        reason="Successor cannot take over blocked tasks without resolution path.",
                    )
                )

        # 2. Dependencies Documented (0-20)
        dep_points = 0
        if not dependencies:
            missing_items.append("Technical dependencies and third-party integrations undocumented.")
            recommendations.append(
                RecommendationItem(
                    priority="medium",
                    action="Document all downstream services, databases, and APIs.",
                    reason="Operational continuity requires knowing what systems the project relies on.",
                )
            )
        else:
            dep_points += 10
            # Higher score if dependencies have contact/link and criticality
            well_defined = sum(
                1 for d in dependencies if d.get("contact_or_link") and d.get("criticality")
            )
            dep_points += min(10, int(10 * (well_defined / max(1, len(dependencies)))))

        # 3. Risk Mitigation (0-20)
        risk_points = 0
        if not risks:
            missing_items.append("No technical risks or single-points-of-failure identified.")
            recommendations.append(
                RecommendationItem(
                    priority="medium",
                    action="Identify potential failure modes, bottlenecks, or single-points-of-failure.",
                    reason="Proactive risk disclosure prevents system outages during transition.",
                )
            )
        else:
            risk_points += 10
            # Check if risks have mitigation strategies
            mitigated = sum(1 for r in risks if r.get("mitigation") and len(r.get("mitigation", "").strip()) > 10)
            risk_points += min(10, int(10 * (mitigated / max(1, len(risks)))))

            unmitigated_critical = [
                r for r in risks if r.get("severity") in ("high", "critical") and not r.get("mitigation")
            ]
            if unmitigated_critical:
                risk_points = max(0, risk_points - 5)
                missing_items.append(f"{len(unmitigated_critical)} high-severity risks have no mitigation.")

        # 4. Resources Complete (0-15)
        res_points = 0
        if not resources:
            missing_items.append("No runbooks, repositories, or documentation links attached.")
            recommendations.append(
                RecommendationItem(
                    priority="high",
                    action="Attach Git repositories, incident runbooks, and monitoring dashboard links.",
                    reason="Successor requires operational links to diagnose production incidents.",
                )
            )
        else:
            res_points += 8
            runbooks_or_repos = [
                r for r in resources if r.get("type") in ("runbook", "repository", "dashboard")
            ]
            if runbooks_or_repos:
                res_points += 7

        # 5. Successor Readiness (0-20)
        succ_points = 0
        if not successor_id:
            missing_items.append("Successor / incoming engineer has not been designated.")
            recommendations.append(
                RecommendationItem(
                    priority="high",
                    action="Designate a successor engineer for this handoff.",
                    reason="Handoff cannot be completed without an assigned recipient.",
                )
            )
        else:
            succ_points += 10  # Assigned
            if is_acknowledged:
                succ_points += 10  # Formal successor acknowledgement
            else:
                missing_items.append("Successor has not yet formally acknowledged receipt of handoff.")
                recommendations.append(
                    RecommendationItem(
                        priority="medium",
                        action="Successor must review and acknowledge the handoff.",
                        reason="Final stage verification requires explicit sign-off from incoming employee.",
                    )
                )

        total_score = task_points + dep_points + risk_points + res_points + succ_points
        total_score = min(100, max(0, total_score))

        if total_score >= 90:
            level = "complete"
        elif total_score >= 75:
            level = "high"
        elif total_score >= 55:
            level = "medium"
        elif total_score >= 35:
            level = "low"
        else:
            level = "critical"

        return ReadinessScoreData(
            score=total_score,
            level=level,
            breakdown=ReadinessBreakdown(
                task_clarity=task_points,
                dependencies_documented=dep_points,
                risk_mitigation=risk_points,
                resources_complete=res_points,
                successor_readiness=succ_points,
            ),
            missing_items=missing_items,
            recommendations=recommendations,
        )


class HandoffService:
    """
    Core handoff lifecycle orchestration service:
    CRUD, strict state transitions, successor assignment,
    readiness scoring, review comments, and audit logging.
    """

    VALID_TRANSITIONS = {
        "draft": ["in_review"],
        "in_review": ["approved", "draft"],
        "approved": ["acknowledged", "draft"],
        "acknowledged": ["completed", "draft"],
        "completed": [],
    }

    @classmethod
    def _format_handoff_response(cls, handoff: Handoff) -> HandoffResponse:
        acks = [
            {
                "id": ack.id,
                "handoff_id": ack.handoff_id,
                "user_id": ack.user_id,
                "user_display_name": ack.user.display_name if ack.user else None,
                "acknowledged_at": ack.acknowledged_at,
            }
            for ack in (handoff.acknowledgements or [])
        ]
        comments = [
            {
                "id": c.id,
                "handoff_id": c.handoff_id,
                "user_id": c.user_id,
                "author_name": c.user.display_name if c.user else "Anonymous",
                "content": c.content,
                "comment_type": c.comment_type,
                "created_at": c.created_at,
            }
            for c in (handoff.comments or [])
        ]

        creator_name = handoff.creator.display_name if handoff.creator else None

        return HandoffResponse(
            id=handoff.id,
            project_id=handoff.project_id,
            creator_id=handoff.creator_id,
            creator_name=creator_name,
            title=handoff.title,
            summary=handoff.summary,
            status=handoff.status,
            created_at=handoff.created_at,
            updated_at=handoff.updated_at,
            acknowledgements=acks,
            comments=comments,
        )

    @classmethod
    def create_handoff(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        data: HandoffCreateRequest,
    ) -> HandoffResponse:
        """Create a new handoff in 'draft' status."""
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

        if membership not in ("owner", "editor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owners and editors can create handoffs",
            )

        summary = data.summary or {}
        # Ensure knowledge owner metadata is present
        if "knowledge_owner_id" not in summary:
            summary["knowledge_owner_id"] = str(current_user.id)
            summary["knowledge_owner_name"] = current_user.display_name

        # Calculate initial readiness score
        score_data = ReadinessScoringEngine.calculate_readiness(summary, is_acknowledged=False)
        summary["readiness_score"] = score_data.model_dump()

        handoff = Handoff(
            project_id=project_id,
            creator_id=current_user.id,
            title=data.title,
            summary=summary,
            status="draft",
        )
        db.add(handoff)
        db.flush()

        audit = AuditEvent(
            user_id=current_user.id,
            project_id=project_id,
            event_type="handoff_created",
            resource_type="handoff",
            resource_id=str(handoff.id),
            metadata_json={"title": handoff.title, "status": handoff.status},
        )
        db.add(audit)
        db.commit()
        db.refresh(handoff)

        return cls._format_handoff_response(handoff)

    @classmethod
    def get_handoff(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        handoff_id: uuid.UUID,
    ) -> HandoffResponse:
        """Retrieve a specific handoff only if user is an authorized project member."""
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

        handoff = db.execute(
            select(Handoff).where(
                Handoff.id == handoff_id,
                Handoff.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not handoff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Handoff not found",
            )

        return cls._format_handoff_response(handoff)

    @classmethod
    def list_handoffs(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> HandoffListResponse:
        """List all handoffs for a project."""
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

        total_stmt = select(func.count(Handoff.id)).where(Handoff.project_id == project_id)
        total = db.execute(total_stmt).scalar_one()

        stmt = (
            select(Handoff)
            .where(Handoff.project_id == project_id)
            .order_by(Handoff.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        handoffs = db.execute(stmt).scalars().all()

        return HandoffListResponse(
            items=[cls._format_handoff_response(h) for h in handoffs],
            total=total,
            limit=limit,
            offset=offset,
        )

    @classmethod
    def update_handoff(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        handoff_id: uuid.UUID,
        data: HandoffUpdateRequest,
    ) -> HandoffResponse:
        """Update handoff title, structured summary, tasks, risks, or resources."""
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

        if membership not in ("owner", "editor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owners and editors can update handoffs",
            )

        handoff = db.execute(
            select(Handoff).where(
                Handoff.id == handoff_id,
                Handoff.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not handoff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Handoff not found",
            )

        if handoff.status == "completed" and membership != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Completed handoffs cannot be modified except by project owners",
            )

        if data.title is not None:
            handoff.title = data.title

        if data.summary is not None:
            # Preserve existing fields and merge
            merged_summary = dict(handoff.summary)
            merged_summary.update(data.summary)

            is_acked = bool(handoff.acknowledgements)
            score_data = ReadinessScoringEngine.calculate_readiness(merged_summary, is_acknowledged=is_acked)
            merged_summary["readiness_score"] = score_data.model_dump()
            handoff.summary = merged_summary

        if data.status is not None:
            cls.transition_status(
                db, current_user, project_id, handoff_id, data.status
            )

        handoff.updated_at = datetime.utcnow()

        audit = AuditEvent(
            user_id=current_user.id,
            project_id=project_id,
            event_type="handoff_updated",
            resource_type="handoff",
            resource_id=str(handoff.id),
            metadata_json={"title": handoff.title, "status": handoff.status},
        )
        db.add(audit)
        db.commit()
        db.refresh(handoff)

        return cls._format_handoff_response(handoff)

    @classmethod
    def transition_status(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        handoff_id: uuid.UUID,
        new_status: HandoffStatusType,
        comment: Optional[str] = None,
    ) -> HandoffResponse:
        """
        Execute a valid state transition with strict transition guards.
        draft -> in_review -> approved -> acknowledged -> completed
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

        handoff = db.execute(
            select(Handoff).where(
                Handoff.id == handoff_id,
                Handoff.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not handoff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Handoff not found",
            )

        current_status = handoff.status
        if new_status == current_status:
            return cls._format_handoff_response(handoff)

        allowed = cls.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed}",
            )

        # Transition Guards:
        if new_status == "in_review":
            # Guard: Must have title and at least 1 task or responsibility
            tasks = handoff.summary.get("tasks", [])
            responsibilities = handoff.summary.get("key_responsibilities", [])
            if not tasks and not responsibilities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot submit handoff for review without defining at least one task or key responsibility.",
                )

        elif new_status == "approved":
            # Guard: Only project owner or designated successor can approve
            successor_id_str = handoff.summary.get("successor_id")
            is_successor = successor_id_str and str(current_user.id) == successor_id_str
            if membership != "owner" and not is_successor:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only project owners or the assigned successor can approve a handoff.",
                )

        elif new_status == "acknowledged":
            # Guard: Handled via acknowledge_handoff endpoint
            pass

        elif new_status == "completed":
            # Guard: Only project owner can mark as completely finished
            if membership != "owner":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only project owners can finalize and complete a handoff.",
                )

        old_status = handoff.status
        handoff.status = new_status
        handoff.updated_at = datetime.utcnow()

        if comment:
            c = HandoffComment(
                handoff_id=handoff.id,
                user_id=current_user.id,
                content=comment,
                comment_type="approval" if new_status == "approved" else "comment",
            )
            db.add(c)

        # Emit notification to relevant parties
        successor_id_str = handoff.summary.get("successor_id")
        if successor_id_str and successor_id_str != str(current_user.id):
            notif = Notification(
                user_id=uuid.UUID(successor_id_str),
                project_id=project_id,
                title=f"Handoff '{handoff.title}' moved to {new_status}",
                message=f"Handoff status changed from {old_status} to {new_status} by {current_user.display_name}.",
                notification_type="handoff_status_changed",
                link=f"/projects/{project_id}?tab=handoffs",
            )
            db.add(notif)

        audit = AuditEvent(
            user_id=current_user.id,
            project_id=project_id,
            event_type="handoff_status_changed",
            resource_type="handoff",
            resource_id=str(handoff.id),
            metadata_json={"from": old_status, "to": new_status, "comment": comment},
        )
        db.add(audit)
        db.commit()
        db.refresh(handoff)

        return cls._format_handoff_response(handoff)

    @classmethod
    def acknowledge_handoff(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        handoff_id: uuid.UUID,
    ) -> HandoffResponse:
        """
        Successor formally acknowledges receiving the operational handoff.
        Creates HandoffAcknowledgement record, transitions status, and updates readiness score.
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

        handoff = db.execute(
            select(Handoff).where(
                Handoff.id == handoff_id,
                Handoff.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not handoff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Handoff not found",
            )

        # Check existing acknowledgement
        existing_ack = db.execute(
            select(HandoffAcknowledgement).where(
                HandoffAcknowledgement.handoff_id == handoff.id,
                HandoffAcknowledgement.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if not existing_ack:
            ack = HandoffAcknowledgement(
                handoff_id=handoff.id,
                user_id=current_user.id,
                acknowledged_at=datetime.utcnow(),
            )
            db.add(ack)

        # Update status to acknowledged if currently approved or in_review
        if handoff.status in ("in_review", "approved", "draft"):
            handoff.status = "acknowledged"

        # Update readiness score with acknowledged bonus (+10 pts)
        summary = dict(handoff.summary)
        score_data = ReadinessScoringEngine.calculate_readiness(summary, is_acknowledged=True)
        summary["readiness_score"] = score_data.model_dump()
        handoff.summary = summary
        handoff.updated_at = datetime.utcnow()

        # Notify creator
        if handoff.creator_id and handoff.creator_id != current_user.id:
            notif = Notification(
                user_id=handoff.creator_id,
                project_id=project_id,
                title=f"Handoff '{handoff.title}' Acknowledged",
                message=f"{current_user.display_name} has acknowledged receipt and assumed operational responsibility.",
                notification_type="handoff_acknowledged",
                link=f"/projects/{project_id}?tab=handoffs",
            )
            db.add(notif)

        audit = AuditEvent(
            user_id=current_user.id,
            project_id=project_id,
            event_type="handoff_acknowledged",
            resource_type="handoff",
            resource_id=str(handoff.id),
            metadata_json={"user": current_user.display_name},
        )
        db.add(audit)
        db.commit()
        db.refresh(handoff)

        return cls._format_handoff_response(handoff)

    @classmethod
    def add_comment(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        handoff_id: uuid.UUID,
        data: HandoffCommentCreateRequest,
    ) -> HandoffCommentResponse:
        """Add a review comment or blocker report to a handoff."""
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

        handoff = db.execute(
            select(Handoff).where(
                Handoff.id == handoff_id,
                Handoff.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not handoff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Handoff not found",
            )

        comment = HandoffComment(
            handoff_id=handoff.id,
            user_id=current_user.id,
            content=data.content,
            comment_type=data.comment_type,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        return HandoffCommentResponse(
            id=comment.id,
            handoff_id=comment.handoff_id,
            user_id=comment.user_id,
            author_name=current_user.display_name,
            content=comment.content,
            comment_type=comment.comment_type,
            created_at=comment.created_at,
        )
