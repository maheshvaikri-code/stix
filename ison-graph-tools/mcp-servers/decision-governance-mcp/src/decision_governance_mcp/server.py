"""
Decision Governance MCP Server
==============================

Complete MCP server for decision governance:
- Identity management (agents, humans, systems)
- Decision traces and reasoning chains
- Immutable audit trail
- Data provenance and lineage
- Policy enforcement and compliance

50+ tools organized by domain.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from decision_governance import (
    DecisionGovernance,
    quick_governance,
    IdentityType,
    DecisionStatus,
    TraceStatus,
    AuditLevel,
    ProvenanceType,
    PolicyEnforcement,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("decision-governance-mcp")


@dataclass
class ServerState:
    engines: Dict[str, DecisionGovernance] = field(default_factory=dict)
    default_project: Optional[str] = None


server = Server("decision-governance-mcp")
state = ServerState()


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

TOOLS = [
    # ==================== ENGINE MANAGEMENT ====================
    Tool(name="governance_init", description="Initialize governance engine for a project.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "setup_defaults": {"type": "boolean", "default": True}
         }, "required": ["project_id"]}),
    Tool(name="governance_list", description="List all governance engines.",
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="governance_stats", description="Get comprehensive governance statistics.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),

    # ==================== SESSION ====================
    Tool(name="session_start", description="Start a session for an agent.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "agent_id": {"type": "string"},
             "metadata": {"type": "object"}
         }, "required": ["agent_id"]}),
    Tool(name="session_end", description="End current session.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "summary": {"type": "string"}
         }}),

    # ==================== IDENTITY ====================
    Tool(name="identity_register_agent", description="Register an AI agent.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "agent_id": {"type": "string"},
             "name": {"type": "string"},
             "capabilities": {"type": "array", "items": {"type": "string"}},
             "authority_level": {"type": "string", "enum": ["none", "read", "write", "admin", "super_admin"]}
         }, "required": ["agent_id", "name"]}),
    Tool(name="identity_register_human", description="Register a human user.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "human_id": {"type": "string"},
             "name": {"type": "string"},
             "email": {"type": "string"},
             "role": {"type": "string"}
         }, "required": ["human_id", "name"]}),
    Tool(name="identity_register_system", description="Register a system/service.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "system_id": {"type": "string"},
             "name": {"type": "string"},
             "endpoint": {"type": "string"}
         }, "required": ["system_id", "name"]}),
    Tool(name="identity_get", description="Get identity details.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "identity_ref": {"type": "string", "description": "Format: type:id (e.g., agent:claude-1)"}
         }, "required": ["identity_ref"]}),
    Tool(name="identity_list_agents", description="List all registered agents.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
    Tool(name="identity_delegate", description="Delegate authority from one identity to another.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "delegator_type": {"type": "string"},
             "delegator_id": {"type": "string"},
             "delegate_type": {"type": "string"},
             "delegate_id": {"type": "string"},
             "scope": {"type": "string"}
         }, "required": ["delegator_id", "delegate_id", "scope"]}),

    # ==================== DECISION TRACES ====================
    Tool(name="trace_start", description="Start a new decision trace.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "name": {"type": "string"},
             "description": {"type": "string"}
         }, "required": ["name"]}),
    Tool(name="trace_add_step", description="Add a reasoning step to a trace.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "trace_id": {"type": "string"},
             "action": {"type": "string"},
             "reasoning": {"type": "string"},
             "inputs": {"type": "object"},
             "outputs": {"type": "object"},
             "alternatives": {"type": "array", "items": {"type": "string"}},
             "confidence": {"type": "number", "minimum": 0, "maximum": 1}
         }, "required": ["trace_id", "action"]}),
    Tool(name="trace_complete", description="Complete a decision trace.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "trace_id": {"type": "string"},
             "outcome": {"type": "string"}
         }, "required": ["trace_id"]}),
    Tool(name="trace_get", description="Get a trace with all steps.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "trace_id": {"type": "string"}
         }, "required": ["trace_id"]}),
    Tool(name="trace_list", description="List traces.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "status": {"type": "string", "enum": ["active", "completed", "abandoned"]},
             "limit": {"type": "integer", "default": 50}
         }}),
    Tool(name="trace_export", description="Export trace for visualization.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "trace_id": {"type": "string"},
             "format": {"type": "string", "enum": ["dict", "mermaid"], "default": "dict"}
         }, "required": ["trace_id"]}),

    # ==================== DECISIONS ====================
    Tool(name="decision_record", description="Record a decision.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "action": {"type": "string"},
             "reasoning": {"type": "string"},
             "agent_id": {"type": "string"},
             "confidence": {"type": "number", "default": 1.0},
             "context": {"type": "object"},
             "trace_id": {"type": "string"},
             "requires_approval": {"type": "boolean", "default": False},
             "alternatives": {"type": "array", "items": {"type": "object"}}
         }, "required": ["action", "reasoning"]}),
    Tool(name="decision_approve", description="Approve a pending decision.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "decision_id": {"type": "string"},
             "approved_by": {"type": "string"},
             "comment": {"type": "string"}
         }, "required": ["decision_id", "approved_by"]}),
    Tool(name="decision_reject", description="Reject a pending decision.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "decision_id": {"type": "string"},
             "rejected_by": {"type": "string"},
             "reason": {"type": "string"}
         }, "required": ["decision_id", "rejected_by"]}),
    Tool(name="decision_get", description="Get decision details.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "decision_id": {"type": "string"}
         }, "required": ["decision_id"]}),
    Tool(name="decision_pending", description="List pending decisions needing approval.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "limit": {"type": "integer", "default": 50}
         }}),
    Tool(name="decision_history", description="Get decision history for an agent.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "agent_id": {"type": "string"},
             "limit": {"type": "integer", "default": 50}
         }}),
    Tool(name="decision_chain", description="Get chain of related decisions.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "decision_id": {"type": "string"},
             "direction": {"type": "string", "enum": ["backward", "forward"], "default": "backward"}
         }, "required": ["decision_id"]}),

    # ==================== AUDIT TRAIL ====================
    Tool(name="audit_log", description="Log an audit entry.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "action_type": {"type": "string"},
             "level": {"type": "string", "enum": ["debug", "info", "warning", "error", "critical", "security"]},
             "description": {"type": "string"},
             "actor_id": {"type": "string"},
             "actor_type": {"type": "string"},
             "target": {"type": "string"},
             "target_type": {"type": "string"},
             "before_state": {"type": "object"},
             "after_state": {"type": "object"},
             "context": {"type": "object"}
         }, "required": ["action_type"]}),
    Tool(name="audit_query", description="Query audit trail.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "actor_id": {"type": "string"},
             "action_type": {"type": "string"},
             "level": {"type": "string"},
             "target": {"type": "string"},
             "limit": {"type": "integer", "default": 100}
         }}),
    Tool(name="audit_by_session", description="Get audit entries for a session.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "session_id": {"type": "string"}
         }, "required": ["session_id"]}),
    Tool(name="audit_export", description="Export audit trail for compliance.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "format": {"type": "string", "enum": ["json", "csv", "ison"], "default": "json"},
             "compliance_type": {"type": "string"}
         }}),
    Tool(name="audit_verify_integrity", description="Verify audit trail integrity.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
    Tool(name="audit_security_events", description="Get security-related events.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "limit": {"type": "integer", "default": 50}
         }}),

    # ==================== PROVENANCE ====================
    Tool(name="provenance_register", description="Register an artifact with provenance tracking.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "name": {"type": "string"},
             "artifact_type": {"type": "string", "enum": ["file", "code", "data", "model", "config", "document", "decision", "output"]},
             "content_hash": {"type": "string"},
             "version": {"type": "string"},
             "location": {"type": "string"},
             "created_by": {"type": "string"},
             "metadata": {"type": "object"}
         }, "required": ["name", "artifact_type"]}),
    Tool(name="provenance_derive", description="Create a derived artifact from sources.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "name": {"type": "string"},
             "artifact_type": {"type": "string"},
             "source_ids": {"type": "array", "items": {"type": "string"}},
             "operation": {"type": "string"},
             "created_by": {"type": "string"}
         }, "required": ["name", "artifact_type", "source_ids"]}),
    Tool(name="provenance_lineage", description="Get lineage chain for an artifact.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "artifact_id": {"type": "string"},
             "direction": {"type": "string", "enum": ["backward", "forward", "both"], "default": "backward"}
         }, "required": ["artifact_id"]}),
    Tool(name="provenance_get", description="Get artifact details.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "artifact_id": {"type": "string"}
         }, "required": ["artifact_id"]}),
    Tool(name="provenance_impact", description="Analyze impact of an artifact.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "artifact_id": {"type": "string"}
         }, "required": ["artifact_id"]}),
    Tool(name="provenance_graph", description="Get lineage graph for visualization.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "artifact_id": {"type": "string"},
             "max_depth": {"type": "integer", "default": 5}
         }, "required": ["artifact_id"]}),

    # ==================== POLICY ====================
    Tool(name="policy_add", description="Add a governance policy.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "name": {"type": "string"},
             "description": {"type": "string"},
             "scope": {"type": "string", "enum": ["global", "project", "team", "agent", "action"]},
             "enforcement": {"type": "string", "enum": ["mandatory", "recommended", "optional", "audit"]}
         }, "required": ["name"]}),
    Tool(name="policy_add_rule", description="Add a rule to a policy.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "policy_id": {"type": "string"},
             "name": {"type": "string"},
             "condition": {"type": "string"},
             "action": {"type": "string", "enum": ["deny", "block", "require_approval", "warn", "audit"]},
             "priority": {"type": "integer", "default": 0}
         }, "required": ["policy_id", "name", "condition", "action"]}),
    Tool(name="policy_check", description="Check if action is allowed by policies.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "action": {"type": "string"},
             "context": {"type": "object"},
             "actor_id": {"type": "string"}
         }, "required": ["action"]}),
    Tool(name="policy_list", description="List all policies.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "status": {"type": "string", "default": "active"}
         }}),
    Tool(name="policy_violations", description="Get policy violations.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "severity": {"type": "string", "enum": ["info", "warning", "error", "critical"]},
             "limit": {"type": "integer", "default": 50}
         }}),
    Tool(name="policy_resolve_violation", description="Resolve a policy violation.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "violation_id": {"type": "string"},
             "resolution": {"type": "string"},
             "resolved_by": {"type": "string"}
         }, "required": ["violation_id", "resolution"]}),
    Tool(name="policy_add_exemption", description="Add policy exemption for an identity.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"},
             "policy_id": {"type": "string"},
             "identity_id": {"type": "string"},
             "identity_type": {"type": "string"},
             "reason": {"type": "string"}
         }, "required": ["policy_id", "identity_id", "reason"]}),
]


@server.list_tools()
async def list_tools() -> List[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


def get_engine(project_id: Optional[str] = None) -> DecisionGovernance:
    """Get governance engine for project."""
    pid = project_id or state.default_project
    if not pid or pid not in state.engines:
        raise ValueError(f"Governance engine not found: {pid}. Call governance_init first.")
    return state.engines[pid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Route tool calls to appropriate handlers."""

    # ==================== ENGINE MANAGEMENT ====================
    if name == "governance_init":
        project_id = args["project_id"]
        engine = quick_governance(project_id, setup_defaults=args.get("setup_defaults", True))
        state.engines[project_id] = engine
        state.default_project = project_id
        return {"project_id": project_id, "initialized": True}

    elif name == "governance_list":
        return {"engines": list(state.engines.keys()), "default": state.default_project}

    elif name == "governance_stats":
        engine = get_engine(args.get("project_id"))
        return engine.stats()

    # ==================== SESSION ====================
    elif name == "session_start":
        engine = get_engine(args.get("project_id"))
        session_id = engine.start_session(args["agent_id"], args.get("metadata"))
        return {"session_id": session_id}

    elif name == "session_end":
        engine = get_engine(args.get("project_id"))
        engine.end_session(args.get("summary"))
        return {"ended": True}

    # ==================== IDENTITY ====================
    elif name == "identity_register_agent":
        engine = get_engine(args.get("project_id"))
        agent_id = engine.identity.register_agent(
            args["agent_id"], args["name"],
            capabilities=args.get("capabilities"),
            authority_level=args.get("authority_level", "write")
        )
        return {"agent_id": agent_id, "registered": True}

    elif name == "identity_register_human":
        engine = get_engine(args.get("project_id"))
        human_id = engine.identity.register_human(
            args["human_id"], args["name"],
            email=args.get("email"), role=args.get("role", "user")
        )
        return {"human_id": human_id, "registered": True}

    elif name == "identity_register_system":
        engine = get_engine(args.get("project_id"))
        system_id = engine.identity.register_system(
            args["system_id"], args["name"], endpoint=args.get("endpoint")
        )
        return {"system_id": system_id, "registered": True}

    elif name == "identity_get":
        engine = get_engine(args.get("project_id"))
        identity = engine.identity.resolve_identity(args["identity_ref"])
        if identity:
            return {
                "id": identity.id,
                "type": identity.type.value,
                "name": identity.name,
                "authority": identity.authority_level.value,
                "status": identity.status,
            }
        return {"error": "Identity not found"}

    elif name == "identity_list_agents":
        engine = get_engine(args.get("project_id"))
        agents = list(engine.identity.list_agents())
        return {"agents": [{"id": a.id, "name": a.name, "authority": a.authority_level.value} for a in agents]}

    elif name == "identity_delegate":
        engine = get_engine(args.get("project_id"))
        engine.identity.delegate(
            args.get("delegator_type", "agent"), args["delegator_id"],
            args.get("delegate_type", "agent"), args["delegate_id"],
            args["scope"]
        )
        return {"delegated": True}

    # ==================== DECISION TRACES ====================
    elif name == "trace_start":
        engine = get_engine(args.get("project_id"))
        trace_id = engine.trace.start(args["name"], args.get("description"))
        return {"trace_id": trace_id}

    elif name == "trace_add_step":
        engine = get_engine(args.get("project_id"))
        step_id = engine.trace.add_step(
            args["trace_id"], args["action"],
            reasoning=args.get("reasoning"),
            inputs=args.get("inputs"),
            outputs=args.get("outputs"),
            alternatives=args.get("alternatives"),
            confidence=args.get("confidence", 1.0)
        )
        return {"step_id": step_id}

    elif name == "trace_complete":
        engine = get_engine(args.get("project_id"))
        engine.trace.complete(args["trace_id"], outcome=args.get("outcome"))
        return {"completed": True}

    elif name == "trace_get":
        engine = get_engine(args.get("project_id"))
        trace = engine.trace.get(args["trace_id"])
        if trace:
            return {
                "trace_id": trace.trace_id,
                "name": trace.name,
                "status": trace.status.value,
                "step_count": trace.step_count,
                "steps": [
                    {"sequence": s.sequence, "action": s.action, "reasoning": s.reasoning, "confidence": s.confidence}
                    for s in trace.steps
                ]
            }
        return {"error": "Trace not found"}

    elif name == "trace_list":
        engine = get_engine(args.get("project_id"))
        status = TraceStatus(args["status"]) if args.get("status") else None
        traces = list(engine.trace.list_traces(status=status, limit=args.get("limit", 50)))
        return {"traces": [{"trace_id": t.trace_id, "name": t.name, "status": t.status.value} for t in traces]}

    elif name == "trace_export":
        engine = get_engine(args.get("project_id"))
        export = engine.trace.export_trace(args["trace_id"], format=args.get("format", "dict"))
        return {"export": export}

    # ==================== DECISIONS ====================
    elif name == "decision_record":
        engine = get_engine(args.get("project_id"))
        decision_id = engine.decision.record(
            args["action"], args["reasoning"],
            made_by=args.get("agent_id"),
            confidence=args.get("confidence", 1.0),
            context=args.get("context"),
            trace_id=args.get("trace_id"),
            requires_approval=args.get("requires_approval", False),
            alternatives=args.get("alternatives")
        )
        return {"decision_id": decision_id}

    elif name == "decision_approve":
        engine = get_engine(args.get("project_id"))
        engine.decision.approve(args["decision_id"], args["approved_by"], comment=args.get("comment"))
        return {"approved": True}

    elif name == "decision_reject":
        engine = get_engine(args.get("project_id"))
        engine.decision.reject(args["decision_id"], args["rejected_by"], reason=args.get("reason", ""))
        return {"rejected": True}

    elif name == "decision_get":
        engine = get_engine(args.get("project_id"))
        decision = engine.decision.get(args["decision_id"])
        if decision:
            return {
                "decision_id": decision.decision_id,
                "action": decision.action,
                "reasoning": decision.reasoning,
                "status": decision.status.value,
                "confidence": decision.confidence,
                "made_by": decision.made_by,
            }
        return {"error": "Decision not found"}

    elif name == "decision_pending":
        engine = get_engine(args.get("project_id"))
        pending = list(engine.decision.pending_approvals(limit=args.get("limit", 50)))
        return {"pending": [{"decision_id": d.decision_id, "action": d.action} for d in pending]}

    elif name == "decision_history":
        engine = get_engine(args.get("project_id"))
        history = engine.get_decision_history(args.get("agent_id"), limit=args.get("limit", 50))
        return {"history": history}

    elif name == "decision_chain":
        engine = get_engine(args.get("project_id"))
        chain = engine.decision.decision_chain(args["decision_id"], direction=args.get("direction", "backward"))
        return {"chain": [{"decision_id": d.decision_id, "action": d.action} for d in chain]}

    # ==================== AUDIT TRAIL ====================
    elif name == "audit_log":
        engine = get_engine(args.get("project_id"))
        level = AuditLevel(args.get("level", "info"))
        action_id = engine.audit.log(
            args["action_type"], level=level,
            description=args.get("description"),
            actor_id=args.get("actor_id"),
            actor_type=args.get("actor_type"),
            target=args.get("target"),
            target_type=args.get("target_type"),
            before_state=args.get("before_state"),
            after_state=args.get("after_state"),
            context=args.get("context")
        )
        return {"action_id": action_id}

    elif name == "audit_query":
        engine = get_engine(args.get("project_id"))
        level = AuditLevel(args["level"]) if args.get("level") else None
        entries = list(engine.audit.query(
            actor_id=args.get("actor_id"),
            action_type=args.get("action_type"),
            level=level,
            target=args.get("target"),
            limit=args.get("limit", 100)
        ))
        return {"entries": [
            {"action_id": e.action_id, "action_type": e.action_type, "level": e.level.value, "description": e.description}
            for e in entries
        ]}

    elif name == "audit_by_session":
        engine = get_engine(args.get("project_id"))
        entries = list(engine.audit.by_session(args["session_id"]))
        return {"entries": [{"action_id": e.action_id, "action_type": e.action_type} for e in entries]}

    elif name == "audit_export":
        engine = get_engine(args.get("project_id"))
        if args.get("compliance_type"):
            export = engine.audit.export_for_compliance(args["compliance_type"])
        else:
            export = engine.audit.export(format=args.get("format", "json"))
        return {"export": export}

    elif name == "audit_verify_integrity":
        engine = get_engine(args.get("project_id"))
        result = engine.audit.verify_integrity()
        return result

    elif name == "audit_security_events":
        engine = get_engine(args.get("project_id"))
        events = list(engine.audit.security_events(limit=args.get("limit", 50)))
        return {"events": [{"action_id": e.action_id, "action_type": e.action_type, "description": e.description} for e in events]}

    # ==================== PROVENANCE ====================
    elif name == "provenance_register":
        engine = get_engine(args.get("project_id"))
        artifact_type = ProvenanceType(args["artifact_type"])
        artifact_id = engine.provenance.register(
            args["name"], artifact_type,
            content_hash=args.get("content_hash"),
            version=args.get("version"),
            location=args.get("location"),
            created_by=args.get("created_by"),
            metadata=args.get("metadata")
        )
        return {"artifact_id": artifact_id}

    elif name == "provenance_derive":
        engine = get_engine(args.get("project_id"))
        artifact_type = ProvenanceType(args["artifact_type"])
        artifact_id = engine.provenance.derive(
            args["source_ids"], args["name"], artifact_type,
            operation=args.get("operation", "derive"),
            created_by=args.get("created_by")
        )
        return {"artifact_id": artifact_id}

    elif name == "provenance_lineage":
        engine = get_engine(args.get("project_id"))
        lineage = engine.get_lineage(args["artifact_id"])
        return lineage

    elif name == "provenance_get":
        engine = get_engine(args.get("project_id"))
        artifact = engine.provenance.get(args["artifact_id"])
        if artifact:
            return {
                "artifact_id": artifact.artifact_id,
                "name": artifact.name,
                "type": artifact.type.value,
                "version": artifact.version,
                "hash": artifact.hash,
            }
        return {"error": "Artifact not found"}

    elif name == "provenance_impact":
        engine = get_engine(args.get("project_id"))
        impact = engine.provenance.impact_analysis(args["artifact_id"])
        return impact

    elif name == "provenance_graph":
        engine = get_engine(args.get("project_id"))
        graph = engine.provenance.lineage_graph(args["artifact_id"], max_depth=args.get("max_depth", 5))
        return graph

    # ==================== POLICY ====================
    elif name == "policy_add":
        engine = get_engine(args.get("project_id"))
        from decision_governance.stores.policy import PolicyScope, PolicyEnforcement
        scope = PolicyScope(args.get("scope", "global"))
        enforcement = PolicyEnforcement(args.get("enforcement", "mandatory"))
        policy_id = engine.policy.add_policy(
            args["name"], description=args.get("description"),
            scope=scope, enforcement=enforcement
        )
        return {"policy_id": policy_id}

    elif name == "policy_add_rule":
        engine = get_engine(args.get("project_id"))
        rule_id = engine.policy.add_rule(
            args["policy_id"], args["name"],
            args["condition"], args["action"],
            priority=args.get("priority", 0)
        )
        return {"rule_id": rule_id}

    elif name == "policy_check":
        engine = get_engine(args.get("project_id"))
        result = engine.check_action(args["action"], args.get("context", {}))
        return result

    elif name == "policy_list":
        engine = get_engine(args.get("project_id"))
        policies = list(engine.policy.list_policies(status=args.get("status", "active")))
        return {"policies": [{"policy_id": p.policy_id, "name": p.name, "enforcement": p.enforcement.value} for p in policies]}

    elif name == "policy_violations":
        engine = get_engine(args.get("project_id"))
        from decision_governance.stores.policy import ViolationSeverity
        severity = ViolationSeverity(args["severity"]) if args.get("severity") else None
        violations = list(engine.policy.pending_violations(severity=severity, limit=args.get("limit", 50)))
        return {"violations": [{"violation_id": v.violation_id, "message": v.message, "severity": v.severity.value} for v in violations]}

    elif name == "policy_resolve_violation":
        engine = get_engine(args.get("project_id"))
        engine.policy.resolve_violation(args["violation_id"], args["resolution"], args.get("resolved_by"))
        return {"resolved": True}

    elif name == "policy_add_exemption":
        engine = get_engine(args.get("project_id"))
        engine.policy.add_exemption(
            args["policy_id"], args["identity_id"],
            args.get("identity_type", "agent"), args["reason"]
        )
        return {"exemption_added": True}

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
