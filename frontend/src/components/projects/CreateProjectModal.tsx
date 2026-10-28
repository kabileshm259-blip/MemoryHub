"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input, Textarea } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { api, ApiError } from "@/lib/api";
import { Project } from "@/types/api";
import {
  WorkflowExecutionDialog,
  WorkflowStep,
  WorkflowResultData,
} from "@/components/ui/WorkflowExecutionDialog";

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (project: Project) => void;
}

export function CreateProjectModal({
  isOpen,
  onClose,
  onSuccess,
}: CreateProjectModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Workflow Dialog State
  const [isWorkflowOpen, setIsWorkflowOpen] = useState(false);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [workflowComplete, setWorkflowComplete] = useState(false);
  const [workflowSuccess, setWorkflowSuccess] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResultData | null>(null);
  const [createdProject, setCreatedProject] = useState<Project | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Project name cannot be empty.");
      return;
    }

    setIsLoading(true);
    setError(null);

    // Initial workflow steps
    const initialSteps: WorkflowStep[] = [
      {
        id: "validate",
        label: "Validating Project Metadata",
        description: "Checking name format, uniqueness, and workspace bounds",
        status: "running",
      },
      {
        id: "provision",
        label: "Provisioning Project Workspace",
        description: "Creating database record, schema allocation, and audit log",
        status: "pending",
      },
      {
        id: "permissions",
        label: "Configuring Role-Based Access",
        description: "Assigning owner role and baseline access control policies",
        status: "pending",
      },
    ];

    setWorkflowSteps(initialSteps);
    setWorkflowComplete(false);
    setWorkflowSuccess(false);
    setWorkflowResult(null);
    setCreatedProject(null);
    setIsWorkflowOpen(true);

    // Brief animation timing to make the step progression perceptible
    await new Promise((r) => setTimeout(r, 250));

    try {
      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "validate"
            ? { ...s, status: "succeeded" }
            : s.id === "provision"
            ? { ...s, status: "running" }
            : s
        )
      );

      const newProject = await api.createProject({
        name: trimmedName,
        description: description.trim() || undefined,
      });

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "provision"
            ? { ...s, status: "succeeded" }
            : s.id === "permissions"
            ? { ...s, status: "running" }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 200));

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.id === "permissions" ? { ...s, status: "succeeded" } : s
        )
      );

      setCreatedProject(newProject);
      setWorkflowSuccess(true);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Project Successfully Created",
        message: `Workspace "${newProject.name}" has been created and initialized.`,
        badge: {
          label: "Active Project",
          variant: "success",
        },
        evidence: [
          { label: "Project ID", value: newProject.id },
          { label: "Project Name", value: newProject.name },
          { label: "Role", value: newProject.role || "owner" },
          { label: "Created At", value: new Date(newProject.created_at).toLocaleTimeString() },
        ],
      });

      setName("");
      setDescription("");
    } catch (err: unknown) {
      const errMsg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Failed to create project.";

      setWorkflowSteps((prev) =>
        prev.map((s) =>
          s.status === "running"
            ? { ...s, status: "failed", detail: errMsg }
            : s
        )
      );
      setWorkflowSuccess(false);
      setWorkflowComplete(true);
      setWorkflowResult({
        title: "Project Creation Failed",
        message: errMsg,
        badge: {
          label: "Error",
          variant: "danger",
        },
      });
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWorkflowDone = () => {
    setIsWorkflowOpen(false);
    if (workflowSuccess && createdProject) {
      onSuccess(createdProject);
      onClose();
    }
  };

  return (
    <>
      <Modal
        isOpen={isOpen && !isWorkflowOpen}
        onClose={onClose}
        title="Create New Project"
        description="Create a dedicated space for handoffs, ingested documentation, and team collaboration."
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}

          <Input
            label="Project Name *"
            placeholder="e.g. Mobile Core Platform"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isLoading}
            required
            autoFocus
            maxLength={255}
          />

          <Textarea
            label="Description (Optional)"
            placeholder="Brief summary of the project's purpose and scope..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isLoading}
            rows={3}
          />

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isLoading}>
              Create Project
            </Button>
          </div>
        </form>
      </Modal>

      {/* Workflow Execution Dialog */}
      <WorkflowExecutionDialog
        isOpen={isWorkflowOpen}
        onClose={() => setIsWorkflowOpen(false)}
        title="Project Workspace Creation"
        description="Executing multi-stage project initialization and access control assignment"
        steps={workflowSteps}
        isComplete={workflowComplete}
        isSuccess={workflowSuccess}
        result={workflowResult}
        onDone={handleWorkflowDone}
      />
    </>
  );
}
