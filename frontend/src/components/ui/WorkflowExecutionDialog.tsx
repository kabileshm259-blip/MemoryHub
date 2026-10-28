"use client";

import React from "react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { Badge } from "./Badge";
import {
  CheckCircleIcon,
  AlertCircleIcon,
  SpinnerIcon,
  ClockIcon,
} from "./Icons";

export type StepStatus = "pending" | "running" | "succeeded" | "failed";

export interface WorkflowStep {
  id: string;
  label: string;
  description?: string;
  status: StepStatus;
  detail?: string;
}

export interface WorkflowEvidenceItem {
  label: string;
  value: React.ReactNode;
}

export interface WorkflowResultData {
  title: string;
  message: string;
  evidence?: WorkflowEvidenceItem[];
  badge?: {
    label: string;
    variant: "default" | "primary" | "success" | "warning" | "danger" | "neutral";
  };
}

// ----------------------------------------------------------------------
// Subcomponent 1: WorkflowStatusBadge
// ----------------------------------------------------------------------
export function WorkflowStatusBadge({ status }: { status: StepStatus }) {
  switch (status) {
    case "running":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
          <SpinnerIcon className="w-3 h-3 text-indigo-600 animate-spin motion-reduce:animate-none" />
          <span>In Progress</span>
        </span>
      );
    case "succeeded":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-600" />
          <span>Completed</span>
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
          <AlertCircleIcon className="w-3.5 h-3.5 text-rose-600" />
          <span>Failed</span>
        </span>
      );
    case "pending":
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
          <ClockIcon className="w-3.5 h-3.5 text-slate-400" />
          <span>Pending</span>
        </span>
      );
  }
}

// ----------------------------------------------------------------------
// Subcomponent 2: WorkflowStepItem
// ----------------------------------------------------------------------
export function WorkflowStepItem({
  step,
  index,
  isLast,
}: {
  step: WorkflowStep;
  index: number;
  isLast: boolean;
}) {
  const isRunning = step.status === "running";
  const isSucceeded = step.status === "succeeded";
  const isFailed = step.status === "failed";

  return (
    <div className="relative flex items-start gap-3.5 group">
      {/* Vertical connector line */}
      {!isLast && (
        <div
          aria-hidden="true"
          className={`absolute left-4 top-8 -bottom-3 w-0.5 transition-colors duration-300 ${
            isSucceeded
              ? "bg-emerald-300"
              : isRunning
              ? "bg-indigo-200"
              : "bg-slate-200"
          }`}
        />
      )}

      {/* Step Icon Indicator */}
      <div
        className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-all duration-200 ${
          isSucceeded
            ? "border-emerald-500 bg-emerald-500 text-white shadow-xs"
            : isRunning
            ? "border-indigo-600 bg-white text-indigo-600 ring-4 ring-indigo-50"
            : isFailed
            ? "border-rose-500 bg-rose-500 text-white shadow-xs"
            : "border-slate-300 bg-white text-slate-500"
        }`}
      >
        {isSucceeded ? (
          <CheckCircleIcon className="w-4 h-4 text-white" />
        ) : isRunning ? (
          <SpinnerIcon className="w-4 h-4 text-indigo-600 animate-spin motion-reduce:animate-none" />
        ) : isFailed ? (
          <AlertCircleIcon className="w-4 h-4 text-white" />
        ) : (
          <span>{index + 1}</span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-4 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p
            className={`text-sm font-semibold truncate ${
              isSucceeded
                ? "text-slate-800"
                : isRunning
                ? "text-indigo-900"
                : isFailed
                ? "text-rose-900"
                : "text-slate-500"
            }`}
          >
            {step.label}
          </p>
          <WorkflowStatusBadge status={step.status} />
        </div>

        {step.description && (
          <p className="mt-0.5 text-xs text-slate-500 leading-relaxed">
            {step.description}
          </p>
        )}

        {step.detail && (
          <div
            className={`mt-1.5 px-2.5 py-1.5 rounded-md text-xs font-mono break-all ${
              isFailed
                ? "bg-rose-50 text-rose-800 border border-rose-200"
                : "bg-slate-50 text-slate-700 border border-slate-200"
            }`}
          >
            {step.detail}
          </div>
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// Subcomponent 3: WorkflowStepTimeline
// ----------------------------------------------------------------------
export function WorkflowStepTimeline({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div className="space-y-1">
      {steps.map((step, idx) => (
        <WorkflowStepItem
          key={step.id || idx}
          step={step}
          index={idx}
          isLast={idx === steps.length - 1}
        />
      ))}
    </div>
  );
}

// ----------------------------------------------------------------------
// Subcomponent 4: WorkflowResultSummary
// ----------------------------------------------------------------------
export function WorkflowResultSummary({
  result,
  isSuccess,
}: {
  result: WorkflowResultData;
  isSuccess: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-4 text-left transition-all ${
        isSuccess
          ? "border-emerald-200 bg-emerald-50/60"
          : "border-rose-200 bg-rose-50/60"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {isSuccess ? (
            <div className="p-1 rounded-full bg-emerald-100 text-emerald-700">
              <CheckCircleIcon className="w-5 h-5" />
            </div>
          ) : (
            <div className="p-1 rounded-full bg-rose-100 text-rose-700">
              <AlertCircleIcon className="w-5 h-5" />
            </div>
          )}
          <div>
            <h4
              className={`text-sm font-bold ${
                isSuccess ? "text-emerald-950" : "text-rose-950"
              }`}
            >
              {result.title}
            </h4>
            <p
              className={`text-xs mt-0.5 leading-relaxed ${
                isSuccess ? "text-emerald-800" : "text-rose-800"
              }`}
            >
              {result.message}
            </p>
          </div>
        </div>

        {result.badge && (
          <Badge variant={result.badge.variant}>{result.badge.label}</Badge>
        )}
      </div>

      {result.evidence && result.evidence.length > 0 && (
        <div className="mt-3.5 pt-3 border-t border-emerald-200/70 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          {result.evidence.map((item, idx) => (
            <div
              key={idx}
              className="bg-white/80 rounded-lg p-2 border border-slate-200/60 shadow-2xs"
            >
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                {item.label}
              </span>
              <div className="mt-0.5 text-xs font-mono font-medium text-slate-800 truncate">
                {item.value}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// Subcomponent 5: Top-Level WorkflowExecutionDialog
// ----------------------------------------------------------------------
interface WorkflowExecutionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  steps: WorkflowStep[];
  isComplete: boolean;
  isSuccess: boolean;
  result?: WorkflowResultData | null;
  onDone?: () => void;
}

export function WorkflowExecutionDialog({
  isOpen,
  onClose,
  title,
  description,
  steps,
  isComplete,
  isSuccess,
  result,
  onDone,
}: WorkflowExecutionDialogProps) {
  if (!isOpen) return null;

  const handleAction = () => {
    if (onDone) {
      onDone();
    } else {
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isComplete ? onClose : () => {}}
      title={title}
      description={description}
      maxWidth="md"
    >
      <div className="space-y-5 py-1">
        {/* Step progression timeline */}
        <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-100">
          <WorkflowStepTimeline steps={steps} />
        </div>

        {/* Real Outcome Result Card */}
        {isComplete && result && (
          <WorkflowResultSummary result={result} isSuccess={isSuccess} />
        )}

        {/* Dialog Actions */}
        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
          {isComplete ? (
            <Button
              variant={isSuccess ? "primary" : "secondary"}
              onClick={handleAction}
              className="min-w-[100px]"
            >
              {isSuccess ? "Done" : "Dismiss"}
            </Button>
          ) : (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <SpinnerIcon className="w-3.5 h-3.5 text-indigo-600 animate-spin motion-reduce:animate-none" />
              <span>Executing workflow operations...</span>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
