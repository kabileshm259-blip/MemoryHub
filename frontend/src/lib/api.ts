import {
  ApiErrorResponse,
  AskQuestionRequest,
  AskQuestionResponse,
  GenerateHandoffRequest,
  GenerateHandoffResponse,
  Handoff,
  HandoffComment,
  HandoffListResponse,
  HandoffStatus,
  HandoffSummaryData,
  HealthResponse,
  IntegrationConnection,
  IntegrationSyncResponse,
  NotificationListResponse,
  Project,
  ProjectListResponse,
  ProjectMember,
  ProjectRole,
  ProjectStatus,
  SearchResponse,
  SourceRecord,
  SourceRecordListResponse,
  TokenResponse,
  User,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

const TOKEN_STORAGE_KEY = "memoryhub_auth_token";

let currentToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  unauthorizedHandler = handler;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  if (!currentToken) {
    currentToken = localStorage.getItem(TOKEN_STORAGE_KEY);
  }
  return currentToken;
}

export function setStoredToken(token: string | null) {
  currentToken = token;
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  data?: ApiErrorResponse;

  constructor(status: number, message: string, data?: ApiErrorResponse) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  requiresAuth = true
): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/$/, "")}${endpoint}`;
  const headers = new Headers(options.headers || {});

  headers.set("Accept", "application/json");
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (requiresAuth) {
    const token = getStoredToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(
      0,
      "Unable to connect to MemoryHub backend. Please verify the service is running at " +
        API_BASE_URL
    );
  }

  if (response.status === 401 && requiresAuth) {
    setStoredToken(null);
    if (unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new ApiError(401, "Your session has expired. Please log in again.");
  }

  if (response.status === 204) {
    return {} as T;
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const errData = body as ApiErrorResponse | null;
    let message = "An unexpected error occurred.";

    if (errData?.detail) {
      if (typeof errData.detail === "string") {
        message = errData.detail;
      } else if (Array.isArray(errData.detail) && errData.detail.length > 0) {
        message = errData.detail.map((e) => e.msg).join("; ");
      }
    } else if (response.status === 403) {
      message = "You do not have permission to perform this action.";
    } else if (response.status === 404) {
      message = "The requested resource was not found.";
    } else if (response.status >= 500) {
      message = "Server error. Please try again later.";
    }

    throw new ApiError(response.status, message, errData || undefined);
  }

  return body as T;
}

export const api = {
  // Health
  checkReadiness(): Promise<HealthResponse> {
    return request<HealthResponse>("/health/readiness", {}, false);
  },

  checkLiveness(): Promise<{ status: string; service: string }> {
    return request<{ status: string; service: string }>("/health", {}, false);
  },

  // Auth
  register(data: {
    email: string;
    password: string;
    display_name: string;
  }): Promise<User> {
    return request<User>(
      "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      false
    );
  },

  login(data: { email: string; password: string }): Promise<TokenResponse> {
    return request<TokenResponse>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      false
    );
  },

  getCurrentUser(): Promise<User> {
    return request<User>("/api/auth/me", { method: "GET" }, true);
  },

  // Projects
  createProject(data: {
    name: string;
    description?: string;
  }): Promise<Project> {
    return request<Project>(
      "/api/projects",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  listProjects(params?: {
    limit?: number;
    offset?: number;
  }): Promise<ProjectListResponse> {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request<ProjectListResponse>(`/api/projects${qs}`, { method: "GET" }, true);
  },

  getProject(projectId: string): Promise<Project> {
    return request<Project>(`/api/projects/${projectId}`, { method: "GET" }, true);
  },

  updateProject(
    projectId: string,
    data: {
      name?: string;
      description?: string;
      status?: ProjectStatus;
    }
  ): Promise<Project> {
    return request<Project>(
      `/api/projects/${projectId}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
      true
    );
  },

  // Project Members
  listMembers(projectId: string): Promise<ProjectMember[]> {
    return request<ProjectMember[]>(
      `/api/projects/${projectId}/members`,
      { method: "GET" },
      true
    );
  },

  addMember(
    projectId: string,
    data: { email: string; role: ProjectRole }
  ): Promise<ProjectMember> {
    return request<ProjectMember>(
      `/api/projects/${projectId}/members`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  // Handoffs
  createHandoff(
    projectId: string,
    data: { title: string; summary?: HandoffSummaryData }
  ): Promise<Handoff> {
    return request<Handoff>(
      `/api/projects/${projectId}/handoffs`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  listHandoffs(
    projectId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<HandoffListResponse> {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request<HandoffListResponse>(
      `/api/projects/${projectId}/handoffs${qs}`,
      { method: "GET" },
      true
    );
  },

  getHandoff(projectId: string, handoffId: string): Promise<Handoff> {
    return request<Handoff>(
      `/api/projects/${projectId}/handoffs/${handoffId}`,
      { method: "GET" },
      true
    );
  },

  updateHandoff(
    projectId: string,
    handoffId: string,
    data: { title?: string; summary?: HandoffSummaryData; status?: HandoffStatus }
  ): Promise<Handoff> {
    return request<Handoff>(
      `/api/projects/${projectId}/handoffs/${handoffId}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
      true
    );
  },

  transitionHandoffStatus(
    projectId: string,
    handoffId: string,
    newStatus: HandoffStatus,
    comment?: string
  ): Promise<Handoff> {
    return request<Handoff>(
      `/api/projects/${projectId}/handoffs/${handoffId}/status`,
      {
        method: "POST",
        body: JSON.stringify({ status: newStatus, comment }),
      },
      true
    );
  },

  acknowledgeHandoff(projectId: string, handoffId: string): Promise<Handoff> {
    return request<Handoff>(
      `/api/projects/${projectId}/handoffs/${handoffId}/acknowledge`,
      { method: "POST" },
      true
    );
  },

  addHandoffComment(
    projectId: string,
    handoffId: string,
    data: { content: string; comment_type?: string }
  ): Promise<HandoffComment> {
    return request<HandoffComment>(
      `/api/projects/${projectId}/handoffs/${handoffId}/comments`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  generateHandoff(
    projectId: string,
    data: GenerateHandoffRequest
  ): Promise<GenerateHandoffResponse> {
    return request<GenerateHandoffResponse>(
      `/api/projects/${projectId}/handoffs/generate`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  // Knowledge Sources & Ingestion
  ingestSource(
    projectId: string,
    data: {
      title: string;
      content: string;
      source_id?: string;
      source_type?: string;
      provider_type?: string;
      canonical_url?: string;
      access_metadata?: Record<string, unknown>;
    }
  ): Promise<SourceRecord> {
    return request<SourceRecord>(
      `/api/projects/${projectId}/sources`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  listSources(projectId: string): Promise<SourceRecordListResponse> {
    return request<SourceRecordListResponse>(
      `/api/projects/${projectId}/sources`,
      { method: "GET" },
      true
    );
  },

  deleteSource(projectId: string, sourceId: string): Promise<void> {
    return request<void>(
      `/api/projects/${projectId}/sources/${sourceId}`,
      { method: "DELETE" },
      true
    );
  },

  // Integrations
  createIntegration(
    projectId: string,
    data: {
      provider_type: string;
      display_name: string;
      provider_metadata?: Record<string, unknown>;
    }
  ): Promise<IntegrationConnection> {
    return request<IntegrationConnection>(
      `/api/projects/${projectId}/integrations`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  listIntegrations(projectId: string): Promise<IntegrationConnection[]> {
    return request<IntegrationConnection[]>(
      `/api/projects/${projectId}/integrations`,
      { method: "GET" },
      true
    );
  },

  syncIntegration(
    projectId: string,
    integrationId: string
  ): Promise<IntegrationSyncResponse> {
    return request<IntegrationSyncResponse>(
      `/api/projects/${projectId}/integrations/${integrationId}/sync`,
      { method: "POST" },
      true
    );
  },

  seedDemoScenario(projectId: string): Promise<{
    project_id: string;
    scenario: string;
    records_ingested: number;
    providers_simulated: string[];
    status: string;
    message: string;
  }> {
    return request(
      `/api/projects/${projectId}/integrations/seed-demo`,
      { method: "POST" },
      true
    );
  },

  // AI / RAG Chatbot
  askQuestion(
    projectId: string,
    data: AskQuestionRequest
  ): Promise<AskQuestionResponse> {
    return request<AskQuestionResponse>(
      `/api/projects/${projectId}/ask`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      true
    );
  },

  // Notifications
  listNotifications(limit = 50): Promise<NotificationListResponse> {
    return request<NotificationListResponse>(
      `/api/notifications?limit=${limit}`,
      { method: "GET" },
      true
    );
  },

  markNotificationRead(notificationId: string): Promise<{ success: boolean }> {
    return request<{ success: boolean }>(
      `/api/notifications/${notificationId}/read`,
      { method: "PATCH" },
      true
    );
  },

  markAllNotificationsRead(): Promise<{ marked_read_count: number }> {
    return request<{ marked_read_count: number }>(
      `/api/notifications/read-all`,
      { method: "POST" },
      true
    );
  },

  // Search
  searchGlobal(query: string, limit = 20): Promise<SearchResponse> {
    return request<SearchResponse>(
      `/api/search?q=${encodeURIComponent(query)}&limit=${limit}`,
      { method: "GET" },
      true
    );
  },

  searchProject(
    projectId: string,
    query: string,
    limit = 20
  ): Promise<SearchResponse> {
    return request<SearchResponse>(
      `/api/projects/${projectId}/search?q=${encodeURIComponent(query)}&limit=${limit}`,
      { method: "GET" },
      true
    );
  },
};
