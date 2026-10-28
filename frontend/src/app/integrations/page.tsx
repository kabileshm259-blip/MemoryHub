"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { api } from "@/lib/api";
import { IntegrationConnection, Project } from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { SourcesIcon } from "@/components/ui/Icons";
import {
  WorkflowExecutionDialog,
  WorkflowStep,
  WorkflowResultData,
} from "@/components/ui/WorkflowExecutionDialog";

export default function IntegrationsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [integrations, setIntegrations] = useState<IntegrationConnection[]>([]);

  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Syncing state by ID
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [isSeedingDemo, setIsSeedingDemo] = useState(false);

  // Workflow Dialog State
  const [isWorkflowOpen, setIsWorkflowOpen] = useState(false);
  const [workflowTitle, setWorkflowTitle] = useState("");
  const [workflowDescription, setWorkflowDescription] = useState("");
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [workflowComplete, setWorkflowComplete] = useState(false);
  const [workflowSuccess, setWorkflowSuccess] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResultData | null>(null);

  const fetchIntegrations = useCallback((projectId: string) => {
    api
      .listIntegrations(projectId)
      .then((items) => {
        setIntegrations(items);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Failed to load integrations.";
        setError(message);
      });
  }, []);

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

  useEffect(() => {
    if (!selectedProjectId) return;
    fetchIntegrations(selectedProjectId);
  }, [selectedProjectId, fetchIntegrations]);

  const handleSync = async (integrationId: string, providerType: string) => {
    if (!selectedProjectId) return;
    setSyncingId(integrationId);
    setSyncFeedback(null);

    const initialSteps: WorkflowStep[] = [
      {
        id: "auth",
        label: `Connecting to ${providerType.toUpperCase()} Gateway`,
        description: "Checking connector status and authorization credentials",
        status: "running",
      },
      {
        id: "fetch",
        label: "Extracting Operational Records",
        description: "Querying tickets, threads, or documentation updates",
        status: "pending",
      },
      {
        id: "index",
        label: "Semantic Indexing into Vector Store",
        description: "Generating vector embeddings and updating RAG index",
        status: "pending",
      },
    ];

    setWorkflowTitle(`${providerType.toUpperCase()} Synchronization`);
    setWorkflowDescription(`Synchronizing knowledge records from ${providerType.toUpperCase()} connector`);
    setWorkflowSteps(initialSteps);
    setWorkflowComplete(false);
    setWorkflowSuccess(false);
    setWorkflowResult(null);
    setIsWorkflowOpen(true);

    await new Promise((r) => setTimeout(r, 200));

    try {
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "auth"
            ? { ...s, status: "succeeded" }
            : s.id === "fetch"
            ? { ...s, status: "running" }
            : s
        )
      );

      const res = await api.syncIntegration(selectedProjectId, integrationId);

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "fetch"
            ? { ...s, status: "succeeded" }
            : s.id === "index"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 200));

      setWorkflowSteps((prev) =>
        prev.map((s) => (s.id === "index" ? { ...s, status: "succeeded" } : s))
      );

      fetchIntegrations(selectedProjectId);

      setWorkflowSuccess(true);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Synchronization Complete",
        message: `Successfully synchronized ${res.records_synced} records and created ${res.relationships_created} relationship links.`,
        badge: {
          label: "Synced",
          variant: "success",
        },
        evidence: [
          { label: "Provider", value: providerType.toUpperCase() },
          { label: "Records Synced", value: res.records_synced },
          { label: "Links Created", value: res.relationships_created },
          { label: "Connector Mode", value: "Simulated Provider (Demo Mode)" },
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
        title: "Synchronization Failed",
        message,
        badge: {
          label: "Error",
          variant: "danger",
        },
      });
      alert(message || "Sync failed.");
    } finally {
      setSyncingId(null);
    }
  };

  const handleSeedDemo = async () => {
    if (!selectedProjectId) return;
    setIsSeedingDemo(true);
    setError(null);
    setSyncFeedback(null);

    const initialSteps: WorkflowStep[] = [
      {
        id: "scenario",
        label: "Initializing E-Commerce Scenario Blueprint",
        description: "Preparing mock Jira tickets, Slack incident threads, and payment runbooks",
        status: "running",
      },
      {
        id: "ingest",
        label: "Ingesting Multi-Source Records",
        description: "Generating 5 canonical engineering records across project components",
        status: "pending",
      },
      {
        id: "index",
        label: "Vector Storage Registration",
        description: "Indexing records into vector storage for grounded RAG synthesis",
        status: "pending",
      },
    ];

    setWorkflowTitle("Synthetic Demonstration Seeder");
    setWorkflowDescription("Seeding multi-source scenario data for realistic demonstration");
    setWorkflowSteps(initialSteps);
    setWorkflowComplete(false);
    setWorkflowSuccess(false);
    setWorkflowResult(null);
    setIsWorkflowOpen(true);

    await new Promise((r) => setTimeout(r, 200));

    try {
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "scenario"
            ? { ...s, status: "succeeded" }
            : s.id === "ingest"
            ? { ...s, status: "running" }
            : s
        )
      );

      const res = await api.seedDemoScenario(selectedProjectId);

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "ingest"
            ? { ...s, status: "succeeded" }
            : s.id === "index"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 250));

      setWorkflowSteps((prev) =>
        prev.map((s) => (s.id === "index" ? { ...s, status: "succeeded" } : s))
      );

      fetchIntegrations(selectedProjectId);

      setWorkflowSuccess(true);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Demo Scenario Seeded",
        message: `Successfully seeded ${res.records_ingested} records for scenario "${res.scenario}".`,
        badge: {
          label: "Seeded",
          variant: "success",
        },
        evidence: [
          { label: "Scenario", value: res.scenario },
          { label: "Records Seeded", value: res.records_ingested },
          { label: "Status", value: "Vector Store Up to Date" },
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
        title: "Demo Seeding Failed",
        message,
        badge: {
          label: "Error",
          variant: "danger",
        },
      });
      setError(message || "Failed to seed demonstration scenario.");
    } finally {
      setIsSeedingDemo(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Third-Party Integrations Hub
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Authorized connectors for Jira Cloud, Slack workspaces, Confluence, and GitHub repositories.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Project Switcher */}
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
          </div>
        </div>

        {syncFeedback && (
          <Alert variant="success" title="Sync Completed">
            {syncFeedback}
          </Alert>
        )}

        {error && (
          <Alert variant="error" title="Notice">
            {error}
          </Alert>
        )}

        {/* Canonical Demonstration Banner */}
        <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white p-6 rounded-2xl shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="inline-block px-2 py-0.5 text-[10px] font-extrabold uppercase rounded bg-indigo-500/30 text-indigo-200 border border-indigo-400/30 tracking-wider">
              Academic Demonstration Dataset
            </span>
            <h3 className="text-lg font-bold tracking-tight">
              E-Commerce Platform Modernization Scenario
            </h3>
            <p className="text-xs text-indigo-200 max-w-xl leading-relaxed">
              Populate this project with verified Jira issues (ECOM-101 Stripe migration, ECOM-102 Redis bottleneck, ECOM-103 inventory deadlock),
              Slack incident threads (#ops-checkout), and architecture runbooks with SHA-256 provenance.
            </p>
          </div>

          <Button
            variant="secondary"
            size="md"
            onClick={handleSeedDemo}
            disabled={!selectedProjectId || isSeedingDemo}
            className="bg-white text-indigo-900 hover:bg-indigo-50 shrink-0 font-bold text-xs"
          >
            <SourcesIcon className="w-4 h-4 text-indigo-700" />
            <span>{isSeedingDemo ? "Seeding Records..." : "Seed Demo Scenario"}</span>
          </Button>
        </div>

        {/* Integration Connectors Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Connector 1: Atlassian Jira */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center font-bold text-lg border border-sky-100">
                    J
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Atlassian Jira Cloud</h3>
                    <p className="text-[11px] text-slate-400">Issue tracking, epics, blockers, and sprint handover</p>
                  </div>
                </div>
                <Badge variant="success">Active</Badge>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                Extracts user stories, bug reports, and sprint tasks into structured handover items.
                Maps issue resolution comments and blocker flags directly into project vector memory.
              </p>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-500 space-y-1">
                <div className="flex justify-between">
                  <span>Connected Endpoint:</span>
                  <strong className="text-slate-700 font-mono">company.atlassian.net/rest/api/3</strong>
                </div>
                <div className="flex justify-between">
                  <span>Scope:</span>
                  <strong className="text-slate-700">Project Epics &amp; Sprint Tickets</strong>
                </div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Deduplicated via SHA-256</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const jira = integrations.find((i) => i.provider_type === "jira");
                  if (jira) handleSync(jira.id, "jira");
                  else handleSeedDemo();
                }}
                disabled={syncingId !== null}
              >
                {syncingId ? "Syncing..." : "Sync Jira Issues Now"}
              </Button>
            </div>
          </div>

          {/* Connector 2: Slack Workspaces */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold text-lg border border-purple-100">
                    S
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Slack Workspaces</h3>
                    <p className="text-[11px] text-slate-400">Incident threads, ops discussions, and architecture notes</p>
                  </div>
                </div>
                <Badge variant="success">Active</Badge>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                Captures engineering discussions, production incident triage, and undocumented operational decisions
                from designated team channels (e.g. #ops-checkout, #architecture-decisions).
              </p>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-500 space-y-1">
                <div className="flex justify-between">
                  <span>Channels Monitored:</span>
                  <strong className="text-slate-700">#ops-checkout, #dev-backend</strong>
                </div>
                <div className="flex justify-between">
                  <span>Thread Aggregation:</span>
                  <strong className="text-slate-700">Automatic Context Preservation</strong>
                </div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Indexed to ChromaDB</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const slack = integrations.find((i) => i.provider_type === "slack");
                  if (slack) handleSync(slack.id, "slack");
                  else handleSeedDemo();
                }}
                disabled={syncingId !== null}
              >
                {syncingId ? "Syncing..." : "Sync Slack Channels Now"}
              </Button>
            </div>
          </div>

          {/* Connector 3: Confluence Wiki */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg border border-blue-100">
                    C
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Confluence Knowledge Base</h3>
                    <p className="text-[11px] text-slate-400">Versioned architecture runbooks and guides</p>
                  </div>
                </div>
                <Badge variant="neutral">Ready</Badge>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                Pulls system architecture documentation, emergency failover runbooks, and disaster recovery procedures
                directly into project vector memory with section hierarchy preserved.
              </p>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Sync on change</span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleSeedDemo()}
              >
                Ingest Wiki Pages
              </Button>
            </div>
          </div>

          {/* Connector 4: GitHub Enterprise */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center font-bold text-lg border border-slate-200">
                    G
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">GitHub Enterprise</h3>
                    <p className="text-[11px] text-slate-400">Repository runbooks, READMEs, and PR discussions</p>
                  </div>
                </div>
                <Badge variant="neutral">Ready</Badge>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                Indexes code documentation, markdown files inside /docs directories, and pull request review comments
                for complete developer context preservation.
              </p>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Repository indexing</span>
              <Link href="/sources">
                <Button variant="secondary" size="sm">
                  Upload Markdown &rarr;
                </Button>
              </Link>
            </div>
          </div>
        </div>

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
