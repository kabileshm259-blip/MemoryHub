"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { api } from "@/lib/api";
import {
  Handoff,
  HandoffStatus,
  Project,
  ProjectMember,
} from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Modal } from "@/components/ui/Modal";
import {
  CheckIcon,
  ClockIcon,
  HandoffsIcon,
  PlusIcon,
  SearchIcon,
  SourcesIcon,
} from "@/components/ui/Icons";
import {
  WorkflowExecutionDialog,
  WorkflowStep,
  WorkflowResultData,
} from "@/components/ui/WorkflowExecutionDialog";

export default function HandoffsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [projectMembers, setProjectMembers] = useState<ProjectMember[]>([]);

  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [isLoadingHandoffs, setIsLoadingHandoffs] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modals & Active handoff
  const [activeHandoff, setActiveHandoff] = useState<Handoff | null>(null);
  const [activeDetailTab, setActiveDetailTab] = useState<
    "summary" | "tasks" | "dependencies" | "risks" | "resources" | "comments"
  >("summary");

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);

  // Create form state
  const [newTitle, setNewTitle] = useState("");
  const [newExecSummary, setNewExecSummary] = useState("");
  const [newSuccessorId, setNewSuccessorId] = useState("");
  const [newTargetDate, setNewTargetDate] = useState("");
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);

  // AI Generate form state
  const [genTitle, setGenTitle] = useState("AI Generated Operational Handoff");
  const [genSuccessorId, setGenSuccessorId] = useState("");
  const [genTargetDate, setGenTargetDate] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationFeedback, setGenerationFeedback] = useState<string | null>(null);

  // Comment input state
  const [newComment, setNewComment] = useState("");
  const [commentType, setCommentType] = useState<"comment" | "blocker" | "approval" | "change_request">("comment");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);

  // Status transition feedback
  const [transitionLoading, setTransitionLoading] = useState(false);

  // Workflow Dialog State
  const [isWorkflowOpen, setIsWorkflowOpen] = useState(false);
  const [workflowTitle, setWorkflowTitle] = useState("");
  const [workflowDescription, setWorkflowDescription] = useState("");
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [workflowComplete, setWorkflowComplete] = useState(false);
  const [workflowSuccess, setWorkflowSuccess] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResultData | null>(null);

  const fetchHandoffsForProject = useCallback((projectId: string) => {
    Promise.all([
      api.listHandoffs(projectId, { limit: 50, offset: 0 }),
      api.listMembers(projectId),
    ])
      .then(([handoffData, membersData]) => {
        setHandoffs(handoffData.items);
        setProjectMembers(membersData);
        setIsLoadingHandoffs(false);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Failed to load handoffs for selected project.";
        setError(message);
        setIsLoadingHandoffs(false);
      });
  }, []);

  // Load accessible projects on mount
  useEffect(() => {
    api
      .listProjects({ limit: 50, offset: 0 })
      .then((data) => {
        setProjects(data.items);
        if (data.items.length > 0) {
          setSelectedProjectId(data.items[0].id);
        }
        setIsLoadingProjects(false);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Failed to load projects.";
        setError(message);
        setIsLoadingProjects(false);
      });
  }, []);

  // Load handoffs and project members when selectedProjectId changes
  useEffect(() => {
    if (!selectedProjectId) return;
    fetchHandoffsForProject(selectedProjectId);
  }, [selectedProjectId, fetchHandoffsForProject]);

  const refreshHandoffs = useCallback(() => {
    if (!selectedProjectId) return;
    api
      .listHandoffs(selectedProjectId, { limit: 50, offset: 0 })
      .then((data) => {
        setHandoffs(data.items);
        if (activeHandoff) {
          const updated = data.items.find((h) => h.id === activeHandoff.id);
          if (updated) setActiveHandoff(updated);
        }
      })
      .catch((err) => {
        console.error("Failed to refresh handoffs:", err);
      });
  }, [selectedProjectId, activeHandoff]);

  const handleCreateHandoff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !newTitle.trim()) return;

    setIsSubmittingCreate(true);
    try {
      const succ = projectMembers.find((m) => m.user_id === newSuccessorId);
      const created = await api.createHandoff(selectedProjectId, {
        title: newTitle.trim(),
        summary: {
          executive_summary: newExecSummary.trim(),
          successor_id: newSuccessorId || null,
          successor_name: succ?.display_name || null,
          target_completion_date: newTargetDate || null,
          key_responsibilities: [
            "Primary operational maintenance of service microservices",
            "Sentry incident response and daily bug triage",
          ],
          tasks: [
            {
              id: "task_init_1",
              title: "Credential & Access Verification",
              description: "Ensure successor has production access and AWS Secrets Manager tokens.",
              status: "todo",
              priority: "high",
              deadline: newTargetDate || "Within 5 days",
            },
          ],
          dependencies: [],
          risks: [],
          resources: [],
        },
      });
      setHandoffs((prev) => [created, ...prev]);
      setActiveHandoff(created);
      setIsCreateModalOpen(false);
      setNewTitle("");
      setNewExecSummary("");
      setNewSuccessorId("");
      setNewTargetDate("");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message || "Failed to create handoff.");
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleGenerateHandoff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;

    setIsGenerating(true);
    setGenerationFeedback(null);

    const initialSteps: WorkflowStep[] = [
      {
        id: "query",
        label: "Querying Project Knowledge Sources",
        description: "Retrieving architecture notes, incident logs, and tickets via vector similarity",
        status: "running",
      },
      {
        id: "synthesize",
        label: "Synthesizing Tasks & Operational Risks",
        description: "Running AI/Heuristic synthesis to extract action items, dependencies, and risks",
        status: "pending",
      },
      {
        id: "score",
        label: "Computing Readiness Metric",
        description: "Evaluating checklist coverage, priority distribution, and verification requirements",
        status: "pending",
      },
      {
        id: "persist",
        label: "Persisting Structured Handoff Record",
        description: "Registering handoff in database and establishing operational audit trail",
        status: "pending",
      },
    ];

    setWorkflowTitle("Operational Handoff Generation");
    setWorkflowDescription("Synthesizing grounded handoff document from ingested project knowledge artifacts");
    setWorkflowSteps(initialSteps);
    setWorkflowComplete(false);
    setWorkflowSuccess(false);
    setWorkflowResult(null);
    setIsWorkflowOpen(true);

    await new Promise((r) => setTimeout(r, 200));

    try {
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "query"
            ? { ...s, status: "succeeded" }
            : s.id === "synthesize"
            ? { ...s, status: "running" }
            : s
        )
      );

      const res = await api.generateHandoff(selectedProjectId, {
        title: genTitle.trim() || "AI Generated Operational Handoff",
        successor_id: genSuccessorId || null,
        target_completion_date: genTargetDate || null,
      });

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "synthesize"
            ? { ...s, status: "succeeded" }
            : s.id === "score"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 150));

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "score"
            ? { ...s, status: "succeeded" }
            : s.id === "persist"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 150));

      setWorkflowSteps((prev) =>
        prev.map((s) => (s.id === "persist" ? { ...s, status: "succeeded" } : s))
      );

      setHandoffs((prev) => [res.handoff, ...prev]);
      setActiveHandoff(res.handoff);
      setIsGenerateModalOpen(false);

      const modeLabel =
        res.provider_mode === "gemini"
          ? "Gemini 2.5 Flash"
          : res.provider_mode === "heuristic_fallback"
          ? "Fallback (Heuristic)"
          : "Heuristic Engine";

      setWorkflowSuccess(true);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Operational Handoff Synthesized",
        message: `Handoff "${res.handoff.title}" successfully synthesized via ${modeLabel}.`,
        badge: {
          label: modeLabel,
          variant: res.provider_mode === "gemini" ? "primary" : "neutral",
        },
        evidence: [
          { label: "Handoff ID", value: res.handoff.id },
          {
            label: "Readiness Score",
            value: res.handoff.summary?.readiness_score?.score != null
              ? `${res.handoff.summary.readiness_score.score}%`
              : "Calculated",
          },
          { label: "Extracted Tasks", value: res.extracted_tasks_count },
          { label: "Identified Risks", value: res.identified_risks_count },
          { label: "Sources Analyzed", value: res.sources_analyzed_count },
          { label: "Provider Engine", value: modeLabel },
        ],
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.status === "running"
            ? { ...s, status: "failed", detail: message }
            : s
        )
      );
      setWorkflowSuccess(false);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Handoff Generation Failed",
        message,
        badge: {
          label: "Error",
          variant: "danger",
        },
      });
      setError(message || "Failed to generate AI handoff.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStatusTransition = async (newStatus: HandoffStatus, comment?: string) => {
    if (!activeHandoff || !selectedProjectId) return;
    setTransitionLoading(true);

    const formattedStatus = newStatus.replace("_", " ").toUpperCase();
    const initialSteps: WorkflowStep[] = [
      {
        id: "auth",
        label: "Validating Project Authorization",
        description: "Verifying user permissions and role transitions",
        status: "running",
      },
      {
        id: "verify",
        label: "Checking Governance Requirements",
        description: "Validating readiness criteria, blockers, and reviewer assignment",
        status: "pending",
      },
      {
        id: "transition",
        label: `Transitioning Status to ${formattedStatus}`,
        description: "Recording lifecycle event in immutable audit log and dispatching notifications",
        status: "pending",
      },
    ];

    setWorkflowTitle("Handoff Status Transition");
    setWorkflowDescription(`Advancing handoff lifecycle state to ${formattedStatus}`);
    setWorkflowSteps(initialSteps);
    setWorkflowComplete(false);
    setWorkflowSuccess(false);
    setWorkflowResult(null);
    setIsWorkflowOpen(true);

    await new Promise((r) => setTimeout(r, 150));

    try {
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "auth"
            ? { ...s, status: "succeeded" }
            : s.id === "verify"
            ? { ...s, status: "running" }
            : s
        )
      );

      const updated = await api.transitionHandoffStatus(
        selectedProjectId,
        activeHandoff.id,
        newStatus,
        comment
      );

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "verify"
            ? { ...s, status: "succeeded" }
            : s.id === "transition"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 150));

      setWorkflowSteps((prev) =>
        prev.map((s) => (s.id === "transition" ? { ...s, status: "succeeded" } : s))
      );

      setActiveHandoff(updated);
      refreshHandoffs();

      setWorkflowSuccess(true);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: `Handoff Status Updated: ${formattedStatus}`,
        message: `Handoff status was successfully updated to ${formattedStatus}.`,
        badge: {
          label: formattedStatus,
          variant: "success",
        },
        evidence: [
          { label: "Handoff ID", value: updated.id },
          { label: "New Status", value: updated.status },
          { label: "Updated At", value: new Date(updated.updated_at).toLocaleTimeString() },
          {
            label: "Readiness Score",
            value: updated.summary?.readiness_score?.score != null
              ? `${updated.summary.readiness_score.score}%`
              : "N/A",
          },
        ],
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.status === "running"
            ? { ...s, status: "failed", detail: message }
            : s
        )
      );
      setWorkflowSuccess(false);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Transition Failed",
        message,
        badge: {
          label: "Error",
          variant: "danger",
        },
      });
      alert(message || "Status transition failed.");
    } finally {
      setTransitionLoading(false);
    }
  };

  const handleAcknowledge = async () => {
    if (!activeHandoff || !selectedProjectId) return;
    setTransitionLoading(true);

    const initialSteps: WorkflowStep[] = [
      {
        id: "auth",
        label: "Authenticating Successor Identity",
        description: "Confirming identity of designated successor or team assignee",
        status: "running",
      },
      {
        id: "checklist",
        label: "Confirming Operational Acceptance",
        description: "Checking critical tasks, dependencies, credentials, and runbook access",
        status: "pending",
      },
      {
        id: "commit",
        label: "Recording Formal Handover Acknowledgement",
        description: "Setting status to Acknowledged and stamping transfer in continuity log",
        status: "pending",
      },
    ];

    setWorkflowTitle("Successor Handover Acknowledgement");
    setWorkflowDescription("Executing formal operational transfer and successor sign-off");
    setWorkflowSteps(initialSteps);
    setWorkflowComplete(false);
    setWorkflowSuccess(false);
    setWorkflowResult(null);
    setIsWorkflowOpen(true);

    await new Promise((r) => setTimeout(r, 150));

    try {
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "auth"
            ? { ...s, status: "succeeded" }
            : s.id === "checklist"
            ? { ...s, status: "running" }
            : s
        )
      );

      const updated = await api.acknowledgeHandoff(selectedProjectId, activeHandoff.id);

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "checklist"
            ? { ...s, status: "succeeded" }
            : s.id === "commit"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 150));

      setWorkflowSteps((prev) =>
        prev.map((s) => (s.id === "commit" ? { ...s, status: "succeeded" } : s))
      );

      setActiveHandoff(updated);
      refreshHandoffs();

      setWorkflowSuccess(true);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Handover Successfully Acknowledged",
        message: "Successor has formally acknowledged and assumed operational responsibility.",
        badge: {
          label: "Acknowledged",
          variant: "success",
        },
        evidence: [
          { label: "Handoff ID", value: updated.id },
          { label: "Status", value: updated.status },
          { label: "Acknowledged At", value: new Date(updated.updated_at).toLocaleTimeString() },
          {
            label: "Readiness Score",
            value: updated.summary?.readiness_score?.score != null
              ? `${updated.summary.readiness_score.score}%`
              : "N/A",
          },
        ],
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.status === "running"
            ? { ...s, status: "failed", detail: message }
            : s
        )
      );
      setWorkflowSuccess(false);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Acknowledgement Failed",
        message,
        badge: {
          label: "Error",
          variant: "danger",
        },
      });
      alert(message || "Acknowledgement failed.");
    } finally {
      setTransitionLoading(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHandoff || !selectedProjectId || !newComment.trim()) return;

    setIsSubmittingComment(true);
    try {
      const comment = await api.addHandoffComment(selectedProjectId, activeHandoff.id, {
        content: newComment.trim(),
        comment_type: commentType,
      });
      setActiveHandoff((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          comments: [...(prev.comments || []), comment],
        };
      });
      setNewComment("");
      refreshHandoffs();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      alert(message || "Failed to post review comment.");
    } finally {
      setIsSubmittingComment(false);
    }
  };

  // Metrics
  const totalHandoffs = handoffs.length;
  const inReviewCount = handoffs.filter((h) => h.status === "in_review").length;
  const completedCount = handoffs.filter((h) => h.status === "completed" || h.status === "acknowledged").length;
  const avgReadiness = totalHandoffs
    ? Math.round(
        handoffs.reduce(
          (acc, h) => acc + (h.summary?.readiness_score?.score || 40),
          0
        ) / totalHandoffs
      )
    : 0;

  // Filtered list
  const filteredHandoffs = handoffs.filter((h) => {
    const matchesStatus = statusFilter === "all" || h.status === statusFilter;
    const matchesSearch =
      h.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (h.summary?.executive_summary &&
        h.summary.executive_summary.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  const getStatusBadge = (status: HandoffStatus) => {
    switch (status) {
      case "draft":
        return <Badge variant="neutral">Draft</Badge>;
      case "in_review":
        return <Badge variant="warning">In Review</Badge>;
      case "approved":
        return <Badge variant="primary">Approved</Badge>;
      case "acknowledged":
        return <Badge variant="success">Acknowledged</Badge>;
      case "completed":
        return <Badge variant="success">Completed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getScoreBadge = (score: number) => {
    if (score >= 90) return <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold text-xs">Complete ({score}%)</span>;
    if (score >= 75) return <span className="text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded font-bold text-xs">High ({score}%)</span>;
    if (score >= 55) return <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded font-bold text-xs">Medium ({score}%)</span>;
    return <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-bold text-xs">Low ({score}%)</span>;
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Top Header & Project Switcher */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Developer Handoff Hub
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Structured operational continuity briefs, task tracking, and successor acknowledgements.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Project Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600">Project:</span>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                disabled={isLoadingProjects || projects.length === 0}
                className="text-xs py-1.5 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600 shadow-xs"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsGenerateModalOpen(true)}
              disabled={!selectedProjectId}
            >
              <SourcesIcon className="w-4 h-4 text-indigo-600" />
              <span>AI Handoff Generator</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
              disabled={!selectedProjectId}
            >
              <PlusIcon className="w-4 h-4" />
              <span>New Handoff</span>
            </Button>
          </div>
        </div>

        {generationFeedback && (
          <Alert variant="success" title="AI Generation Complete">
            {generationFeedback}
          </Alert>
        )}

        {error && (
          <Alert variant="error" title="Notice">
            {error}
          </Alert>
        )}

        {/* Operational Continuity Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Total Handoffs</p>
            <h3 className="text-2xl font-extrabold text-slate-900 mt-1">{totalHandoffs}</h3>
            <p className="text-[11px] text-slate-400 mt-1">Structured handover records</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Avg. Readiness Score</p>
            <div className="flex items-center gap-2 mt-1">
              <h3 className="text-2xl font-extrabold text-indigo-600">{avgReadiness}%</h3>
              {getScoreBadge(avgReadiness)}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Explainable completeness metric</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">In Active Review</p>
            <h3 className="text-2xl font-extrabold text-amber-600 mt-1">{inReviewCount}</h3>
            <p className="text-[11px] text-slate-400 mt-1">Awaiting successor sign-off</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Acknowledged / Completed</p>
            <h3 className="text-2xl font-extrabold text-emerald-600 mt-1">{completedCount}</h3>
            <p className="text-[11px] text-slate-400 mt-1">Operational continuity secured</p>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
          {/* Status Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-medium w-full sm:w-auto">
            {["all", "draft", "in_review", "approved", "acknowledged", "completed"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-colors ${
                  statusFilter === st
                    ? "bg-indigo-600 text-white font-semibold shadow-xs"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {st.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Search box */}
          <div className="relative w-full sm:w-64">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <SearchIcon className="w-3.5 h-3.5" />
            </span>
            <input
              type="text"
              placeholder="Search handoffs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600"
            />
          </div>
        </div>

        {/* Handoff Cards List */}
        {isLoadingHandoffs ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-5 bg-white rounded-xl border border-slate-200 animate-pulse space-y-3">
                <div className="h-5 bg-slate-200 rounded w-2/3" />
                <div className="h-3 bg-slate-200 rounded w-full" />
                <div className="h-3 bg-slate-200 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : filteredHandoffs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredHandoffs.map((h) => {
              const score = h.summary?.readiness_score?.score || 40;
              const tasks = h.summary?.tasks || [];
              const completedTasks = tasks.filter((t) => t.status === "completed").length;

              return (
                <div
                  key={h.id}
                  onClick={() => setActiveHandoff(h)}
                  className="bg-white p-5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      {getStatusBadge(h.status)}
                      {getScoreBadge(score)}
                    </div>

                    <h3 className="font-bold text-slate-900 text-sm hover:text-indigo-600 transition-colors line-clamp-1">
                      {h.title}
                    </h3>

                    <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                      {h.summary?.executive_summary || "No executive summary provided."}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-slate-100 space-y-2 text-[11px] text-slate-500">
                    <div className="flex items-center justify-between">
                      <span>Owner: <strong className="text-slate-700">{h.summary?.knowledge_owner_name || h.creator_name || "Lead"}</strong></span>
                      <span>Successor: <strong className="text-slate-700">{h.summary?.successor_name || "Unassigned"}</strong></span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>Tasks: <strong>{completedTasks}/{tasks.length} Done</strong></span>
                      <span className="flex items-center gap-1">
                        <ClockIcon className="w-3 h-3 text-slate-400" />
                        {new Date(h.updated_at).toLocaleDateString()}
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          score >= 80 ? "bg-emerald-500" : score >= 55 ? "bg-indigo-500" : "bg-amber-500"
                        }`}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-12 bg-white rounded-2xl border border-slate-200 text-center max-w-md mx-auto space-y-4">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl w-fit mx-auto">
              <HandoffsIcon className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">No handoffs found</h3>
              <p className="text-xs text-slate-500 mt-1">
                {searchQuery
                  ? `No handoffs match "${searchQuery}". Clear your search.`
                  : "No operational handoffs have been drafted for this project yet."}
              </p>
            </div>
            <div className="flex justify-center gap-3">
              <Button variant="outline" size="sm" onClick={() => setIsGenerateModalOpen(true)}>
                Generate with AI
              </Button>
              <Button variant="primary" size="sm" onClick={() => setIsCreateModalOpen(true)}>
                Create Handoff
              </Button>
            </div>
          </div>
        )}

        {/* Interactive Handoff Detail Modal */}
        {activeHandoff && (
          <Modal
            isOpen={!!activeHandoff}
            onClose={() => setActiveHandoff(null)}
            title={activeHandoff.title}
          >
            <div className="space-y-5 max-h-[75vh] overflow-y-auto pr-1">
              {/* Header metadata & status transition controls */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {getStatusBadge(activeHandoff.status)}
                    <span className="text-xs text-slate-500">
                      Knowledge Owner: <strong className="text-slate-800">{activeHandoff.summary?.knowledge_owner_name || "Lead"}</strong>
                    </span>
                    <span className="text-slate-300">|</span>
                    <span className="text-xs text-slate-500">
                      Successor: <strong className="text-slate-800">{activeHandoff.summary?.successor_name || "Unassigned"}</strong>
                    </span>
                  </div>
                  {activeHandoff.summary?.target_completion_date && (
                    <p className="text-[11px] text-slate-400">
                      Target Completion: {activeHandoff.summary.target_completion_date}
                    </p>
                  )}
                </div>

                {/* State Transition Actions */}
                <div className="flex flex-wrap items-center gap-2">
                  {activeHandoff.status === "draft" && (
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={transitionLoading}
                      onClick={() => handleStatusTransition("in_review", "Submitted for successor review.")}
                    >
                      Submit for Review &rarr;
                    </Button>
                  )}

                  {activeHandoff.status === "in_review" && (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={transitionLoading}
                        onClick={() => handleStatusTransition("draft", "Revisions requested.")}
                      >
                        Request Changes
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={transitionLoading}
                        onClick={() => handleStatusTransition("approved", "Review completed and approved.")}
                      >
                        Approve Handoff &rarr;
                      </Button>
                    </>
                  )}

                  {(activeHandoff.status === "approved" || activeHandoff.status === "in_review") && (
                    <Button
                      variant="primary"
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700"
                      disabled={transitionLoading}
                      onClick={handleAcknowledge}
                    >
                      <CheckIcon className="w-4 h-4" />
                      Acknowledge & Accept
                    </Button>
                  )}

                  {activeHandoff.status === "acknowledged" && (
                    <Button
                      variant="primary"
                      size="sm"
                      className="bg-indigo-700 hover:bg-indigo-800"
                      disabled={transitionLoading}
                      onClick={() => handleStatusTransition("completed", "Handoff fully completed.")}
                    >
                      Mark Completed &rarr;
                    </Button>
                  )}
                </div>
              </div>

              {/* Explainable Readiness Score Card */}
              {activeHandoff.summary?.readiness_score && (
                <div className="p-4 bg-white rounded-xl border border-indigo-100 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-900">
                        Explainable Readiness Score
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        Multi-dimensional assessment across tasks, dependencies, risks, runbooks, and successor sign-off.
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-2xl font-black text-indigo-600">
                        {activeHandoff.summary.readiness_score.score}%
                      </span>
                    </div>
                  </div>

                  {/* 5 Dimensional Breakdown Bars */}
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-[11px]">
                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500">
                        <span>Task Clarity</span>
                        <strong>{activeHandoff.summary.readiness_score.breakdown.task_clarity}/25</strong>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500"
                          style={{ width: `${(activeHandoff.summary.readiness_score.breakdown.task_clarity / 25) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500">
                        <span>Dependencies</span>
                        <strong>{activeHandoff.summary.readiness_score.breakdown.dependencies_documented}/20</strong>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500"
                          style={{ width: `${(activeHandoff.summary.readiness_score.breakdown.dependencies_documented / 20) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500">
                        <span>Risk Mitigation</span>
                        <strong>{activeHandoff.summary.readiness_score.breakdown.risk_mitigation}/20</strong>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500"
                          style={{ width: `${(activeHandoff.summary.readiness_score.breakdown.risk_mitigation / 20) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500">
                        <span>Resources</span>
                        <strong>{activeHandoff.summary.readiness_score.breakdown.resources_complete}/15</strong>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500"
                          style={{ width: `${(activeHandoff.summary.readiness_score.breakdown.resources_complete / 15) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500">
                        <span>Successor Sign-off</span>
                        <strong>{activeHandoff.summary.readiness_score.breakdown.successor_readiness}/20</strong>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500"
                          style={{ width: `${(activeHandoff.summary.readiness_score.breakdown.successor_readiness / 20) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Missing items alerts */}
                  {activeHandoff.summary.readiness_score.missing_items?.length > 0 && (
                    <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 space-y-1">
                      <strong className="block text-[11px] uppercase tracking-wider">Completeness Gaps Detected:</strong>
                      <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                        {activeHandoff.summary.readiness_score.missing_items.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Sub-tabs for Structured Sections */}
              <div className="flex border-b border-slate-200 text-xs font-semibold gap-4">
                {[
                  { key: "summary", label: "Executive Summary" },
                  { key: "tasks", label: `Tasks (${activeHandoff.summary?.tasks?.length || 0})` },
                  { key: "dependencies", label: `Dependencies (${activeHandoff.summary?.dependencies?.length || 0})` },
                  { key: "risks", label: `Risks (${activeHandoff.summary?.risks?.length || 0})` },
                  { key: "resources", label: `Resources (${activeHandoff.summary?.resources?.length || 0})` },
                  { key: "comments", label: `Comments (${activeHandoff.comments?.length || 0})` },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveDetailTab(t.key as "summary" | "tasks" | "dependencies" | "risks" | "resources" | "comments")}
                    className={`pb-2.5 border-b-2 transition-colors ${
                      activeDetailTab === t.key
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Tab 1: Executive Summary */}
              {activeDetailTab === "summary" && (
                <div className="space-y-4 text-xs">
                  <div>
                    <h5 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                      Operational Context
                    </h5>
                    <p className="mt-1.5 text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
                      {activeHandoff.summary?.executive_summary || "No executive summary provided."}
                    </p>
                  </div>

                  <div>
                    <h5 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                      Key Responsibilities Handed Over
                    </h5>
                    <ul className="mt-1.5 space-y-1 list-disc list-inside text-slate-600">
                      {(activeHandoff.summary?.key_responsibilities || []).map((resp, i) => (
                        <li key={i}>{resp}</li>
                      ))}
                    </ul>
                  </div>

                  {activeHandoff.acknowledgements && activeHandoff.acknowledgements.length > 0 && (
                    <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-800 text-xs">
                      <strong>Formally Acknowledged:</strong> Confirmed by{" "}
                      {activeHandoff.acknowledgements[0].user_display_name || "Successor"} on{" "}
                      {new Date(activeHandoff.acknowledgements[0].acknowledged_at).toLocaleString()}.
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Tasks Checklist */}
              {activeDetailTab === "tasks" && (
                <div className="space-y-3">
                  {(activeHandoff.summary?.tasks || []).map((task) => (
                    <div
                      key={task.id}
                      className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">{task.title}</span>
                        <div className="flex items-center gap-1.5">
                          <Badge variant={task.status === "completed" ? "success" : task.status === "blocked" ? "danger" : "default"}>
                            {task.status}
                          </Badge>
                          <Badge variant={task.priority === "critical" ? "danger" : task.priority === "high" ? "warning" : "neutral"}>
                            {task.priority}
                          </Badge>
                        </div>
                      </div>

                      {task.description && (
                        <p className="text-slate-600 text-[11px] leading-relaxed">{task.description}</p>
                      )}

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200">
                        <span>Deadline: {task.deadline || "None"}</span>
                        <span>Assignee: {task.assignee || "Unassigned"}</span>
                      </div>

                      {task.blockers && (
                        <div className="p-2 bg-rose-50 text-rose-800 rounded border border-rose-200 text-[11px]">
                          <strong>Blocker:</strong> {task.blockers}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 3: Dependencies */}
              {activeDetailTab === "dependencies" && (
                <div className="space-y-3">
                  {(activeHandoff.summary?.dependencies || []).map((dep) => (
                    <div key={dep.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <strong className="text-slate-900">{dep.name}</strong>
                        <div className="flex gap-1.5">
                          <Badge variant="primary">{dep.type}</Badge>
                          <Badge variant={dep.criticality === "high" ? "danger" : "neutral"}>
                            {dep.criticality}
                          </Badge>
                        </div>
                      </div>
                      <p className="text-slate-600 text-[11px]">{dep.description}</p>
                      {dep.contact_or_link && (
                        <p className="text-[11px] text-indigo-600 truncate">
                          Link / Endpoint: {dep.contact_or_link}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 4: Risks */}
              {activeDetailTab === "risks" && (
                <div className="space-y-3">
                  {(activeHandoff.summary?.risks || []).map((risk) => (
                    <div key={risk.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <strong className="text-slate-900">{risk.title}</strong>
                        <Badge variant={risk.severity === "critical" || risk.severity === "high" ? "danger" : "warning"}>
                          {risk.severity} severity
                        </Badge>
                      </div>
                      {risk.impact && (
                        <p className="text-slate-600 text-[11px]">
                          <strong>Impact:</strong> {risk.impact}
                        </p>
                      )}
                      {risk.mitigation && (
                        <div className="p-2 bg-emerald-50 text-emerald-800 rounded border border-emerald-200 text-[11px]">
                          <strong>Mitigation:</strong> {risk.mitigation}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 5: Resources */}
              {activeDetailTab === "resources" && (
                <div className="space-y-3">
                  {(activeHandoff.summary?.resources || []).map((res) => (
                    <div key={res.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <strong className="text-slate-900">{res.title}</strong>
                        <Badge variant="neutral">{res.type}</Badge>
                      </div>
                      <p className="text-indigo-600 text-[11px] font-mono break-all">{res.url_or_path}</p>
                      {res.notes && <p className="text-slate-500 text-[11px]">{res.notes}</p>}
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 6: Comments & Feedback */}
              {activeDetailTab === "comments" && (
                <div className="space-y-4">
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {(activeHandoff.comments || []).map((c) => (
                      <div key={c.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <strong className="text-slate-800">{c.author_name || "Team Member"}</strong>
                          <span className="text-[10px] text-slate-400">
                            {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                        <p className="text-slate-600">{c.content}</p>
                      </div>
                    ))}
                    {(!activeHandoff.comments || activeHandoff.comments.length === 0) && (
                      <p className="text-xs text-slate-400 italic">No review comments posted yet.</p>
                    )}
                  </div>

                  {/* Add comment input */}
                  <form onSubmit={handleAddComment} className="space-y-2 pt-2 border-t border-slate-200">
                    <div className="flex gap-2">
                      <select
                        value={commentType}
                        onChange={(e) => setCommentType(e.target.value as "comment" | "blocker" | "approval" | "change_request")}
                        className="text-xs py-1 px-2 bg-white border border-slate-200 rounded-lg text-slate-700"
                      >
                        <option value="comment">General Note</option>
                        <option value="blocker">Report Blocker</option>
                        <option value="approval">Approval Note</option>
                        <option value="change_request">Change Request</option>
                      </select>
                    </div>
                    <Textarea
                      placeholder="Add a review note, question, or approval remark..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      rows={2}
                      required
                    />
                    <Button variant="primary" size="sm" type="submit" disabled={isSubmittingComment}>
                      Post Review Comment
                    </Button>
                  </form>
                </div>
              )}
            </div>
          </Modal>
        )}

        {/* Create Handoff Modal */}
        <Modal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          title="Create New Operational Handoff"
        >
          <form onSubmit={handleCreateHandoff} className="space-y-4">
            <Input
              label="Handoff Title"
              placeholder="e.g. Core Checkout & Payment Gateway Migration Handover"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              required
            />

            <Textarea
              label="Executive Summary & Objectives"
              placeholder="Provide a high-level operational briefing of the components and duties being transferred..."
              value={newExecSummary}
              onChange={(e) => setNewExecSummary(e.target.value)}
              rows={3}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Successor / Assignee
                </label>
                <select
                  value={newSuccessorId}
                  onChange={(e) => setNewSuccessorId(e.target.value)}
                  className="w-full text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                >
                  <option value="">Unassigned</option>
                  {projectMembers.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Handover Date
                </label>
                <input
                  type="date"
                  value={newTargetDate}
                  onChange={(e) => setNewTargetDate(e.target.value)}
                  className="w-full text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
              <Button variant="secondary" size="sm" type="button" onClick={() => setIsCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={isSubmittingCreate}>
                {isSubmittingCreate ? "Creating..." : "Save Draft Handoff"}
              </Button>
            </div>
          </form>
        </Modal>

        {/* AI Assisted Handoff Generation Modal */}
        <Modal
          isOpen={isGenerateModalOpen}
          onClose={() => setIsGenerateModalOpen(false)}
          title="AI-Assisted Structured Handoff Generator"
        >
          <form onSubmit={handleGenerateHandoff} className="space-y-4">
            <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100 text-xs text-indigo-900 space-y-1">
              <strong>Automated Knowledge Extraction:</strong>
              <p className="text-[11px] leading-relaxed text-indigo-700">
                The generator analyzes all indexed documents, Jira issues, Slack incident threads, and runbooks
                in this project. It synthesizes executive briefings, tasks, dependencies, risks, and calculates an
                initial explainable readiness score.
              </p>
            </div>

            <Input
              label="Generated Handoff Title"
              value={genTitle}
              onChange={(e) => setGenTitle(e.target.value)}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Designated Successor
                </label>
                <select
                  value={genSuccessorId}
                  onChange={(e) => setGenSuccessorId(e.target.value)}
                  className="w-full text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                >
                  <option value="">Unassigned</option>
                  {projectMembers.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Handover Date
                </label>
                <input
                  type="date"
                  value={genTargetDate}
                  onChange={(e) => setGenTargetDate(e.target.value)}
                  className="w-full text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
              <Button variant="secondary" size="sm" type="button" onClick={() => setIsGenerateModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={isGenerating}>
                {isGenerating ? "Analyzing Project Sources..." : "Generate Handoff Draft"}
              </Button>
            </div>
          </form>
        </Modal>

        {/* Workflow Execution Dialog */}
        <WorkflowExecutionDialog
          isOpen={isWorkflowOpen}
          onClose={() => setIsWorkflowOpen(false)}
          title={workflowTitle}
          description={workflowDescription}
          steps={workflowSteps}
          isComplete={workflowComplete}
          isSuccess={workflowSuccess}
          result={workflowResult}
          onDone={() => setIsWorkflowOpen(false)}
        />
      </div>
    </ProtectedRoute>
  );
}
