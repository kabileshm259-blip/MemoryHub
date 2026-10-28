"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/Button";
import { LogoIcon, ProjectsIcon, HandoffsIcon, SourcesIcon } from "@/components/ui/Icons";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/dashboard");
    }
  }, [user, isLoading, router]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Navigation Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-xs">
              <LogoIcon className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-lg tracking-tight">
                MemoryHub
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="secondary" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="primary" size="sm">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-16 md:py-24 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold mb-6">
          <span>Phase 3</span>
          <span className="text-indigo-400">•</span>
          <span>Core Project & Auth Foundation</span>
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-950 tracking-tight leading-tight max-w-3xl">
          Continuous Team Memory & Smooth Developer Handoffs
        </h1>

        <p className="mt-5 text-base md:text-lg text-slate-600 max-w-2xl leading-relaxed">
          MemoryHub brings together project knowledge, team handoffs, and external records into a unified, searchable hub backed by PostgreSQL and ChromaDB.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Link href="/register">
            <Button size="lg" className="w-full sm:w-auto">
              Create Free Account
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary" size="lg" className="w-full sm:w-auto">
              Sign In to Existing Workspace
            </Button>
          </Link>
        </div>

        {/* Feature Cards Grid */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left">
          <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-xs">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl w-fit mb-4">
              <ProjectsIcon className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1.5">
              Role-Governed Projects
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Create isolated workspaces with strictly enforced owner, editor, and viewer permissions to ensure project security.
            </p>
          </div>

          <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-xs">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl w-fit mb-4">
              <HandoffsIcon className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1.5">
              Structured Handoffs
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Eliminate context loss between engineers with draftable, reviewable, and acknowledged handover briefs.
            </p>
          </div>

          <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-xs">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl w-fit mb-4">
              <SourcesIcon className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 text-base mb-1.5">
              Knowledge Ingestion
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Connect Jira issues, Slack threads, and commits into an indexed vector graph for unified search.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p>© 2026 MemoryHub Platform. Academic & Enterprise Demo.</p>
          <div className="flex items-center gap-4">
            <span className="font-mono">FastAPI • Next.js • PostgreSQL • ChromaDB</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
