"use client";

import { useEffect, useMemo, useRef } from "react";
import { animate, createScope, stagger } from "animejs";
import { motion, useReducedMotion } from "motion/react";
import {
  GitBranch,
  Radar,
  ShieldCheck,
  TerminalSquare,
  Workflow,
} from "lucide-react";

interface FabricOrbitProps {
  agents: number;
  enforcementPoints: number;
  toolActions: number;
  policyChannels: number;
  postureScore: number;
}

const formatCount = (value: number) => value.toLocaleString();

export function FabricOrbit({
  agents,
  enforcementPoints,
  toolActions,
  policyChannels,
  postureScore,
}: FabricOrbitProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const scopeRef = useRef<ReturnType<typeof createScope> | null>(null);
  const shouldReduceMotion = useReducedMotion();

  const orbitNodes = useMemo(
    () => [
      {
        label: "Agents",
        value: agents,
        className: "left-[18%] top-[24%] border-cyan-200/30 bg-cyan-300/15 text-cyan-100",
        icon: <Radar className="h-4 w-4" />,
      },
      {
        label: "Guards",
        value: enforcementPoints,
        className:
          "left-[82%] top-[28%] border-emerald-200/30 bg-emerald-300/15 text-emerald-100",
        icon: <ShieldCheck className="h-4 w-4" />,
      },
      {
        label: "Tools",
        value: toolActions,
        className:
          "left-[76%] top-[76%] border-amber-200/30 bg-amber-300/15 text-amber-100",
        icon: <TerminalSquare className="h-4 w-4" />,
      },
      {
        label: "Channels",
        value: policyChannels,
        className:
          "left-[22%] top-[72%] border-blue-200/30 bg-blue-300/15 text-blue-100",
        icon: <GitBranch className="h-4 w-4" />,
      },
    ],
    [agents, enforcementPoints, policyChannels, toolActions],
  );

  useEffect(() => {
    if (shouldReduceMotion || !rootRef.current) {
      return;
    }

    scopeRef.current = createScope({ root: rootRef }).add(() => {
      animate(".fabric-orbit-ring", {
        rotate: 360,
        duration: 28000,
        loop: true,
        ease: "linear",
      });

      animate(".fabric-orbit-node", {
        y: [-4, 4],
        opacity: [0.82, 1],
        duration: 1800,
        alternate: true,
        loop: true,
        delay: stagger(180),
        ease: "inOutSine",
      });

      animate(".fabric-orbit-pulse", {
        scale: [1, 1.16, 1],
        opacity: [0.65, 0.2, 0.65],
        duration: 3600,
        loop: true,
        ease: "inOutSine",
      });
    });

    return () => {
      scopeRef.current?.revert();
      scopeRef.current = null;
    };
  }, [shouldReduceMotion]);

  return (
    <div
      ref={rootRef}
      className="relative min-h-[340px] overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-cyan-950/30"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(34,211,238,0.24),transparent_30%),radial-gradient(circle_at_75%_72%,rgba(16,185,129,0.18),transparent_28%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:24px_24px] opacity-60" />

      <div className="relative h-[300px]">
        <div className="fabric-orbit-ring absolute inset-8 rounded-full border border-dashed border-cyan-200/25" />
        <div className="fabric-orbit-ring absolute inset-16 rounded-full border border-emerald-200/20" />
        <div className="fabric-orbit-pulse absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-300/10 blur-xl" />

        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="absolute left-1/2 top-1/2 flex h-36 w-36 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-[2rem] border border-white/15 bg-white/10 text-center shadow-2xl shadow-cyan-500/20 backdrop-blur"
        >
          <Workflow className="mb-2 h-7 w-7 text-cyan-200" />
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-100">
            STIX
          </p>
          <p className="mt-1 text-3xl font-bold text-white">{postureScore}%</p>
          <p className="text-[11px] text-slate-300">fabric posture</p>
        </motion.div>

        {orbitNodes.map((node) => (
          <div
            key={node.label}
            className={`absolute -translate-x-1/2 -translate-y-1/2 ${node.className}`}
          >
            <div className="fabric-orbit-node min-w-24 rounded-2xl border px-3 py-2 shadow-xl backdrop-blur">
              <div className="flex items-center gap-2">
                {node.icon}
                <div>
                  <p className="text-xs text-white/60">{node.label}</p>
                  <p className="text-lg font-bold text-white">
                    {formatCount(node.value)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="relative mt-2 grid grid-cols-3 gap-2 text-center text-xs text-slate-300">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          Deterministic
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          Signed
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          Auditable
        </div>
      </div>
    </div>
  );
}
