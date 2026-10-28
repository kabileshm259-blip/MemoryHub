export type ProjectRole = "owner" | "editor" | "viewer";
export type ProjectStatus = "active" | "archived" | "suspended";
export type HandoffStatus = "draft" | "in_review" | "approved" | "acknowledged" | "completed";

export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  role?: ProjectRole;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectMember {
  id: string;
  user_id: string;
  project_id: string;
  role: ProjectRole;
  email?: string;
  display_name?: string;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  postgres?: string;
  chroma?: string;
}

export interface ApiValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorResponse {
  detail: string | ApiValidationError[];
}

// ==========================================
// Handoff Types
// ==========================================

export interface HandoffTaskItem {
  id: string;
  title: string;
  description?: string;
  status: "todo" | "in_progress" | "blocked" | "completed";
  priority: "low" | "medium" | "high" | "critical";
  deadline?: string | null;
  assignee?: string | null;
  blockers?: string | null;
  source_reference_id?: string | null;
}

export interface HandoffDependencyItem {
  id: string;
  name: string;
  type: "service" | "database" | "api" | "infrastructure" | "team" | "other";
  description?: string;
  criticality: "low" | "medium" | "high";
  contact_or_link?: string | null;
}

export interface HandoffRiskItem {
  id: string;
  category: "operational" | "technical" | "access" | "knowledge" | "timeline";
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  impact?: string;
  mitigation?: string;
  status: "identified" | "mitigated" | "accepted";
}

export interface HandoffResourceItem {
  id: string;
  title: string;
  type: "repository" | "runbook" | "dashboard" | "document" | "credentials" | "other";
  url_or_path: string;
  notes?: string;
}

export interface ReadinessBreakdown {
  task_clarity: number;
  dependencies_documented: number;
  risk_mitigation: number;
  resources_complete: number;
  successor_readiness: number;
}

export interface RecommendationItem {
  priority: "high" | "medium" | "low";
  action: string;
  reason: string;
}

export interface ReadinessScoreData {
  score: number;
  level: "critical" | "low" | "medium" | "high" | "complete";
  breakdown: ReadinessBreakdown;
  missing_items: string[];
  recommendations: RecommendationItem[];
}

export interface CitationItem {
  source_id: string;
  title: string;
  provider_type: string;
  chunk_index?: number;
  snippet: string;
  score?: number | null;
}

export interface HandoffSummaryData {
  executive_summary?: string;
  knowledge_owner_id?: string | null;
  knowledge_owner_name?: string | null;
  successor_id?: string | null;
  successor_name?: string | null;
  target_completion_date?: string | null;
  key_responsibilities?: string[];
  tasks?: HandoffTaskItem[];
  dependencies?: HandoffDependencyItem[];
  risks?: HandoffRiskItem[];
  resources?: HandoffResourceItem[];
  readiness_score?: ReadinessScoreData | null;
  citations?: CitationItem[];
}

export interface HandoffComment {
  id: string;
  handoff_id: string;
  user_id: string;
  author_name?: string | null;
  content: string;
  comment_type: "comment" | "blocker" | "approval" | "change_request";
  created_at: string;
}

export interface HandoffAcknowledgement {
  id: string;
  handoff_id: string;
  user_id: string;
  user_display_name?: string | null;
  acknowledged_at: string;
}

export interface Handoff {
  id: string;
  project_id: string;
  creator_id?: string | null;
  creator_name?: string | null;
  title: string;
  summary: HandoffSummaryData;
  status: HandoffStatus;
  created_at: string;
  updated_at: string;
  acknowledgements?: HandoffAcknowledgement[];
  comments?: HandoffComment[];
}

export interface HandoffListResponse {
  items: Handoff[];
  total: number;
  limit: number;
  offset: number;
}

// ==========================================
// Knowledge Source Types
// ==========================================

export interface SourceRecord {
  id: string;
  project_id: string;
  integration_id?: string | null;
  provider_type: "file_upload" | "jira" | "slack" | "confluence" | "manual_note";
  source_id: string;
  source_type: "document" | "ticket" | "discussion" | "runbook" | "architecture_note" | "file_upload";
  title?: string | null;
  content?: string | null;
  canonical_url?: string | null;
  source_created_at?: string | null;
  source_updated_at?: string | null;
  last_synced_at: string;
  content_hash?: string | null;
  chunk_count?: number;
}

export interface SourceRecordListResponse {
  items: SourceRecord[];
  total: number;
}

// ==========================================
// Integration Types
// ==========================================

export interface IntegrationConnection {
  id: string;
  project_id: string;
  provider_type: "jira" | "slack" | "confluence" | "github";
  display_name: string;
  status: string;
  provider_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IntegrationSyncResponse {
  integration_id: string;
  provider_type: string;
  records_synced: number;
  relationships_created: number;
  status: string;
  details: string;
}

// ==========================================
// AI / RAG Types
// ==========================================

export interface AskQuestionRequest {
  question: string;
  top_k?: number;
}

export interface AskQuestionResponse {
  question: string;
  answer: string;
  citations: CitationItem[];
  confidence: number;
  has_sufficient_evidence: boolean;
  provider_mode?: "heuristic" | "gemini" | "heuristic_fallback" | string;
}

export interface GenerateHandoffRequest {
  title?: string;
  successor_id?: string | null;
  target_completion_date?: string | null;
  focus_areas?: string[];
}

export interface GenerateHandoffResponse {
  handoff: Handoff;
  sources_analyzed_count: number;
  extracted_tasks_count: number;
  identified_risks_count: number;
  readiness_score: number;
  provider_mode?: "heuristic" | "gemini" | "heuristic_fallback" | string;
}

// ==========================================
// Notification Types
// ==========================================

export interface Notification {
  id: string;
  user_id: string;
  project_id?: string | null;
  title: string;
  message: string;
  notification_type: string;
  link?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  unread_count: number;
}

// ==========================================
// Search Types
// ==========================================

export interface SearchItem {
  id: string;
  entity_type: "project" | "handoff" | "task" | "source" | "vector_chunk";
  title: string;
  snippet: string;
  link?: string | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchItem[];
  total_matches: number;
}
