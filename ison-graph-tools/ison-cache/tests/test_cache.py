"""
ISONCache Tests
===============

Unit tests for ISONCache functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from datetime import timedelta


class TestISONCache:
    """Tests for ISONCache class"""

    def test_basic_set_get(self):
        """Test basic set and get operations"""
        from ison_cache import ISONCache

        cache = ISONCache()

        # Set a value
        entry = cache.set("test:1", {"id": 1, "name": "Test"})
        assert entry.key == "test:1"
        assert entry.tokens > 0

        # Get the value
        result = cache.get("test:1")
        assert result is not None
        assert "Test" in result

    def test_get_nonexistent(self):
        """Test get on nonexistent key"""
        from ison_cache import ISONCache

        cache = ISONCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_delete(self):
        """Test delete operation"""
        from ison_cache import ISONCache

        cache = ISONCache()
        cache.set("test:del", {"data": "value"})

        assert cache.exists("test:del")
        assert cache.delete("test:del")
        assert not cache.exists("test:del")

    def test_ttl_expiry(self):
        """Test TTL expiration"""
        from ison_cache import ISONCache
        import time

        cache = ISONCache()
        cache.set("test:ttl", {"data": "value"}, ttl=1)

        assert cache.exists("test:ttl")

        # Wait for expiry
        time.sleep(1.5)

        assert not cache.exists("test:ttl")
        assert cache.get("test:ttl") is None

    def test_mset_mget(self):
        """Test batch operations"""
        from ison_cache import ISONCache

        cache = ISONCache()

        cache.mset({
            "batch:1": {"id": 1},
            "batch:2": {"id": 2},
            "batch:3": {"id": 3},
        })

        result = cache.mget(["batch:1", "batch:2", "batch:3"])
        assert result is not None
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_keys_pattern(self):
        """Test pattern matching for keys"""
        from ison_cache import ISONCache

        cache = ISONCache()

        cache.set("user:1", {"id": 1})
        cache.set("user:2", {"id": 2})
        cache.set("product:1", {"id": 1})

        user_keys = cache.keys("user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys

    def test_budget_retrieval(self):
        """Test token-budgeted retrieval"""
        from ison_cache import ISONCache
        from ison_cache.schema import Priority

        cache = ISONCache()

        for i in range(10):
            cache.set(f"item:{i}", {"id": i, "data": f"Item {i}"})

        result = cache.get_within_budget(
            patterns="item:*",
            token_budget=100,
            priority=Priority.TOKENS
        )

        assert result.tokens_used <= 100
        assert len(result.keys_included) > 0

    def test_tags(self):
        """Test tag operations"""
        from ison_cache import ISONCache

        cache = ISONCache()

        cache.set("tagged:1", {"id": 1}, tags=["important"])
        cache.set("tagged:2", {"id": 2}, tags=["important", "urgent"])
        cache.set("tagged:3", {"id": 3}, tags=["normal"])

        important = cache.get_by_tag("important")
        assert len(important) == 2

    def test_stats(self):
        """Test cache statistics"""
        from ison_cache import ISONCache

        cache = ISONCache()

        cache.set("stat:1", {"id": 1})
        cache.get("stat:1")
        cache.get("stat:1")
        cache.get("nonexistent")

        stats = cache.stats()
        assert stats.total_entries == 1
        assert stats.total_hits == 2
        assert stats.total_misses == 1


class TestISONGraphCache:
    """Tests for ISONGraphCache class"""

    def test_set_graph(self):
        """Test setting a graph"""
        from ison_cache import ISONGraphCache

        cache = ISONGraphCache()

        entities = [
            {"id": "e1", "type": "person", "name": "Alice"},
            {"id": "e2", "type": "person", "name": "Bob"},
        ]
        relations = [
            {"from": "e1", "to": "e2", "type": "KNOWS"},
        ]

        entry = cache.set_graph("test:graph", entities, relations)
        assert entry.entity_count == 2
        assert entry.relation_count == 1

    def test_get_graph(self):
        """Test getting a graph"""
        from ison_cache import ISONGraphCache

        cache = ISONGraphCache()

        entities = [{"id": "e1", "name": "Test"}]
        relations = []

        cache.set_graph("test:get", entities, relations)
        result = cache.get_graph("test:get")

        assert result is not None
        assert "Test" in result

    def test_traverse(self):
        """Test graph traversal"""
        from ison_cache import ISONGraphCache

        cache = ISONGraphCache()

        entities = [
            {"id": "a", "name": "A"},
            {"id": "b", "name": "B"},
            {"id": "c", "name": "C"},
        ]
        relations = [
            {"from": "a", "to": "b", "type": "LINK"},
            {"from": "b", "to": "c", "type": "LINK"},
        ]

        cache.set_graph("traverse:test", entities, relations)

        result = cache.traverse("a", max_hops=2)
        assert "a" in result.entities_included
        assert "b" in result.entities_included
        assert "c" in result.entities_included


class TestEmbeddingCache:
    """Tests for EmbeddingCache class"""

    def test_set_embedding(self):
        """Test setting an embedding"""
        from ison_cache import EmbeddingCache

        cache = EmbeddingCache(embedding_dim=64)

        entry = cache.set("emb:1", "This is a test document")
        assert entry.key == "emb:1"
        assert len(entry.vector) == 64
        assert entry.tokens > 0

    def test_search(self):
        """Test similarity search"""
        from ison_cache import EmbeddingCache

        cache = EmbeddingCache(embedding_dim=64)

        cache.set("doc:1", "Machine learning and AI")
        cache.set("doc:2", "Deep neural networks")
        cache.set("doc:3", "Python programming")

        results = cache.search("artificial intelligence", k=2)
        assert len(results) == 2


class TestTokenManager:
    """Tests for TokenManager class"""

    def test_count_tokens(self):
        """Test token counting"""
        from ison_cache import TokenManager

        tm = TokenManager()
        count = tm.count_tokens("Hello world")
        assert count > 0

    def test_compare_formats(self):
        """Test format comparison"""
        from ison_cache import TokenManager

        tm = TokenManager()

        data = [
            {"id": 1, "name": "Test"},
            {"id": 2, "name": "Another"},
        ]

        comparison = tm.compare_formats(data)
        assert comparison["ison_tokens"] < comparison["json_tokens"]
        assert comparison["savings"] > 0

    def test_budget(self):
        """Test token budget"""
        from ison_cache import TokenBudget

        budget = TokenBudget(total=100)
        assert budget.remaining == 100
        assert budget.can_fit(50)
        assert budget.consume(50)
        assert budget.remaining == 50
        assert not budget.can_fit(60)


class TestSerializer:
    """Tests for ISON serialization"""

    def test_serialize_object(self):
        """Test object serialization"""
        from ison_cache.serializer import to_ison

        result = to_ison({"id": 1, "name": "Test"}, "user")
        assert "object.user" in result
        assert "id" in result
        assert "name" in result

    def test_serialize_table(self):
        """Test table serialization"""
        from ison_cache.serializer import to_ison

        data = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
        result = to_ison(data, "items")
        assert "table.items" in result

    def test_deserialize(self):
        """Test deserialization"""
        from ison_cache.serializer import to_ison, from_ison

        original = {"id": 1, "name": "Test", "active": True}
        ison = to_ison(original, "data")
        parsed = from_ison(ison)

        assert "data" in parsed
        assert parsed["data"]["id"] == 1
        assert parsed["data"]["name"] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
