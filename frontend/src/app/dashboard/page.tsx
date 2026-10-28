"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { useAuth } from "@/context/auth-context";
import { api, ApiError } from "@/lib/api";
import { Project } from "@/types/api";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { CreateProjectModal } from "@/components/projects/CreateProjectModal";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { PlusIcon, ProjectsIcon, HandoffsIcon, SourcesIcon } from "@/components/ui/Icons";

export default function DashboardPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [handoffCount, setHandoffCount] = useState<number>(0);
  const [sourceCount, setSourceCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  const fetchDashboardData = useCallback(() => {
    api
      .listProjects({ limit: 6, offset: 0 })
      .then(async (data) => {
        setProjects(data.items);
        setTotalCount(data.total);

        // Fetch counts across recent projects
        if (data.items.length > 0) {
          try {
            const handoffPromises = data.items.map((p) =>
              api.listHandoffs(p.id).catch(() => ({ items: [], total: 0 }))
            );
            const sourcePromises = data.items.map((p) =>
              api.listSources(p.id).catch(() => ({ items: [], total: 0 }))
            );

            const [handoffResults, sourceResults] = await Promise.all([
              Promise.all(handoffPromises),
              Promise.all(sourcePromises),
            ]);

            const totalHandoffs = handoffResults.reduce(
              (acc, curr) => acc + (curr.total || curr.items?.length || 0),
              0
            );
            const totalSources = sourceResults.reduce(
              (acc, curr) => acc + (curr.total || curr.items?.length || 0),
              0
            );

            setHandoffCount(totalHandoffs);
            setSourceCount(totalSources);
          } catch {
            // Non-critical count aggregation fallback
          }
        }
        setIsLoading(false);
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError(err.message || "Unable to load projects from the server.");
        }
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleProjectCreated = (newProject: Project) => {
    setProjects((prev) => [newProject, ...prev]);
    setTotalCount((prev) => prev + 1);
  };

  return (
    <ProtectedRoute>
      <div className="space-y-8">
        {/* Welcome Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Welcome back, {user?.display_name || "Developer"}
            </h1>
            <p className="text-xs md:text-sm text-slate-500 mt-1">
              Here is an overview of the projects, active handoffs, and indexed knowledge sources in MemoryHub.
            </p>
          </div>
          <div>
            <Button
              variant="primary"
              onClick={() => setIsCreateModalOpen(true)}
              className="w-full md:w-auto"
            >
              <PlusIcon className="w-4 h-4" />
              Create Project
            </Button>
          </div>
        </div>

        {/* Real Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <Link href="/projects" className="group p-5 bg-white rounded-xl border border-slate-200 shadow-xs hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                  Accessible Projects
                </p>
                <h3 className="text-3xl font-extrabold text-slate-900 mt-2">
                  {isLoading ? "..." : totalCount}
                </h3>
              </div>
              <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl group-hover:bg-indigo-100 transition-colors">
                <ProjectsIcon className="w-6 h-6" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 flex items-center justify-between">
              <span>Owner, Editor, or Viewer access.</span>
              <span className="text-indigo-600 font-medium group-hover:translate-x-0.5 transition-transform">&rarr;</span>
            </p>
          </Link>

          <Link href="/handoffs" className="group p-5 bg-white rounded-xl border border-slate-200 shadow-xs hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                  Active Handoffs
                </p>
                <h3 className="text-3xl font-extrabold text-slate-900 mt-2">
                  {isLoading ? "..." : handoffCount}
                </h3>
              </div>
              <div className="p-3 bg-amber-50 text-amber-600 rounded-xl group-hover:bg-amber-100 transition-colors">
                <HandoffsIcon className="w-6 h-6" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 flex items-center justify-between">
              <span>Readiness scoring & review workflows.</span>
              <span className="text-indigo-600 font-medium group-hover:translate-x-0.5 transition-transform">&rarr;</span>
            </p>
          </Link>

          <Link href="/sources" className="group p-5 bg-white rounded-xl border border-slate-200 shadow-xs hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                  Indexed Sources
                </p>
                <h3 className="text-3xl font-extrabold text-slate-900 mt-2">
                  {isLoading ? "..." : sourceCount}
                </h3>
              </div>
              <div className="p-3 bg-teal-50 text-teal-600 rounded-xl group-hover:bg-teal-100 transition-colors">
                <SourcesIcon className="w-6 h-6" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 flex items-center justify-between">
              <span>Vectorized Jira, Slack, & docs.</span>
              <span className="text-indigo-600 font-medium group-hover:translate-x-0.5 transition-transform">&rarr;</span>
            </p>
          </Link>
        </div>

        {/* Recent Projects Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Recent Projects
            </h2>
            {totalCount > 6 && (
              <Link
                href="/projects"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
              >
                View all ({totalCount}) &rarr;
              </Link>
            )}
          </div>

          {error && (
            <div className="space-y-3">
              <Alert variant="error" title="Failed to load projects">
                {error}
              </Alert>
              <Button variant="secondary" size="sm" onClick={fetchDashboardData}>
                Retry loading
              </Button>
            </div>
          )}

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-5 bg-white rounded-xl border border-slate-200 animate-pulse space-y-3"
                >
                  <div className="h-5 bg-slate-200 rounded w-1/2" />
                  <div className="h-3 bg-slate-200 rounded w-full" />
                  <div className="h-3 bg-slate-200 rounded w-3/4" />
                </div>
              ))}
            </div>
          ) : projects.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((proj) => (
                <ProjectCard key={proj.id} project={proj} />
              ))}
            </div>
          ) : !error ? (
            <div className="p-12 bg-white rounded-2xl border border-slate-200 text-center flex flex-col items-center justify-center max-w-xl mx-auto">
              <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl mb-4">
                <ProjectsIcon className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                No projects found
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm leading-relaxed">
                You haven&apos;t created or been invited to any projects yet. Get started by creating your first project workspace.
              </p>
              <Button
                variant="primary"
                size="sm"
                className="mt-5"
                onClick={() => setIsCreateModalOpen(true)}
              >
                <PlusIcon className="w-4 h-4" />
                Create your first project
              </Button>
            </div>
          ) : null}
        </div>
      </div>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </ProtectedRoute>
  );
}
