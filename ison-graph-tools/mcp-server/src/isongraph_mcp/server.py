"""
ISONGraph Unified MCP Server
============================

A single MCP server that exposes ALL ISONGraph tools:
- Format Converters (GraphML, RDF, CSV, Cypher, DOT)
- Schema Generator
- ISON Cache
- Agent Memory
- Agent Governance
- Agent Learning
- Regulatory Compliance (GDPR, CCPA, PII, EU AI Act, HIPAA)
- Code Flow Graph
- Unified Governance

This allows any MCP-compatible AI agent to use all capabilities
through a single connection.
"""

import json
import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

# ISONGraph imports
from ison_graph import ISONGraph

# Tool imports (lazy-loaded for efficiency)
_converters = None
_schema_generator = None
_ison_cache = None
_agent_memory = None
_agent_governance = None
_agent_learning = None
_gdpr_governance = None
_ccpa_governance = None
_pii_governance = None
_eu_ai_act_governance = None
_medical_governance = None
_unified_governance = None
_code_flow_graph = None


def get_converters():
    global _converters
    if _converters is None:
        from tools.converters import (
            GraphMLConverter,
            RDFConverter,
            CSVConverter,
            CypherConverter,
            DOTConverter,
        )
        _converters = {
            "graphml": GraphMLConverter,
            "rdf": RDFConverter,
            "csv": CSVConverter,
            "cypher": CypherConverter,
            "dot": DOTConverter,
        }
    return _converters


def get_schema_generator():
    global _schema_generator
    if _schema_generator is None:
        from tools.schema_generator import SchemaGenerator, SchemaFormatter
        _schema_generator = {"generator": SchemaGenerator, "formatter": SchemaFormatter}
    return _schema_generator


def get_ison_cache():
    global _ison_cache
    if _ison_cache is None:
        from ison_cache import ISONCache, ISONGraphCache, TokenManager
        _ison_cache = {
            "cache": ISONCache,
            "graph_cache": ISONGraphCache,
            "token_manager": TokenManager,
        }
    return _ison_cache


def get_agent_memory():
    global _agent_memory
    if _agent_memory is None:
        from agent_memory import AgentMemory, AgentIntegration, prepare_for_project
        _agent_memory = {
            "memory": AgentMemory,
            "integration": AgentIntegration,
            "prepare": prepare_for_project,
        }
    return _agent_memory


def get_agent_governance():
    global _agent_governance
    if _agent_governance is None:
        from agent_governance import GovernanceEngine, quick_governance
        _agent_governance = {
            "engine": GovernanceEngine,
            "quick": quick_governance,
        }
    return _agent_governance


def get_agent_learning():
    global _agent_learning
    if _agent_learning is None:
        from agent_learning import AgentLearningEngine
        _agent_learning = {"engine": AgentLearningEngine}
    return _agent_learning


def get_gdpr():
    global _gdpr_governance
    if _gdpr_governance is None:
        from gdpr_governance import GDPRGovernance
        _gdpr_governance = {"engine": GDPRGovernance}
    return _gdpr_governance


def get_ccpa():
    global _ccpa_governance
    if _ccpa_governance is None:
        from ccpa_governance import CCPAGovernance
        _ccpa_governance = {"engine": CCPAGovernance}
    return _ccpa_governance


def get_pii():
    global _pii_governance
    if _pii_governance is None:
        from pii_governance import PIIGovernance
        _pii_governance = {"engine": PIIGovernance}
    return _pii_governance


def get_eu_ai_act():
    global _eu_ai_act_governance
    if _eu_ai_act_governance is None:
        from eu_ai_act_governance import EUAIActGovernanceEngine
        _eu_ai_act_governance = {"engine": EUAIActGovernanceEngine}
    return _eu_ai_act_governance


def get_medical():
    global _medical_governance
    if _medical_governance is None:
        from medical_governance import HIPAAGovernanceEngine
        _medical_governance = {"engine": HIPAAGovernanceEngine}
    return _medical_governance


def get_unified():
    global _unified_governance
    if _unified_governance is None:
        from unified_governance import UnifiedGovernanceEngine, quick_unified_governance
        _unified_governance = {
            "engine": UnifiedGovernanceEngine,
            "quick": quick_unified_governance,
        }
    return _unified_governance


def get_code_flow():
    global _code_flow_graph
    if _code_flow_graph is None:
        from code_flow_graph import CodeFlowAnalyzer, analyze_local, analyze_github
        _code_flow_graph = {
            "analyzer": CodeFlowAnalyzer,
            "analyze_local": analyze_local,
            "analyze_github": analyze_github,
        }
    return _code_flow_graph


@dataclass
class ServerState:
    """Shared state across all tools."""
    graphs: dict = field(default_factory=dict)
    memories: dict = field(default_factory=dict)
    governance_engines: dict = field(default_factory=dict)
    learning_engines: dict = field(default_factory=dict)
    caches: dict = field(default_factory=dict)
    compliance_engines: dict = field(default_factory=dict)


# Global state
state = ServerState()


# ============================================================================
# MCP SERVER DEFINITION
# ============================================================================

server = Server("isongraph-unified")


# ============================================================================
# TOOL DEFINITIONS - All 80+ tools organized by category
# ============================================================================

def get_all_tools() -> list[Tool]:
    """Return all available tools."""
    tools = []

    # --- CONVERTER TOOLS ---
    tools.extend([
        Tool(
            name="convert_to_graphml",
            description="Convert ISONGraph to GraphML format (XML, compatible with Gephi/yEd)",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph identifier"},
                    "include_properties": {"type": "boolean", "default": True},
                },
                "required": ["graph_id"]
            }
        ),
        Tool(
            name="convert_to_rdf",
            description="Convert ISONGraph to RDF/Turtle format (semantic web)",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "base_uri": {"type": "string", "default": "http://example.org/"},
                    "format": {"type": "string", "enum": ["turtle", "ntriples"], "default": "turtle"},
                },
                "required": ["graph_id"]
            }
        ),
        Tool(
            name="convert_to_csv",
            description="Convert ISONGraph to CSV format (nodes.csv, edges.csv)",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "delimiter": {"type": "string", "default": ","},
                },
                "required": ["graph_id"]
            }
        ),
        Tool(
            name="convert_to_cypher",
            description="Convert ISONGraph to Neo4j Cypher statements",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "mode": {"type": "string", "enum": ["create", "merge"], "default": "merge"},
                    "batch": {"type": "boolean", "default": False},
                },
                "required": ["graph_id"]
            }
        ),
        Tool(
            name="convert_to_dot",
            description="Convert ISONGraph to DOT/Graphviz format for visualization",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "label_property": {"type": "string", "default": "name"},
                    "clustered": {"type": "boolean", "default": False},
                },
                "required": ["graph_id"]
            }
        ),
        Tool(
            name="import_from_graphml",
            description="Import a graph from GraphML format",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "content": {"type": "string", "description": "GraphML XML content"},
                },
                "required": ["graph_id", "content"]
            }
        ),
    ])

    # --- SCHEMA GENERATOR TOOLS ---
    tools.extend([
        Tool(
            name="generate_schema",
            description="Auto-generate ISONGraph schema from JSON data with type inference",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "object", "description": "JSON graph data with nodes and edges"},
                    "name": {"type": "string", "default": "generated_schema"},
                    "infer_constraints": {"type": "boolean", "default": True},
                    "infer_enums": {"type": "boolean", "default": True},
                    "infer_patterns": {"type": "boolean", "default": True},
                },
                "required": ["data"]
            }
        ),
        Tool(
            name="format_schema",
            description="Format schema in different output formats",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "format": {"type": "string", "enum": ["python", "typescript", "json", "ison"]},
                },
                "required": ["schema", "format"]
            }
        ),
        Tool(
            name="analyze_data_structure",
            description="Analyze graph data structure and return statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                },
                "required": ["data"]
            }
        ),
    ])

    # --- ISON CACHE TOOLS ---
    tools.extend([
        Tool(
            name="cache_set",
            description="Store a value in token-efficient ISON cache",
            inputSchema={
                "type": "object",
                "properties": {
                    "cache_id": {"type": "string", "default": "default"},
                    "key": {"type": "string"},
                    "value": {"type": "object"},
                    "ttl": {"type": "integer", "description": "TTL in seconds"},
                },
                "required": ["key", "value"]
            }
        ),
        Tool(
            name="cache_get",
            description="Retrieve value from cache in ISON format (token-efficient)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cache_id": {"type": "string", "default": "default"},
                    "key": {"type": "string"},
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="cache_get_within_budget",
            description="Get multiple cached values within a token budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "cache_id": {"type": "string", "default": "default"},
                    "patterns": {"type": "array", "items": {"type": "string"}},
                    "token_budget": {"type": "integer"},
                },
                "required": ["patterns", "token_budget"]
            }
        ),
        Tool(
            name="cache_graph_traverse",
            description="Cache a graph and traverse with multi-hop support",
            inputSchema={
                "type": "object",
                "properties": {
                    "cache_id": {"type": "string", "default": "default"},
                    "start_node": {"type": "string"},
                    "max_hops": {"type": "integer", "default": 2},
                },
                "required": ["start_node"]
            }
        ),
        Tool(
            name="count_tokens",
            description="Count tokens for content (useful for LLM context management)",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                },
                "required": ["content"]
            }
        ),
    ])

    # --- AGENT MEMORY TOOLS ---
    tools.extend([
        Tool(
            name="memory_init",
            description="Initialize agent memory for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="memory_get_context",
            description="Get coding context for a task (conventions, decisions, bugs, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "task": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project_id", "task"]
            }
        ),
        Tool(
            name="memory_add_convention",
            description="Record a code convention",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "category": {"type": "string"},
                    "rule": {"type": "string"},
                    "enforced_by": {"type": "string"},
                    "example": {"type": "string"},
                },
                "required": ["project_id", "category", "rule"]
            }
        ),
        Tool(
            name="memory_add_decision",
            description="Record an architectural decision (ADR)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "title": {"type": "string"},
                    "context": {"type": "string"},
                    "consequences_positive": {"type": "array", "items": {"type": "string"}},
                    "consequences_negative": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project_id", "title", "context"]
            }
        ),
        Tool(
            name="memory_add_bug_pattern",
            description="Record a bug pattern for future prevention",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "name": {"type": "string"},
                    "signature": {"type": "string"},
                    "modules_affected": {"type": "array", "items": {"type": "string"}},
                    "fix_template": {"type": "string"},
                },
                "required": ["project_id", "name", "signature"]
            }
        ),
        Tool(
            name="memory_check_before_coding",
            description="Check if an approach might cause known issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "approach": {"type": "string"},
                },
                "required": ["project_id", "approach"]
            }
        ),
        Tool(
            name="memory_session_start",
            description="Start a new coding session",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "task_description": {"type": "string"},
                },
                "required": ["project_id", "task_description"]
            }
        ),
        Tool(
            name="memory_session_end",
            description="End a coding session with summary",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "completion": {"type": "number", "minimum": 0, "maximum": 1},
                    "outcome": {"type": "string", "enum": ["success", "partial", "blocked", "failed"]},
                    "lessons": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project_id", "completion", "outcome"]
            }
        ),
        Tool(
            name="memory_get_handoff",
            description="Get session handoff for continuity",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="memory_who_knows",
            description="Find who has expertise in a topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "topic": {"type": "string"},
                },
                "required": ["project_id", "topic"]
            }
        ),
        Tool(
            name="memory_save",
            description="Save memory to file",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["project_id", "path"]
            }
        ),
        Tool(
            name="memory_load",
            description="Load memory from file",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["project_id", "path"]
            }
        ),
    ])

    # --- AGENT GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="governance_init",
            description="Initialize governance engine with optional defaults",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "setup_defaults": {"type": "boolean", "default": True},
                },
                "required": ["governance_id"]
            }
        ),
        Tool(
            name="governance_register_agent",
            description="Register an agent with authority level",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "name": {"type": "string"},
                    "authority_level": {"type": "string", "enum": ["none", "limited", "standard", "delegated", "elevated", "full"]},
                },
                "required": ["governance_id", "agent_id", "name", "authority_level"]
            }
        ),
        Tool(
            name="governance_check_action",
            description="Check if an action is permitted for an agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "action": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["governance_id", "agent_id", "action"]
            }
        ),
        Tool(
            name="governance_add_policy",
            description="Add a governance policy with rules",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "policy_name": {"type": "string"},
                    "rules": {"type": "array", "items": {"type": "object"}},
                    "priority": {"type": "integer", "default": 50},
                },
                "required": ["governance_id", "policy_name", "rules"]
            }
        ),
        Tool(
            name="governance_evaluate_policy",
            description="Evaluate policies against a context",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["governance_id", "context"]
            }
        ),
        Tool(
            name="governance_add_escalation_trigger",
            description="Add an escalation trigger condition",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "condition": {"type": "string"},
                    "level": {"type": "string", "enum": ["L1_SELF", "L2_PEER", "L3_OPERATOR", "L4_MANAGER", "L5_EXECUTIVE"]},
                    "timeout": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["governance_id", "condition", "level"]
            }
        ),
        Tool(
            name="governance_trigger_escalation",
            description="Trigger an escalation based on context",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["governance_id", "context"]
            }
        ),
        Tool(
            name="governance_resolve_escalation",
            description="Resolve an escalation (human action)",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "escalation_id": {"type": "string"},
                    "decision": {"type": "string", "enum": ["approved", "denied", "modified"]},
                    "reason": {"type": "string"},
                },
                "required": ["governance_id", "escalation_id", "decision", "reason"]
            }
        ),
        Tool(
            name="governance_assess_risk",
            description="Get risk posture assessment",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                },
                "required": ["governance_id"]
            }
        ),
        Tool(
            name="governance_report_incident",
            description="Report a security/compliance incident",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["governance_id", "severity", "category", "description"]
            }
        ),
        Tool(
            name="governance_create_agent_group",
            description="Create a multi-agent coordination group",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "group_name": {"type": "string"},
                    "description": {"type": "string"},
                    "membership_type": {"type": "string", "enum": ["static", "dynamic"]},
                },
                "required": ["governance_id", "group_name"]
            }
        ),
        Tool(
            name="governance_assign_group_role",
            description="Assign a role to an agent in a group",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "group_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "role": {"type": "string"},
                    "permissions": {"type": "string"},
                },
                "required": ["governance_id", "group_id", "agent_id", "role"]
            }
        ),
        Tool(
            name="governance_get_audit_trail",
            description="Get audit trail of decisions",
            inputSchema={
                "type": "object",
                "properties": {
                    "governance_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "days": {"type": "integer", "default": 7},
                },
                "required": ["governance_id"]
            }
        ),
    ])

    # --- AGENT LEARNING TOOLS ---
    tools.extend([
        Tool(
            name="learning_init",
            description="Initialize learning engine for an agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_id": {"type": "string"},
                },
                "required": ["learning_id"]
            }
        ),
        Tool(
            name="learning_record_experience",
            description="Record an experience for learning",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "task": {"type": "string"},
                    "task_type": {"type": "string"},
                    "outcome": {"type": "string", "enum": ["success", "partial_success", "failure", "blocked"]},
                    "reward_signal": {"type": "number"},
                    "key_learnings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["learning_id", "agent_id", "task", "outcome"]
            }
        ),
        Tool(
            name="learning_record_mistake",
            description="Record a mistake for pattern detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "category": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "task_context": {"type": "string"},
                    "agent_action": {"type": "string"},
                    "expected_action": {"type": "string"},
                    "root_cause": {"type": "string"},
                },
                "required": ["learning_id", "agent_id", "category", "severity", "task_context"]
            }
        ),
        Tool(
            name="learning_identify_retraining_needs",
            description="Identify areas where agent needs retraining",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                },
                "required": ["learning_id", "agent_id"]
            }
        ),
        Tool(
            name="learning_generate_curriculum",
            description="Generate retraining curriculum",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "need_id": {"type": "string"},
                },
                "required": ["learning_id", "agent_id", "need_id"]
            }
        ),
        Tool(
            name="learning_get_skill_progression",
            description="Get agent's skill progression",
            inputSchema={
                "type": "object",
                "properties": {
                    "learning_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                },
                "required": ["learning_id", "agent_id"]
            }
        ),
    ])

    # --- GDPR GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="gdpr_register_processing",
            description="Register a processing activity (Article 30)",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "gdpr"},
                    "name": {"type": "string"},
                    "purpose": {"type": "string"},
                    "lawful_basis": {"type": "string"},
                    "data_categories": {"type": "array", "items": {"type": "string"}},
                    "retention_period": {"type": "string"},
                },
                "required": ["name", "purpose", "lawful_basis"]
            }
        ),
        Tool(
            name="gdpr_record_consent",
            description="Record consent (Article 7)",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "gdpr"},
                    "data_subject_id": {"type": "string"},
                    "purpose": {"type": "string"},
                    "consent_type": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["data_subject_id", "purpose"]
            }
        ),
        Tool(
            name="gdpr_submit_rights_request",
            description="Submit data subject rights request (Articles 15-22)",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "gdpr"},
                    "data_subject_id": {"type": "string"},
                    "right_type": {"type": "string", "enum": ["access", "rectification", "erasure", "restriction", "portability", "objection"]},
                },
                "required": ["data_subject_id", "right_type"]
            }
        ),
        Tool(
            name="gdpr_report_breach",
            description="Report a data breach (Articles 33-34)",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "gdpr"},
                    "description": {"type": "string"},
                    "data_categories_affected": {"type": "array", "items": {"type": "string"}},
                    "subjects_affected_count": {"type": "integer"},
                    "severity": {"type": "string"},
                },
                "required": ["description", "data_categories_affected"]
            }
        ),
        Tool(
            name="gdpr_get_compliance_status",
            description="Get GDPR compliance status",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "gdpr"},
                },
                "required": []
            }
        ),
    ])

    # --- CCPA GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="ccpa_register_consumer",
            description="Register a California consumer",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "ccpa"},
                    "consumer_id": {"type": "string"},
                    "email": {"type": "string"},
                    "is_california_resident": {"type": "boolean"},
                },
                "required": ["consumer_id"]
            }
        ),
        Tool(
            name="ccpa_process_opt_out",
            description="Process Do Not Sell / Do Not Share opt-out",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "ccpa"},
                    "consumer_id": {"type": "string"},
                    "opt_out_sale": {"type": "boolean"},
                    "opt_out_share": {"type": "boolean"},
                },
                "required": ["consumer_id"]
            }
        ),
        Tool(
            name="ccpa_submit_request",
            description="Submit consumer rights request",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "ccpa"},
                    "consumer_id": {"type": "string"},
                    "right_type": {"type": "string", "enum": ["know", "delete", "correct", "opt_out", "limit_spi"]},
                },
                "required": ["consumer_id", "right_type"]
            }
        ),
        Tool(
            name="ccpa_get_compliance_status",
            description="Get CCPA compliance status",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "ccpa"},
                },
                "required": []
            }
        ),
    ])

    # --- PII GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="pii_scan_text",
            description="Scan text for PII (email, SSN, phone, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="pii_classify_field",
            description="Classify a data field for PII type",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "pii"},
                    "field_name": {"type": "string"},
                    "field_id": {"type": "string"},
                    "source_id": {"type": "string"},
                    "sample_values": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["field_name", "source_id"]
            }
        ),
        Tool(
            name="pii_register_data_source",
            description="Register a data source for PII inventory",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "pii"},
                    "source_id": {"type": "string"},
                    "name": {"type": "string"},
                    "source_type": {"type": "string"},
                    "owner": {"type": "string"},
                },
                "required": ["source_id", "name", "source_type"]
            }
        ),
        Tool(
            name="pii_get_governance_report",
            description="Get PII governance report",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "pii"},
                },
                "required": []
            }
        ),
    ])

    # --- EU AI ACT GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="eu_ai_act_onboard_system",
            description="Onboard an AI system for EU AI Act compliance",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "eu_ai_act"},
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "provider": {"type": "string"},
                    "intended_purpose": {"type": "string"},
                    "technical_description": {"type": "string"},
                },
                "required": ["name", "version", "provider", "intended_purpose"]
            }
        ),
        Tool(
            name="eu_ai_act_classify_risk",
            description="Classify AI system risk level (Art. 5-7)",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "eu_ai_act"},
                    "system_id": {"type": "string"},
                    "assessor": {"type": "string"},
                },
                "required": ["system_id"]
            }
        ),
        Tool(
            name="eu_ai_act_check_prohibited",
            description="Check for prohibited practices (Art. 5)",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "eu_ai_act"},
                    "system_id": {"type": "string"},
                },
                "required": ["system_id"]
            }
        ),
        Tool(
            name="eu_ai_act_get_compliance_status",
            description="Get EU AI Act compliance status",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "eu_ai_act"},
                    "system_id": {"type": "string"},
                },
                "required": ["system_id"]
            }
        ),
    ])

    # --- HIPAA GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="hipaa_authorize_phi_access",
            description="Authorize PHI access with minimum necessary check",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "hipaa"},
                    "actor_id": {"type": "string"},
                    "actor_type": {"type": "string"},
                    "patient_id": {"type": "string"},
                    "phi_elements": {"type": "array", "items": {"type": "string"}},
                    "purpose": {"type": "string", "enum": ["treatment", "payment", "operations", "research", "other"]},
                },
                "required": ["actor_id", "patient_id", "phi_elements", "purpose"]
            }
        ),
        Tool(
            name="hipaa_apply_minimum_necessary",
            description="Apply minimum necessary standard to PHI request",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "hipaa"},
                    "requestor": {"type": "string"},
                    "patient_id": {"type": "string"},
                    "requested_phi": {"type": "array", "items": {"type": "string"}},
                    "purpose": {"type": "string"},
                },
                "required": ["requestor", "patient_id", "requested_phi", "purpose"]
            }
        ),
        Tool(
            name="hipaa_get_compliance_dashboard",
            description="Get HIPAA compliance dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "compliance_id": {"type": "string", "default": "hipaa"},
                },
                "required": []
            }
        ),
    ])

    # --- UNIFIED GOVERNANCE TOOLS ---
    tools.extend([
        Tool(
            name="unified_check_compliance",
            description="Check cross-regulation compliance (GDPR + CCPA + PII)",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "action": {"type": "string"},
                    "pii_types": {"type": "array", "items": {"type": "string"}},
                    "data_subject_id": {"type": "string"},
                },
                "required": ["agent_id", "action", "pii_types"]
            }
        ),
        Tool(
            name="unified_grant_agent_pii_access",
            description="Grant agent access to specific PII types",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "pii_types": {"type": "array", "items": {"type": "string"}},
                    "purpose": {"type": "string"},
                    "legal_basis": {"type": "string"},
                },
                "required": ["agent_id", "pii_types", "purpose"]
            }
        ),
        Tool(
            name="unified_record_agent_action",
            description="Record agent action for unified audit",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "action": {"type": "string"},
                    "pii_types": {"type": "array", "items": {"type": "string"}},
                    "data_source": {"type": "string"},
                    "outcome": {"type": "string"},
                },
                "required": ["agent_id", "action", "outcome"]
            }
        ),
    ])

    # --- CODE FLOW GRAPH TOOLS ---
    tools.extend([
        Tool(
            name="codeflow_analyze_local",
            description="Analyze local directory and create code flow graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["graph_id", "path"]
            }
        ),
        Tool(
            name="codeflow_analyze_github",
            description="Analyze GitHub repository and create code flow graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "repo_url": {"type": "string"},
                },
                "required": ["graph_id", "repo_url"]
            }
        ),
        Tool(
            name="codeflow_query",
            description="Query code flow graph (find callers, imports, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "query": {"type": "string", "description": "TRAVERSE query like 'function:main <- CALLS <- function'"},
                },
                "required": ["graph_id", "query"]
            }
        ),
        Tool(
            name="codeflow_get_function_callers",
            description="Find all callers of a function",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "function_name": {"type": "string"},
                },
                "required": ["graph_id", "function_name"]
            }
        ),
        Tool(
            name="codeflow_get_import_chain",
            description="Get import chain for a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "file_path": {"type": "string"},
                    "max_depth": {"type": "integer", "default": 5},
                },
                "required": ["graph_id", "file_path"]
            }
        ),
    ])

    return tools


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return get_all_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    try:
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


async def handle_tool_call(name: str, args: dict) -> dict:
    """Route tool calls to appropriate handlers."""

    # --- CONVERTERS ---
    if name == "convert_to_graphml":
        graph = state.graphs.get(args["graph_id"])
        if not graph:
            return {"error": f"Graph {args['graph_id']} not found"}
        converter = get_converters()["graphml"](include_properties=args.get("include_properties", True))
        return {"graphml": converter.to_graphml(graph)}

    elif name == "convert_to_rdf":
        graph = state.graphs.get(args["graph_id"])
        if not graph:
            return {"error": f"Graph {args['graph_id']} not found"}
        converter = get_converters()["rdf"](base_uri=args.get("base_uri", "http://example.org/"))
        fmt = args.get("format", "turtle")
        if fmt == "turtle":
            return {"rdf": converter.to_turtle(graph)}
        else:
            return {"rdf": converter.to_ntriples(graph)}

    elif name == "convert_to_csv":
        graph = state.graphs.get(args["graph_id"])
        if not graph:
            return {"error": f"Graph {args['graph_id']} not found"}
        converter = get_converters()["csv"](delimiter=args.get("delimiter", ","))
        nodes, edges = converter.to_csv(graph)
        return {"nodes_csv": nodes, "edges_csv": edges}

    elif name == "convert_to_cypher":
        graph = state.graphs.get(args["graph_id"])
        if not graph:
            return {"error": f"Graph {args['graph_id']} not found"}
        converter = get_converters()["cypher"]()
        mode = args.get("mode", "merge")
        if args.get("batch"):
            return {"cypher": converter.to_cypher_batch(graph, mode=mode)}
        return {"cypher": converter.to_cypher(graph, mode=mode)}

    elif name == "convert_to_dot":
        graph = state.graphs.get(args["graph_id"])
        if not graph:
            return {"error": f"Graph {args['graph_id']} not found"}
        converter = get_converters()["dot"](label_property=args.get("label_property", "name"))
        if args.get("clustered"):
            return {"dot": converter.to_dot_clustered(graph)}
        return {"dot": converter.to_dot(graph)}

    elif name == "import_from_graphml":
        converter = get_converters()["graphml"]()
        graph = converter.from_graphml(args["content"])
        state.graphs[args["graph_id"]] = graph
        return {"success": True, "graph_id": args["graph_id"]}

    # --- SCHEMA GENERATOR ---
    elif name == "generate_schema":
        gen = get_schema_generator()["generator"](
            infer_constraints=args.get("infer_constraints", True),
            infer_enums=args.get("infer_enums", True),
            infer_patterns=args.get("infer_patterns", True),
        )
        schema = gen.generate(args["data"], name=args.get("name", "generated_schema"))
        return {"schema": gen.to_dict(schema), "python_code": gen.to_python(schema)}

    elif name == "format_schema":
        fmt = get_schema_generator()["formatter"]
        schema = args["schema"]
        format_type = args["format"]
        if format_type == "python":
            return {"formatted": fmt.to_python(schema)}
        elif format_type == "typescript":
            return {"formatted": fmt.to_typescript(schema)}
        elif format_type == "json":
            return {"formatted": fmt.to_json(schema)}
        elif format_type == "ison":
            return {"formatted": fmt.to_ison_schema(schema)}

    # --- ISON CACHE ---
    elif name == "cache_set":
        cache_id = args.get("cache_id", "default")
        if cache_id not in state.caches:
            state.caches[cache_id] = get_ison_cache()["cache"]()
        cache = state.caches[cache_id]
        cache.set(args["key"], args["value"], ttl=args.get("ttl"))
        return {"success": True, "key": args["key"]}

    elif name == "cache_get":
        cache_id = args.get("cache_id", "default")
        cache = state.caches.get(cache_id)
        if not cache:
            return {"error": f"Cache {cache_id} not found"}
        value = cache.get(args["key"])
        return {"key": args["key"], "value": value}

    elif name == "cache_get_within_budget":
        cache_id = args.get("cache_id", "default")
        cache = state.caches.get(cache_id)
        if not cache:
            return {"error": f"Cache {cache_id} not found"}
        result = cache.get_within_budget(args["patterns"], args["token_budget"])
        return result

    elif name == "count_tokens":
        tm = get_ison_cache()["token_manager"]()
        count = tm.count_tokens(args["content"])
        return {"token_count": count}

    # --- AGENT MEMORY ---
    elif name == "memory_init":
        project_id = args["project_id"]
        if args.get("project_path"):
            agent = get_agent_memory()["prepare"](args["project_path"])
            state.memories[project_id] = agent.memory
        else:
            state.memories[project_id] = get_agent_memory()["memory"](project_id)
        return {"success": True, "project_id": project_id}

    elif name == "memory_get_context":
        memory = state.memories.get(args["project_id"])
        if not memory:
            return {"error": f"Memory {args['project_id']} not found"}
        context = memory.get_coding_context(task=args["task"], files=args.get("files", []))
        return {"context": context.to_dict() if hasattr(context, "to_dict") else str(context)}

    elif name == "memory_add_convention":
        memory = state.memories.get(args["project_id"])
        if not memory:
            return {"error": f"Memory {args['project_id']} not found"}
        memory.conventions.add(
            category=args["category"],
            rule=args["rule"],
            enforced_by=args.get("enforced_by"),
            example=args.get("example")
        )
        return {"success": True}

    elif name == "memory_add_decision":
        memory = state.memories.get(args["project_id"])
        if not memory:
            return {"error": f"Memory {args['project_id']} not found"}
        memory.decisions.add_decision(
            title=args["title"],
            context=args["context"],
            consequences_positive=args.get("consequences_positive", []),
            consequences_negative=args.get("consequences_negative", [])
        )
        return {"success": True}

    elif name == "memory_add_bug_pattern":
        memory = state.memories.get(args["project_id"])
        if not memory:
            return {"error": f"Memory {args['project_id']} not found"}
        memory.bugs.add_pattern(
            name=args["name"],
            signature=args["signature"],
            modules_affected=args.get("modules_affected", [])
        )
        if args.get("fix_template"):
            memory.bugs.add_fix_pattern(args["name"], args["fix_template"])
        return {"success": True}

    elif name == "memory_check_before_coding":
        memory = state.memories.get(args["project_id"])
        if not memory:
            return {"error": f"Memory {args['project_id']} not found"}
        # This would need the AgentIntegration wrapper
        return {"warnings": []}  # Placeholder

    elif name == "memory_save":
        memory = state.memories.get(args["project_id"])
        if not memory:
            return {"error": f"Memory {args['project_id']} not found"}
        memory.save(args["path"])
        return {"success": True, "path": args["path"]}

    elif name == "memory_load":
        memory = get_agent_memory()["memory"].load(args["path"])
        state.memories[args["project_id"]] = memory
        return {"success": True, "project_id": args["project_id"]}

    # --- AGENT GOVERNANCE ---
    elif name == "governance_init":
        engine = get_agent_governance()["quick"](
            args["governance_id"],
            setup_defaults=args.get("setup_defaults", True)
        )
        state.governance_engines[args["governance_id"]] = engine
        return {"success": True, "governance_id": args["governance_id"]}

    elif name == "governance_register_agent":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        engine.register_agent(args["agent_id"], args["name"], args["authority_level"])
        return {"success": True, "agent_id": args["agent_id"]}

    elif name == "governance_check_action":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        result = engine.check_action(
            args["agent_id"],
            args["action"],
            args.get("context", {})
        )
        return result

    elif name == "governance_add_policy":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        engine.add_policy(
            args["policy_name"],
            args["rules"],
            priority=args.get("priority", 50)
        )
        return {"success": True, "policy_name": args["policy_name"]}

    elif name == "governance_evaluate_policy":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        result = engine.policy.evaluate(args["context"])
        return result

    elif name == "governance_trigger_escalation":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        escalation_ids = engine.escalation.trigger_escalation(args["context"])
        return {"escalation_ids": escalation_ids}

    elif name == "governance_resolve_escalation":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        engine.escalation.resolve_escalation(
            args["escalation_id"],
            args["decision"],
            args["reason"]
        )
        return {"success": True}

    elif name == "governance_assess_risk":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        posture = engine.assess_risk_posture()
        return posture

    elif name == "governance_report_incident":
        engine = state.governance_engines.get(args["governance_id"])
        if not engine:
            return {"error": f"Governance engine {args['governance_id']} not found"}
        incident_id = engine.report_incident(
            args["severity"],
            args["category"],
            args["description"]
        )
        return {"incident_id": incident_id}

    # --- LEARNING ---
    elif name == "learning_init":
        graph = ISONGraph(f"learning_{args['learning_id']}")
        engine = get_agent_learning()["engine"](graph)
        state.learning_engines[args["learning_id"]] = engine
        return {"success": True, "learning_id": args["learning_id"]}

    elif name == "learning_record_experience":
        engine = state.learning_engines.get(args["learning_id"])
        if not engine:
            return {"error": f"Learning engine {args['learning_id']} not found"}
        exp_id = engine.record_experience(
            agent_id=args["agent_id"],
            task=args["task"],
            task_type=args.get("task_type", "general"),
            outcome=args["outcome"],
            reward_signal=args.get("reward_signal", 0.5),
            key_learnings=args.get("key_learnings", [])
        )
        return {"experience_id": exp_id}

    elif name == "learning_record_mistake":
        engine = state.learning_engines.get(args["learning_id"])
        if not engine:
            return {"error": f"Learning engine {args['learning_id']} not found"}
        mistake_id = engine.record_mistake(
            agent_id=args["agent_id"],
            category=args["category"],
            severity=args["severity"],
            task_context=args["task_context"],
            agent_action=args.get("agent_action", ""),
            expected_action=args.get("expected_action", ""),
            root_cause=args.get("root_cause", "")
        )
        return {"mistake_id": mistake_id}

    elif name == "learning_identify_retraining_needs":
        engine = state.learning_engines.get(args["learning_id"])
        if not engine:
            return {"error": f"Learning engine {args['learning_id']} not found"}
        needs = engine.identify_retraining_needs(args["agent_id"])
        return needs

    # --- CODE FLOW ---
    elif name == "codeflow_analyze_local":
        graph = get_code_flow()["analyze_local"](args["path"])
        state.graphs[args["graph_id"]] = graph
        return {"success": True, "graph_id": args["graph_id"]}

    elif name == "codeflow_analyze_github":
        graph = get_code_flow()["analyze_github"](args["repo_url"])
        state.graphs[args["graph_id"]] = graph
        return {"success": True, "graph_id": args["graph_id"]}

    elif name == "codeflow_query":
        graph = state.graphs.get(args["graph_id"])
        if not graph:
            return {"error": f"Graph {args['graph_id']} not found"}
        from ison_graph.query import QueryEngine
        engine = QueryEngine(graph)
        result = engine.execute(args["query"])
        return {"result": result}

    # --- PII ---
    elif name == "pii_scan_text":
        pii = get_pii()["engine"](ISONGraph("pii_temp"))
        detections = pii.scan_text_for_pii(args["text"])
        return {"detections": detections}

    # --- UNIFIED ---
    elif name == "unified_check_compliance":
        unified = get_unified()["quick"](setup_defaults=True)
        result = unified.check_compliance(
            agent_id=args["agent_id"],
            action=args["action"],
            pii_types=args["pii_types"],
            data_subject_id=args.get("data_subject_id")
        )
        return result

    # Default: tool not implemented
    return {"error": f"Tool {name} not yet implemented"}


# ============================================================================
# RESOURCES
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    resources = []

    # List all graphs
    for graph_id in state.graphs:
        resources.append(Resource(
            uri=f"isongraph://graph/{graph_id}",
            name=f"Graph: {graph_id}",
            mimeType="application/json"
        ))

    # List all memories
    for project_id in state.memories:
        resources.append(Resource(
            uri=f"isongraph://memory/{project_id}",
            name=f"Memory: {project_id}",
            mimeType="application/json"
        ))

    # List all governance engines
    for gov_id in state.governance_engines:
        resources.append(Resource(
            uri=f"isongraph://governance/{gov_id}",
            name=f"Governance: {gov_id}",
            mimeType="application/json"
        ))

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    parts = uri.replace("isongraph://", "").split("/")

    if parts[0] == "graph" and len(parts) > 1:
        graph = state.graphs.get(parts[1])
        if graph:
            return json.dumps(graph.to_dict(), indent=2)

    elif parts[0] == "memory" and len(parts) > 1:
        memory = state.memories.get(parts[1])
        if memory:
            return json.dumps(memory.get_stats(), indent=2)

    elif parts[0] == "governance" and len(parts) > 1:
        engine = state.governance_engines.get(parts[1])
        if engine:
            return json.dumps(engine.get_stats(), indent=2)

    return json.dumps({"error": "Resource not found"})


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
