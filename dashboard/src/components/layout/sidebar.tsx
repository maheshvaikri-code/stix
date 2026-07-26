"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CheckCircle,
  ClipboardList,
  Command,
  Database,
  ExternalLink,
  FileText,
  GitBranch,
  HelpCircle,
  LayoutDashboard,
  Network,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { useApprovals, useDashboardOperator } from "@/lib/hooks";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Policies", href: "/policies", icon: FileText },
  { name: "Governance", href: "/governance", icon: ClipboardList },
  { name: "Fabric", href: "/fabric", icon: Network },
  { name: "Doctrine Ops", href: "/doctrine", icon: Command },
  { name: "Evidence", href: "/evidence", icon: Database },
  { name: "Approvals", href: "/approvals", icon: CheckCircle, badge: true },
  { name: "GitLab", href: "/gitlab", icon: GitBranch },
  { name: "Settings", href: "/settings", icon: Settings },
];

const resources = [
  { name: "Documentation", href: "https://stix.dev/docs", external: true },
  { name: "API Reference", href: "https://stix.dev/api", external: true },
  { name: "Support", href: "https://stix.dev/support", external: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: pendingData } = useApprovals({
    status: "PENDING",
    page_size: 1,
  });
  const operator = useDashboardOperator();
  const pendingCount = pendingData?.total || 0;

  return (
    <>
      <aside className="fixed inset-y-4 left-4 z-30 hidden w-64 flex-col overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/92 text-white shadow-2xl shadow-slate-900/30 backdrop-blur-xl lg:flex">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-16 -top-16 h-44 w-44 rounded-full bg-cyan-400/30 blur-3xl" />
          <div className="absolute bottom-20 right-0 h-36 w-36 rounded-full bg-emerald-400/20 blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.055)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.055)_1px,transparent_1px)] bg-[size:24px_24px]" />
        </div>

        <div className="relative border-b border-white/10 px-5 py-6">
          <div className="rounded-3xl border border-white/10 bg-white px-3 py-4 shadow-glow">
            <Image
              src="/images/logo-wordmark.png"
              alt="STIX"
              width={220}
              height={56}
              className="object-contain"
              priority
            />
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-2xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs text-cyan-100">
            <ShieldCheck className="h-4 w-4 text-cyan-200" />
            Core enforces. Fabric governs.
          </div>
        </div>

        <nav className="relative flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <p className="px-3 text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">
            Command
          </p>
          {navigation.map((item) => {
            const isActive = isActiveRoute(pathname, item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`
                  group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold
                  transition-all duration-200
                  ${
                    isActive
                      ? "bg-white text-slate-950 shadow-lg shadow-cyan-950/20"
                      : "text-slate-400 hover:bg-white/10 hover:text-white"
                  }
                `}
              >
                <span
                  className={`rounded-xl p-2 transition-colors ${
                    isActive
                      ? "bg-cyan-50 text-cyan-700"
                      : "bg-white/5 text-slate-400 group-hover:text-cyan-200"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span className="flex-1">{item.name}</span>
                {item.badge && pendingCount > 0 && (
                  <span className="rounded-full bg-amber-300 px-2 py-0.5 text-xs font-bold text-amber-950">
                    {pendingCount}
                  </span>
                )}
              </Link>
            );
          })}

          <div className="pt-6">
            <p className="px-3 text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">
              Resources
            </p>
            {resources.map((item) => (
              <a
                key={item.name}
                href={item.href}
                target={item.external ? "_blank" : undefined}
                rel={item.external ? "noopener noreferrer" : undefined}
                className="flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              >
                <HelpCircle className="h-4 w-4" />
                <span className="flex-1">{item.name}</span>
                {item.external && <ExternalLink className="h-4 w-4" />}
              </a>
            ))}
          </div>
        </nav>

        <div className="relative border-t border-white/10 p-4">
          <div className="rounded-3xl border border-white/10 bg-white/[0.08] p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
              Signed In
            </p>
            <div className="mt-3 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-300 to-emerald-300 text-sm font-bold text-slate-950">
                A
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-white">
                  {operator.id}
                </p>
                <p className="truncate text-xs text-slate-400">
                  {operator.role}
                </p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <nav className="fixed inset-x-3 bottom-3 z-40 flex gap-2 overflow-x-auto rounded-3xl border border-white/70 bg-slate-950/92 p-2 shadow-2xl shadow-slate-900/25 backdrop-blur-xl lg:hidden">
        {navigation.map((item) => {
          const isActive = isActiveRoute(pathname, item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              aria-label={item.name}
              className={`relative flex min-w-14 flex-col items-center gap-1 rounded-2xl px-3 py-2 text-[10px] font-semibold transition-colors ${
                isActive
                  ? "bg-white text-slate-950"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.name}</span>
              {item.badge && pendingCount > 0 && (
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-amber-300" />
              )}
            </Link>
          );
        })}
      </nav>
    </>
  );
}

function isActiveRoute(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(href));
}
