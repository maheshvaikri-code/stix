"""
HTTP/REST API Server
====================

FastAPI-based REST API for ISONCache.
"""

import json
from typing import Any, Dict, List, Optional, Union

from ..cache import ISONCache
from ..graph_cache import ISONGraphCache
from ..embedding_cache import EmbeddingCache
from ..schema import Priority


def create_app(
    cache: Optional[ISONCache] = None,
    graph_cache: Optional[ISONGraphCache] = None,
    embedding_cache: Optional[EmbeddingCache] = None,
):
    """
    Create FastAPI application for ISONCache.

    Args:
        cache: ISONCache instance
        graph_cache: ISONGraphCache instance
        embedding_cache: EmbeddingCache instance

    Returns:
        FastAPI application
    """
    try:
        from fastapi import FastAPI, HTTPException, Query, Body
        from fastapi.responses import PlainTextResponse, JSONResponse
        from pydantic import BaseModel
    except ImportError:
        raise ImportError("FastAPI not installed. Install with: pip install ison-cache[http]")

    app = FastAPI(
        title="ISONCache API",
        description="Token-efficient cache for LLM applications",
        version="1.0.0",
    )

    # Initialize caches
    _cache = cache or ISONCache()
    _graph_cache = graph_cache or ISONGraphCache()
    _embedding_cache = embedding_cache or EmbeddingCache()

    # =========================================================================
    # Request/Response Models
    # =========================================================================

    class SetRequest(BaseModel):
        key: str
        value: Any
        ttl: Optional[int] = 3600
        tags: Optional[List[str]] = None

    class MSetRequest(BaseModel):
        items: Dict[str, Any]
        ttl: Optional[int] = 3600

    class BudgetRequest(BaseModel):
        patterns: Union[str, List[str]]
        token_budget: int
        priority: str = "hits"
        exclude_keys: Optional[List[str]] = None

    class GraphSetRequest(BaseModel):
        key: str
        entities: List[Dict[str, Any]]
        relations: List[Dict[str, Any]]
        observations: Optional[List[Dict[str, Any]]] = None
        ttl: Optional[int] = None

    class TraverseRequest(BaseModel):
        start_entity: str
        max_hops: int = 2
        relation_types: Optional[List[str]] = None
        token_budget: Optional[int] = None
        direction: str = "out"

    class EmbeddingSetRequest(BaseModel):
        key: str
        text: str
        metadata: Optional[Dict[str, Any]] = None

    class SearchRequest(BaseModel):
        query: str
        k: int = 10
        token_budget: Optional[int] = None

    # =========================================================================
    # Key-Value Endpoints
    # =========================================================================

    @app.post("/cache/set")
    async def cache_set(request: SetRequest):
        """Store a value in the cache"""
        entry = _cache.set(
            key=request.key,
            value=request.value,
            ttl=request.ttl,
            tags=request.tags,
        )
        return {
            "key": entry.key,
            "tokens": entry.tokens,
            "expires_in": entry.ttl_seconds,
        }

    @app.get("/cache/get/{key}")
    async def cache_get(
        key: str,
        max_tokens: Optional[int] = None,
        format: str = "ison"
    ):
        """Get a cached value"""
        if format == "ison":
            result = _cache.get(key, max_tokens=max_tokens)
            if result is None:
                raise HTTPException(status_code=404, detail="Key not found")
            return PlainTextResponse(result, media_type="text/plain")
        else:
            result = _cache.get_raw(key)
            if result is None:
                raise HTTPException(status_code=404, detail="Key not found")
            return result

    @app.delete("/cache/delete/{key}")
    async def cache_delete(key: str):
        """Delete a key"""
        deleted = _cache.delete(key)
        return {"deleted": deleted}

    @app.get("/cache/exists/{key}")
    async def cache_exists(key: str):
        """Check if key exists"""
        return {"exists": _cache.exists(key)}

    @app.get("/cache/ttl/{key}")
    async def cache_ttl(key: str):
        """Get TTL for a key"""
        ttl = _cache.ttl(key)
        return {"ttl": ttl}

    @app.get("/cache/keys")
    async def cache_keys(pattern: str = "*"):
        """Get keys matching pattern"""
        keys = _cache.keys(pattern)
        return {"keys": keys, "count": len(keys)}

    @app.post("/cache/mset")
    async def cache_mset(request: MSetRequest):
        """Set multiple keys"""
        count = _cache.mset(request.items, ttl=request.ttl)
        return {"count": count}

    @app.post("/cache/mget")
    async def cache_mget(
        keys: List[str] = Body(...),
        max_tokens: Optional[int] = None,
        merge: bool = True
    ):
        """Get multiple keys as combined ISON"""
        result = _cache.mget(keys, max_tokens=max_tokens, merge=merge)
        if result is None:
            raise HTTPException(status_code=404, detail="No keys found")
        return PlainTextResponse(result, media_type="text/plain")

    @app.post("/cache/budget")
    async def cache_budget(request: BudgetRequest):
        """Get values within token budget"""
        priority = Priority[request.priority.upper()]
        exclude = set(request.exclude_keys) if request.exclude_keys else None

        result = _cache.get_within_budget(
            patterns=request.patterns,
            token_budget=request.token_budget,
            priority=priority,
            exclude_keys=exclude,
        )
        return {
            "ison": result.ison,
            "tokens_used": result.tokens_used,
            "tokens_budget": result.tokens_budget,
            "keys_included": result.keys_included,
            "keys_excluded": result.keys_excluded,
            "truncated": result.truncated,
        }

    @app.get("/cache/stats")
    async def cache_stats():
        """Get cache statistics"""
        stats = _cache.stats()
        return {
            "entries": stats.total_entries,
            "tokens": stats.total_tokens,
            "hits": stats.total_hits,
            "misses": stats.total_misses,
            "hit_rate": round(stats.hit_rate, 2),
            "memory_mb": round(stats.memory_bytes / 1024 / 1024, 2),
            "entries_by_type": stats.entries_by_type,
        }

    @app.post("/cache/clear")
    async def cache_clear():
        """Clear all cache entries"""
        count = _cache.clear()
        return {"cleared": count}

    # =========================================================================
    # Graph Endpoints
    # =========================================================================

    @app.post("/graph/set")
    async def graph_set(request: GraphSetRequest):
        """Store a graph"""
        entry = _graph_cache.set_graph(
            key=request.key,
            entities=request.entities,
            relations=request.relations,
            observations=request.observations,
            ttl=request.ttl,
        )
        return {
            "key": entry.key,
            "entities": entry.entity_count,
            "relations": entry.relation_count,
            "tokens": entry.tokens,
        }

    @app.get("/graph/get/{key}")
    async def graph_get(key: str, max_tokens: Optional[int] = None):
        """Get a cached graph"""
        result = _graph_cache.get_graph(key, max_tokens=max_tokens)
        if result is None:
            raise HTTPException(status_code=404, detail="Graph not found")
        return PlainTextResponse(result, media_type="text/plain")

    @app.delete("/graph/delete/{key}")
    async def graph_delete(key: str):
        """Delete a graph"""
        deleted = _graph_cache.delete(key)
        return {"deleted": deleted}

    @app.post("/graph/traverse")
    async def graph_traverse(request: TraverseRequest):
        """Traverse from an entity"""
        result = _graph_cache.traverse(
            start_entity=request.start_entity,
            max_hops=request.max_hops,
            relation_types=request.relation_types,
            token_budget=request.token_budget,
            direction=request.direction,
        )
        return {
            "ison": result.ison,
            "tokens_used": result.tokens_used,
            "entities_included": result.entities_included,
            "relations_included": result.relations_included,
            "hops_traversed": result.hops_traversed,
            "truncated": result.truncated,
        }

    @app.get("/graph/entity/{entity_id}")
    async def graph_entity(entity_id: str):
        """Get an entity by ID"""
        entity = _graph_cache.get_entity(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    @app.get("/graph/stats")
    async def graph_stats():
        """Get graph cache statistics"""
        return _graph_cache.stats()

    # =========================================================================
    # Embedding Endpoints
    # =========================================================================

    @app.post("/embedding/set")
    async def embedding_set(request: EmbeddingSetRequest):
        """Store text with embedding"""
        entry = _embedding_cache.set(
            key=request.key,
            text=request.text,
            metadata=request.metadata,
        )
        return {
            "key": entry.key,
            "tokens": entry.tokens,
            "dimension": entry.dimension,
        }

    @app.post("/embedding/search")
    async def embedding_search(request: SearchRequest):
        """Search for similar texts"""
        results = _embedding_cache.search(
            query=request.query,
            k=request.k,
            token_budget=request.token_budget,
        )
        return {
            "results": [
                {
                    "key": r.key,
                    "text": r.text,
                    "score": round(r.score, 4),
                    "tokens": r.tokens,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "count": len(results),
        }

    @app.get("/embedding/search/ison")
    async def embedding_search_ison(
        query: str,
        k: int = 10,
        token_budget: Optional[int] = None
    ):
        """Search and return results as ISON"""
        result = _embedding_cache.search_to_ison(query, k=k, token_budget=token_budget)
        return PlainTextResponse(result, media_type="text/plain")

    @app.get("/embedding/stats")
    async def embedding_stats():
        """Get embedding cache statistics"""
        return _embedding_cache.stats()

    # =========================================================================
    # Health/Info
    # =========================================================================

    @app.get("/health")
    async def health():
        """Health check"""
        return {"status": "healthy"}

    @app.get("/info")
    async def info():
        """Server info"""
        return {
            "name": "ISONCache",
            "version": "1.0.0",
            "cache": _cache.info(),
            "graph": _graph_cache.stats(),
            "embedding": _embedding_cache.stats(),
        }

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 8380,
    cache: Optional[ISONCache] = None,
):
    """Run the HTTP server"""
    try:
        import uvicorn
    except ImportError:
        raise ImportError("Uvicorn not installed. Install with: pip install ison-cache[http]")

    app = create_app(cache)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
