import hashlib
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import AuditEvent, IntegrationConnection, Project, ProjectMembership, SourceRecord, User
from app.schemas import SourceRecordCreateRequest, SourceRecordResponse
from app.services.vector_service import VectorService


class TextChunker:
    """
    Sliding window chunking algorithm with paragraph and sentence boundary preservation.
    Default chunk size: ~800 characters with 150 characters overlap.
    """

    @classmethod
    def chunk(cls, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        if not text or not text.strip():
            return []

        cleaned_text = text.strip()
        if len(cleaned_text) <= chunk_size:
            return [cleaned_text]

        chunks = []
        start = 0
        text_len = len(cleaned_text)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(cleaned_text[start:])
                break

            # Try to find a paragraph break (\n\n) near the end
            split_idx = cleaned_text.rfind("\n\n", start + overlap, end)
            if split_idx == -1:
                # Try sentence break (. or ! or ?)
                split_idx = cleaned_text.rfind(". ", start + overlap, end)
                if split_idx != -1:
                    split_idx += 1  # Include the period
            if split_idx == -1:
                # Try line break (\n)
                split_idx = cleaned_text.rfind("\n", start + overlap, end)
            if split_idx == -1:
                # Try whitespace
                split_idx = cleaned_text.rfind(" ", start + overlap, end)

            # Fallback to hard cut if no boundary found
            if split_idx == -1 or split_idx <= start:
                split_idx = end

            chunk = cleaned_text[start:split_idx].strip()
            if chunk:
                chunks.append(chunk)

            # Advance start index accounting for overlap
            start = max(start + 1, split_idx - overlap)

        return chunks


class IngestionService:
    """
    Knowledge source ingestion, SHA-256 deduplication,
    text extraction, chunking, and vector indexing service.
    """

    @classmethod
    def compute_hash(cls, content: str) -> str:
        """Compute SHA-256 hash of normalized text for deduplication."""
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    @classmethod
    def ingest_document(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        data: SourceRecordCreateRequest,
    ) -> SourceRecordResponse:
        """
        Ingest a document or external record into the project.
        Enforces project membership, computes content hash, detects duplicates,
        generates sliding-window chunks, and indexes vectors into ChromaDB.
        """
        # Verify user has access to project
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
                detail="Only project owners and editors can ingest knowledge sources",
            )

        content_hash = cls.compute_hash(data.content)

        # Check for duplicate document by hash in this project
        existing_stmt = select(SourceRecord).where(
            SourceRecord.project_id == project_id,
            SourceRecord.content_hash == content_hash,
        )
        existing = db.execute(existing_stmt).scalar_one_or_none()

        if existing:
            # Refresh timestamp on existing record
            existing.last_synced_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return SourceRecordResponse(
                id=existing.id,
                project_id=existing.project_id,
                integration_id=existing.integration_id,
                provider_type=existing.provider_type,
                source_id=existing.source_id,
                source_type=existing.source_type,
                title=existing.title,
                content=existing.content,
                canonical_url=existing.canonical_url,
                source_created_at=existing.source_created_at,
                source_updated_at=existing.source_updated_at,
                last_synced_at=existing.last_synced_at,
                content_hash=existing.content_hash,
                chunk_count=len(TextChunker.chunk(existing.content or "")),
            )

        # Find or create default integration connection for this provider type
        integration = db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.project_id == project_id,
                IntegrationConnection.provider_type == data.provider_type,
            )
        ).scalar_one_or_none()

        if not integration:
            integration = IntegrationConnection(
                project_id=project_id,
                provider_type=data.provider_type,
                display_name=f"Default {data.provider_type.replace('_', ' ').title()}",
                status="active",
                provider_metadata={"auto_created": True},
            )
            db.add(integration)
            db.flush()

        source_id = data.source_id or f"doc_{uuid.uuid4().hex[:8]}"

        record = SourceRecord(
            project_id=project_id,
            integration_id=integration.id,
            provider_type=data.provider_type,
            source_id=source_id,
            source_type=data.source_type,
            title=data.title,
            content=data.content,
            canonical_url=data.canonical_url,
            source_created_at=datetime.utcnow(),
            source_updated_at=datetime.utcnow(),
            access_metadata=data.access_metadata or {},
            content_hash=content_hash,
        )
        db.add(record)
        db.flush()

        # Chunk text and index into vector store
        chunks = TextChunker.chunk(data.content)
        for idx, chunk_text in enumerate(chunks):
            chunk_id = f"{record.id}_chunk_{idx}"
            metadata = {
                "source_id": str(record.id),
                "project_id": str(project_id),
                "title": data.title,
                "source_type": data.source_type,
                "provider_type": data.provider_type,
                "chunk_index": idx,
                "total_chunks": len(chunks),
            }
            VectorService.index_chunk(
                project_id=project_id,
                chunk_id=chunk_id,
                document=chunk_text,
                metadata=metadata,
            )

        # Record audit event
        audit = AuditEvent(
            user_id=current_user.id,
            project_id=project_id,
            event_type="source_ingested",
            resource_type="source_record",
            resource_id=str(record.id),
            metadata_json={
                "title": record.title,
                "provider_type": record.provider_type,
                "chunks_count": len(chunks),
                "content_hash": content_hash,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(record)

        return SourceRecordResponse(
            id=record.id,
            project_id=record.project_id,
            integration_id=record.integration_id,
            provider_type=record.provider_type,
            source_id=record.source_id,
            source_type=record.source_type,
            title=record.title,
            content=record.content,
            canonical_url=record.canonical_url,
            source_created_at=record.source_created_at,
            source_updated_at=record.source_updated_at,
            last_synced_at=record.last_synced_at,
            content_hash=record.content_hash,
            chunk_count=len(chunks),
        )

    @classmethod
    def list_sources(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
    ) -> List[SourceRecordResponse]:
        """List all indexed sources for a project."""
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

        stmt = (
            select(SourceRecord)
            .where(SourceRecord.project_id == project_id)
            .order_by(SourceRecord.last_synced_at.desc())
        )
        records = db.execute(stmt).scalars().all()

        results = []
        for r in records:
            chunk_count = len(TextChunker.chunk(r.content or ""))
            results.append(
                SourceRecordResponse(
                    id=r.id,
                    project_id=r.project_id,
                    integration_id=r.integration_id,
                    provider_type=r.provider_type,
                    source_id=r.source_id,
                    source_type=r.source_type,
                    title=r.title,
                    content=r.content,
                    canonical_url=r.canonical_url,
                    source_created_at=r.source_created_at,
                    source_updated_at=r.source_updated_at,
                    last_synced_at=r.last_synced_at,
                    content_hash=r.content_hash,
                    chunk_count=chunk_count,
                )
            )
        return results

    @classmethod
    def delete_source(
        cls,
        db: Session,
        current_user: User,
        project_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> None:
        """Delete a source record and remove all vector index chunks."""
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
                detail="Only project owners and editors can delete knowledge sources",
            )

        record = db.execute(
            select(SourceRecord).where(
                SourceRecord.id == source_id,
                SourceRecord.project_id == project_id,
            )
        ).scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source record not found",
            )

        # Remove vector chunks from vector store
        VectorService.delete_source_chunks(project_id, source_id)

        # Audit event
        audit = AuditEvent(
            user_id=current_user.id,
            project_id=project_id,
            event_type="source_deleted",
            resource_type="source_record",
            resource_id=str(source_id),
            metadata_json={"title": record.title},
        )
        db.add(audit)
        db.delete(record)
        db.commit()
