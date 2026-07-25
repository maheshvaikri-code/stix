"use client";

import { motion } from "motion/react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Command,
  FileCheck2,
  GitBranch,
  Network,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useFabricInventory } from "@/lib/hooks";
import type { FabricInventory } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

const gates = [
  { id: "G0", label: "Intake", owner: "Product", state: "Ready" },
  { id: "G1", label: "Architecture", owner: "Chief Architect", state: "Ready" },
  { id: "G2", label: "Plan", owner: "Architect", state: "Ready" },
  { id: "G3", label: "Build", owner: "Engineering", state: "Active" },
  { id: "G4", label: "Review", owner: "Code Review", state: "Guarded" },
  { id: "G5", label: "Verify", owner: "QA + Security", state: "Guarded" },
  { id: "G6", label: "Release", owner: "Release", state: "Blocked until green" },
  { id: "G7", label: "Retro", owner: "Project Review", state: "Required" },
];

export default function DoctrinePage() {
  const { data, isLoading, error, refetch, isFetching } = useFabricInventory();
  const doctrine = data ? getDoctrineInventory(data) : null;

  return (
    <div className="relative z-10 min-h-screen space-y-6 p-4 sm:p-6">
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-slate-950 p-6 text-white shadow-2xl shadow-slate-300/50 sm:p-8"
      >
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-amber-300/25 blur-3xl" />
          <div className="absolute right-10 top-10 h-56 w-56 rounded-full bg-cyan-300/25 blur-3xl" />
          <div className="absolute bottom-0 left-1/2 h-52 w-52 rounded-full bg-emerald-300/20 blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.07)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.07)_1px,transparent_1px)] bg-[size:28px_28px]" />
        </div>

        <div className="relative grid gap-8 lg:grid-cols-[1fr_420px]">
          <div>
            <Badge variant="warning">Doctrine engaged</Badge>
            <h1 className="mt-5 max-w-3xl text-3xl font-bold tracking-tight sm:text-4xl">
              Engineering gates governed as Fabric runtime.
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
              Doctrine supplies the operating loop. STIX Fabric registers it as
              an agent runtime, enforcement point, and policy channel so release
              actions can be authorized, evidenced, and reviewed with the same
              control plane as any autonomous agent.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                onClick={() => refetch()}
                loading={isFetching}
                className="border-white/10 bg-white/10 text-white hover:bg-white/20"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh Doctrine Wiring
              </Button>
              <span className="flex items-center gap-2 text-sm text-slate-300">
                <Sparkles className="h-4 w-4 text-amber-200" />
                Registry-level integration
              </span>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/10 p-5 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-amber-100">
              Gate posture
            </p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {gates.map((gate) => (
                <div
                  key={gate.id}
                  className="rounded-2xl border border-white/10 bg-slate-950/50 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-amber-100">
                      {gate.id}
                    </span>
                    <CheckCircle className="h-3.5 w-3.5 text-emerald-200" />
                  </div>
                  <p className="mt-2 text-sm font-semibold">{gate.label}</p>
                  <p className="text-xs text-slate-400">{gate.owner}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.section>

      {isLoading ? (
        <div className="py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <Card className="border-red-200 bg-red-50">
          <EmptyState
            icon={<AlertTriangle className="h-12 w-12 text-red-400" />}
            title="Fabric API is not reachable"
            description={
              error instanceof Error
                ? error.message
                : "Start services/fabric, seed the registry, and refresh this page."
            }
          />
        </Card>
      ) : doctrine ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <DoctrineMetric
              label="Doctrine Agents"
              value={doctrine.agents.length}
              icon={<Command className="h-5 w-5" />}
              tone="amber"
            />
            <DoctrineMetric
              label="Gatekeepers"
              value={doctrine.enforcementPoints.length}
              icon={<ShieldCheck className="h-5 w-5" />}
              tone="cyan"
            />
            <DoctrineMetric
              label="Governed Actions"
              value={doctrine.actions.length}
              icon={<Workflow className="h-5 w-5" />}
              tone="emerald"
            />
            <DoctrineMetric
              label="Release Channels"
              value={doctrine.channels.length}
              icon={<GitBranch className="h-5 w-5" />}
              tone="blue"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
            <Card className="border-0 bg-slate-950 text-white shadow-xl shadow-slate-300/40">
              <CardHeader
                title="Doctrine Fabric Wiring"
                description="Live records discovered through the Fabric registry"
              />
              <div className="grid gap-3 md:grid-cols-2">
                {doctrine.actions.map((action) => (
                  <div
                    key={action.action_id}
                    className="rounded-2xl border border-white/10 bg-white/10 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-white">
                          {action.display_name}
                        </p>
                        <p className="mt-1 font-mono text-xs text-slate-400">
                          {action.action}
                        </p>
                      </div>
                      <Badge
                        variant={
                          action.risk_tier === "HIGH" ||
                          action.risk_tier === "CRITICAL"
                            ? "warning"
                            : "info"
                        }
                        size="sm"
                      >
                        {action.risk_tier}
                      </Badge>
                    </div>
                    <p className="mt-3 text-xs text-slate-400">
                      Resource: {action.resource_type}
                    </p>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="bg-white/90">
              <CardHeader
                title="Safe Boundary"
                description="What is wired now versus next"
              />
              <div className="space-y-3">
                <BoundaryItem
                  icon={<Network className="h-4 w-4" />}
                  title="Wired now"
                  text="Doctrine is visible as Fabric inventory and graph data."
                />
                <BoundaryItem
                  icon={<Activity className="h-4 w-4" />}
                  title="Next adapter"
                  text="Expose read-only Doctrine gate and state-plane summaries."
                />
                <BoundaryItem
                  icon={<FileCheck2 className="h-4 w-4" />}
                  title="Later enforcement"
                  text="Wrap checkpoint and release actions with STIX authorization."
                />
              </div>
            </Card>
          </div>
        </>
      ) : (
        <Card className="border-dashed border-slate-300 bg-white/80">
          <EmptyState
            icon={<Command className="h-12 w-12" />}
            title="Doctrine is not registered in Fabric yet"
            description="Run pnpm demo:fabric:seed or register Doctrine records through the Fabric API to light up this page."
          />
        </Card>
      )}
    </div>
  );
}

function DoctrineMetric({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: "amber" | "cyan" | "emerald" | "blue";
}) {
  const styles = {
    amber: "from-amber-50 to-orange-50 text-amber-700 ring-amber-100",
    cyan: "from-cyan-50 to-sky-50 text-cyan-700 ring-cyan-100",
    emerald: "from-emerald-50 to-teal-50 text-emerald-700 ring-emerald-100",
    blue: "from-blue-50 to-indigo-50 text-blue-700 ring-blue-100",
  };

  return (
    <Card className="overflow-hidden border-0 bg-white/90 shadow-lg shadow-slate-200/70">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-950">
            {value.toLocaleString()}
          </p>
        </div>
        <div className={`rounded-2xl bg-gradient-to-br p-3 ring-1 ${styles[tone]}`}>
          {icon}
        </div>
      </div>
    </Card>
  );
}

function BoundaryItem({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-white p-2 text-slate-700 shadow-sm">
          {icon}
        </div>
        <div>
          <p className="font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-sm text-slate-500">{text}</p>
        </div>
      </div>
    </div>
  );
}

function getDoctrineInventory(data: FabricInventory) {
  const agents = data.agents.data.filter((agent) =>
    [agent.agent_id, agent.runtime, ...agent.labels].some((value) =>
      value.toLowerCase().includes("doctrine"),
    ),
  );
  const enforcementPoints = data.enforcementPoints.data.filter((point) =>
    [point.enforcement_point_id, point.display_name]
      .join(" ")
      .toLowerCase()
      .includes("doctrine"),
  );
  const actions = data.toolActions.data.filter((action) =>
    [action.action_id, action.action, action.display_name]
      .join(" ")
      .toLowerCase()
      .includes("doctrine"),
  );
  const channels = data.policyChannels.data.filter((channel) =>
    [channel.channel_id, channel.display_name]
      .join(" ")
      .toLowerCase()
      .includes("doctrine"),
  );

  if (
    !agents.length &&
    !enforcementPoints.length &&
    !actions.length &&
    !channels.length
  ) {
    return null;
  }

  return {
    agents,
    enforcementPoints,
    actions,
    channels,
  };
}
