"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { api, ApiError } from "@/lib/api";
import { ProjectMember, ProjectRole } from "@/types/api";

interface AddMemberModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (member: ProjectMember) => void;
}

export function AddMemberModal({
  projectId,
  isOpen,
  onClose,
  onSuccess,
}: AddMemberModalProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>("viewer");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setError("Please enter a valid user email address.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const newMember = await api.addMember(projectId, {
        email: cleanEmail,
        role,
      });
      setEmail("");
      setRole("viewer");
      onSuccess(newMember);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to add project member. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Project Member"
      description="Invite an existing registered user to collaborate on this project."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        <Input
          label="User Email Address *"
          type="email"
          placeholder="colleague@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isLoading}
          required
          autoFocus
        />

        <div className="w-full flex flex-col gap-1.5">
          <label
            htmlFor="member-role-select"
            className="text-xs font-semibold text-slate-700 tracking-wide uppercase"
          >
            Project Role *
          </label>
          <select
            id="member-role-select"
            value={role}
            onChange={(e) => setRole(e.target.value as ProjectRole)}
            disabled={isLoading}
            className="w-full px-3.5 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-600"
          >
            <option value="viewer">Viewer (Read-only project and members)</option>
            <option value="editor">Editor (Collaborator)</option>
            <option value="owner">Owner (Full admin and membership control)</option>
          </select>
          <p className="text-xs text-slate-500">
            Owners can modify settings and invite others. Viewers and editors cannot change project settings.
          </p>
        </div>

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
            Add Member
          </Button>
        </div>
      </form>
    </Modal>
  );
}
