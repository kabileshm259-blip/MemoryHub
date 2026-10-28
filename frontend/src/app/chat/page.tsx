"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { api, ApiError } from "@/lib/api";
import { Project, CitationItem } from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  ChatIcon,
  SparklesIcon,
  SpinnerIcon,
  SendIcon,
  AlertCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CheckCircleIcon,
} from "@/components/ui/Icons";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: CitationItem[];
  confidence?: number;
  has_sufficient_evidence?: boolean;
  provider_mode?: string;
  isError?: boolean;
}

let messageCounter = 0;
function generateMessageId(prefix: string): string {
  messageCounter += 1;
  return `${prefix}-${Date.now()}-${messageCounter}`;
}

function getFormattedTime(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const DEMO_SUGGESTED_QUESTIONS = [
  {
    topic: "Payment & Auth",
    prompt: "What authentication or payment gateway changes were recorded in the project?",
  },
  {
    topic: "Redis Flash-Sale Issue",
    prompt: "What Redis session-cache issue was documented under flash-sale traffic?",
  },
  {
    topic: "Deadlock in ECOM-103",
    prompt: "What inventory reservation deadlock was reported in ECOM-103?",
  },
  {
    topic: "Operational Continuity",
    prompt: "What operational risks should the successor review before a checkout release?",
  },
];

export default function ChatPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);

  // Chat message history scoped per project
  const [projectChats, setProjectChats] = useState<Record<string, ChatMessage[]>>({});
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [expandedCitationIds, setExpandedCitationIds] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load accessible projects on mount
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
      .catch(() => {
        setIsLoadingProjects(false);
      });
  }, []);

  const currentMessages = useMemo(
    () => (selectedProjectId ? projectChats[selectedProjectId] || [] : []),
    [selectedProjectId, projectChats]
  );
  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages, isSending, scrollToBottom]);

  const toggleCitation = (citationKey: string) => {
    setExpandedCitationIds((prev) => ({
      ...prev,
      [citationKey]: !prev[citationKey],
    }));
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend ?? inputMessage).trim();
    if (!text || !selectedProjectId || isSending) return;

    const userMessage: ChatMessage = {
      id: generateMessageId("user"),
      role: "user",
      content: text,
      timestamp: getFormattedTime(),
    };

    // Append user message immediately
    setProjectChats((prev) => ({
      ...prev,
      [selectedProjectId]: [...(prev[selectedProjectId] || []), userMessage],
    }));
    setInputMessage("");
    setIsSending(true);

    try {
      const res = await api.askQuestion(selectedProjectId, {
        question: text,
        top_k: 3,
      });

      const assistantMessage: ChatMessage = {
        id: generateMessageId("asst"),
        role: "assistant",
        content: res.answer,
        timestamp: getFormattedTime(),
        citations: res.citations,
        confidence: res.confidence,
        has_sufficient_evidence: res.has_sufficient_evidence,
        provider_mode: res.provider_mode,
      };

      setProjectChats((prev) => ({
        ...prev,
        [selectedProjectId]: [...(prev[selectedProjectId] || []), assistantMessage],
      }));
    } catch (err: unknown) {
      const errMsg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Failed to communicate with knowledge assistant.";

      const errorMessage: ChatMessage = {
        id: generateMessageId("err"),
        role: "assistant",
        content: `Error: ${errMsg}`,
        timestamp: getFormattedTime(),
        isError: true,
      };

      setProjectChats((prev) => ({
        ...prev,
        [selectedProjectId]: [...(prev[selectedProjectId] || []), errorMessage],
      }));
    } finally {
      setIsSending(false);
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearHistory = () => {
    if (!selectedProjectId) return;
    setProjectChats((prev) => ({
      ...prev,
      [selectedProjectId]: [],
    }));
  };

  const getProviderBadge = (mode?: string) => {
    switch (mode) {
      case "gemini":
        return <Badge variant="primary">Gemini 2.5 Flash</Badge>;
      case "heuristic_fallback":
        return <Badge variant="warning">Fallback (Heuristic)</Badge>;
      case "heuristic":
      default:
        return <Badge variant="neutral">Heuristic Engine</Badge>;
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-[calc(100vh-5rem)] max-w-6xl mx-auto space-y-4">
        {/* Top Control Bar */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <SparklesIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-900 tracking-tight">
                  AI Knowledge Assistant
                </h1>
                <span className="hidden sm:inline-flex">
                  <Badge variant="primary" size="sm">RAG Grounded</Badge>
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Evidence-grounded question answering across ingested tickets, runbooks, and incident notes
              </p>
            </div>
          </div>

          {/* Project Selector & Actions */}
          <div className="flex items-center gap-2 self-end sm:self-auto">
            <div className="flex items-center gap-1.5">
              <label htmlFor="chat-project-select" className="text-xs font-semibold text-slate-600 shrink-0">
                Project:
              </label>
              <select
                id="chat-project-select"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                disabled={isLoadingProjects || projects.length === 0}
                className="text-xs py-1.5 px-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-100 max-w-[200px] truncate"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {currentMessages.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleClearHistory}
                className="text-xs"
              >
                Clear
              </Button>
            )}
          </div>
        </div>

        {/* Chat Stream Window */}
        <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-y-auto p-4 sm:p-6 space-y-5">
          {currentMessages.length === 0 ? (
            /* Empty State & Prompt Suggestions */
            <div className="h-full flex flex-col justify-center items-center text-center max-w-xl mx-auto py-8">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
                <ChatIcon className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900">
                Explore Knowledge in {selectedProject?.name || "Workspace"}
              </h2>
              <p className="text-xs text-slate-500 mt-1 max-w-md leading-relaxed">
                Ask specific questions about system architecture, past incidents, dependencies, or handoff tasks. Every answer is grounded with verifiable source citations.
              </p>

              {/* Grounded Suggested Prompts */}
              <div className="mt-6 w-full text-left space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 text-center">
                  Suggested Questions for Demonstration
                </p>
                <div className="grid grid-cols-1 gap-2 pt-1">
                  {DEMO_SUGGESTED_QUESTIONS.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSendMessage(item.prompt)}
                      className="group flex items-start justify-between gap-3 p-3 text-left rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 transition-all text-xs cursor-pointer shadow-2xs"
                    >
                      <div>
                        <span className="font-semibold text-indigo-700 block text-[11px]">
                          {item.topic}
                        </span>
                        <span className="text-slate-700 group-hover:text-slate-900">
                          {item.prompt}
                        </span>
                      </div>
                      <ChevronRightIcon className="w-4 h-4 text-slate-300 group-hover:text-indigo-600 shrink-0 mt-1 transition-transform group-hover:translate-x-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Message Thread */
            <>
              {currentMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {/* Assistant Avatar */}
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-1">
                      <SparklesIcon className="w-4 h-4" />
                    </div>
                  )}

                  {/* Message Bubble Container */}
                  <div
                    className={`max-w-[85%] sm:max-w-2xl space-y-2 ${
                      msg.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    {/* Header info (Provider badge, timestamp) */}
                    <div
                      className={`flex items-center gap-2 text-[11px] text-slate-400 ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {msg.role === "assistant" && !msg.isError && (
                        <>
                          {getProviderBadge(msg.provider_mode)}
                          {msg.confidence != null && (
                            <span className="font-mono text-slate-500">
                              Confidence: {Math.round(msg.confidence * 100)}%
                            </span>
                          )}
                        </>
                      )}
                      <span>{msg.timestamp}</span>
                    </div>

                    {/* Content Box */}
                    <div
                      className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap ${
                        msg.role === "user"
                          ? "bg-indigo-600 text-white rounded-tr-xs shadow-xs"
                          : msg.isError
                          ? "bg-rose-50 text-rose-900 border border-rose-200 rounded-tl-xs"
                          : "bg-slate-50 text-slate-800 border border-slate-200/80 rounded-tl-xs"
                      }`}
                    >
                      {msg.content}
                    </div>

                    {/* Honest Abstention Alert */}
                    {msg.role === "assistant" &&
                      msg.has_sufficient_evidence === false && (
                        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs">
                          <AlertCircleIcon className="w-4 h-4 text-amber-600 shrink-0" />
                          <span>
                            <strong>Insufficient Evidence:</strong> No indexed project sources met the confidence threshold. The model declined to fabricate an answer.
                          </span>
                        </div>
                      )}

                    {/* Verified Citations List */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-1 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                          <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Verified Citations ({msg.citations.length})</span>
                        </div>

                        <div className="space-y-1.5">
                          {msg.citations.map((cite, cIdx) => {
                            const citationKey = `${msg.id}-cite-${cIdx}`;
                            const isExpanded = !!expandedCitationIds[citationKey];
                            return (
                              <div
                                key={cIdx}
                                className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs transition-all hover:border-slate-300"
                              >
                                <button
                                  type="button"
                                  onClick={() => toggleCitation(citationKey)}
                                  className="w-full flex items-center justify-between text-left font-medium text-slate-800 hover:text-indigo-600 gap-2 cursor-pointer"
                                >
                                  <div className="flex items-center gap-2 truncate">
                                    <Badge variant="neutral" size="sm">
                                      {cite.provider_type?.toUpperCase() || "SOURCE"}
                                    </Badge>
                                    <span className="truncate font-semibold">
                                      {cite.title || `Source ${cite.source_id.slice(0, 8)}`}
                                    </span>
                                  </div>

                                  <div className="flex items-center gap-2 shrink-0">
                                    {cite.score != null && (
                                      <span className="text-[10px] text-slate-400 font-mono">
                                        Relevance: {(cite.score * 100).toFixed(0)}%
                                      </span>
                                    )}
                                    {isExpanded ? (
                                      <ChevronDownIcon className="w-3.5 h-3.5 text-slate-400" />
                                    ) : (
                                      <ChevronRightIcon className="w-3.5 h-3.5 text-slate-400" />
                                    )}
                                  </div>
                                </button>

                                {isExpanded && (
                                  <div className="mt-2 pt-2 border-t border-slate-200/70 text-slate-600 font-mono text-[11px] leading-relaxed bg-white p-2 rounded-lg border border-slate-100">
                                    {cite.snippet}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Typing / Processing Indicator */}
              {isSending && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                    <SparklesIcon className="w-4 h-4" />
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-xs p-3.5 flex items-center gap-2 text-xs text-slate-500 shadow-2xs">
                    <SpinnerIcon className="w-4 h-4 text-indigo-600 animate-spin motion-reduce:animate-none" />
                    <span>Querying vector store and synthesizing evidence...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Message Input Composer */}
        <div className="bg-white rounded-2xl border border-slate-200 p-3 shadow-2xs shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-end gap-2"
          >
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about architecture, incidents, or handoff tasks in this project... (Enter to send, Shift+Enter for newline)"
                rows={2}
                disabled={isSending || !selectedProjectId}
                className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50/50 p-2.5 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              disabled={isSending || !inputMessage.trim() || !selectedProjectId}
              className="h-10 px-4 rounded-xl shrink-0"
            >
              {isSending ? (
                <SpinnerIcon className="w-4 h-4 animate-spin motion-reduce:animate-none" />
              ) : (
                <SendIcon className="w-4 h-4" />
              )}
            </Button>
          </form>

          <div className="flex items-center justify-between px-1 pt-2 text-[11px] text-slate-400">
            <span>Evidence Grounded Knowledge Retrieval</span>
            <span>Enter to Send &bull; Shift+Enter for Newline</span>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
