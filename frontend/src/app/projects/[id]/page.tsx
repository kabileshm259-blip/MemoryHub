"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { api, ApiError } from "@/lib/api";
import { CitationItem, Handoff, Project, ProjectMember, ProjectRole, ProjectStatus, SourceRecord } from "@/types/api";
import { RoleBadge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { AddMemberModal } from "@/components/projects/AddMemberModal";
import {
  ClockIcon,
  PlusIcon,
  ShieldIcon,
} from "@/components/ui/Icons";

function ProjectDetailsContent() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "members" | "roadmap">("overview");

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Settings edit state
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editStatus, setEditStatus] = useState<ProjectStatus>("active");
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState<string | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  // Member invite modal state
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);

  // Tab 3 state: Handoffs, Sources, and AI Chatbot
  const [activeWorkspaceSubtab, setActiveWorkspaceSubtab] = useState<"handoffs" | "sources" | "assistant">("handoffs");
  const [projectHandoffs, setProjectHandoffs] = useState<Handoff[]>([]);
  const [projectSources, setProjectSources] = useState<SourceRecord[]>([]);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);

  // AI Chatbot state
  const [chatMessages, setChatMessages] = useState<
    Array<{
      role: "user" | "ai";
      text: string;
      citations?: CitationItem[];
      hasEvidence?: boolean;
      providerMode?: string;
    }>
  >([
    {
      role: "ai",
      text: "Hello! I am your MemoryHub Knowledge Assistant. I answer questions grounded strictly in this project's verified runbooks, Jira issues, and incident postmortems. Ask me anything about system architecture, credentials, or ongoing blockers.",
    },
  ]);
  const [chatQuery, setChatQuery] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  const fetchProjectData = () => {
    if (!projectId) return;
    setIsLoading(true);
    setError(null);

    Promise.all([api.getProject(projectId), api.listMembers(projectId)])
      .then(([projData, membersData]) => {
        setProject(projData);
        setMembers(membersData);
        setEditName(projData.name);
        setEditDescription(projData.description || "");
        setEditStatus(projData.status);
        setIsLoading(false);
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setError("Project not found or you do not have permission to view it.");
          } else {
            setError(err.message);
          }
        } else {
          setError("Failed to load project details.");
        }
        setIsLoading(false);
      });
  };

  useEffect(() => {
    if (!projectId) return;
    let isCurrent = true;

    Promise.all([api.getProject(projectId), api.listMembers(projectId)])
      .then(([projData, membersData]) => {
        if (isCurrent) {
          setProject(projData);
          setMembers(membersData);
          setEditName(projData.name);
          setEditDescription(projData.description || "");
          setEditStatus(projData.status);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          if (err instanceof ApiError) {
            if (err.status === 404) {
              setError("Project not found or you do not have permission to view it.");
            } else {
              setError(err.message);
            }
          } else {
            setError("Failed to load project details.");
          }
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [projectId]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project || project.role !== "owner") return;

    setIsSavingSettings(true);
    setSettingsSuccess(null);
    setSettingsError(null);

    try {
      const updated = await api.updateProject(projectId, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
        status: editStatus,
      });
      setProject((prev) => (prev ? { ...prev, ...updated } : updated));
      setSettingsSuccess("Project settings saved successfully.");
      setTimeout(() => setSettingsSuccess(null), 4000);
    } catch (err) {
      if (err instanceof ApiError) {
        setSettingsError(err.message);
      } else {
        setSettingsError("Failed to update project settings.");
      }
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleMemberAdded = (newMember: ProjectMember) => {
    setMembers((prev) => [...prev, newMember]);
  };

  const isOwner = project?.role === "owner";

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Link href="/projects" className="hover:text-indigo-600 transition-colors">
            Projects
          </Link>
          <span>/</span>
          <span className="text-slate-800 font-medium truncate max-w-xs">
            {project?.name || "Project Details"}
          </span>
        </div>

        {error && (
          <div className="space-y-4">
            <Alert variant="error" title="Access Denied or Not Found">
              {error}
            </Alert>
            <div className="flex gap-3">
              <Button variant="secondary" size="sm" onClick={() => router.push("/projects")}>
                &larr; Back to Projects
              </Button>
              <Button variant="outline" size="sm" onClick={fetchProjectData}>
                Retry
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="space-y-6 animate-pulse">
            <div className="h-10 bg-slate-200 rounded w-1/3" />
            <div className="h-4 bg-slate-200 rounded w-1/4" />
            <div className="h-64 bg-white rounded-xl border border-slate-200" />
          </div>
        ) : project ? (
          <>
            {/* Project Header Banner */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 min-w-0">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight truncate">
                      {project.name}
                    </h1>
                    <StatusBadge status={project.status} />
                    {project.role && <RoleBadge role={project.role} />}
                  </div>
                  <p className="text-xs text-slate-500 flex items-center gap-1.5">
                    <ClockIcon className="w-3.5 h-3.5" />
                    Created on {new Date(project.created_at).toLocaleDateString(undefined, {
                      dateStyle: "medium",
                    })}
                  </p>
                </div>

                <div className="flex items-center gap-2.5">
                  {isOwner && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setIsAddMemberModalOpen(true)}
                    >
                      <PlusIcon className="w-4 h-4" />
                      Add Member
                    </Button>
                  )}
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-slate-100 mt-6 -mb-2 gap-6 text-sm font-medium">
                <button
                  onClick={() => setActiveTab("overview")}
                  className={`pb-3 border-b-2 transition-colors ${
                    activeTab === "overview"
                      ? "border-indigo-600 text-indigo-600 font-semibold"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Settings & Overview
                </button>
                <button
                  onClick={() => setActiveTab("members")}
                  className={`pb-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                    activeTab === "members"
                      ? "border-indigo-600 text-indigo-600 font-semibold"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <span>Team Members</span>
                  <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-slate-100 text-slate-600">
                    {members.length}
                  </span>
                </button>
                <button
                  onClick={() => {
                    setActiveTab("roadmap");
                    if (projectId) {
                      setIsLoadingWorkspace(true);
                      Promise.all([
                        api.listHandoffs(projectId, { limit: 20 }),
                        api.listSources(projectId),
                      ]).then(([hData, sData]) => {
                        setProjectHandoffs(hData.items);
                        setProjectSources(sData.items);
                        setIsLoadingWorkspace(false);
                      }).catch(() => setIsLoadingWorkspace(false));
                    }
                  }}
                  className={`pb-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                    activeTab === "roadmap"
                      ? "border-indigo-600 text-indigo-600 font-semibold"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <span>Handoffs, Sources &amp; AI</span>
                  <span className="px-1.5 py-0.2 rounded text-[10px] bg-indigo-50 text-indigo-600 font-bold">
                    Active
                  </span>
                </button>
              </div>
            </div>

            {/* Tab 1: Overview & Settings */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
                  <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
                    <div>
                      <h2 className="text-base font-bold text-slate-900">
                        Project Configuration
                      </h2>
                      <p className="text-xs text-slate-500">
                        {isOwner
                          ? "Update project attributes and lifecycle status."
                          : "Project settings are read-only for editors and viewers."}
                      </p>
                    </div>
                    {!isOwner && (
                      <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md border border-slate-200">
                        Read-Only View
                      </span>
                    )}
                  </div>

                  {settingsSuccess && (
                    <Alert variant="success">{settingsSuccess}</Alert>
                  )}
                  {settingsError && (
                    <Alert variant="error">{settingsError}</Alert>
                  )}

                  <form onSubmit={handleSaveSettings} className="space-y-4">
                    <Input
                      label="Project Name *"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      disabled={!isOwner || isSavingSettings}
                      required
                    />

                    <Textarea
                      label="Project Description"
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      disabled={!isOwner || isSavingSettings}
                      rows={4}
                      placeholder="Outline project objectives, repository locations, or key handoff goals..."
                    />

                    <div className="w-full flex flex-col gap-1.5">
                      <label
                        htmlFor="project-status-select"
                        className="text-xs font-semibold text-slate-700 tracking-wide uppercase"
                      >
                        Lifecycle Status
                      </label>
                      <select
                        id="project-status-select"
                        value={editStatus}
                        onChange={(e) => setEditStatus(e.target.value as ProjectStatus)}
                        disabled={!isOwner || isSavingSettings}
                        className="w-full px-3.5 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600 disabled:bg-slate-50 disabled:text-slate-400"
                      >
                        <option value="active">Active</option>
                        <option value="archived">Archived</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </div>

                    {isOwner ? (
                      <div className="pt-2">
                        <Button
                          type="submit"
                          variant="primary"
                          size="md"
                          isLoading={isSavingSettings}
                        >
                          Save Changes
                        </Button>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic">
                        Only users with the Owner role can modify project settings.
                      </p>
                    )}
                  </form>
                </div>

                {/* Sidebar Info Card */}
                <div className="space-y-6">
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Access & Governance
                    </h3>
                    <div className="space-y-3 text-xs">
                      <div className="flex items-center justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-500">Your Project Role</span>
                        {project.role && <RoleBadge role={project.role} />}
                      </div>
                      <div className="flex items-center justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-500">Members Count</span>
                        <span className="font-semibold text-slate-800">{members.length}</span>
                      </div>
                      <div className="flex items-center justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-500">Project UUID</span>
                        <span className="font-mono text-[11px] text-slate-500 truncate max-w-[150px]" title={project.id}>
                          {project.id}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-indigo-50/60 rounded-xl border border-indigo-100 text-xs text-indigo-900 leading-relaxed">
                    <div className="flex items-center gap-1.5 font-bold mb-1 text-indigo-950">
                      <ShieldIcon className="w-4 h-4 text-indigo-600" />
                      Role Enforcement
                    </div>
                    Permissions are strictly enforced on the server. Editors and viewers cannot modify project attributes or invite members.
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: Team Members */}
            {activeTab === "members" && (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
                <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      Project Members ({members.length})
                    </h2>
                    <p className="text-xs text-slate-500">
                      Collaborators with authorized access to this project workspace.
                    </p>
                  </div>
                  {isOwner ? (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setIsAddMemberModalOpen(true)}
                    >
                      <PlusIcon className="w-4 h-4" />
                      Add Member
                    </Button>
                  ) : (
                    <span className="text-xs text-slate-400 italic">
                      Only project owners can invite members
                    </span>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-700">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                      <tr>
                        <th className="px-5 py-3">Member</th>
                        <th className="px-5 py-3">Role</th>
                        <th className="px-5 py-3">Joined Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {members.map((m) => (
                        <tr key={m.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="px-5 py-3.5">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs border border-slate-200">
                                {(m.display_name || m.email || "U")
                                  .slice(0, 2)
                                  .toUpperCase()}
                              </div>
                              <div>
                                <p className="font-semibold text-slate-900">
                                  {m.display_name || "User"}
                                </p>
                                <p className="text-slate-500 text-[11px] font-mono">
                                  {m.email || m.user_id}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-5 py-3.5">
                            <RoleBadge role={m.role as ProjectRole} />
                          </td>
                          <td className="px-5 py-3.5 text-slate-500">
                            {new Date(m.created_at).toLocaleDateString(undefined, {
                              dateStyle: "medium",
                            })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab 3: Handoffs, Sources & AI Assistant Workspace */}
            {activeTab === "roadmap" && (
              <div className="space-y-6">
                {/* Subtab Navigation */}
                <div className="flex border-b border-slate-200 gap-6 text-xs font-semibold">
                  {[
                    { key: "handoffs", label: `Operational Handoffs (${projectHandoffs.length})` },
                    { key: "sources", label: `Knowledge Sources (${projectSources.length})` },
                    { key: "assistant", label: "AI Knowledge Chatbot (RAG)" },
                  ].map((sub) => (
                    <button
                      key={sub.key}
                      onClick={() => setActiveWorkspaceSubtab(sub.key as "handoffs" | "sources" | "assistant")}
                      className={`pb-2.5 border-b-2 transition-colors ${
                        activeWorkspaceSubtab === sub.key
                          ? "border-indigo-600 text-indigo-600"
                          : "border-transparent text-slate-500 hover:text-slate-800"
                      }`}
                    >
                      {sub.label}
                    </button>
                  ))}
                </div>

                {/* Subtab 1: Handoffs */}
                {activeWorkspaceSubtab === "handoffs" && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-500">
                        Operational handover briefs drafted for this project workspace.
                      </p>
                      <Link href="/handoffs">
                        <Button variant="outline" size="sm">
                          Open Handoff Hub &rarr;
                        </Button>
                      </Link>
                    </div>

                    {isLoadingWorkspace ? (
                      <div className="p-6 bg-white rounded-xl border border-slate-200 text-center text-xs text-slate-400">
                        Loading project handoffs...
                      </div>
                    ) : projectHandoffs.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {projectHandoffs.map((h) => (
                          <div key={h.id} className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-900 text-sm">{h.title}</span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-indigo-50 text-indigo-700">
                                {h.status}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 line-clamp-2">
                              {h.summary?.executive_summary || "Operational handover brief."}
                            </p>
                            <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px] text-slate-400">
                              <span>Readiness: <strong className="text-indigo-600">{h.summary?.readiness_score?.score || 40}%</strong></span>
                              <span>Tasks: {h.summary?.tasks?.length || 0}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 bg-white rounded-xl border border-slate-200 text-center space-y-3">
                        <p className="text-xs text-slate-500">No handoffs drafted yet for this project.</p>
                        <Link href="/handoffs">
                          <Button variant="primary" size="sm">Create First Handoff</Button>
                        </Link>
                      </div>
                    )}
                  </div>
                )}

                {/* Subtab 2: Sources */}
                {activeWorkspaceSubtab === "sources" && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-500">
                        Indexed engineering documents, tickets, and incident discussions in ChromaDB.
                      </p>
                      <Link href="/sources">
                        <Button variant="outline" size="sm">
                          Manage All Sources &rarr;
                        </Button>
                      </Link>
                    </div>

                    {projectSources.length > 0 ? (
                      <div className="space-y-2">
                        {projectSources.map((s) => (
                          <div key={s.id} className="p-3 bg-white rounded-xl border border-slate-200 flex items-center justify-between text-xs">
                            <div className="space-y-0.5 min-w-0 pr-4">
                              <strong className="text-slate-900 block truncate">{s.title || s.source_id}</strong>
                              <p className="text-[11px] text-slate-500 truncate">{s.content}</p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-semibold uppercase">
                                {s.provider_type}
                              </span>
                              <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-bold text-[10px]">
                                {s.chunk_count || 1} Chunks
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 bg-white rounded-xl border border-slate-200 text-center space-y-3">
                        <p className="text-xs text-slate-500">No knowledge sources indexed yet.</p>
                        <Link href="/sources">
                          <Button variant="primary" size="sm">Ingest or Seed Demo Sources</Button>
                        </Link>
                      </div>
                    )}
                  </div>
                )}

                {/* Subtab 3: AI Knowledge Assistant (RAG Chatbot) */}
                {activeWorkspaceSubtab === "assistant" && (
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col h-[520px]">
                    <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm">
                          Evidence-Grounded AI Knowledge Chatbot
                        </h4>
                        <p className="text-[11px] text-slate-400">
                          Retrieval-Augmented Generation (RAG) with source verification and citations.
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[11px] font-bold border border-emerald-200">
                        ChromaDB RAG Active
                      </span>
                    </div>

                    {/* Messages scroll area */}
                    <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
                      {chatMessages.map((msg, i) => (
                        <div
                          key={i}
                          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`max-w-[85%] rounded-2xl p-4 space-y-2 leading-relaxed ${
                              msg.role === "user"
                                ? "bg-indigo-600 text-white rounded-tr-none"
                                : "bg-slate-50 text-slate-800 border border-slate-200 rounded-tl-none"
                            }`}
                          >
                            {msg.role === "ai" && (
                              <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-slate-200/70 text-[10px]">
                                <span className="font-semibold text-slate-500">MemoryHub Assistant</span>
                                {msg.providerMode === "gemini" ? (
                                  <span className="px-1.5 py-0.5 rounded font-bold bg-indigo-100 text-indigo-700 border border-indigo-200">
                                    Gemini 2.5 Flash
                                  </span>
                                ) : msg.providerMode === "heuristic_fallback" ? (
                                  <span
                                    className="px-1.5 py-0.5 rounded font-bold bg-amber-100 text-amber-800 border border-amber-200"
                                    title="Gemini call timed out or failed; safely fell back to deterministic heuristic"
                                  >
                                    Fallback (Heuristic)
                                  </span>
                                ) : (
                                  <span className="px-1.5 py-0.5 rounded font-medium bg-slate-100 text-slate-600 border border-slate-200">
                                    Heuristic Mode
                                  </span>
                                )}
                              </div>
                            )}

                            <p className="whitespace-pre-line text-xs">{msg.text}</p>

                            {/* Citations block */}
                            {msg.citations && msg.citations.length > 0 && (
                              <div className="pt-2 border-t border-slate-200 text-[11px] space-y-1.5 text-slate-600">
                                <strong className="block font-bold text-indigo-700">Verified Citations:</strong>
                                <div className="space-y-1">
                                  {msg.citations.map((c, ci) => (
                                    <div key={ci} className="p-2 bg-white rounded border border-slate-200">
                                      <div className="flex justify-between font-semibold text-slate-800">
                                        <span>[{ci + 1}] {c.title} ({c.provider_type})</span>
                                        {c.score && <span>Relevance: {Math.round(c.score * 100)}%</span>}
                                      </div>
                                      <p className="text-[10px] text-slate-500 mt-0.5 italic">&quot;{c.snippet}&quot;</p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}

                      {isAsking && (
                        <div className="flex justify-start">
                          <div className="bg-slate-50 text-slate-500 border border-slate-200 rounded-2xl p-3 text-xs animate-pulse">
                            Searching project vector memory and synthesizing answer...
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Chat input box */}
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        if (!chatQuery.trim() || isAsking) return;
                        const userQ = chatQuery.trim();
                        setChatMessages((prev) => [...prev, { role: "user", text: userQ }]);
                        setChatQuery("");
                        setIsAsking(true);

                        try {
                          const res = await api.askQuestion(projectId, { question: userQ, top_k: 3 });
                          setChatMessages((prev) => [
                            ...prev,
                            {
                              role: "ai",
                              text: res.answer,
                              citations: res.citations,
                              hasEvidence: res.has_sufficient_evidence,
                              providerMode: res.provider_mode || "heuristic",
                            },
                          ]);
                        } catch (err: unknown) {
                          const message = err instanceof Error ? err.message : String(err);
                          setChatMessages((prev) => [
                            ...prev,
                            {
                              role: "ai",
                              text: `Sorry, an error occurred while searching project memory: ${message}`,
                            },
                          ]);
                        } finally {
                          setIsAsking(false);
                        }
                      }}
                      className="p-3 border-t border-slate-200 flex gap-2"
                    >
                      <input
                        type="text"
                        placeholder="Ask a technical or operational question (e.g. 'What is the max client connections for PgBouncer?')..."
                        value={chatQuery}
                        onChange={(e) => setChatQuery(e.target.value)}
                        disabled={isAsking}
                        className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600"
                      />
                      <Button variant="primary" size="sm" type="submit" disabled={isAsking || !chatQuery.trim()}>
                        Ask AI
                      </Button>
                    </form>
                  </div>
                )}
              </div>
            )}
          </>
        ) : null}
      </div>

      {project && isOwner && (
        <AddMemberModal
          projectId={projectId}
          isOpen={isAddMemberModalOpen}
          onClose={() => setIsAddMemberModalOpen(false)}
          onSuccess={handleMemberAdded}
        />
      )}
    </ProtectedRoute>
  );
}

export default function ProjectDetailsPage() {
  return (
    <React.Suspense
      fallback={
        <ProtectedRoute>
          <div className="p-8 space-y-4 animate-pulse">
            <div className="h-8 bg-slate-200 rounded w-1/3" />
            <div className="h-4 bg-slate-200 rounded w-1/4" />
          </div>
        </ProtectedRoute>
      }
    >
      <ProjectDetailsContent />
    </React.Suspense>
  );
}
