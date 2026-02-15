"""
Agent Governance MCP Server - Policy, Authority, Safety Control
================================================================

MCP server for comprehensive AI agent governance with 15 domains:
1. Authority & Delegation
2. Policy Engine
3. Compliance Framework
4. Audit Trail
5. Risk Assessment
6. Human Oversight (Escalation)
7. Resource Governance
8. Multi-Agent Coordination
9. Ethics & Values
10. Capability Governance
11. Incident Response
12. Meta-Governance
13. Cross-Organizational
14. Temporal Governance
15. Observability
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from agent_governance import (
    GovernanceEngine,
    quick_governance,
    AuthorityStore,
    PolicyStore,
    AuditStore,
    RiskStore,
    EscalationStore,
    EthicsStore,
    AuthorityLevel,
    RiskLevel,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-governance-mcp")


@dataclass
class ServerState:
    engines: Dict[str, GovernanceEngine] = field(default_factory=dict)
    default_project: Optional[str] = None


server = Server("agent-governance-mcp")
state = ServerState()


TOOLS = [
    # --- Engine Management ---
    Tool(name="governance_init", description="Initialize governance engine for a project.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "setup_defaults": {"type": "boolean", "default": True}}, "required": ["project_id"]}),
    Tool(name="governance_list", description="List all governance engines.",
         inputSchema={"type": "object", "properties": {}}),

    # --- Authority (Domain 1) ---
    Tool(name="agent_register", description="Register an agent with authority level.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "authority_level": {"type": "string", "enum": ["none", "read", "write", "admin", "super_admin"]}, "capabilities": {"type": "array", "items": {"type": "string"}}}, "required": ["agent_id"]}),
    Tool(name="human_register", description="Register a human overseer.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "human_id": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string"}}, "required": ["human_id", "name"]}),
    Tool(name="authority_grant", description="Grant authority to an agent.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "scope": {"type": "string"}, "level": {"type": "string"}}, "required": ["agent_id", "scope", "level"]}),
    Tool(name="authority_revoke", description="Revoke authority from an agent.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "scope": {"type": "string"}}, "required": ["agent_id", "scope"]}),
    Tool(name="authority_check", description="Check if agent has authority for action.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "context": {"type": "object"}}, "required": ["agent_id", "action"]}),
    Tool(name="delegation_create", description="Delegate authority from one agent to another.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "delegator_id": {"type": "string"}, "delegate_id": {"type": "string"}, "scope": {"type": "string"}, "expires_at": {"type": "string"}}, "required": ["delegator_id", "delegate_id", "scope"]}),

    # --- Policy (Domain 2) ---
    Tool(name="policy_add", description="Add a governance policy.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "scope": {"type": "string"}, "enforcement": {"type": "string", "enum": ["mandatory", "recommended", "optional"]}}, "required": ["name"]}),
    Tool(name="policy_evaluate", description="Evaluate context against policies.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "context": {"type": "object"}, "action": {"type": "string"}}, "required": ["context", "action"]}),
    Tool(name="rule_add", description="Add a rule to a policy.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "policy_id": {"type": "string"}, "condition": {"type": "string"}, "action": {"type": "string"}}, "required": ["policy_id", "condition", "action"]}),
    Tool(name="policy_list", description="List all policies.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),

    # --- Action Control ---
    Tool(name="action_check", description="Check if an action is permitted.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "context": {"type": "object"}}, "required": ["agent_id", "action"]}),
    Tool(name="action_record", description="Record an action taken.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "context": {"type": "object"}, "outcome": {"type": "string"}}, "required": ["agent_id", "action"]}),

    # --- Escalation (Domain 6) ---
    Tool(name="escalation_trigger", description="Trigger an escalation to human.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "reason": {"type": "string"}, "context": {"type": "object"}, "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]}}, "required": ["agent_id", "reason"]}),
    Tool(name="escalation_resolve", description="Resolve an escalation.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "escalation_id": {"type": "string"}, "resolution": {"type": "string"}, "resolved_by": {"type": "string"}}, "required": ["escalation_id", "resolution", "resolved_by"]}),
    Tool(name="escalation_pending", description="List pending escalations.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
    Tool(name="reviewer_add", description="Add a human reviewer.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "human_id": {"type": "string"}, "review_types": {"type": "array", "items": {"type": "string"}}}, "required": ["human_id"]}),

    # --- Risk (Domain 5) ---
    Tool(name="risk_assess", description="Assess risk posture.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "context": {"type": "object"}}}),
    Tool(name="threat_add", description="Add a threat.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "likelihood": {"type": "string"}, "impact": {"type": "string"}}, "required": ["name"]}),
    Tool(name="control_add", description="Add a control.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"}, "threat_id": {"type": "string"}}, "required": ["name"]}),
    Tool(name="incident_report", description="Report an incident.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}, "severity": {"type": "string"}}, "required": ["title"]}),

    # --- Coordination (Domain 8) ---
    Tool(name="group_create", description="Create an agent group.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "group_id": {"type": "string"}, "name": {"type": "string"}, "members": {"type": "array", "items": {"type": "string"}}}, "required": ["group_id", "name"]}),
    Tool(name="role_assign", description="Assign a role to an agent.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "role": {"type": "string"}, "group_id": {"type": "string"}}, "required": ["agent_id", "role"]}),
    Tool(name="protocol_add", description="Add a coordination protocol.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "steps": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "steps"]}),

    # --- Ethics (Domain 9) ---
    Tool(name="value_add", description="Add a core value.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "priority": {"type": "integer"}}, "required": ["name"]}),
    Tool(name="principle_add", description="Add an ethical principle.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "related_values": {"type": "array", "items": {"type": "string"}}}, "required": ["name"]}),
    Tool(name="dilemma_resolve", description="Resolve an ethical dilemma.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "situation": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}}, "required": ["situation", "options"]}),
    Tool(name="alignment_score", description="Calculate value alignment score.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}, "required": ["agent_id"]}),

    # --- Audit (Domain 4) ---
    Tool(name="audit_trail", description="Get decision audit trail.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}}}),
    Tool(name="audit_export", description="Export audit log for compliance.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "format": {"type": "string", "enum": ["json", "csv", "ison"]}}}),
    Tool(name="audit_query", description="Query audit log.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "limit": {"type": "integer", "default": 100}}}),
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


def get_engine(project_id: Optional[str] = None) -> GovernanceEngine:
    pid = project_id or state.default_project
    if not pid or pid not in state.engines:
        raise ValueError(f"Governance engine not found: {pid}")
    return state.engines[pid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "governance_init":
        project_id = args["project_id"]
        engine = quick_governance(project_id, setup_defaults=args.get("setup_defaults", True))
        state.engines[project_id] = engine
        state.default_project = project_id
        return {"project_id": project_id, "initialized": True}

    elif name == "governance_list":
        return {"engines": list(state.engines.keys()), "default": state.default_project}

    # Authority
    elif name == "agent_register":
        engine = get_engine(args.get("project_id"))
        engine.authority.register_agent(args["agent_id"], args.get("authority_level", "read"), args.get("capabilities", []))
        return {"agent_id": args["agent_id"], "registered": True}

    elif name == "human_register":
        engine = get_engine(args.get("project_id"))
        engine.authority.register_human(args["human_id"], args["name"], args.get("role", "reviewer"))
        return {"human_id": args["human_id"], "registered": True}

    elif name == "authority_grant":
        engine = get_engine(args.get("project_id"))
        engine.authority.grant(args["agent_id"], args["scope"], args["level"])
        return {"granted": True}

    elif name == "authority_revoke":
        engine = get_engine(args.get("project_id"))
        engine.authority.revoke(args["agent_id"], args["scope"])
        return {"revoked": True}

    elif name == "authority_check":
        engine = get_engine(args.get("project_id"))
        result = engine.authority.check(args["agent_id"], args["action"], args.get("context", {}))
        return {"permitted": result.get("permitted", False), "reason": result.get("reason", "")}

    elif name == "delegation_create":
        engine = get_engine(args.get("project_id"))
        engine.authority.delegate(args["delegator_id"], args["delegate_id"], args["scope"], args.get("expires_at"))
        return {"delegated": True}

    # Policy
    elif name == "policy_add":
        engine = get_engine(args.get("project_id"))
        policy_id = engine.policy.add(args["name"], args.get("description", ""), args.get("scope", "global"), args.get("enforcement", "mandatory"))
        return {"policy_id": policy_id}

    elif name == "policy_evaluate":
        engine = get_engine(args.get("project_id"))
        result = engine.policy.evaluate(args["context"], args["action"])
        return result

    elif name == "rule_add":
        engine = get_engine(args.get("project_id"))
        engine.policy.add_rule(args["policy_id"], args["condition"], args["action"])
        return {"rule_added": True}

    elif name == "policy_list":
        engine = get_engine(args.get("project_id"))
        policies = list(engine.policy.list())
        return {"policies": policies}

    # Action Control
    elif name == "action_check":
        engine = get_engine(args.get("project_id"))
        result = engine.check_action(args["agent_id"], args["action"], args.get("context", {}))
        return result

    elif name == "action_record":
        engine = get_engine(args.get("project_id"))
        engine.audit.record_action(args["agent_id"], args["action"], args.get("context", {}), args.get("outcome", "success"))
        return {"recorded": True}

    # Escalation
    elif name == "escalation_trigger":
        engine = get_engine(args.get("project_id"))
        esc_id = engine.escalation.trigger(args["agent_id"], args["reason"], args.get("context", {}), args.get("urgency", "medium"))
        return {"escalation_id": esc_id, "triggered": True}

    elif name == "escalation_resolve":
        engine = get_engine(args.get("project_id"))
        engine.escalation.resolve(args["escalation_id"], args["resolution"], args["resolved_by"])
        return {"resolved": True}

    elif name == "escalation_pending":
        engine = get_engine(args.get("project_id"))
        pending = list(engine.escalation.pending())
        return {"pending": pending, "count": len(pending)}

    elif name == "reviewer_add":
        engine = get_engine(args.get("project_id"))
        engine.escalation.add_reviewer(args["human_id"], args.get("review_types", []))
        return {"reviewer_added": True}

    # Risk
    elif name == "risk_assess":
        engine = get_engine(args.get("project_id"))
        assessment = engine.risk.assess(args.get("context", {}))
        return assessment

    elif name == "threat_add":
        engine = get_engine(args.get("project_id"))
        threat_id = engine.risk.add_threat(args["name"], args.get("description", ""), args.get("likelihood", "medium"), args.get("impact", "medium"))
        return {"threat_id": threat_id}

    elif name == "control_add":
        engine = get_engine(args.get("project_id"))
        control_id = engine.risk.add_control(args["name"], args.get("type", "preventive"), args.get("threat_id"))
        return {"control_id": control_id}

    elif name == "incident_report":
        engine = get_engine(args.get("project_id"))
        incident_id = engine.risk.report_incident(args["title"], args.get("description", ""), args.get("severity", "medium"))
        return {"incident_id": incident_id}

    # Coordination
    elif name == "group_create":
        engine = get_engine(args.get("project_id"))
        engine.coordination.create_group(args["group_id"], args["name"], args.get("members", []))
        return {"group_id": args["group_id"], "created": True}

    elif name == "role_assign":
        engine = get_engine(args.get("project_id"))
        engine.coordination.assign_role(args["agent_id"], args["role"], args.get("group_id"))
        return {"assigned": True}

    elif name == "protocol_add":
        engine = get_engine(args.get("project_id"))
        protocol_id = engine.coordination.add_protocol(args["name"], args["steps"])
        return {"protocol_id": protocol_id}

    # Ethics
    elif name == "value_add":
        engine = get_engine(args.get("project_id"))
        value_id = engine.ethics.add_value(args["name"], args.get("description", ""), args.get("priority", 1))
        return {"value_id": value_id}

    elif name == "principle_add":
        engine = get_engine(args.get("project_id"))
        principle_id = engine.ethics.add_principle(args["name"], args.get("description", ""), args.get("related_values", []))
        return {"principle_id": principle_id}

    elif name == "dilemma_resolve":
        engine = get_engine(args.get("project_id"))
        resolution = engine.ethics.resolve_dilemma(args["situation"], args["options"])
        return resolution

    elif name == "alignment_score":
        engine = get_engine(args.get("project_id"))
        score = engine.ethics.alignment_score(args["agent_id"])
        return {"agent_id": args["agent_id"], "alignment_score": score}

    # Audit
    elif name == "audit_trail":
        engine = get_engine(args.get("project_id"))
        trail = engine.audit.get_trail(args.get("agent_id"), args.get("start_time"), args.get("end_time"))
        return {"trail": list(trail)}

    elif name == "audit_export":
        engine = get_engine(args.get("project_id"))
        export = engine.audit.export(args.get("format", "json"))
        return {"export": export}

    elif name == "audit_query":
        engine = get_engine(args.get("project_id"))
        results = engine.audit.query(args.get("agent_id"), args.get("action"), args.get("limit", 100))
        return {"results": list(results)}

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
