"""
ISON Memory MCP Server Implementation

A robust MCP server providing persistent memory capabilities for Claude.
All responses are in ISON format for maximum token efficiency.

Tools:
- create_entities: Create entities with optional initial observations
- create_observations: Add atomic facts to entities
- create_relations: Create typed relationships between entities
- search_memory: Full-text search across memory
- read_graph: Get full knowledge graph in ISON format
- multi_hop_search: Graph traversal from starting entity
- delete_entities: Remove entities and their data
- update_entity: Modify existing entities
- memory_stats: Get memory statistics
- compact_memory: Run memory compaction
- backup_memory: Create backup
- list_backups: List available backups
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    Resource,
    ResourceTemplate,
    Prompt,
    PromptMessage,
    PromptArgument,
    GetPromptResult,
    INTERNAL_ERROR,
    INVALID_PARAMS,
)

from ison_memory_mcp.config import MemoryConfig, load_config, get_config
from ison_memory_mcp.store import MemoryStore
from ison_memory_mcp.compaction import MemoryCompactor, BackupManager
from ison_memory_mcp.models import utc_now, format_timestamp
from ison_memory_mcp.prompts import (
    get_system_prompt,
    get_custom_instructions,
    format_search_results,
    format_graph_output,
    format_entity_created,
    ISON_OUTPUT_INSTRUCTIONS,
)

# Configure logging
logger = logging.getLogger("ison-memory-mcp")


class ISONMemoryServer:
    """
    MCP Server for ISON Memory operations.

    Provides tools for managing a persistent knowledge graph
    with entities, observations, and relations.
    """

    def __init__(self, config: Optional[MemoryConfig] = None) -> None:
        self.config = config or get_config()
        self.server = Server("ison-memory")
        self.store: Optional[MemoryStore] = None
        self.compactor: Optional[MemoryCompactor] = None
        self.backup_manager: Optional[BackupManager] = None

        # Register handlers
        self._register_tools()
        self._register_resources()
        self._register_prompts()

    async def initialize(self) -> None:
        """Initialize the memory store and components"""
        self.store = MemoryStore(self.config)
        await self.store.initialize()

        self.compactor = MemoryCompactor(self.config)
        self.backup_manager = BackupManager(self.config)

        logger.info(f"ISON Memory Server initialized: {self.config.storage.path}")

    async def shutdown(self) -> None:
        """Cleanup resources"""
        if self.store:
            await self.store.close()
        logger.info("ISON Memory Server shutdown")

    def _register_tools(self) -> None:
        """Register all MCP tools"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="create_entities",
                    description=(
                        "Create one or more entities in the knowledge graph. "
                        "Entities are the primary objects Claude remembers (people, projects, tools, concepts). "
                        "Returns ISON-formatted result for token efficiency."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Human-readable name for the entity"
                                        },
                                        "entityType": {
                                            "type": "string",
                                            "description": "Type: person, project, organization, tool, concept, location, event, document, code, task",
                                            "enum": ["person", "project", "organization", "tool", "concept", "location", "event", "document", "code", "task", "preference"]
                                        },
                                        "observations": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Initial observations (atomic facts) about the entity"
                                        }
                                    },
                                    "required": ["name", "entityType"]
                                },
                                "description": "Array of entities to create"
                            }
                        },
                        "required": ["entities"]
                    }
                ),
                Tool(
                    name="create_observations",
                    description=(
                        "Add observations (atomic facts) to existing entities. "
                        "Observations should be single, clear facts. Duplicates are automatically handled. "
                        "Returns ISON-formatted result."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "observations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "entityName": {
                                            "type": "string",
                                            "description": "Name of the entity to add observation to"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "The observation (atomic fact)"
                                        },
                                        "source": {
                                            "type": "string",
                                            "description": "Source: chat, code, manual, import, inference",
                                            "default": "chat"
                                        },
                                        "confidence": {
                                            "type": "number",
                                            "description": "Confidence score 0.0-1.0",
                                            "default": 1.0,
                                            "minimum": 0.0,
                                            "maximum": 1.0
                                        }
                                    },
                                    "required": ["entityName", "content"]
                                }
                            }
                        },
                        "required": ["observations"]
                    }
                ),
                Tool(
                    name="create_relations",
                    description=(
                        "Create typed relationships between entities. "
                        "Relations define how entities connect in the knowledge graph. "
                        "Returns ISON-formatted result."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "relations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "fromEntity": {
                                            "type": "string",
                                            "description": "Source entity name"
                                        },
                                        "toEntity": {
                                            "type": "string",
                                            "description": "Target entity name"
                                        },
                                        "relationType": {
                                            "type": "string",
                                            "description": "Relationship type",
                                            "enum": [
                                                "CREATOR_OF", "MEMBER_OF", "LEADS", "USES",
                                                "WORKS_ON", "RELATED_TO", "DEPENDS_ON", "INTEGRATES",
                                                "LOCATED_IN", "OCCURRED_AT", "IS_A", "HAS_PART",
                                                "KNOWS", "PREFERS", "MENTIONED_IN", "SIMILAR_TO"
                                            ]
                                        },
                                        "bidirectional": {
                                            "type": "boolean",
                                            "description": "Create reverse relation too",
                                            "default": False
                                        }
                                    },
                                    "required": ["fromEntity", "toEntity", "relationType"]
                                }
                            }
                        },
                        "required": ["relations"]
                    }
                ),
                Tool(
                    name="search_memory",
                    description=(
                        "Search the knowledge graph for entities and observations. "
                        "Supports full-text search on observation content. "
                        "Returns ISON-formatted results with entities, observations, and relations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (searches names and observation content)"
                            },
                            "entityType": {
                                "type": "string",
                                "description": "Filter by entity type (optional)"
                            },
                            "maxResults": {
                                "type": "integer",
                                "description": "Maximum results to return",
                                "default": 20,
                                "minimum": 1,
                                "maximum": 100
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="read_graph",
                    description=(
                        "Read the entire knowledge graph in ISON format. "
                        "Returns all entities, observations, and relations. "
                        "For large graphs, use search_memory instead for specific queries."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "description": "Output format: ison, isonl, isongraph",
                                "enum": ["ison", "isonl", "isongraph"],
                                "default": "ison"
                            },
                            "includeStats": {
                                "type": "boolean",
                                "description": "Include statistics in output",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="multi_hop_search",
                    description=(
                        "Traverse the knowledge graph from a starting entity. "
                        "Returns all connected entities within N hops. "
                        "Useful for exploring entity neighborhoods and relationships."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entityName": {
                                "type": "string",
                                "description": "Starting entity name"
                            },
                            "maxHops": {
                                "type": "integer",
                                "description": "Maximum traversal depth",
                                "default": 2,
                                "minimum": 1,
                                "maximum": 5
                            },
                            "relationType": {
                                "type": "string",
                                "description": "Filter by relation type (optional)"
                            }
                        },
                        "required": ["entityName"]
                    }
                ),
                Tool(
                    name="delete_entities",
                    description=(
                        "Delete entities and all their associated observations and relations. "
                        "This action is irreversible. Use with caution."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entityNames": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Names of entities to delete"
                            }
                        },
                        "required": ["entityNames"]
                    }
                ),
                Tool(
                    name="update_entity",
                    description=(
                        "Update an existing entity's name or type. "
                        "Use create_observations to add new facts."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entityName": {
                                "type": "string",
                                "description": "Current name of the entity"
                            },
                            "newName": {
                                "type": "string",
                                "description": "New name (optional)"
                            },
                            "newType": {
                                "type": "string",
                                "description": "New entity type (optional)"
                            }
                        },
                        "required": ["entityName"]
                    }
                ),
                Tool(
                    name="memory_stats",
                    description=(
                        "Get statistics about the memory store including "
                        "entity counts, observation counts, relation counts, and storage size. "
                        "Returns ISON-formatted statistics."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="compact_memory",
                    description=(
                        "Run memory compaction to remove old and low-relevance data. "
                        "Strategies: time_based, relevance, aggressive, smart. "
                        "Returns compaction statistics in ISON format."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "strategy": {
                                "type": "string",
                                "description": "Compaction strategy",
                                "enum": ["time_based", "relevance", "aggressive", "smart"],
                                "default": "smart"
                            },
                            "dryRun": {
                                "type": "boolean",
                                "description": "Simulate without making changes",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="backup_memory",
                    description=(
                        "Create a backup of the memory store. "
                        "Backups are stored in the configured backup directory. "
                        "Returns backup details in ISON format."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "includeIson": {
                                "type": "boolean",
                                "description": "Also export to ISON file",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="list_backups",
                    description="List all available memory backups with their details.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls"""
            if not self.store:
                return [TextContent(
                    type="text",
                    text="error: Store not initialized"
                )]

            try:
                if name == "create_entities":
                    return await self._handle_create_entities(arguments)
                elif name == "create_observations":
                    return await self._handle_create_observations(arguments)
                elif name == "create_relations":
                    return await self._handle_create_relations(arguments)
                elif name == "search_memory":
                    return await self._handle_search_memory(arguments)
                elif name == "read_graph":
                    return await self._handle_read_graph(arguments)
                elif name == "multi_hop_search":
                    return await self._handle_multi_hop_search(arguments)
                elif name == "delete_entities":
                    return await self._handle_delete_entities(arguments)
                elif name == "update_entity":
                    return await self._handle_update_entity(arguments)
                elif name == "memory_stats":
                    return await self._handle_memory_stats(arguments)
                elif name == "compact_memory":
                    return await self._handle_compact_memory(arguments)
                elif name == "backup_memory":
                    return await self._handle_backup_memory(arguments)
                elif name == "list_backups":
                    return await self._handle_list_backups(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"error: Unknown tool '{name}'"
                    )]

            except ValueError as e:
                return [TextContent(
                    type="text",
                    text=f"error.validation\nmessage\n\"{str(e)}\""
                )]
            except Exception as e:
                logger.exception(f"Error in tool {name}")
                return [TextContent(
                    type="text",
                    text=f"error.internal\nmessage\n\"{str(e)}\""
                )]

    def _register_resources(self) -> None:
        """Register MCP resources for ISON system context"""

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            return [
                Resource(
                    uri="ison-memory://system/prompt",
                    name="ISON Memory System Prompt",
                    description=(
                        "System prompt teaching Claude to read and write ISON format. "
                        "Include this in context for optimal token efficiency."
                    ),
                    mimeType="text/plain",
                ),
                Resource(
                    uri="ison-memory://system/reference",
                    name="ISON Quick Reference",
                    description="Compact ISON syntax reference guide",
                    mimeType="text/plain",
                ),
                Resource(
                    uri="ison-memory://graph/current",
                    name="Current Knowledge Graph",
                    description="Current memory graph in ISON format",
                    mimeType="text/plain",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            if uri == "ison-memory://system/prompt":
                return get_system_prompt(include_guide=True)

            elif uri == "ison-memory://system/reference":
                from ison_memory_mcp.prompts import ISON_REFERENCE_GUIDE
                return ISON_REFERENCE_GUIDE

            elif uri == "ison-memory://graph/current":
                if self.store:
                    return format_graph_output(await self.store.export_to_ison())
                return "# No graph loaded"

            else:
                raise ValueError(f"Unknown resource: {uri}")

    def _register_prompts(self) -> None:
        """Register MCP prompts for ISON-aware interactions"""

        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            return [
                Prompt(
                    name="ison-memory-context",
                    description=(
                        "Initialize Claude with ISON Memory context. "
                        "Use at conversation start for memory-aware interactions."
                    ),
                    arguments=[
                        PromptArgument(
                            name="include_graph",
                            description="Include current graph snapshot",
                            required=False,
                        ),
                        PromptArgument(
                            name="topic",
                            description="Optional topic to search and include",
                            required=False,
                        ),
                    ],
                ),
                Prompt(
                    name="ison-output-format",
                    description=(
                        "Instructions for Claude to output data in ISON format. "
                        "Use when requesting structured data output."
                    ),
                    arguments=[],
                ),
                Prompt(
                    name="ison-entity-reference",
                    description=(
                        "Get reference syntax for mentioning entities. "
                        "Use when discussing stored entities."
                    ),
                    arguments=[
                        PromptArgument(
                            name="entity_name",
                            description="Name of entity to reference",
                            required=True,
                        ),
                    ],
                ),
            ]

        @self.server.get_prompt()
        async def get_prompt(
            name: str,
            arguments: dict[str, str] | None = None
        ) -> GetPromptResult:
            arguments = arguments or {}

            if name == "ison-memory-context":
                # Build context message
                content_parts = [get_system_prompt(include_guide=True)]

                # Optionally include graph snapshot
                if arguments.get("include_graph", "").lower() == "true":
                    if self.store:
                        graph_ison = await self.store.export_to_ison()
                        content_parts.append("\n\n# Current Knowledge Graph\n")
                        content_parts.append(graph_ison)

                # Optionally search for topic
                topic = arguments.get("topic")
                if topic and self.store:
                    result = await self.store.search(topic, max_results=10)
                    if result.entities:
                        content_parts.append(f"\n\n# Relevant Memory for '{topic}'\n")
                        content_parts.append(format_search_results(result.to_ison()))

                return GetPromptResult(
                    description="ISON Memory context with system instructions",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text="\n".join(content_parts),
                            ),
                        ),
                    ],
                )

            elif name == "ison-output-format":
                return GetPromptResult(
                    description="Instructions for ISON output format",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=ISON_OUTPUT_INSTRUCTIONS,
                            ),
                        ),
                    ],
                )

            elif name == "ison-entity-reference":
                entity_name = arguments.get("entity_name", "")
                if not entity_name:
                    raise ValueError("entity_name argument required")

                if self.store:
                    entity = await self.store.find_entity_by_name(entity_name)
                    if entity:
                        ref_text = (
                            f"# Entity Reference\n"
                            f"# Use this syntax to reference '{entity_name}' in responses:\n"
                            f"#   :{entity.id}\n"
                            f"# Or with type prefix:\n"
                            f"#   :{entity.entity_type}:{entity.id}\n"
                            f"\n"
                            f"object.entity\n"
                            f"id name type ref\n"
                            f":{entity.id} \"{entity.name}\" {entity.entity_type} "
                            f":{entity.entity_type}:{entity.id}"
                        )
                        return GetPromptResult(
                            description=f"Reference for entity '{entity_name}'",
                            messages=[
                                PromptMessage(
                                    role="user",
                                    content=TextContent(
                                        type="text",
                                        text=ref_text,
                                    ),
                                ),
                            ],
                        )

                raise ValueError(f"Entity '{entity_name}' not found")

            else:
                raise ValueError(f"Unknown prompt: {name}")

    # =========================================================================
    # Tool Handlers
    # =========================================================================

    async def _handle_create_entities(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle create_entities tool"""
        entities_data = arguments.get("entities", [])
        if not entities_data:
            return [TextContent(type="text", text="error: No entities provided")]

        created = []
        errors = []

        for entity_data in entities_data:
            try:
                name = entity_data.get("name")
                entity_type = entity_data.get("entityType", "concept")
                observations = entity_data.get("observations", [])

                # Check if entity already exists
                existing = await self.store.find_entity_by_name(name)
                if existing:
                    # Add observations to existing entity
                    for obs_content in observations:
                        await self.store.create_observation(
                            existing.id, obs_content, source="creation"
                        )
                    created.append({
                        "id": existing.id,
                        "name": existing.name,
                        "status": "existing",
                        "observations_added": len(observations)
                    })
                else:
                    # Create new entity
                    entity = await self.store.create_entity(name, entity_type)

                    # Add initial observations
                    for obs_content in observations:
                        await self.store.create_observation(
                            entity.id, obs_content, source="creation"
                        )

                    created.append({
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.entity_type,
                        "status": "created",
                        "observations_added": len(observations)
                    })

            except Exception as e:
                errors.append({"name": entity_data.get("name"), "error": str(e)})

        # Build ISON response
        lines = [
            "# Entity Creation Result",
            f"# Created: {len(created)} entities",
            "",
            "table.created",
            "id name type status observations_added",
        ]

        for item in created:
            name_escaped = item["name"].replace('"', '\\"')
            lines.append(
                f":{item['id']} \"{name_escaped}\" "
                f"{item.get('type', 'existing')} {item['status']} "
                f"{item.get('observations_added', 0)}"
            )

        if errors:
            lines.append("")
            lines.append("table.errors")
            lines.append("name error")
            for err in errors:
                lines.append(f"\"{err['name']}\" \"{err['error']}\"")

        return [TextContent(type="text", text=format_entity_created("\n".join(lines)))]

    async def _handle_create_observations(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle create_observations tool"""
        observations_data = arguments.get("observations", [])
        if not observations_data:
            return [TextContent(type="text", text="error: No observations provided")]

        added = []
        errors = []

        for obs_data in observations_data:
            try:
                entity_name = obs_data.get("entityName")
                content = obs_data.get("content")
                source = obs_data.get("source", "chat")
                confidence = obs_data.get("confidence", 1.0)

                entity = await self.store.find_entity_by_name(entity_name)
                if not entity:
                    errors.append({
                        "entityName": entity_name,
                        "error": "Entity not found"
                    })
                    continue

                observation = await self.store.create_observation(
                    entity.id, content, source, confidence
                )

                added.append({
                    "id": observation.id,
                    "entity": entity.name,
                    "content_preview": content[:50] + "..." if len(content) > 50 else content
                })

            except Exception as e:
                errors.append({
                    "entityName": obs_data.get("entityName"),
                    "error": str(e)
                })

        # Build ISON response
        lines = [
            "# Observations Added",
            f"# Count: {len(added)}",
            "",
            "table.added",
            "id entity content_preview",
        ]

        for item in added:
            preview = item["content_preview"].replace('"', '\\"')
            lines.append(f":{item['id']} \"{item['entity']}\" \"{preview}\"")

        if errors:
            lines.append("")
            lines.append("table.errors")
            lines.append("entity error")
            for err in errors:
                lines.append(f"\"{err['entityName']}\" \"{err['error']}\"")

        return [TextContent(type="text", text="\n".join(lines))]

    async def _handle_create_relations(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle create_relations tool"""
        relations_data = arguments.get("relations", [])
        if not relations_data:
            return [TextContent(type="text", text="error: No relations provided")]

        created = []
        errors = []

        for rel_data in relations_data:
            try:
                from_name = rel_data.get("fromEntity")
                to_name = rel_data.get("toEntity")
                relation_type = rel_data.get("relationType")
                bidirectional = rel_data.get("bidirectional", False)

                from_entity = await self.store.find_entity_by_name(from_name)
                to_entity = await self.store.find_entity_by_name(to_name)

                if not from_entity:
                    errors.append({
                        "from": from_name,
                        "to": to_name,
                        "error": f"Source entity '{from_name}' not found"
                    })
                    continue

                if not to_entity:
                    errors.append({
                        "from": from_name,
                        "to": to_name,
                        "error": f"Target entity '{to_name}' not found"
                    })
                    continue

                relation = await self.store.create_relation(
                    from_entity.id,
                    to_entity.id,
                    relation_type,
                    bidirectional=bidirectional
                )

                created.append({
                    "id": relation.id,
                    "from": from_entity.name,
                    "to": to_entity.name,
                    "type": relation_type
                })

            except Exception as e:
                errors.append({
                    "from": rel_data.get("fromEntity"),
                    "to": rel_data.get("toEntity"),
                    "error": str(e)
                })

        # Build ISON response
        lines = [
            "# Relations Created",
            f"# Count: {len(created)}",
            "",
            "table.created",
            "id from_entity to_entity relation_type",
        ]

        for item in created:
            lines.append(
                f":{item['id']} \"{item['from']}\" \"{item['to']}\" {item['type']}"
            )

        if errors:
            lines.append("")
            lines.append("table.errors")
            lines.append("from_entity to_entity error")
            for err in errors:
                lines.append(f"\"{err['from']}\" \"{err['to']}\" \"{err['error']}\"")

        return [TextContent(type="text", text="\n".join(lines))]

    async def _handle_search_memory(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle search_memory tool"""
        query = arguments.get("query", "")
        max_results = arguments.get("maxResults", 20)

        if not query:
            return [TextContent(type="text", text="error: Query required")]

        result = await self.store.search(query, max_results)

        return [TextContent(type="text", text=format_search_results(result.to_ison()))]

    async def _handle_read_graph(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle read_graph tool"""
        output_format = arguments.get("format", "ison")
        include_stats = arguments.get("includeStats", True)

        if output_format == "isonl":
            content = await self.store.export_to_isonl()
        elif output_format == "isongraph":
            content = await self.store.export_to_isongraph()
        else:
            content = await self.store.export_to_ison()

        if include_stats:
            stats = await self.store.get_stats()
            content = stats.to_ison() + "\n\n" + content

        return [TextContent(type="text", text=format_graph_output(content))]

    async def _handle_multi_hop_search(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle multi_hop_search tool"""
        entity_name = arguments.get("entityName")
        max_hops = arguments.get("maxHops", 2)
        relation_type = arguments.get("relationType")

        if not entity_name:
            return [TextContent(type="text", text="error: entityName required")]

        entity = await self.store.find_entity_by_name(entity_name)
        if not entity:
            return [TextContent(type="text", text=f"error: Entity '{entity_name}' not found")]

        result = await self.store.multi_hop_search(
            entity.id, max_hops, relation_type
        )

        # Add header
        header = [
            f"# Multi-Hop Search from '{entity_name}'",
            f"# Max hops: {max_hops}",
            f"# Relation filter: {relation_type or 'any'}",
            "",
        ]

        return [TextContent(type="text", text="\n".join(header) + result.to_ison())]

    async def _handle_delete_entities(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle delete_entities tool"""
        entity_names = arguments.get("entityNames", [])
        if not entity_names:
            return [TextContent(type="text", text="error: No entity names provided")]

        deleted = []
        errors = []

        for name in entity_names:
            entity = await self.store.find_entity_by_name(name)
            if not entity:
                errors.append({"name": name, "error": "Entity not found"})
                continue

            success = await self.store.delete_entity(entity.id)
            if success:
                deleted.append({"id": entity.id, "name": name})
            else:
                errors.append({"name": name, "error": "Delete failed"})

        # Build ISON response
        lines = [
            "# Entities Deleted",
            f"# Count: {len(deleted)}",
            "",
            "table.deleted",
            "id name",
        ]

        for item in deleted:
            lines.append(f":{item['id']} \"{item['name']}\"")

        if errors:
            lines.append("")
            lines.append("table.errors")
            lines.append("name error")
            for err in errors:
                lines.append(f"\"{err['name']}\" \"{err['error']}\"")

        return [TextContent(type="text", text="\n".join(lines))]

    async def _handle_update_entity(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle update_entity tool"""
        entity_name = arguments.get("entityName")
        new_name = arguments.get("newName")
        new_type = arguments.get("newType")

        if not entity_name:
            return [TextContent(type="text", text="error: entityName required")]

        entity = await self.store.find_entity_by_name(entity_name)
        if not entity:
            return [TextContent(type="text", text=f"error: Entity '{entity_name}' not found")]

        updated = await self.store.update_entity(
            entity.id,
            name=new_name,
            entity_type=new_type
        )

        if not updated:
            return [TextContent(type="text", text="error: Update failed")]

        # Build ISON response
        lines = [
            "# Entity Updated",
            "",
            "object.entity",
            "id name type updated_at",
            f":{updated.id} \"{updated.name}\" {updated.entity_type} "
            f"{format_timestamp(updated.updated_at or utc_now())}",
        ]

        return [TextContent(type="text", text="\n".join(lines))]

    async def _handle_memory_stats(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle memory_stats tool"""
        stats = await self.store.get_stats()
        return [TextContent(type="text", text=stats.to_ison())]

    async def _handle_compact_memory(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle compact_memory tool"""
        from ison_memory_mcp.config import CompactionStrategy

        strategy_str = arguments.get("strategy", "smart")
        dry_run = arguments.get("dryRun", False)

        strategy = CompactionStrategy(strategy_str)

        if not self.compactor:
            return [TextContent(type="text", text="error: Compactor not initialized")]

        result = await self.compactor.compact(self.store, strategy, dry_run)

        return [TextContent(type="text", text=result.to_ison())]

    async def _handle_backup_memory(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle backup_memory tool"""
        include_ison = arguments.get("includeIson", True)

        if not self.backup_manager:
            return [TextContent(type="text", text="error: Backup manager not initialized")]

        result = await self.backup_manager.create_backup(self.store, include_ison)

        # Build ISON response
        lines = [
            "# Backup Created",
            "",
            "object.backup",
            "success path size_mb compressed",
            f"{str(result.success).lower()} "
            f"\"{result.backup_path}\" "
            f"{round(result.size_bytes / (1024 * 1024), 2)} "
            f"{str(result.compressed).lower()}",
        ]

        if result.errors:
            lines.append("")
            lines.append("table.errors")
            lines.append("message")
            for err in result.errors:
                lines.append(f"\"{err}\"")

        return [TextContent(type="text", text="\n".join(lines))]

    async def _handle_list_backups(
        self,
        arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle list_backups tool"""
        if not self.backup_manager:
            return [TextContent(type="text", text="error: Backup manager not initialized")]

        backups = self.backup_manager.list_backups()

        # Build ISON response
        lines = [
            "# Available Backups",
            f"# Count: {len(backups)}",
            "",
            "table.backups",
            "name size_mb created_at compressed",
        ]

        for backup in backups:
            lines.append(
                f"\"{backup['name']}\" {backup['size_mb']} "
                f"{backup['created_at']} {str(backup['compressed']).lower()}"
            )

        return [TextContent(type="text", text="\n".join(lines))]

    async def run(self) -> None:
        """Run the MCP server"""
        await self.initialize()

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.shutdown()


async def run_server(config: Optional[MemoryConfig] = None) -> None:
    """Entry point for running the server"""
    server = ISONMemoryServer(config)
    await server.run()


def main() -> None:
    """Synchronous entry point"""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
