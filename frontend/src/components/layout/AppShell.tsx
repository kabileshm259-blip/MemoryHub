"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { api } from "@/lib/api";
import {
  BellIcon,
  CloseIcon,
  DashboardIcon,
  HandoffsIcon,
  IntegrationsIcon,
  LogoIcon,
  LogoutIcon,
  MenuIcon,
  ProjectsIcon,
  SourcesIcon,
} from "@/components/ui/Icons";
import { HealthResponse, Notification } from "@/types/api";

interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  isComingSoon?: boolean;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout, isLoading } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<"checking" | "online" | "offline">("checking");
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function checkBackend() {
      try {
        const res = await api.checkReadiness();
        if (isMounted) {
          setHealth(res);
          setHealthStatus(res.status === "ready" ? "online" : "offline");
        }
      } catch {
        if (isMounted) {
          setHealthStatus("offline");
        }
      }
    }
    checkBackend();
    const interval = setInterval(checkBackend, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    let isMounted = true;
    async function loadNotifications() {
      try {
        const res = await api.listNotifications(20);
        if (isMounted) {
          setNotifications(res.items);
          setUnreadCount(res.unread_count);
        }
      } catch {
        // Notification fetch fallback
      }
    }
    loadNotifications();
    const interval = setInterval(loadNotifications, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [user]);

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  };

  const handleMarkOneRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // ignore
    }
  };

  const navItems: NavItem[] = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: <DashboardIcon className="w-5 h-5" />,
    },
    {
      name: "Projects",
      href: "/projects",
      icon: <ProjectsIcon className="w-5 h-5" />,
    },
    {
      name: "Handoffs",
      href: "/handoffs",
      icon: <HandoffsIcon className="w-5 h-5" />,
    },
    {
      name: "Knowledge Sources",
      href: "/sources",
      icon: <SourcesIcon className="w-5 h-5" />,
    },
    {
      name: "Integrations",
      href: "/integrations",
      icon: <IntegrationsIcon className="w-5 h-5" />,
    },
  ];

  const getInitials = (name?: string) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((part) => part[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row text-slate-900 font-sans antialiased">
      {/* Mobile Top Bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-indigo-600 text-white rounded-lg">
            <LogoIcon className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-slate-900 tracking-tight text-base">
              MemoryHub
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {user && (
            <button
              onClick={() => setIsNotificationsOpen((prev) => !prev)}
              aria-label="View notifications"
              className="relative p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              <BellIcon className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-rose-500 text-[8px] font-bold text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>
          )}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            className="p-2 rounded-lg text-slate-600 hover:bg-slate-100"
          >
            {mobileMenuOpen ? <CloseIcon className="w-6 h-6" /> : <MenuIcon className="w-6 h-6" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu Backdrop */}
      {mobileMenuOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-slate-900/40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200 flex flex-col justify-between transition-transform duration-200 ease-in-out md:translate-x-0 ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col flex-1">
          {/* Brand Header */}
          <div className="p-5 border-b border-slate-100 flex items-center gap-3">
            <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-xs">
              <LogoIcon className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-slate-950 text-base tracking-tight leading-tight">
                MemoryHub
              </h1>
              <p className="text-xs text-slate-500 font-medium">
                Knowledge & Handover Hub
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1 flex-1 overflow-y-auto" aria-label="Main Navigation">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700 font-semibold"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={isActive ? "text-indigo-600" : "text-slate-400"}>
                      {item.icon}
                    </span>
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-slate-100 text-slate-500 border border-slate-200">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* System Status Indicator */}
          <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span
                    className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                      healthStatus === "online"
                        ? "bg-emerald-400"
                        : healthStatus === "checking"
                        ? "bg-amber-400"
                        : "bg-rose-400"
                    }`}
                  />
                  <span
                    className={`relative inline-flex rounded-full h-2 w-2 ${
                      healthStatus === "online"
                        ? "bg-emerald-500"
                        : healthStatus === "checking"
                        ? "bg-amber-500"
                        : "bg-rose-500"
                    }`}
                  />
                </span>
                <span className="text-xs font-medium text-slate-600">
                  {healthStatus === "online"
                    ? "API Connected"
                    : healthStatus === "checking"
                    ? "Connecting..."
                    : "Backend Offline"}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">v0.1.0</span>
            </div>
            {healthStatus === "online" && health && (
              <p className="text-[10px] text-slate-400 mt-1">
                PostgreSQL: {health.postgres} • ChromaDB: {health.chroma}
              </p>
            )}
          </div>
        </div>

        {/* User Profile / Logout Area */}
        <div className="p-3 border-t border-slate-200 bg-white">
          {isLoading ? (
            <div className="flex items-center gap-3 p-2 animate-pulse">
              <div className="w-9 h-9 rounded-full bg-slate-200" />
              <div className="flex-1 space-y-1">
                <div className="h-3.5 bg-slate-200 rounded w-24" />
                <div className="h-2.5 bg-slate-200 rounded w-32" />
              </div>
            </div>
          ) : user ? (
            <div className="flex items-center justify-between gap-2 p-1.5 rounded-lg">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs shrink-0 border border-indigo-200">
                  {getInitials(user.display_name)}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-900 truncate">
                    {user.display_name}
                  </p>
                  <p className="text-[11px] text-slate-500 truncate">{user.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => setIsNotificationsOpen((prev) => !prev)}
                  title="Notifications"
                  aria-label="View notifications"
                  className="relative p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                >
                  <BellIcon className="w-4 h-4" />
                  {unreadCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-rose-500 text-[8px] font-bold text-white shadow-xs">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  )}
                </button>
                <button
                  onClick={logout}
                  title="Log out"
                  aria-label="Log out of account"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                >
                  <LogoutIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center justify-center w-full px-3 py-2 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
            >
              Sign In
            </Link>
          )}
        </div>
      </aside>

      {/* Main Page Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">{children}</div>
      </main>

      {/* Notifications Drawer */}
      {isNotificationsOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
            onClick={() => setIsNotificationsOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-sm bg-white shadow-2xl flex flex-col">
              <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg">
                    <BellIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-900">Notifications</h2>
                    <p className="text-[11px] text-slate-500">
                      {unreadCount} unread update{unreadCount === 1 ? "" : "s"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                    >
                      Mark all read
                    </button>
                  )}
                  <button
                    onClick={() => setIsNotificationsOpen(false)}
                    aria-label="Close notifications"
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                  >
                    <CloseIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {notifications.length === 0 ? (
                  <div className="py-12 text-center text-xs text-slate-400">
                    No notifications yet.
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => !n.is_read && handleMarkOneRead(n.id)}
                      className={`p-3 rounded-xl border text-xs transition-all cursor-pointer ${
                        n.is_read
                          ? "bg-white border-slate-200 text-slate-600"
                          : "bg-indigo-50/60 border-indigo-200 text-slate-900 shadow-xs"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-semibold text-slate-900 leading-snug">
                          {n.title}
                        </span>
                        {!n.is_read && (
                          <span className="shrink-0 w-2 h-2 rounded-full bg-indigo-600 mt-1" />
                        )}
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        {n.message}
                      </p>
                      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-100/80 text-[10px] text-slate-400">
                        <span className="uppercase font-mono tracking-wider font-semibold text-slate-500">
                          {n.notification_type}
                        </span>
                        <span>{new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
