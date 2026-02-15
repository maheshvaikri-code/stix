"""
Agent Learning MCP Server - Experience & Improvement
====================================================

MCP server for agent learning, experience recording, and retraining.

Features:
- Experience recording and replay
- Mistake tracking with pattern detection
- Skill development with spaced repetition
- Attention monitoring
- Automated retraining curriculum
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

from agent_learning import (
    AgentLearningEngine,
    ExperienceOutcome,
    MistakeCategory,
    MistakeSeverity,
    SkillLevel,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-learning-mcp")


@dataclass
class ServerState:
    engines: Dict[str, AgentLearningEngine] = field(default_factory=dict)
    default_project: Optional[str] = None


server = Server("agent-learning-mcp")
state = ServerState()


TOOLS = [
    # Engine Management
    Tool(name="learning_init", description="Initialize learning engine.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}),

    # Experience
    Tool(name="experience_record", description="Record an experience.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"}, "agent_id": {"type": "string"}, "task": {"type": "string"},
             "task_type": {"type": "string"}, "actions": {"type": "array", "items": {"type": "object"}},
             "outcome": {"type": "string", "enum": ["success", "partial", "failure"]},
             "learnings": {"type": "array", "items": {"type": "string"}}, "reward": {"type": "number"}
         }, "required": ["agent_id", "task", "outcome"]}),
    Tool(name="experience_query", description="Query past experiences.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "task_type": {"type": "string"}, "outcome": {"type": "string"}, "limit": {"type": "integer", "default": 50}}}),
    Tool(name="experience_similar", description="Find similar experiences.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "task": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["task"]}),

    # Mistakes
    Tool(name="mistake_record", description="Record a mistake.",
         inputSchema={"type": "object", "properties": {
             "project_id": {"type": "string"}, "agent_id": {"type": "string"},
             "category": {"type": "string", "enum": ["judgment_error", "knowledge_gap", "execution_error", "communication_error", "process_error"]},
             "severity": {"type": "string", "enum": ["minor", "moderate", "major", "critical"]},
             "description": {"type": "string"}, "root_cause": {"type": "string"},
             "expected_action": {"type": "string"}, "actual_action": {"type": "string"}
         }, "required": ["agent_id", "category", "description"]}),
    Tool(name="mistake_patterns", description="Detect mistake patterns.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}}),
    Tool(name="mistake_query", description="Query mistakes.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "category": {"type": "string"}, "severity": {"type": "string"}}}),
    Tool(name="mistake_prevent", description="Get prevention advice.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "task": {"type": "string"}}, "required": ["task"]}),

    # Skills
    Tool(name="skill_record", description="Record skill usage.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "skill": {"type": "string"}, "success": {"type": "boolean"}, "context": {"type": "string"}}, "required": ["agent_id", "skill", "success"]}),
    Tool(name="skill_level", description="Get current skill level.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "skill": {"type": "string"}}, "required": ["agent_id", "skill"]}),
    Tool(name="skill_progression", description="Get skill progression history.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "skill": {"type": "string"}}}),
    Tool(name="skill_recommend", description="Recommend skills to practice.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}, "required": ["agent_id"]}),

    # Attention
    Tool(name="attention_record", description="Record attention/focus.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "focus_area": {"type": "string"}, "duration_seconds": {"type": "integer"}, "quality": {"type": "string"}}, "required": ["agent_id", "focus_area"]}),
    Tool(name="attention_analyze", description="Analyze attention patterns.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}, "required": ["agent_id"]}),

    # Supervision
    Tool(name="supervision_record", description="Record supervision event.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "supervisor": {"type": "string"}, "feedback": {"type": "string"}, "outcome": {"type": "string"}}, "required": ["agent_id", "supervisor"]}),
    Tool(name="supervision_stats", description="Get supervision statistics.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}}),

    # Retraining
    Tool(name="needs_identify", description="Identify retraining needs.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}, "required": ["agent_id"]}),
    Tool(name="curriculum_generate", description="Generate retraining curriculum.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}, "need_id": {"type": "string"}}, "required": ["agent_id", "need_id"]}),
    Tool(name="curriculum_execute", description="Execute curriculum step.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "curriculum_id": {"type": "string"}, "step": {"type": "integer"}}, "required": ["curriculum_id", "step"]}),
    Tool(name="progress_track", description="Track learning progress.",
         inputSchema={"type": "object", "properties": {"project_id": {"type": "string"}, "agent_id": {"type": "string"}}, "required": ["agent_id"]}),
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


def get_engine(project_id: Optional[str] = None) -> AgentLearningEngine:
    pid = project_id or state.default_project
    if not pid or pid not in state.engines:
        raise ValueError(f"Learning engine not found: {pid}")
    return state.engines[pid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "learning_init":
        project_id = args["project_id"]
        from ison_graph import ISONGraph
        graph = ISONGraph(project_id)
        engine = AgentLearningEngine(graph)
        state.engines[project_id] = engine
        state.default_project = project_id
        return {"project_id": project_id, "initialized": True}

    elif name == "experience_record":
        engine = get_engine(args.get("project_id"))
        outcome_map = {"success": ExperienceOutcome.SUCCESS, "partial": ExperienceOutcome.PARTIAL, "failure": ExperienceOutcome.FAILURE}
        exp_id = engine.record_experience(
            agent_id=args["agent_id"], task=args["task"], task_type=args.get("task_type", "general"),
            actions_taken=args.get("actions", []), outcome=outcome_map.get(args["outcome"], ExperienceOutcome.SUCCESS),
            key_learnings=args.get("learnings", []), reward_signal=args.get("reward", 0.5)
        )
        return {"experience_id": exp_id}

    elif name == "experience_query":
        engine = get_engine(args.get("project_id"))
        experiences = engine.query_experiences(args.get("agent_id"), args.get("task_type"), args.get("outcome"), args.get("limit", 50))
        return {"experiences": list(experiences)}

    elif name == "experience_similar":
        engine = get_engine(args.get("project_id"))
        similar = engine.find_similar_experiences(args["task"], args.get("limit", 5))
        return {"similar": list(similar)}

    elif name == "mistake_record":
        engine = get_engine(args.get("project_id"))
        cat_map = {"judgment_error": MistakeCategory.JUDGMENT_ERROR, "knowledge_gap": MistakeCategory.KNOWLEDGE_GAP,
                   "execution_error": MistakeCategory.EXECUTION_ERROR, "communication_error": MistakeCategory.COMMUNICATION_ERROR,
                   "process_error": MistakeCategory.PROCESS_ERROR}
        sev_map = {"minor": MistakeSeverity.MINOR, "moderate": MistakeSeverity.MODERATE, "major": MistakeSeverity.MAJOR, "critical": MistakeSeverity.CRITICAL}
        mistake_id = engine.record_mistake(
            agent_id=args["agent_id"], category=cat_map.get(args["category"], MistakeCategory.JUDGMENT_ERROR),
            severity=sev_map.get(args.get("severity", "moderate"), MistakeSeverity.MODERATE),
            task_context=args["description"], root_cause=args.get("root_cause", ""),
            expected_action=args.get("expected_action", ""), agent_action=args.get("actual_action", "")
        )
        return {"mistake_id": mistake_id}

    elif name == "mistake_patterns":
        engine = get_engine(args.get("project_id"))
        patterns = engine.detect_mistake_patterns(args.get("agent_id"))
        return {"patterns": patterns}

    elif name == "mistake_query":
        engine = get_engine(args.get("project_id"))
        mistakes = engine.query_mistakes(args.get("agent_id"), args.get("category"), args.get("severity"))
        return {"mistakes": list(mistakes)}

    elif name == "mistake_prevent":
        engine = get_engine(args.get("project_id"))
        advice = engine.get_prevention_advice(args["task"])
        return {"advice": advice}

    elif name == "skill_record":
        engine = get_engine(args.get("project_id"))
        engine.record_skill_use(args["agent_id"], args["skill"], args["success"], args.get("context", ""))
        return {"recorded": True}

    elif name == "skill_level":
        engine = get_engine(args.get("project_id"))
        level = engine.get_skill_level(args["agent_id"], args["skill"])
        return {"skill": args["skill"], "level": level}

    elif name == "skill_progression":
        engine = get_engine(args.get("project_id"))
        progression = engine.get_skill_progression(args.get("agent_id"), args.get("skill"))
        return {"progression": progression}

    elif name == "skill_recommend":
        engine = get_engine(args.get("project_id"))
        recommendations = engine.recommend_skills(args["agent_id"])
        return {"recommendations": recommendations}

    elif name == "attention_record":
        engine = get_engine(args.get("project_id"))
        engine.record_attention(args["agent_id"], args["focus_area"], args.get("duration_seconds", 0), args.get("quality", "medium"))
        return {"recorded": True}

    elif name == "attention_analyze":
        engine = get_engine(args.get("project_id"))
        analysis = engine.analyze_attention(args["agent_id"])
        return {"analysis": analysis}

    elif name == "supervision_record":
        engine = get_engine(args.get("project_id"))
        engine.record_supervision(args["agent_id"], args["supervisor"], args.get("feedback", ""), args.get("outcome", "success"))
        return {"recorded": True}

    elif name == "supervision_stats":
        engine = get_engine(args.get("project_id"))
        stats = engine.get_supervision_stats(args.get("agent_id"))
        return {"stats": stats}

    elif name == "needs_identify":
        engine = get_engine(args.get("project_id"))
        needs = engine.identify_retraining_needs(args["agent_id"])
        return needs

    elif name == "curriculum_generate":
        engine = get_engine(args.get("project_id"))
        curriculum = engine.generate_curriculum(args["agent_id"], args["need_id"])
        return curriculum

    elif name == "curriculum_execute":
        engine = get_engine(args.get("project_id"))
        result = engine.execute_curriculum_step(args["curriculum_id"], args["step"])
        return result

    elif name == "progress_track":
        engine = get_engine(args.get("project_id"))
        progress = engine.get_learning_progress(args["agent_id"])
        return {"progress": progress}

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
