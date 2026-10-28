import uuid
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.models import Handoff, Project, ProjectMembership, SourceRecord, User
from app.schemas import SearchItem, SearchResponse
from app.services.vector_service import VectorService


class SearchService:
    """
    Multi-entity unified keyword and semantic search engine.
    Searches across projects, handoffs, tasks, source documents, and vector memory.
    """

    @classmethod
    def search(
        cls,
        db: Session,
        current_user: User,
        query: str,
        project_id: Optional[uuid.UUID] = None,
        limit: int = 20,
    ) -> SearchResponse:
        """
        Unified search endpoint.
        If project_id is provided, scopes search to that project;
        otherwise searches all projects accessible to current_user.
        """
        results: List[SearchItem] = []
        term = query.strip()
        if not term:
            return SearchResponse(query=query, results=[], total_matches=0)

        pattern = f"%{term}%"

        # 1. Search Accessible Projects
        proj_stmt = (
            select(Project)
            .join(ProjectMembership, Project.id == ProjectMembership.project_id)
            .where(
                ProjectMembership.user_id == current_user.id,
                or_(
                    Project.name.ilike(pattern),
                    Project.description.ilike(pattern),
                ),
            )
        )
        if project_id:
            proj_stmt = proj_stmt.where(Project.id == project_id)

        projects = db.execute(proj_stmt).scalars().all()
        for p in projects:
            results.append(
                SearchItem(
                    id=str(p.id),
                    entity_type="project",
                    title=p.name,
                    snippet=(p.description or "Project Workspace")[:200],
                    link=f"/projects/{p.id}",
                    score=1.0,
                )
            )

        # 2. Search Handoffs
        handoff_stmt = (
            select(Handoff)
            .join(ProjectMembership, Handoff.project_id == ProjectMembership.project_id)
            .where(
                ProjectMembership.user_id == current_user.id,
                or_(
                    Handoff.title.ilike(pattern),
                    Handoff.status.ilike(pattern),
                ),
            )
        )
        if project_id:
            handoff_stmt = handoff_stmt.where(Handoff.project_id == project_id)

        handoffs = db.execute(handoff_stmt).scalars().all()
        for h in handoffs:
            summary = h.summary or {}
            exec_summary = summary.get("executive_summary", "")
            results.append(
                SearchItem(
                    id=str(h.id),
                    entity_type="handoff",
                    title=f"Handoff: {h.title} ({h.status.upper()})",
                    snippet=exec_summary[:200] if exec_summary else f"Handoff document in {h.status} status.",
                    link=f"/projects/{h.project_id}?tab=handoffs",
                    score=0.95,
                )
            )

            # Search tasks inside handoff summary
            tasks = summary.get("tasks", [])
            for t in tasks:
                t_title = t.get("title", "")
                t_desc = t.get("description", "")
                if term.lower() in t_title.lower() or term.lower() in t_desc.lower():
                    results.append(
                        SearchItem(
                            id=t.get("id", str(uuid.uuid4())),
                            entity_type="task",
                            title=f"Task: {t_title}",
                            snippet=f"Status: {t.get('status')} | Priority: {t.get('priority')} | {t_desc[:120]}",
                            link=f"/projects/{h.project_id}?tab=handoffs",
                            score=0.9,
                        )
                    )

        # 3. Search Source Records
        source_stmt = (
            select(SourceRecord)
            .join(ProjectMembership, SourceRecord.project_id == ProjectMembership.project_id)
            .where(
                ProjectMembership.user_id == current_user.id,
                or_(
                    SourceRecord.title.ilike(pattern),
                    SourceRecord.content.ilike(pattern),
                    SourceRecord.source_id.ilike(pattern),
                ),
            )
        )
        if project_id:
            source_stmt = source_stmt.where(SourceRecord.project_id == project_id)

        sources = db.execute(source_stmt).scalars().all()
        for s in sources:
            results.append(
                SearchItem(
                    id=str(s.id),
                    entity_type="source",
                    title=f"Source: {s.title or s.source_id} ({s.provider_type})",
                    snippet=(s.content or "")[:200],
                    link=f"/projects/{s.project_id}?tab=sources",
                    score=0.85,
                )
            )

        # 4. Semantic Search via Vector Service if project_id is given
        if project_id:
            vector_matches = VectorService.search_similar(
                project_id=project_id,
                query=term,
                top_k=4,
            )
            for vm in vector_matches:
                meta = vm.get("metadata", {})
                results.append(
                    SearchItem(
                        id=vm.get("id", str(uuid.uuid4())),
                        entity_type="vector_chunk",
                        title=f"Vector Context: {meta.get('title', 'Memory Chunk')}",
                        snippet=vm.get("document", "")[:200],
                        link=f"/projects/{project_id}?tab=sources",
                        score=vm.get("score", 0.8),
                    )
                )

        # Sort by score descending and truncate
        results.sort(key=lambda x: x.score, reverse=True)
        return SearchResponse(
            query=query,
            results=results[:limit],
            total_matches=len(results),
        )
