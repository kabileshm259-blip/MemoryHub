import React from "react";
import { ProjectRole, ProjectStatus } from "@/types/api";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "primary" | "success" | "warning" | "danger" | "neutral";
  size?: "sm" | "md";
}

export function Badge({ children, variant = "default", size = "sm" }: BadgeProps) {
  const variantStyles = {
    default: "bg-slate-100 text-slate-700 border-slate-200",
    primary: "bg-indigo-50 text-indigo-700 border-indigo-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    danger: "bg-rose-50 text-rose-700 border-rose-200",
    neutral: "bg-zinc-100 text-zinc-600 border-zinc-200",
  };

  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-xs",
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      {children}
    </span>
  );
}

export function RoleBadge({ role }: { role: ProjectRole }) {
  const configs: Record<ProjectRole, { label: string; variant: BadgeProps["variant"] }> = {
    owner: { label: "Owner", variant: "primary" },
    editor: { label: "Editor", variant: "neutral" },
    viewer: { label: "Viewer", variant: "default" },
  };

  const config = configs[role] || { label: role, variant: "default" };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  const configs: Record<ProjectStatus, { label: string; variant: BadgeProps["variant"] }> = {
    active: { label: "Active", variant: "success" },
    archived: { label: "Archived", variant: "warning" },
    suspended: { label: "Suspended", variant: "danger" },
  };

  const config = configs[status] || { label: status, variant: "default" };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
