"use client";

import React, { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { api, ApiError } from "@/lib/api";
import { Project } from "@/types/api";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { CreateProjectModal } from "@/components/projects/CreateProjectModal";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { PlusIcon, ProjectsIcon, SearchIcon } from "@/components/ui/Icons";

const PAGE_SIZE = 9;

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [offset, setOffset] = useState<number>(0);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  const fetchProjects = (pageOffset: number) => {
    setIsLoading(true);
    setError(null);
    api
      .listProjects({ limit: PAGE_SIZE, offset: pageOffset })
      .then((data) => {
        setProjects(data.items);
        setTotalCount(data.total);
        setOffset(pageOffset);
        setIsLoading(false);
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Unable to load projects from the server.");
        }
        setIsLoading(false);
      });
  };

  useEffect(() => {
    let isCurrent = true;
    api
      .listProjects({ limit: PAGE_SIZE, offset: 0 })
      .then((data) => {
        if (isCurrent) {
          setProjects(data.items);
          setTotalCount(data.total);
          setOffset(0);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError("Unable to load projects from the server.");
          }
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const handleProjectCreated = (newProject: Project) => {
    setProjects((prev) => [newProject, ...prev]);
    setTotalCount((prev) => prev + 1);
  };

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Projects
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Manage your workspaces, team access, and member permissions.
            </p>
          </div>
          <div>
            <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
              <PlusIcon className="w-4 h-4" />
              New Project
            </Button>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200">
          <div className="relative w-full sm:w-80">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <SearchIcon className="w-4 h-4" />
            </span>
            <input
              type="text"
              placeholder="Search projects by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600 transition-colors"
            />
          </div>
          <div className="text-xs text-slate-500 shrink-0">
            Showing {filteredProjects.length} of {totalCount} total projects
          </div>
        </div>

        {error && (
          <div className="space-y-3">
            <Alert variant="error" title="Failed to load projects">
              {error}
            </Alert>
            <Button variant="secondary" size="sm" onClick={() => fetchProjects(offset)}>
              Retry
            </Button>
          </div>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
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
        ) : filteredProjects.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredProjects.map((proj) => (
                <ProjectCard key={proj.id} project={proj} />
              ))}
            </div>

            {/* Pagination Controls */}
            {totalCount > PAGE_SIZE && (
              <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => fetchProjects(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  &larr; Previous
                </Button>
                <span className="text-xs text-slate-500">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => fetchProjects(offset + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= totalCount}
                >
                  Next &rarr;
                </Button>
              </div>
            )}
          </>
        ) : !error ? (
          <div className="p-12 bg-white rounded-2xl border border-slate-200 text-center flex flex-col items-center justify-center max-w-md mx-auto">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl mb-4">
              <ProjectsIcon className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              {searchTerm ? "No matching projects" : "No projects found"}
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm leading-relaxed">
              {searchTerm
                ? `No projects matched "${searchTerm}". Try a different keyword or clear the search.`
                : "You don't have access to any projects yet. Create one to begin organizing handoffs and documents."}
            </p>
            {searchTerm ? (
              <Button
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={() => setSearchTerm("")}
              >
                Clear Search
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                className="mt-5"
                onClick={() => setIsCreateModalOpen(true)}
              >
                <PlusIcon className="w-4 h-4" />
                Create your first project
              </Button>
            )}
          </div>
        ) : null}
      </div>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </ProtectedRoute>
  );
}
