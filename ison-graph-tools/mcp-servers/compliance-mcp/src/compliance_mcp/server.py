"""
Compliance MCP Server - Unified Regulatory Compliance
=====================================================

MCP server for unified regulatory compliance:
- GDPR (EU General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- HIPAA (Health Insurance Portability and Accountability Act)
- EU AI Act
- PII Governance
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from unified_governance import UnifiedGovernanceEngine, quick_unified_governance
from gdpr_governance import GDPRGovernance, LawfulBasis, DataSubjectRight
from ccpa_governance import CCPAGovernance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compliance-mcp")


@dataclass
class ServerState:
    engines: Dict[str, UnifiedGovernanceEngine] = field(default_factory=dict)
    default_project: Optional[str] = None


server = Server("compliance-mcp")
state = ServerState()


TOOLS = [
    # Engine Management
    Tool(name="compliance_init", description="Initialize compliance engine.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "regulations": {"type": "array", "items": {"type": "string"}, "default": ["gdpr", "ccpa", "pii"]}}, "required": ["project_id"]}),

    # Unified Compliance
    Tool(name="compliance_check", description="Cross-regulation compliance check.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "pii_types": {"type": "array", "items": {"type": "string"}}, "data_subject_id": {"type": "string"}, "context": {"type": "object"}}, "required": ["agent_id", "action"]}),
    Tool(name="subject_register", description="Register a data subject (unified).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "subject_id": {"type": "string"}, "email": {"type": "string"}, "jurisdiction": {"type": "string"}, "metadata": {"type": "object"}}, "required": ["subject_id"]}),
    Tool(name="pii_access_grant", description="Grant agent access to PII.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "pii_types": {"type": "array", "items": {"type": "string"}}, "purpose": {"type": "string"}, "legal_basis": {"type": "string"}}, "required": ["agent_id", "pii_types", "purpose"]}),
    Tool(name="action_record", description="Record action for audit trail.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "action": {"type": "string"}, "pii_types": {"type": "array", "items": {"type": "string"}}, "data_source": {"type": "string"}, "outcome": {"type": "string"}}, "required": ["agent_id", "action"]}),
    Tool(name="report_generate", description="Generate compliance report.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "regulation": {"type": "string"}, "format": {"type": "string", "enum": ["json", "ison", "markdown"]}}}),

    # GDPR Specific
    Tool(name="gdpr_processing_add", description="Register processing activity (Art. 30).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}, "purpose": {"type": "string"}, "lawful_basis": {"type": "string"}, "data_categories": {"type": "array", "items": {"type": "string"}}, "retention_period": {"type": "string"}}, "required": ["name", "purpose", "lawful_basis"]}),
    Tool(name="gdpr_consent_record", description="Record consent (Art. 7).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "data_subject_id": {"type": "string"}, "purpose": {"type": "string"}, "consent_type": {"type": "string"}, "evidence": {"type": "string"}}, "required": ["data_subject_id", "purpose"]}),
    Tool(name="gdpr_consent_withdraw", description="Withdraw consent.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "data_subject_id": {"type": "string"}, "purpose": {"type": "string"}}, "required": ["data_subject_id", "purpose"]}),
    Tool(name="gdpr_rights_request", description="Handle data subject rights (Art. 15-22).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "data_subject_id": {"type": "string"}, "right_type": {"type": "string", "enum": ["access", "rectification", "erasure", "restriction", "portability", "objection"]}}, "required": ["data_subject_id", "right_type"]}),
    Tool(name="gdpr_breach_report", description="Report data breach (Art. 33-34).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "description": {"type": "string"}, "data_affected": {"type": "array", "items": {"type": "string"}}, "subjects_affected": {"type": "integer"}, "severity": {"type": "string"}}, "required": ["description"]}),
    Tool(name="gdpr_dpia", description="Data Protection Impact Assessment (Art. 35).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "processing_name": {"type": "string"}, "necessity": {"type": "string"}, "risks": {"type": "array", "items": {"type": "object"}}, "mitigations": {"type": "array", "items": {"type": "object"}}}, "required": ["processing_name"]}),

    # CCPA Specific
    Tool(name="ccpa_consumer_register", description="Register CCPA consumer.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "consumer_id": {"type": "string"}, "email": {"type": "string"}, "california_resident": {"type": "boolean"}}, "required": ["consumer_id"]}),
    Tool(name="ccpa_opt_out", description="Handle Do Not Sell/Share request.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "consumer_id": {"type": "string"}, "opt_out_type": {"type": "string", "enum": ["sell", "share", "both"]}}, "required": ["consumer_id"]}),
    Tool(name="ccpa_rights_request", description="Handle CCPA consumer rights.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "consumer_id": {"type": "string"}, "right_type": {"type": "string", "enum": ["know", "delete", "correct", "limit"]}}, "required": ["consumer_id", "right_type"]}),
    Tool(name="ccpa_disclosure", description="Track disclosure to consumer.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "consumer_id": {"type": "string"}, "categories_collected": {"type": "array", "items": {"type": "string"}}, "purposes": {"type": "array", "items": {"type": "string"}}}, "required": ["consumer_id"]}),

    # HIPAA Specific (Medical)
    Tool(name="hipaa_phi_classify", description="Classify PHI (Protected Health Information).",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "data_field": {"type": "string"}, "phi_type": {"type": "string"}}, "required": ["data_field"]}),
    Tool(name="hipaa_access_authorize", description="Authorize PHI access.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "requester_id": {"type": "string"}, "patient_id": {"type": "string"}, "phi_types": {"type": "array", "items": {"type": "string"}}, "purpose": {"type": "string"}}, "required": ["requester_id", "patient_id", "purpose"]}),
    Tool(name="hipaa_minimum_necessary", description="Apply minimum necessary standard.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "request": {"type": "object"}}, "required": ["request"]}),
    Tool(name="hipaa_breach_report", description="Report HIPAA breach.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "description": {"type": "string"}, "phi_involved": {"type": "array", "items": {"type": "string"}}, "individuals_affected": {"type": "integer"}}, "required": ["description"]}),

    # EU AI Act
    Tool(name="euai_system_register", description="Register AI system.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "system_id": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "provider": {"type": "string"}}, "required": ["system_id", "name"]}),
    Tool(name="euai_risk_classify", description="Classify AI system risk level.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "system_id": {"type": "string"}, "use_case": {"type": "string"}, "sector": {"type": "string"}}, "required": ["system_id"]}),
    Tool(name="euai_prohibited_check", description="Check if system is prohibited.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "system_id": {"type": "string"}, "capabilities": {"type": "array", "items": {"type": "string"}}}, "required": ["system_id"]}),
    Tool(name="euai_conformity", description="Perform conformity assessment.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "system_id": {"type": "string"}}, "required": ["system_id"]}),

    # PII Governance
    Tool(name="pii_scan", description="Scan data for PII.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "data": {"type": "object"}}, "required": ["data"]}),
    Tool(name="pii_classify", description="Classify a data field as PII.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "field_name": {"type": "string"}, "pii_type": {"type": "string"}, "sensitivity": {"type": "string"}}, "required": ["field_name"]}),
    Tool(name="pii_inventory", description="Get PII data inventory.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}}),
    Tool(name="pii_lineage", description="Track PII data lineage.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "pii_type": {"type": "string"}}, "required": ["pii_type"]}),
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


def get_engine(project_id: Optional[str] = None) -> UnifiedGovernanceEngine:
    pid = project_id or state.default_project
    if not pid or pid not in state.engines:
        raise ValueError(f"Compliance engine not found: {pid}")
    return state.engines[pid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "compliance_init":
        project_id = args["project_id"]
        engine = quick_unified_governance(setup_defaults=True)
        state.engines[project_id] = engine
        state.default_project = project_id
        return {"project_id": project_id, "regulations": args.get("regulations", ["gdpr", "ccpa", "pii"]), "initialized": True}

    elif name == "compliance_check":
        engine = get_engine(args.get("project_id"))
        result = engine.check_compliance(args["agent_id"], args["action"], args.get("pii_types", []), args.get("data_subject_id"), args.get("context", {}))
        return result

    elif name == "subject_register":
        engine = get_engine(args.get("project_id"))
        engine.register_subject(args["subject_id"], args.get("email"), args.get("jurisdiction"), args.get("metadata", {}))
        return {"subject_id": args["subject_id"], "registered": True}

    elif name == "pii_access_grant":
        engine = get_engine(args.get("project_id"))
        engine.grant_agent_pii_access(args["agent_id"], args["pii_types"], args["purpose"], args.get("legal_basis", "legitimate_interest"))
        return {"granted": True}

    elif name == "action_record":
        engine = get_engine(args.get("project_id"))
        engine.record_agent_action(args["agent_id"], args["action"], args.get("pii_types", []), args.get("data_source"), args.get("outcome", "success"))
        return {"recorded": True}

    elif name == "report_generate":
        engine = get_engine(args.get("project_id"))
        report = engine.generate_report(args.get("regulation"), args.get("format", "json"))
        return {"report": report}

    # GDPR handlers
    elif name == "gdpr_processing_add":
        engine = get_engine(args.get("project_id"))
        activity_id = engine.gdpr.processing.register_activity(args["name"], args["purpose"], args["lawful_basis"], args.get("data_categories", []), args.get("retention_period"))
        return {"activity_id": activity_id}

    elif name == "gdpr_consent_record":
        engine = get_engine(args.get("project_id"))
        consent_id = engine.gdpr.consent.record_consent(args["data_subject_id"], args["purpose"], args.get("consent_type", "explicit"), args.get("evidence"))
        return {"consent_id": consent_id}

    elif name == "gdpr_consent_withdraw":
        engine = get_engine(args.get("project_id"))
        engine.gdpr.consent.withdraw_consent(args["data_subject_id"], args["purpose"])
        return {"withdrawn": True}

    elif name == "gdpr_rights_request":
        engine = get_engine(args.get("project_id"))
        request_id = engine.gdpr.rights.submit_request(args["data_subject_id"], args["right_type"])
        return {"request_id": request_id}

    elif name == "gdpr_breach_report":
        engine = get_engine(args.get("project_id"))
        breach_id = engine.gdpr.breach.report(args["description"], args.get("data_affected", []), args.get("subjects_affected", 0), args.get("severity", "medium"))
        return {"breach_id": breach_id}

    elif name == "gdpr_dpia":
        engine = get_engine(args.get("project_id"))
        dpia_id = engine.gdpr.dpia.create(args["processing_name"], args.get("necessity", ""), args.get("risks", []), args.get("mitigations", []))
        return {"dpia_id": dpia_id}

    # CCPA handlers
    elif name == "ccpa_consumer_register":
        engine = get_engine(args.get("project_id"))
        engine.ccpa.consumer.register(args["consumer_id"], args.get("email"), args.get("california_resident", True))
        return {"consumer_id": args["consumer_id"], "registered": True}

    elif name == "ccpa_opt_out":
        engine = get_engine(args.get("project_id"))
        engine.ccpa.opt_out(args["consumer_id"], args.get("opt_out_type", "both"))
        return {"opted_out": True}

    elif name == "ccpa_rights_request":
        engine = get_engine(args.get("project_id"))
        request_id = engine.ccpa.rights.submit(args["consumer_id"], args["right_type"])
        return {"request_id": request_id}

    elif name == "ccpa_disclosure":
        engine = get_engine(args.get("project_id"))
        engine.ccpa.disclosure.record(args["consumer_id"], args.get("categories_collected", []), args.get("purposes", []))
        return {"disclosed": True}

    # HIPAA handlers
    elif name == "hipaa_phi_classify":
        engine = get_engine(args.get("project_id"))
        classification = engine.hipaa.classify(args["data_field"], args.get("phi_type"))
        return classification

    elif name == "hipaa_access_authorize":
        engine = get_engine(args.get("project_id"))
        auth_id = engine.hipaa.authorize(args["requester_id"], args["patient_id"], args.get("phi_types", []), args["purpose"])
        return {"authorization_id": auth_id}

    elif name == "hipaa_minimum_necessary":
        engine = get_engine(args.get("project_id"))
        result = engine.hipaa.apply_minimum_necessary(args["request"])
        return result

    elif name == "hipaa_breach_report":
        engine = get_engine(args.get("project_id"))
        breach_id = engine.hipaa.report_breach(args["description"], args.get("phi_involved", []), args.get("individuals_affected", 0))
        return {"breach_id": breach_id}

    # EU AI Act handlers
    elif name == "euai_system_register":
        engine = get_engine(args.get("project_id"))
        engine.euai.register_system(args["system_id"], args["name"], args.get("description", ""), args.get("provider", ""))
        return {"system_id": args["system_id"], "registered": True}

    elif name == "euai_risk_classify":
        engine = get_engine(args.get("project_id"))
        risk = engine.euai.classify_risk(args["system_id"], args.get("use_case"), args.get("sector"))
        return {"system_id": args["system_id"], "risk_level": risk}

    elif name == "euai_prohibited_check":
        engine = get_engine(args.get("project_id"))
        result = engine.euai.check_prohibited(args["system_id"], args.get("capabilities", []))
        return result

    elif name == "euai_conformity":
        engine = get_engine(args.get("project_id"))
        assessment = engine.euai.conformity_assessment(args["system_id"])
        return assessment

    # PII handlers
    elif name == "pii_scan":
        engine = get_engine(args.get("project_id"))
        results = engine.pii.scan(args["data"])
        return {"pii_found": results}

    elif name == "pii_classify":
        engine = get_engine(args.get("project_id"))
        engine.pii.classify(args["field_name"], args.get("pii_type"), args.get("sensitivity", "medium"))
        return {"classified": True}

    elif name == "pii_inventory":
        engine = get_engine(args.get("project_id"))
        inventory = engine.pii.get_inventory()
        return {"inventory": inventory}

    elif name == "pii_lineage":
        engine = get_engine(args.get("project_id"))
        lineage = engine.pii.get_lineage(args["pii_type"])
        return {"lineage": lineage}

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
