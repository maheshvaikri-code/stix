"""
ISONCache MCP Server
====================

Model Context Protocol server for ISONCache operations.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from .cache import ISONCache
from .graph_cache import ISONGraphCache
from .embedding_cache import EmbeddingCache
from .schema import CacheConfig, Priority


# Global cache instances
_cache: Optional[ISONCache] = None
_graph_cache: Optional[ISONGraphCache] = None
_embedding_cache: Optional[EmbeddingCache] = None


def get_cache() -> ISONCache:
    """Get or create the cache instance"""
    global _cache
    if _cache is None:
        _cache = ISONCache()
    return _cache


def get_graph_cache() -> ISONGraphCache:
    """Get or create the graph cache instance"""
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = ISONGraphCache()
    return _graph_cache


def get_embedding_cache() -> EmbeddingCache:
    """Get or create the embedding cache instance"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


# Tool definitions for MCP
TOOLS = [
    {
        "name": "cache_set",
        "description": "Store a value in the cache with optional TTL. Values are automatically token-counted and ISON-formatted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Cache key (e.g., 'user:101', 'session:abc')"
                },
                "value": {
                    "type": "object",
                    "description": "Value to cache (dict, list, or primitive)"
                },
                "ttl": {
                    "type": "integer",
                    "description": "Time-to-live in seconds (default: 3600)",
                    "default": 3600
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for grouping"
                }
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "cache_get",
        "description": "Retrieve a cached value in ISON format, ready for LLM context injection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Cache key to retrieve"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to return (truncates if exceeded)",
                    "default": 4000
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "cache_mget",
        "description": "Get multiple cached values as combined ISON output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of keys to retrieve"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Total token budget"
                },
                "merge": {
                    "type": "boolean",
                    "description": "Merge similar schemas into tables",
                    "default": True
                }
            },
            "required": ["keys"]
        }
    },
    {
        "name": "cache_budget_get",
        "description": "Get as many cached values as fit within a token budget, prioritized by access patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Key pattern to match (e.g., 'user:*', 'session:abc*')"
                },
                "token_budget": {
                    "type": "integer",
                    "description": "Maximum total tokens"
                },
                "priority": {
                    "type": "string",
                    "enum": ["hits", "recent", "oldest", "tokens", "priority"],
                    "description": "Priority for selection",
                    "default": "hits"
                }
            },
            "required": ["pattern", "token_budget"]
        }
    },
    {
        "name": "cache_delete",
        "description": "Delete a key from the cache.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key to delete"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "cache_keys",
        "description": "List cache keys matching a pattern.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., 'user:*')",
                    "default": "*"
                }
            }
        }
    },
    {
        "name": "cache_stats",
        "description": "Get cache statistics including entries, tokens, hit rate.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "graph_set",
        "description": "Store a knowledge graph (entities + relations) in the cache.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Graph key"
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of entity objects with id, type, name"
                },
                "relations": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of relation objects with from, to, type"
                },
                "ttl": {
                    "type": "integer",
                    "description": "Time-to-live in seconds"
                }
            },
            "required": ["key", "entities", "relations"]
        }
    },
    {
        "name": "graph_traverse",
        "description": "Traverse from an entity and return connected subgraph in ISON format.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_entity": {
                    "type": "string",
                    "description": "Starting entity ID"
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum traversal depth",
                    "default": 2
                },
                "relation_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by relation types (optional)"
                },
                "token_budget": {
                    "type": "integer",
                    "description": "Maximum tokens for result"
                },
                "direction": {
                    "type": "string",
                    "enum": ["out", "in", "both"],
                    "default": "out"
                }
            },
            "required": ["start_entity"]
        }
    },
    {
        "name": "graph_get",
        "description": "Get a cached graph in ISON format.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Graph key"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "embedding_set",
        "description": "Store text with its embedding for similarity search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Entry key"
                },
                "text": {
                    "type": "string",
                    "description": "Text content"
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata"
                }
            },
            "required": ["key", "text"]
        }
    },
    {
        "name": "embedding_search",
        "description": "Search for similar texts using semantic similarity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query text"
                },
                "k": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 10
                },
                "token_budget": {
                    "type": "integer",
                    "description": "Maximum tokens in results"
                }
            },
            "required": ["query"]
        }
    }
]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a tool call from MCP"""

    cache = get_cache()
    graph_cache = get_graph_cache()
    embedding_cache = get_embedding_cache()

    try:
        # Key-Value Cache Operations
        if name == "cache_set":
            entry = cache.set(
                key=arguments["key"],
                value=arguments["value"],
                ttl=arguments.get("ttl", 3600),
                tags=arguments.get("tags"),
            )
            return {
                "success": True,
                "key": entry.key,
                "tokens": entry.tokens,
                "expires_in": entry.ttl_seconds,
            }

        elif name == "cache_get":
            result = cache.get(
                key=arguments["key"],
                max_tokens=arguments.get("max_tokens"),
            )
            if result is None:
                return {"success": False, "error": "Key not found"}
            return {"success": True, "ison": result}

        elif name == "cache_mget":
            result = cache.mget(
                keys=arguments["keys"],
                max_tokens=arguments.get("max_tokens"),
                merge=arguments.get("merge", True),
            )
            if result is None:
                return {"success": False, "error": "No keys found"}
            return {"success": True, "ison": result}

        elif name == "cache_budget_get":
            priority_str = arguments.get("priority", "hits")
            priority = Priority[priority_str.upper()]

            result = cache.get_within_budget(
                patterns=arguments["pattern"],
                token_budget=arguments["token_budget"],
                priority=priority,
            )
            return {
                "success": True,
                "ison": result.ison,
                "tokens_used": result.tokens_used,
                "tokens_budget": result.tokens_budget,
                "keys_included": result.keys_included,
                "keys_excluded": result.keys_excluded,
                "truncated": result.truncated,
            }

        elif name == "cache_delete":
            deleted = cache.delete(arguments["key"])
            return {"success": deleted}

        elif name == "cache_keys":
            keys = cache.keys(arguments.get("pattern", "*"))
            return {"success": True, "keys": keys, "count": len(keys)}

        elif name == "cache_stats":
            stats = cache.stats()
            return {
                "success": True,
                "entries": stats.total_entries,
                "tokens": stats.total_tokens,
                "hits": stats.total_hits,
                "misses": stats.total_misses,
                "hit_rate": round(stats.hit_rate, 2),
                "memory_mb": round(stats.memory_bytes / 1024 / 1024, 2),
            }

        # Graph Cache Operations
        elif name == "graph_set":
            entry = graph_cache.set_graph(
                key=arguments["key"],
                entities=arguments["entities"],
                relations=arguments["relations"],
                ttl=arguments.get("ttl"),
            )
            return {
                "success": True,
                "key": entry.key,
                "entities": entry.entity_count,
                "relations": entry.relation_count,
                "tokens": entry.tokens,
            }

        elif name == "graph_get":
            result = graph_cache.get_graph(
                key=arguments["key"],
                max_tokens=arguments.get("max_tokens"),
            )
            if result is None:
                return {"success": False, "error": "Graph not found"}
            return {"success": True, "ison": result}

        elif name == "graph_traverse":
            result = graph_cache.traverse(
                start_entity=arguments["start_entity"],
                max_hops=arguments.get("max_hops", 2),
                relation_types=arguments.get("relation_types"),
                token_budget=arguments.get("token_budget"),
                direction=arguments.get("direction", "out"),
            )
            return {
                "success": True,
                "ison": result.ison,
                "tokens_used": result.tokens_used,
                "entities": result.entities_included,
                "relations": result.relations_included,
                "hops": result.hops_traversed,
                "truncated": result.truncated,
            }

        # Embedding Cache Operations
        elif name == "embedding_set":
            entry = embedding_cache.set(
                key=arguments["key"],
                text=arguments["text"],
                metadata=arguments.get("metadata"),
            )
            return {
                "success": True,
                "key": entry.key,
                "tokens": entry.tokens,
                "dimension": entry.dimension,
            }

        elif name == "embedding_search":
            results = embedding_cache.search(
                query=arguments["query"],
                k=arguments.get("k", 10),
                token_budget=arguments.get("token_budget"),
            )
            return {
                "success": True,
                "results": [
                    {
                        "key": r.key,
                        "text": r.text,
                        "score": round(r.score, 4),
                        "tokens": r.tokens,
                    }
                    for r in results
                ],
                "count": len(results),
            }

        else:
            return {"success": False, "error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def serve():
    """Start the MCP server"""
    try:
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        import mcp.server.stdio

        server = Server("isoncache")

        @server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"]
                )
                for t in TOOLS
            ]

        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list:
            result = await handle_tool_call(name, arguments)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        async def main():
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )

        asyncio.run(main())

    except ImportError:
        print("MCP package not installed. Install with: pip install ison-cache[mcp]")
        raise SystemExit(1)


if __name__ == "__main__":
    serve()
