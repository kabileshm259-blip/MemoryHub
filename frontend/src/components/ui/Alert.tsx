import React from "react";
import { AlertCircleIcon, CheckCircleIcon } from "./Icons";

interface AlertProps {
  children: React.ReactNode;
  variant?: "error" | "warning" | "success" | "info";
  title?: string;
  className?: string;
}

export function Alert({
  children,
  variant = "info",
  title,
  className = "",
}: AlertProps) {
  const styles = {
    error: {
      wrapper: "bg-rose-50 border-rose-200 text-rose-900",
      icon: <AlertCircleIcon className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />,
      titleColor: "text-rose-950",
    },
    warning: {
      wrapper: "bg-amber-50 border-amber-200 text-amber-900",
      icon: <AlertCircleIcon className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />,
      titleColor: "text-amber-950",
    },
    success: {
      wrapper: "bg-emerald-50 border-emerald-200 text-emerald-900",
      icon: <CheckCircleIcon className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />,
      titleColor: "text-emerald-950",
    },
    info: {
      wrapper: "bg-slate-50 border-slate-200 text-slate-800",
      icon: <AlertCircleIcon className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />,
      titleColor: "text-slate-900",
    },
  };

  const selected = styles[variant];

  return (
    <div
      role="alert"
      className={`flex items-start gap-3 p-3.5 border rounded-lg text-sm ${selected.wrapper} ${className}`}
    >
      {selected.icon}
      <div className="flex-1">
        {title && (
          <h4 className={`font-semibold mb-0.5 ${selected.titleColor}`}>{title}</h4>
        )}
        <div className="leading-relaxed">{children}</div>
      </div>
    </div>
  );
}
