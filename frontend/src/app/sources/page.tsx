"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { api } from "@/lib/api";
import { Project, SourceRecord } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Modal } from "@/components/ui/Modal";
import {
  PlusIcon,
  SearchIcon,
  SourcesIcon,
} from "@/components/ui/Icons";

export default function SourcesPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [sources, setSources] = useState<SourceRecord[]>([]);

  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [activeViewerSource, setActiveViewerSource] = useState<SourceRecord | null>(null);

  // Ingest modal state
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newSourceType, setNewSourceType] = useState<string>("document");
  const [newProviderType, setNewProviderType] = useState<string>("file_upload");
  const [isIngesting, setIsIngesting] = useState(false);

  // Demo seeder state
  const [isSeeding, setIsSeeding] = useState(false);

  const fetchSources = useCallback((projectId: string) => {
    api
      .listSources(projectId)
      .then((data) => {
        setSources(data.items);
        setIsLoadingSources(false);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Failed to load knowledge sources.";
        setError(message);
        setIsLoadingSources(false);
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
    fetchSources(selectedProjectId);
  }, [selectedProjectId, fetchSources]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !newTitle.trim() || !newContent.trim()) return;

    setIsIngesting(true);
    try {
      const created = await api.ingestSource(selectedProjectId, {
        title: newTitle.trim(),
        content: newContent.trim(),
        source_type: newSourceType,
        provider_type: newProviderType,
      });
      setSources((prev) => [created, ...prev]);
      setIsIngestModalOpen(false);
      setNewTitle("");
      setNewContent("");
      setSuccessMessage(`Document '${created.title}' ingested and indexed into vector memory.`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message || "Failed to ingest source document.");
    } finally {
      setIsIngesting(false);
    }
  };

  const handleSeedDemo = async () => {
    if (!selectedProjectId) return;
    setIsSeeding(true);
    setError(null);
    try {
      const res = await api.seedDemoScenario(selectedProjectId);
      setSuccessMessage(
        `Seeded ${res.records_ingested} demonstration sources for '${res.scenario}'! Generated ChromaDB vector embeddings.`
      );
      fetchSources(selectedProjectId);
      setTimeout(() => setSuccessMessage(null), 7000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message || "Failed to seed demonstration scenario.");
    } finally {
      setIsSeeding(false);
    }
  };

  const handleDeleteSource = async (sourceId: string, title?: string | null) => {
    if (!confirm(`Are you sure you want to delete '${title || "this source"}' and all its vector chunks?`)) {
      return;
    }
    try {
      await api.deleteSource(selectedProjectId, sourceId);
      setSources((prev) => prev.filter((s) => s.id !== sourceId));
      if (activeViewerSource?.id === sourceId) setActiveViewerSource(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      alert(message || "Failed to delete source.");
    }
  };

  const filteredSources = sources.filter((s) => {
    const q = searchQuery.toLowerCase();
    return (
      (s.title && s.title.toLowerCase().includes(q)) ||
      (s.content && s.content.toLowerCase().includes(q)) ||
      s.provider_type.toLowerCase().includes(q)
    );
  });

  const totalChunks = sources.reduce((acc, s) => acc + (s.chunk_count || 1), 0);
  const providersSet = new Set(sources.map((s) => s.provider_type));

  const getProviderBadge = (provider: string) => {
    switch (provider) {
      case "jira":
        return <span className="bg-sky-50 text-sky-700 border border-sky-200 px-2 py-0.5 rounded text-xs font-semibold">Jira</span>;
      case "slack":
        return <span className="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded text-xs font-semibold">Slack</span>;
      case "confluence":
        return <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded text-xs font-semibold">Confluence</span>;
      default:
        return <span className="bg-slate-100 text-slate-700 border border-slate-200 px-2 py-0.5 rounded text-xs font-semibold">File Upload</span>;
    }
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Knowledge Sources & Vector Indexing
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Ingest engineering runbooks, Jira sprint archives, and Slack discussions into ChromaDB embeddings.
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

            <Button
              variant="outline"
              size="sm"
              onClick={handleSeedDemo}
              disabled={!selectedProjectId || isSeeding}
            >
              <SourcesIcon className="w-4 h-4 text-indigo-600" />
              <span>{isSeeding ? "Seeding Demo Data..." : "Seed E-Commerce Demo"}</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsIngestModalOpen(true)}
              disabled={!selectedProjectId}
            >
              <PlusIcon className="w-4 h-4" />
              <span>Ingest Document</span>
            </Button>
          </div>
        </div>

        {successMessage && (
          <Alert variant="success" title="Success">
            {successMessage}
          </Alert>
        )}

        {error && (
          <Alert variant="error" title="Notice">
            {error}
          </Alert>
        )}

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Total Sources</p>
            <h3 className="text-2xl font-extrabold text-slate-900 mt-1">{sources.length}</h3>
            <p className="text-[11px] text-slate-400 mt-1">Indexed knowledge records</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Indexed Vector Chunks</p>
            <h3 className="text-2xl font-extrabold text-indigo-600 mt-1">{totalChunks}</h3>
            <p className="text-[11px] text-slate-400 mt-1">384-dimensional embeddings</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Connected Providers</p>
            <h3 className="text-2xl font-extrabold text-purple-600 mt-1">{providersSet.size}</h3>
            <p className="text-[11px] text-slate-400 mt-1">Jira, Slack, Documents</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <p className="text-xs font-semibold uppercase text-slate-400">Deduplication Hash</p>
            <h3 className="text-2xl font-extrabold text-emerald-600 mt-1">SHA-256</h3>
            <p className="text-[11px] text-slate-400 mt-1">Prevents duplicate chunks</p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-4">
          <div className="relative w-full sm:w-80">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <SearchIcon className="w-3.5 h-3.5" />
            </span>
            <input
              type="text"
              placeholder="Filter sources by title, content, or provider..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600"
            />
          </div>
          <span className="text-xs text-slate-400 shrink-0">
            Showing {filteredSources.length} of {sources.length} indexed records
          </span>
        </div>

        {/* Source Records Table */}
        {isLoadingSources ? (
          <div className="p-8 bg-white rounded-xl border border-slate-200 text-center animate-pulse text-xs text-slate-400">
            Loading project knowledge sources...
          </div>
        ) : filteredSources.length > 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Title & Details</th>
                  <th className="py-3 px-3">Provider</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Chunks</th>
                  <th className="py-3 px-3">Content Hash</th>
                  <th className="py-3 px-3">Last Synced</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSources.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900 line-clamp-1">{s.title || s.source_id}</div>
                      <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{s.content}</div>
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">{getProviderBadge(s.provider_type)}</td>
                    <td className="py-3 px-3 whitespace-nowrap capitalize text-slate-600">{s.source_type}</td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-bold text-[11px]">
                        {s.chunk_count || 1}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      {s.content_hash ? `${s.content_hash.slice(0, 8)}...` : "—"}
                    </td>
                    <td className="py-3 px-3 text-slate-500 whitespace-nowrap text-[11px]">
                      {new Date(s.last_synced_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap space-x-2">
                      <button
                        onClick={() => setActiveViewerSource(s)}
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                      >
                        View Content
                      </button>
                      <button
                        onClick={() => handleDeleteSource(s.id, s.title)}
                        className="text-xs font-semibold text-rose-600 hover:text-rose-800"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 bg-white rounded-2xl border border-slate-200 text-center max-w-md mx-auto space-y-4">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl w-fit mx-auto">
              <SourcesIcon className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">No knowledge sources yet</h3>
              <p className="text-xs text-slate-500 mt-1">
                Upload architecture notes or click &quot;Seed E-Commerce Demo&quot; to load tickets and runbooks into vector store.
              </p>
            </div>
            <div className="flex justify-center gap-3">
              <Button variant="outline" size="sm" onClick={handleSeedDemo} disabled={isSeeding}>
                Seed E-Commerce Demo
              </Button>
              <Button variant="primary" size="sm" onClick={() => setIsIngestModalOpen(true)}>
                Ingest Document
              </Button>
            </div>
          </div>
        )}

        {/* Source Text Viewer Modal */}
        {activeViewerSource && (
          <Modal
            isOpen={!!activeViewerSource}
            onClose={() => setActiveViewerSource(null)}
            title={activeViewerSource.title || activeViewerSource.source_id}
          >
            <div className="space-y-4 text-xs">
              <div className="flex flex-wrap items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span>Provider: {getProviderBadge(activeViewerSource.provider_type)}</span>
                <span className="text-slate-300">|</span>
                <span>Type: <strong className="capitalize">{activeViewerSource.source_type}</strong></span>
                <span className="text-slate-300">|</span>
                <span>Chunks: <strong>{activeViewerSource.chunk_count || 1}</strong></span>
                <span className="text-slate-300">|</span>
                <span className="font-mono text-[11px] text-slate-500">Hash: {activeViewerSource.content_hash}</span>
              </div>

              <div>
                <h4 className="font-bold text-slate-800 mb-1">Full Document Text:</h4>
                <div className="p-4 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                  {activeViewerSource.content || "Empty content."}
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button variant="secondary" size="sm" onClick={() => setActiveViewerSource(null)}>
                  Close Viewer
                </Button>
              </div>
            </div>
          </Modal>
        )}

        {/* Ingest Document Modal */}
        <Modal
          isOpen={isIngestModalOpen}
          onClose={() => setIsIngestModalOpen(false)}
          title="Ingest Knowledge Document"
        >
          <form onSubmit={handleIngest} className="space-y-4">
            <Input
              label="Document Title"
              placeholder="e.g. Checkout Service Disaster Recovery Runbook"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Source Type</label>
                <select
                  value={newSourceType}
                  onChange={(e) => setNewSourceType(e.target.value)}
                  className="w-full text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800"
                >
                  <option value="runbook">Runbook</option>
                  <option value="architecture_note">Architecture Note</option>
                  <option value="document">Documentation</option>
                  <option value="ticket">Ticket / Issue</option>
                  <option value="discussion">Discussion Thread</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Provider Origin</label>
                <select
                  value={newProviderType}
                  onChange={(e) => setNewProviderType(e.target.value)}
                  className="w-full text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-800"
                >
                  <option value="file_upload">File Upload (Markdown / Text)</option>
                  <option value="jira">Jira Ticket</option>
                  <option value="slack">Slack Channel Discussion</option>
                  <option value="confluence">Confluence Wiki</option>
                  <option value="manual_note">Manual Engineer Note</option>
                </select>
              </div>
            </div>

            <Textarea
              label="Document Content (Markdown or Plaintext)"
              placeholder="Paste operational guidelines, runbooks, or architecture instructions here..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              rows={8}
              required
            />

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
              <Button variant="secondary" size="sm" type="button" onClick={() => setIsIngestModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={isIngesting}>
                {isIngesting ? "Chunking & Indexing Vectors..." : "Ingest & Index Document"}
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </ProtectedRoute>
  );
}
