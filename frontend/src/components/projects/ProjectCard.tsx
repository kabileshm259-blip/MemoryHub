import React from "react";
import Link from "next/link";
import { RoleBadge, StatusBadge } from "@/components/ui/Badge";
import { ClockIcon, ProjectsIcon } from "@/components/ui/Icons";
import { Project } from "@/types/api";

export function ProjectCard({ project }: { project: Project }) {
  const formattedDate = new Date(project.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Link
      href={`/projects/${project.id}`}
      className="group block p-5 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all relative overflow-hidden"
    >
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 bg-slate-50 text-slate-600 group-hover:bg-indigo-50 group-hover:text-indigo-600 rounded-lg transition-colors border border-slate-100">
            <ProjectsIcon className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors truncate text-base">
            {project.name}
          </h3>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {project.role && <RoleBadge role={project.role} />}
          <StatusBadge status={project.status} />
        </div>
      </div>

      <p className="text-xs text-slate-500 line-clamp-2 mb-4 leading-relaxed min-h-[2rem]">
        {project.description || "No description provided."}
      </p>

      <div className="flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-slate-100">
        <span className="flex items-center gap-1">
          <ClockIcon className="w-3.5 h-3.5" />
          Created {formattedDate}
        </span>
        <span className="font-medium text-indigo-600 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
          View details &rarr;
        </span>
      </div>
    </Link>
  );
}
