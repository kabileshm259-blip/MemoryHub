import uuid
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Plaintext password (8-72 characters)",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Public display name",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Display name cannot be empty or only whitespace")
        return cleaned


class UserLoginRequest(BaseModel):
    """Payload for email/password authentication."""

    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TokenResponse(BaseModel):
    """Bearer token authentication response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Public user profile schema excluding sensitive hashes."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime


class ProjectCreateRequest(BaseModel):
    """Payload for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Project name cannot be empty or only whitespace")
        return cleaned


class ProjectUpdateRequest(BaseModel):
    """Payload for updating project settings."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|suspended)$")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Project name cannot be empty or only whitespace")
            return cleaned
        return v


class ProjectResponse(BaseModel):
    """Project schema returned to authorized members."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    role: Optional[str] = None


class ProjectListResponse(BaseModel):
    """Paginated list of projects belonging to the user."""

    items: List[ProjectResponse]
    total: int
    limit: int
    offset: int


AllowedRole = Literal["owner", "editor", "viewer"]


class MemberAddRequest(BaseModel):
    """Payload for adding an existing user to a project."""

    email: EmailStr
    role: AllowedRole = "viewer"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ProjectMemberResponse(BaseModel):
    """Project member details returned to authorized project members."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    role: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    created_at: datetime


# ==========================================
# Handoff Schemas
# ==========================================

HandoffStatusType = Literal["draft", "in_review", "approved", "acknowledged", "completed"]


class HandoffTaskItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    status: Literal["todo", "in_progress", "blocked", "completed"] = "todo"
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    deadline: Optional[str] = None
    assignee: Optional[str] = None
    blockers: Optional[str] = None
    source_reference_id: Optional[str] = None


class HandoffDependencyItem(BaseModel):
    id: str
    name: str
    type: Literal["service", "database", "api", "infrastructure", "team", "other"] = "service"
    description: Optional[str] = ""
    criticality: Literal["low", "medium", "high"] = "medium"
    contact_or_link: Optional[str] = None


class HandoffRiskItem(BaseModel):
    id: str
    category: Literal["operational", "technical", "access", "knowledge", "timeline"] = "operational"
    title: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    impact: Optional[str] = ""
    mitigation: Optional[str] = ""
    status: Literal["identified", "mitigated", "accepted"] = "identified"


class HandoffResourceItem(BaseModel):
    id: str
    title: str
    type: Literal["repository", "runbook", "dashboard", "document", "credentials", "other"] = "document"
    url_or_path: str
    notes: Optional[str] = ""


class ReadinessBreakdown(BaseModel):
    task_clarity: int = Field(ge=0, le=25)
    dependencies_documented: int = Field(ge=0, le=20)
    risk_mitigation: int = Field(ge=0, le=20)
    resources_complete: int = Field(ge=0, le=15)
    successor_readiness: int = Field(ge=0, le=20)


class RecommendationItem(BaseModel):
    priority: Literal["high", "medium", "low"]
    action: str
    reason: str


class ReadinessScoreData(BaseModel):
    score: int = Field(ge=0, le=100)
    level: Literal["critical", "low", "medium", "high", "complete"]
    breakdown: ReadinessBreakdown
    missing_items: List[str] = Field(default_factory=list)
    recommendations: List[RecommendationItem] = Field(default_factory=list)


class CitationItem(BaseModel):
    source_id: str
    title: str
    provider_type: str
    chunk_index: int = 0
    snippet: str
    score: Optional[float] = None


class HandoffSummaryData(BaseModel):
    executive_summary: Optional[str] = ""
    knowledge_owner_id: Optional[str] = None
    knowledge_owner_name: Optional[str] = None
    successor_id: Optional[str] = None
    successor_name: Optional[str] = None
    target_completion_date: Optional[str] = None
    key_responsibilities: List[str] = Field(default_factory=list)
    tasks: List[HandoffTaskItem] = Field(default_factory=list)
    dependencies: List[HandoffDependencyItem] = Field(default_factory=list)
    risks: List[HandoffRiskItem] = Field(default_factory=list)
    resources: List[HandoffResourceItem] = Field(default_factory=list)
    readiness_score: Optional[ReadinessScoreData] = None
    citations: List[CitationItem] = Field(default_factory=list)


class HandoffCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[dict] = Field(default_factory=dict)


class HandoffUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[dict] = None
    status: Optional[HandoffStatusType] = None


class HandoffStatusUpdateRequest(BaseModel):
    status: HandoffStatusType
    comment: Optional[str] = None


class HandoffCommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    comment_type: Literal["comment", "blocker", "approval", "change_request"] = "comment"


class HandoffCommentResponse(BaseModel):
    id: uuid.UUID
    handoff_id: uuid.UUID
    user_id: uuid.UUID
    author_name: Optional[str] = None
    content: str
    comment_type: str
    created_at: datetime


class HandoffAcknowledgementResponse(BaseModel):
    id: uuid.UUID
    handoff_id: uuid.UUID
    user_id: uuid.UUID
    user_display_name: Optional[str] = None
    acknowledged_at: datetime


class HandoffResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    creator_id: Optional[uuid.UUID] = None
    creator_name: Optional[str] = None
    title: str
    summary: dict
    status: str
    created_at: datetime
    updated_at: datetime
    acknowledgements: List[HandoffAcknowledgementResponse] = Field(default_factory=list)
    comments: List[HandoffCommentResponse] = Field(default_factory=list)


class HandoffListResponse(BaseModel):
    items: List[HandoffResponse]
    total: int
    limit: int
    offset: int


# ==========================================
# Sources & Ingestion Schemas
# ==========================================

class SourceRecordCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    source_id: Optional[str] = None
    source_type: Literal["document", "ticket", "discussion", "runbook", "architecture_note", "file_upload"] = "document"
    provider_type: Literal["file_upload", "jira", "slack", "confluence", "manual_note"] = "file_upload"
    canonical_url: Optional[str] = None
    access_metadata: Optional[dict] = Field(default_factory=dict)


class SourceRecordResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    integration_id: Optional[uuid.UUID] = None
    provider_type: str
    source_id: str
    source_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    canonical_url: Optional[str] = None
    source_created_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None
    last_synced_at: datetime
    content_hash: Optional[str] = None
    chunk_count: Optional[int] = 0


class SourceRecordListResponse(BaseModel):
    items: List[SourceRecordResponse]
    total: int


# ==========================================
# Integration Schemas
# ==========================================

class IntegrationConnectionCreateRequest(BaseModel):
    provider_type: Literal["jira", "slack", "confluence", "github"]
    display_name: str = Field(..., min_length=1, max_length=255)
    provider_metadata: Optional[dict] = Field(default_factory=dict)


class IntegrationConnectionResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    provider_type: str
    display_name: str
    status: str
    provider_metadata: dict
    created_at: datetime
    updated_at: datetime


class IntegrationSyncResponse(BaseModel):
    integration_id: uuid.UUID
    provider_type: str
    records_synced: int
    relationships_created: int
    status: str
    details: str


# ==========================================
# AI / RAG Schemas
# ==========================================

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2)
    top_k: int = Field(default=4, ge=1, le=10)


class AskQuestionResponse(BaseModel):
    question: str
    answer: str
    citations: List[CitationItem]
    confidence: float
    has_sufficient_evidence: bool
    provider_mode: str = "heuristic"


class GenerateHandoffRequest(BaseModel):
    title: Optional[str] = "AI Generated Operational Handoff"
    successor_id: Optional[uuid.UUID] = None
    target_completion_date: Optional[str] = None
    focus_areas: Optional[List[str]] = Field(default_factory=list)


class GenerateHandoffResponse(BaseModel):
    handoff: HandoffResponse
    sources_analyzed_count: int
    extracted_tasks_count: int
    identified_risks_count: int
    readiness_score: int
    provider_mode: str = "heuristic"


# ==========================================
# Notification Schemas
# ==========================================

class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    title: str
    message: str
    notification_type: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    unread_count: int


# ==========================================
# Search Schemas
# ==========================================

class SearchItem(BaseModel):
    id: str
    entity_type: Literal["project", "handoff", "task", "source", "vector_chunk"]
    title: str
    snippet: str
    link: Optional[str] = None
    score: float = 1.0


class SearchResponse(BaseModel):
    query: str
    results: List[SearchItem]
    total_matches: int
