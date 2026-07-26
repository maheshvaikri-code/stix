"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Activity,
  AlertTriangle,
  Boxes,
  CheckCircle,
  CircuitBoard,
  Clock,
  Database,
  GitBranch,
  Layers,
  Network,
  Plus,
  Radar,
  RefreshCw,
  Route,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Workflow,
} from "lucide-react";
import {
  useFabricInventory,
  useFabricReadiness,
  useRegisterFabricAgent,
  useRegisterFabricEnforcementPoint,
  useRegisterFabricPolicyChannel,
  useRegisterFabricToolAction,
} from "@/lib/hooks";
import type {
  FabricAgent,
  FabricEnforcementPoint,
  FabricGraphSummary,
  FabricInventory,
  FabricPolicyChannel,
  FabricToolAction,
} from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Modal, ModalFooter } from "@/components/ui/modal";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { TabPanel, Tabs } from "@/components/ui/tabs";
import { FabricOrbit } from "@/components/fabric/fabric-orbit";
import {
  buildFabricPosture,
  type FabricPosture,
  type FabricReadinessIssue,
} from "@/lib/fabric-readiness";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type FabricTab = "posture" | "inventory" | "graph";
type RegistrationKind = "agent" | "enforcement_point" | "tool_action" | "policy_channel";
type GraphNode = FabricGraphSummary["nodes"][number];
type GraphEdge = FabricGraphSummary["edges"][number];

const emptyStats = {
  agents: 0,
  enforcement_points: 0,
  tool_actions: 0,
  policy_channels: 0,
  active_agents: 0,
  active_enforcement_points: 0,
  critical_tool_actions: 0,
};

const nodeTypeLabels: Record<GraphNode["type"], string> = {
  agent: "Agent",
  enforcement_point: "Enforcement",
  tool_action: "Tool Action",
  policy_channel: "Policy Channel",
};

const relationLabels: Record<GraphEdge["relation"], string> = {
  protected_by: "protected by",
  can_execute: "can execute",
  governed_by: "governed by",
};

const motionTransition = { duration: 0.45, ease: "easeOut" as const };

export default function FabricPage() {
  const [activeTab, setActiveTab] = useState<FabricTab>("posture");
  const [registrationKind, setRegistrationKind] = useState<RegistrationKind>("agent");
  const [showRegistration, setShowRegistration] = useState(false);
  const { data, isLoading, error, refetch, isFetching } = useFabricInventory();
  const {
    data: readiness,
    refetch: refetchReadiness,
    isFetching: isReadinessFetching,
  } = useFabricReadiness();

  const stats = data?.stats ?? emptyStats;
  const hasInventory = Boolean(
    data &&
    (data.agents.total ||
      data.enforcementPoints.total ||
      data.toolActions.total ||
      data.policyChannels.total),
  );

  const posture = useMemo(
    () => readiness?.fabric ?? buildFabricPosture(data),
    [data, readiness?.fabric],
  );

  const refreshFabric = () => {
    void refetch();
    void refetchReadiness();
  };

  return (
    <div className="relative z-10 min-h-screen space-y-6 p-4 sm:p-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={motionTransition}
        className="relative overflow-hidden rounded-3xl border border-slate-200 bg-slate-950 text-white shadow-2xl shadow-slate-300/30"
      >
        <div className="absolute inset-0 opacity-40">
          <div className="absolute -left-16 -top-20 h-64 w-64 rounded-full bg-cyan-400 blur-3xl" />
          <div className="absolute right-6 top-8 h-40 w-40 rounded-full bg-emerald-300 blur-3xl" />
          <div className="absolute bottom-0 left-1/2 h-48 w-48 rounded-full bg-blue-500 blur-3xl" />
        </div>
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px)] bg-[size:28px_28px]" />
        <div className="relative grid gap-8 p-8 lg:grid-cols-[minmax(0,0.92fr)_minmax(360px,0.85fr)]">
          <div className="space-y-5">
            <Badge variant="info">STIX Fabric Control Plane</Badge>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                Agent Policy Fabric
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
                Inventory agents, enforcement points, tools, and rollout
                channels from one fabric view. Core still enforces; Fabric shows
                where governance is wired.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                onClick={refreshFabric}
                loading={isFetching || isReadinessFetching}
                className="bg-white/10 text-white hover:bg-white/20 focus:ring-cyan-400"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh Fabric
              </Button>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Clock className="h-4 w-4 text-cyan-300" />
                Auto-refresh every 60s
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <FabricOrbit
              agents={stats.agents}
              enforcementPoints={stats.enforcement_points}
              toolActions={stats.tool_actions}
              policyChannels={stats.policy_channels}
              postureScore={posture.score}
            />
            <FabricSignalPanel
              totalNodes={data?.graph.nodes.length ?? 0}
              totalEdges={data?.graph.edges.length ?? 0}
              postureScore={posture.score}
              postureLevel={posture.level}
            />
          </div>
        </div>
      </motion.div>

      {isLoading ? (
        <div className="py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <Card className="border-red-200 bg-red-50">
          <EmptyState
            icon={<Network className="h-12 w-12 text-red-400" />}
            title="Fabric API is not reachable"
            description={
              error instanceof Error
                ? error.message
                : "Start services/fabric on port 3005 and refresh this page."
            }
          />
        </Card>
      ) : (
        <>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...motionTransition, delay: 0.08 }}
            className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4"
          >
            <MetricCard
              title="Registered Agents"
              value={stats.agents}
              subtitle={`${stats.active_agents} active`}
              icon={<Radar className="h-5 w-5" />}
              accent="cyan"
            />
            <MetricCard
              title="Enforcement Points"
              value={stats.enforcement_points}
              subtitle={`${stats.active_enforcement_points} active guards`}
              icon={<ShieldCheck className="h-5 w-5" />}
              accent="emerald"
            />
            <MetricCard
              title="Tool Actions"
              value={stats.tool_actions}
              subtitle={`${stats.critical_tool_actions} critical actions`}
              icon={<TerminalSquare className="h-5 w-5" />}
              accent="amber"
            />
            <MetricCard
              title="Policy Channels"
              value={stats.policy_channels}
              subtitle="Rollout lanes"
              icon={<GitBranch className="h-5 w-5" />}
              accent="blue"
            />
          </motion.div>

          {!hasInventory ? (
            <Card className="border-dashed border-slate-300 bg-white/80">
              <EmptyState
                icon={<Boxes className="h-12 w-12" />}
                title="No Fabric inventory yet"
                description="Register agents with the Fabric-aware SDK or POST records to the Fabric API to light up the graph."
              />
            </Card>
          ) : (
            <>
              <Tabs
                tabs={[
                  {
                    id: "posture",
                    label: "Posture",
                    icon: <Activity className="h-4 w-4" />,
                  },
                  {
                    id: "inventory",
                    label: "Inventory",
                    icon: <Database className="h-4 w-4" />,
                  },
                  {
                    id: "graph",
                    label: "Graph",
                    icon: <Workflow className="h-4 w-4" />,
                  },
                ]}
                activeTab={activeTab}
                onChange={(tab) => setActiveTab(tab as FabricTab)}
              />

              <TabPanel active={activeTab === "posture"}>
                <PostureView data={data!} posture={posture} />
              </TabPanel>

              <TabPanel active={activeTab === "inventory"}>
                <InventoryView
                  data={data!}
                  onRegister={(kind) => {
                    setRegistrationKind(kind);
                    setShowRegistration(true);
                  }}
                />
              </TabPanel>

              <TabPanel active={activeTab === "graph"}>
                <GraphView graph={data!.graph} />
              </TabPanel>
            </>
          )}
        </>
      )}

      <RegisterFabricModal
        isOpen={showRegistration}
        kind={registrationKind}
        onKindChange={setRegistrationKind}
        onClose={() => setShowRegistration(false)}
      />
    </div>
  );
}

function FabricSignalPanel({
  totalNodes,
  totalEdges,
  postureScore,
  postureLevel,
}: {
  totalNodes: number;
  totalEdges: number;
  postureScore: number;
  postureLevel: FabricPosture["level"];
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/10 p-5 backdrop-blur">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-200">
            Live Fabric
          </p>
          <p className="mt-1 text-sm text-slate-300">
            Registry graph readiness
          </p>
        </div>
        <Sparkles className="h-5 w-5 text-cyan-200" />
      </div>
      <div className="space-y-4">
        <div>
          <div className="flex items-end justify-between">
            <span className="text-sm text-slate-300">Posture score</span>
            <span className="text-3xl font-bold">{postureScore}%</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${postureScore}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-emerald-300 to-blue-300"
            />
          </div>
          <p className="mt-2 text-xs uppercase tracking-[0.22em] text-slate-400">
            {postureLevel === "ready"
              ? "Ready"
              : postureLevel === "watch"
                ? "Watch"
                : "Blocked"}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-slate-900/60 p-4">
            <p className="text-xs text-slate-400">Graph Nodes</p>
            <p className="mt-1 text-2xl font-bold">{totalNodes}</p>
          </div>
          <div className="rounded-xl bg-slate-900/60 p-4">
            <p className="text-xs text-slate-400">Graph Edges</p>
            <p className="mt-1 text-2xl font-bold">{totalEdges}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  accent,
}: {
  title: string;
  value: number;
  subtitle: string;
  icon: React.ReactNode;
  accent: "cyan" | "emerald" | "amber" | "blue";
}) {
  const styles = {
    cyan: "from-cyan-50 to-sky-50 text-cyan-700 ring-cyan-100",
    emerald: "from-emerald-50 to-teal-50 text-emerald-700 ring-emerald-100",
    amber: "from-amber-50 to-orange-50 text-amber-700 ring-amber-100",
    blue: "from-blue-50 to-indigo-50 text-blue-700 ring-blue-100",
  };

  return (
    <Card className="overflow-hidden border-0 bg-white/90 shadow-lg shadow-slate-200/70">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-slate-950">
            {value.toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
        </div>
        <div
          className={`rounded-2xl bg-gradient-to-br p-3 ring-1 ${styles[accent]}`}
        >
          {icon}
        </div>
      </div>
    </Card>
  );
}

function PostureView({
  data,
  posture,
}: {
  data: FabricInventory;
  posture: FabricPosture;
}) {
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <Card className="border-0 bg-slate-950 text-white shadow-xl shadow-slate-300/40">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white">
            Governance Readiness
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Coverage signals from the Fabric registry
          </p>
        </div>
        <div className="space-y-5">
          {posture.signals.map((signal, index) => (
            <motion.div
              key={signal.label}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ ...motionTransition, delay: index * 0.04 }}
            >
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-slate-300">{signal.label}</span>
                <span className="flex items-center gap-2 font-semibold">
                  <ReadinessDot level={signal.status} />
                  {signal.value}%
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/10">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${signal.value}%` }}
                  transition={{ duration: 0.7, delay: index * 0.06 }}
                  className={signal.className}
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">{signal.summary}</p>
            </motion.div>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="bg-white/90 md:col-span-2">
          <CardHeader
            title="Readiness Exceptions"
            description="Release-impacting gaps computed from Fabric registry data"
          />
          <div className="grid gap-3 md:grid-cols-2">
            {posture.issues.slice(0, 6).map((issue) => (
              <ReadinessIssueCard key={issue.id} issue={issue} />
            ))}
            {!posture.issues.length && (
              <p className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700 md:col-span-2">
                No readiness exceptions detected in the Fabric registry.
              </p>
            )}
          </div>
        </Card>

        <Card className="bg-white/90">
          <CardHeader
            title="Risk Watch"
            description="Critical or approval-heavy paths"
          />
          <div className="space-y-3">
            {data.toolActions.data
              .filter(
                (action) =>
                  action.risk_tier === "CRITICAL" || action.approval_required,
              )
              .slice(0, 6)
              .map((action) => (
                <div
                  key={action.action_id}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">
                        {action.display_name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {action.action} on {action.resource_type}
                      </p>
                    </div>
                    <RiskBadge risk={action.risk_tier} />
                  </div>
                  {action.approval_required && (
                    <p className="mt-2 flex items-center gap-1 text-xs text-amber-700">
                      <CheckCircle className="h-3 w-3" />
                      Approval required
                    </p>
                  )}
                </div>
              ))}
            {!data.toolActions.data.some(
              (action) =>
                action.risk_tier === "CRITICAL" || action.approval_required,
            ) && (
              <p className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">
                No critical or approval-required tool actions registered.
              </p>
            )}
          </div>
        </Card>

        <Card className="bg-white/90">
          <CardHeader
            title="Rollout Channels"
            description="Policy bundle lanes by environment"
          />
          <div className="space-y-3">
            {data.policyChannels.data.slice(0, 6).map((channel) => (
              <div
                key={channel.channel_id}
                className="rounded-xl border border-slate-200 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">
                      {channel.display_name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {channel.channel_id}
                    </p>
                  </div>
                  <RolloutBadge state={channel.rollout_state} />
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                  <EnvironmentBadge environment={channel.environment} />
                  <span>{channel.active_bundle_id ?? "No active bundle"}</span>
                </div>
              </div>
            ))}
            {!data.policyChannels.data.length && (
              <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                No policy channels registered yet.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function ReadinessIssueCard({ issue }: { issue: FabricReadinessIssue }) {
  const styles = {
    info: "border-cyan-100 bg-cyan-50 text-cyan-800",
    warning: "border-amber-100 bg-amber-50 text-amber-800",
    critical: "border-red-100 bg-red-50 text-red-800",
  };

  return (
    <div className={`rounded-2xl border p-4 ${styles[issue.severity]}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-semibold">{issue.title}</p>
          <p className="mt-1 text-sm opacity-80">{issue.detail}</p>
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] opacity-70">
            {issue.remediation}
          </p>
        </div>
      </div>
    </div>
  );
}

function ReadinessDot({ level }: { level: FabricPosture["level"] }) {
  const color =
    level === "ready"
      ? "bg-emerald-300"
      : level === "watch"
        ? "bg-amber-300"
        : "bg-red-300";

  return <span className={`h-2.5 w-2.5 rounded-full ${color}`} />;
}

function InventoryView({
  data,
  onRegister,
}: {
  data: FabricInventory;
  onRegister: (kind: RegistrationKind) => void;
}) {
  return (
    <div className="space-y-6">
      <Card className="border-cyan-100 bg-gradient-to-r from-cyan-50 via-white to-emerald-50">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-950">Register Fabric inventory</h3>
            <p className="mt-1 text-sm text-slate-600">
              Add a governed registry record. New records are immediately reflected in posture and graph views.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => onRegister("agent")}>
              <Plus className="mr-1.5 h-4 w-4" /> Agent
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onRegister("enforcement_point")}>
              <Plus className="mr-1.5 h-4 w-4" /> Enforcement Point
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onRegister("tool_action")}>
              <Plus className="mr-1.5 h-4 w-4" /> Tool Action
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onRegister("policy_channel")}>
              <Plus className="mr-1.5 h-4 w-4" /> Policy Channel
            </Button>
          </div>
        </div>
      </Card>
      <AgentsTable agents={data.agents.data} />
      <EnforcementPointsTable enforcementPoints={data.enforcementPoints.data} />
      <ToolActionsTable actions={data.toolActions.data} />
      <PolicyChannelsTable channels={data.policyChannels.data} />
    </div>
  );
}

function AgentsTable({ agents }: { agents: FabricAgent[] }) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 pb-0">
        <CardHeader
          title="Agents"
          description="Runtime identity, owner, risk, and lifecycle state"
        />
      </div>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeader>Agent</TableHeader>
            <TableHeader>Owner</TableHeader>
            <TableHeader>Runtime</TableHeader>
            <TableHeader>Environment</TableHeader>
            <TableHeader>Risk</TableHeader>
            <TableHeader>Status</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {agents.map((agent) => (
            <TableRow key={agent.agent_id}>
              <TableCell>
                <div>
                  <p className="font-medium text-slate-900">
                    {agent.display_name}
                  </p>
                  <p className="font-mono text-xs text-slate-500">
                    {agent.agent_id}
                  </p>
                  <LabelStrip labels={agent.labels} />
                </div>
              </TableCell>
              <TableCell>{agent.owner}</TableCell>
              <TableCell>{agent.runtime}</TableCell>
              <TableCell>
                <EnvironmentBadge environment={agent.environment} />
              </TableCell>
              <TableCell>
                <RiskBadge risk={agent.risk_tier} />
              </TableCell>
              <TableCell>
                <LifecycleBadge status={agent.status} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!agents.length && <EmptyRow message="No agents registered" />}
    </Card>
  );
}

function EnforcementPointsTable({
  enforcementPoints,
}: {
  enforcementPoints: FabricEnforcementPoint[];
}) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 pb-0">
        <CardHeader
          title="Enforcement Points"
          description="SDKs, gateways, CI gates, and protected targets"
        />
      </div>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeader>Point</TableHeader>
            <TableHeader>Type</TableHeader>
            <TableHeader>Environment</TableHeader>
            <TableHeader>Status</TableHeader>
            <TableHeader>Agents</TableHeader>
            <TableHeader>URL</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {enforcementPoints.map((point) => (
            <TableRow key={point.enforcement_point_id}>
              <TableCell>
                <div>
                  <p className="font-medium text-slate-900">
                    {point.display_name}
                  </p>
                  <p className="font-mono text-xs text-slate-500">
                    {point.enforcement_point_id}
                  </p>
                </div>
              </TableCell>
              <TableCell>{formatToken(point.type)}</TableCell>
              <TableCell>
                <EnvironmentBadge environment={point.environment} />
              </TableCell>
              <TableCell>
                <LifecycleBadge status={point.status} />
              </TableCell>
              <TableCell>{point.agent_ids.length}</TableCell>
              <TableCell>
                <span className="font-mono text-xs text-slate-500">
                  {point.url ?? "-"}
                </span>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!enforcementPoints.length && (
        <EmptyRow message="No enforcement points registered" />
      )}
    </Card>
  );
}

function ToolActionsTable({ actions }: { actions: FabricToolAction[] }) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 pb-0">
        <CardHeader
          title="Tool Actions"
          description="Normalized tool operations and approval posture"
        />
      </div>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeader>Action</TableHeader>
            <TableHeader>Resource</TableHeader>
            <TableHeader>Risk</TableHeader>
            <TableHeader>Approval</TableHeader>
            <TableHeader>Allowed Environments</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {actions.map((action) => (
            <TableRow key={action.action_id}>
              <TableCell>
                <div>
                  <p className="font-medium text-slate-900">
                    {action.display_name}
                  </p>
                  <p className="font-mono text-xs text-slate-500">
                    {action.action}
                  </p>
                </div>
              </TableCell>
              <TableCell>{action.resource_type}</TableCell>
              <TableCell>
                <RiskBadge risk={action.risk_tier} />
              </TableCell>
              <TableCell>
                <Badge
                  variant={action.approval_required ? "warning" : "success"}
                  size="sm"
                >
                  {action.approval_required ? "Required" : "Not required"}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {action.allowed_environments.map((environment) => (
                    <EnvironmentBadge
                      key={environment}
                      environment={environment}
                    />
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!actions.length && <EmptyRow message="No tool actions registered" />}
    </Card>
  );
}

function PolicyChannelsTable({
  channels,
}: {
  channels: FabricPolicyChannel[];
}) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 pb-0">
        <CardHeader
          title="Policy Channels"
          description="Signed bundle rollout channels by environment"
        />
      </div>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeader>Channel</TableHeader>
            <TableHeader>Environment</TableHeader>
            <TableHeader>State</TableHeader>
            <TableHeader>Active Bundle</TableHeader>
            <TableHeader>Updated</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {channels.map((channel) => (
            <TableRow key={channel.channel_id}>
              <TableCell>
                <div>
                  <p className="font-medium text-slate-900">
                    {channel.display_name}
                  </p>
                  <p className="font-mono text-xs text-slate-500">
                    {channel.channel_id}
                  </p>
                </div>
              </TableCell>
              <TableCell>
                <EnvironmentBadge environment={channel.environment} />
              </TableCell>
              <TableCell>
                <RolloutBadge state={channel.rollout_state} />
              </TableCell>
              <TableCell>
                <span className="font-mono text-xs text-slate-500">
                  {channel.active_bundle_id ?? "-"}
                </span>
              </TableCell>
              <TableCell>
                {new Date(channel.updated_at).toLocaleString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!channels.length && <EmptyRow message="No policy channels registered" />}
    </Card>
  );
}

function GraphView({ graph }: { graph: FabricGraphSummary }) {
  const nodesByType = useMemo(
    () =>
      graph.nodes.reduce<Record<GraphNode["type"], GraphNode[]>>(
        (groups, node) => {
          groups[node.type].push(node);
          return groups;
        },
        {
          agent: [],
          enforcement_point: [],
          tool_action: [],
          policy_channel: [],
        },
      ),
    [graph.nodes],
  );

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
      <Card className="overflow-hidden border-0 bg-slate-950 text-white shadow-xl shadow-slate-300/40">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white">Governance Graph</h3>
          <p className="mt-1 text-sm text-slate-400">
            Agents connect to enforcement points, executable tool actions, and
            active policy channels
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-4">
          {(Object.keys(nodesByType) as GraphNode["type"][]).map(
            (type, columnIndex) => (
              <div key={type} className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <NodeIcon type={type} />
                  {nodeTypeLabels[type]}
                </div>
                <div className="space-y-3">
                  {nodesByType[type].slice(0, 8).map((node, index) => (
                    <motion.div
                      key={node.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        ...motionTransition,
                        delay: columnIndex * 0.05 + index * 0.03,
                      }}
                      className="rounded-2xl border border-white/10 bg-white/10 p-3 backdrop-blur"
                    >
                      <p className="text-sm font-medium">{node.label}</p>
                      <p className="mt-1 truncate font-mono text-xs text-slate-400">
                        {node.id}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-1">
                        {node.status && (
                          <Badge size="sm">{formatToken(node.status)}</Badge>
                        )}
                        {node.risk_tier && <RiskBadge risk={node.risk_tier} />}
                      </div>
                    </motion.div>
                  ))}
                  {!nodesByType[type].length && (
                    <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-slate-500">
                      Empty
                    </div>
                  )}
                </div>
              </div>
            ),
          )}
        </div>
      </Card>

      <Card className="bg-white/90">
        <CardHeader
          title="Edges"
          description={`${graph.edges.length} relationships discovered`}
        />
        <div className="max-h-[560px] space-y-3 overflow-y-auto pr-1">
          {graph.edges.slice(0, 50).map((edge, index) => (
            <motion.div
              key={`${edge.from}-${edge.to}-${edge.relation}-${index}`}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ ...motionTransition, delay: index * 0.01 }}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3"
            >
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Route className="h-3.5 w-3.5" />
                {relationLabels[edge.relation]}
              </div>
              <p className="mt-2 truncate font-mono text-xs text-slate-700">
                {edge.from}
              </p>
              <p className="truncate font-mono text-xs text-slate-400">
                to {edge.to}
              </p>
            </motion.div>
          ))}
          {!graph.edges.length && (
            <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
              No graph relationships yet. Link enforcement points to agents and
              activate policy channels.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}

interface RegistrationFormState {
  id: string;
  displayName: string;
  owner: string;
  runtime: string;
  action: string;
  resourceType: string;
  environment: string;
  riskTier: string;
  enforcementType: string;
  url: string;
  agentIds: string;
  allowedEnvironments: string;
  approvalRequired: boolean;
  rolloutState: string;
  activeBundleId: string;
  labels: string;
  metadata: string;
}

const emptyRegistrationForm: RegistrationFormState = {
  id: "",
  displayName: "",
  owner: "",
  runtime: "",
  action: "",
  resourceType: "",
  environment: "stage",
  riskTier: "MEDIUM",
  enforcementType: "sdk",
  url: "",
  agentIds: "",
  allowedEnvironments: "stage, prod",
  approvalRequired: false,
  rolloutState: "DRAFT",
  activeBundleId: "",
  labels: "",
  metadata: "",
};

const environmentOptions = [
  { value: "dev", label: "Development" },
  { value: "test", label: "Test" },
  { value: "stage", label: "Staging" },
  { value: "prod", label: "Production" },
];

const riskOptions = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
];

function RegisterFabricModal({
  isOpen,
  kind,
  onKindChange,
  onClose,
}: {
  isOpen: boolean;
  kind: RegistrationKind;
  onKindChange: (kind: RegistrationKind) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<RegistrationFormState>(emptyRegistrationForm);
  const [formError, setFormError] = useState<string | null>(null);
  const registerAgent = useRegisterFabricAgent();
  const registerEnforcementPoint = useRegisterFabricEnforcementPoint();
  const registerToolAction = useRegisterFabricToolAction();
  const registerPolicyChannel = useRegisterFabricPolicyChannel();

  useEffect(() => {
    if (isOpen) {
      setForm(emptyRegistrationForm);
      setFormError(null);
    }
  }, [isOpen, kind]);

  const setField = <K extends keyof RegistrationFormState>(
    field: K,
    value: RegistrationFormState[K],
  ) => setForm((current) => ({ ...current, [field]: value }));

  const isPending =
    registerAgent.isPending ||
    registerEnforcementPoint.isPending ||
    registerToolAction.isPending ||
    registerPolicyChannel.isPending;

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    try {
      if (!form.displayName.trim()) {
        throw new Error("Display name is required");
      }

      const metadata = form.metadata.trim() ? JSON.parse(form.metadata) : {};
      if (!metadata || Array.isArray(metadata) || typeof metadata !== "object") {
        throw new Error("Metadata must be a JSON object");
      }

      if (kind === "agent") {
        if (!form.owner.trim() || !form.runtime.trim()) {
          throw new Error("Owner and runtime are required for agents");
        }
        await registerAgent.mutateAsync({
          ...(form.id.trim() ? { agent_id: form.id.trim() } : {}),
          display_name: form.displayName.trim(),
          owner: form.owner.trim(),
          runtime: form.runtime.trim(),
          environment: form.environment as "dev" | "test" | "stage" | "prod",
          risk_tier: form.riskTier as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
          status: "ACTIVE",
          labels: splitList(form.labels),
          metadata,
        });
      } else if (kind === "enforcement_point") {
        await registerEnforcementPoint.mutateAsync({
          ...(form.id.trim() ? { enforcement_point_id: form.id.trim() } : {}),
          display_name: form.displayName.trim(),
          type: form.enforcementType as "sdk" | "ci" | "mcp_gateway" | "tool_gateway" | "service_gateway" | "target",
          environment: form.environment as "dev" | "test" | "stage" | "prod",
          status: "ACTIVE",
          ...(form.url.trim() ? { url: form.url.trim() } : {}),
          agent_ids: splitList(form.agentIds),
          metadata,
        });
      } else if (kind === "tool_action") {
        if (!form.action.trim() || !form.resourceType.trim()) {
          throw new Error("Action and resource type are required for tool actions");
        }
        const allowedEnvironments = splitList(form.allowedEnvironments);
        if (!allowedEnvironments.length) {
          throw new Error("At least one allowed environment is required");
        }
        await registerToolAction.mutateAsync({
          ...(form.id.trim() ? { action_id: form.id.trim() } : {}),
          display_name: form.displayName.trim(),
          action: form.action.trim(),
          resource_type: form.resourceType.trim(),
          risk_tier: form.riskTier as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
          approval_required: form.approvalRequired,
          allowed_environments: allowedEnvironments as Array<"dev" | "test" | "stage" | "prod">,
          metadata,
        });
      } else {
        await registerPolicyChannel.mutateAsync({
          ...(form.id.trim() ? { channel_id: form.id.trim() } : {}),
          display_name: form.displayName.trim(),
          environment: form.environment as "dev" | "test" | "stage" | "prod",
          rollout_state: form.rolloutState as "DRAFT" | "CANARY" | "ACTIVE" | "PAUSED" | "RETIRED",
          ...(form.activeBundleId.trim() ? { active_bundle_id: form.activeBundleId.trim() } : {}),
          metadata,
        });
      }

      onClose();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Registration failed");
    }
  };

  const title = {
    agent: "Register Agent",
    enforcement_point: "Register Enforcement Point",
    tool_action: "Register Tool Action",
    policy_channel: "Register Policy Channel",
  }[kind];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="lg">
      <form onSubmit={submit} className="space-y-4">
        <Select
          label="Record type"
          value={kind}
          onChange={(event) => onKindChange(event.target.value as RegistrationKind)}
          options={[
            { value: "agent", label: "Agent" },
            { value: "enforcement_point", label: "Enforcement Point" },
            { value: "tool_action", label: "Tool Action" },
            { value: "policy_channel", label: "Policy Channel" },
          ]}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Display name"
            value={form.displayName}
            onChange={(event) => setField("displayName", event.target.value)}
            placeholder="Production release agent"
            required
          />
          <Input
            label="Stable ID (optional)"
            value={form.id}
            onChange={(event) => setField("id", event.target.value)}
            placeholder="Generated if blank"
          />
        </div>

        {kind === "agent" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Owner"
              value={form.owner}
              onChange={(event) => setField("owner", event.target.value)}
              placeholder="platform-security"
              required
            />
            <Input
              label="Runtime"
              value={form.runtime}
              onChange={(event) => setField("runtime", event.target.value)}
              placeholder="agent-sdk"
              required
            />
          </div>
        )}

        {kind === "enforcement_point" && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Point type"
                value={form.enforcementType}
                onChange={(event) => setField("enforcementType", event.target.value)}
                options={[
                  { value: "sdk", label: "SDK" },
                  { value: "ci", label: "CI" },
                  { value: "mcp_gateway", label: "MCP Gateway" },
                  { value: "tool_gateway", label: "Tool Gateway" },
                  { value: "service_gateway", label: "Service Gateway" },
                  { value: "target", label: "Target" },
                ]}
              />
              <Input
                label="URL (optional)"
                type="url"
                value={form.url}
                onChange={(event) => setField("url", event.target.value)}
                placeholder="https://gateway.example.com"
              />
            </div>
            <Input
              label="Protected agent IDs"
              value={form.agentIds}
              onChange={(event) => setField("agentIds", event.target.value)}
              placeholder="agent_release_captain, agent_finops_sentinel"
              helperText="Comma-separated IDs from the Fabric agent registry."
            />
          </>
        )}

        {kind === "tool_action" && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Action"
                value={form.action}
                onChange={(event) => setField("action", event.target.value)}
                placeholder="deploy"
                required
              />
              <Input
                label="Resource type"
                value={form.resourceType}
                onChange={(event) => setField("resourceType", event.target.value)}
                placeholder="production_environment"
                required
              />
            </div>
            <label className="flex items-center gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.approvalRequired}
                onChange={(event) => setField("approvalRequired", event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-cyan-600"
              />
              Require human approval before execution
            </label>
            <Input
              label="Allowed environments"
              value={form.allowedEnvironments}
              onChange={(event) => setField("allowedEnvironments", event.target.value)}
              placeholder="stage, prod"
              helperText="Comma-separated values: dev, test, stage, prod."
            />
          </>
        )}

        {kind === "policy_channel" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Rollout state"
              value={form.rolloutState}
              onChange={(event) => setField("rolloutState", event.target.value)}
              options={[
                { value: "DRAFT", label: "Draft" },
                { value: "CANARY", label: "Canary" },
                { value: "ACTIVE", label: "Active" },
                { value: "PAUSED", label: "Paused" },
                { value: "RETIRED", label: "Retired" },
              ]}
            />
            <Input
              label="Active bundle ID (optional)"
              value={form.activeBundleId}
              onChange={(event) => setField("activeBundleId", event.target.value)}
              placeholder="bundle_0_1_15_stage"
            />
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {kind !== "tool_action" && (
            <Select
              label="Environment"
              value={form.environment}
              onChange={(event) => setField("environment", event.target.value)}
              options={environmentOptions}
            />
          )}
          {kind !== "enforcement_point" && kind !== "policy_channel" && (
            <Select
              label="Risk tier"
              value={form.riskTier}
              onChange={(event) => setField("riskTier", event.target.value)}
              options={riskOptions}
            />
          )}
          {kind === "tool_action" && (
            <Select
              label="Risk tier"
              value={form.riskTier}
              onChange={(event) => setField("riskTier", event.target.value)}
              options={riskOptions}
            />
          )}
        </div>

        {kind === "agent" && (
          <Input
            label="Labels"
            value={form.labels}
            onChange={(event) => setField("labels", event.target.value)}
            placeholder="production, release, governed"
            helperText="Comma-separated labels for filtering and discovery."
          />
        )}

        <Textarea
          label="Metadata JSON (optional)"
          value={form.metadata}
          onChange={(event) => setField("metadata", event.target.value)}
          placeholder={'{"owner_team":"platform-security"}'}
          rows={3}
        />

        {formError && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
            {formError}
          </div>
        )}

        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending}>
            Register {title.replace("Register ", "")}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  );
}

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function NodeIcon({ type }: { type: GraphNode["type"] }) {
  const icons: Record<GraphNode["type"], React.ReactNode> = {
    agent: <Radar className="h-4 w-4" />,
    enforcement_point: <CircuitBoard className="h-4 w-4" />,
    tool_action: <TerminalSquare className="h-4 w-4" />,
    policy_channel: <Layers className="h-4 w-4" />,
  };
  return icons[type];
}

function LabelStrip({ labels }: { labels: string[] }) {
  if (!labels.length) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {labels.slice(0, 3).map((label) => (
        <Badge key={label} variant="default" size="sm">
          {label}
        </Badge>
      ))}
      {labels.length > 3 && (
        <Badge variant="default" size="sm">
          +{labels.length - 3}
        </Badge>
      )}
    </div>
  );
}

function EmptyRow({ message }: { message: string }) {
  return (
    <div className="border-t border-slate-100 p-6 text-sm text-slate-500">
      {message}
    </div>
  );
}

function EnvironmentBadge({ environment }: { environment: string }) {
  const variants: Record<
    string,
    "default" | "success" | "warning" | "error" | "info"
  > = {
    dev: "info",
    test: "default",
    stage: "warning",
    prod: "error",
  };

  return (
    <Badge variant={variants[environment] ?? "default"} size="sm">
      {environment}
    </Badge>
  );
}

function RiskBadge({ risk }: { risk: string }) {
  const variants: Record<
    string,
    "default" | "success" | "warning" | "error" | "info"
  > = {
    LOW: "success",
    MEDIUM: "info",
    HIGH: "warning",
    CRITICAL: "error",
  };

  return (
    <Badge variant={variants[risk] ?? "default"} size="sm">
      {risk}
    </Badge>
  );
}

function LifecycleBadge({ status }: { status: string }) {
  const variants: Record<
    string,
    "default" | "success" | "warning" | "error" | "info"
  > = {
    ACTIVE: "success",
    INACTIVE: "default",
    QUARANTINED: "warning",
    DECOMMISSIONED: "error",
  };

  return (
    <Badge variant={variants[status] ?? "default"} size="sm">
      {formatToken(status)}
    </Badge>
  );
}

function RolloutBadge({ state }: { state: string }) {
  const variants: Record<
    string,
    "default" | "success" | "warning" | "error" | "info"
  > = {
    DRAFT: "default",
    CANARY: "info",
    ACTIVE: "success",
    PAUSED: "warning",
    RETIRED: "error",
  };

  return (
    <Badge variant={variants[state] ?? "default"} size="sm">
      {formatToken(state)}
    </Badge>
  );
}

function formatToken(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}
