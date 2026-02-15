"""
Tests for ISON Memory Store
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from ison_memory_mcp.config import MemoryConfig
from ison_memory_mcp.store import MemoryStore


@pytest.fixture
def temp_config():
    """Create a temporary configuration for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MemoryConfig()
        config.storage.path = Path(tmpdir) / "test_memory.db"
        config.ensure_directories()
        yield config


@pytest.fixture
async def store(temp_config):
    """Create an initialized store for testing"""
    store = MemoryStore(temp_config)
    await store.initialize()
    yield store
    await store.close()


class TestEntityOperations:
    """Test entity CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_entity(self, store):
        """Test creating an entity"""
        entity = await store.create_entity("Test Entity", "concept")

        assert entity.id is not None
        assert entity.name == "Test Entity"
        assert entity.entity_type == "concept"
        assert entity.created_at is not None

    @pytest.mark.asyncio
    async def test_get_entity(self, store):
        """Test retrieving an entity"""
        created = await store.create_entity("Test Entity", "person")
        retrieved = await store.get_entity(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_find_entity_by_name(self, store):
        """Test finding entity by name"""
        await store.create_entity("Alice", "person")
        found = await store.find_entity_by_name("alice")  # Case insensitive

        assert found is not None
        assert found.name == "Alice"

    @pytest.mark.asyncio
    async def test_update_entity(self, store):
        """Test updating an entity"""
        entity = await store.create_entity("Old Name", "concept")
        updated = await store.update_entity(entity.id, name="New Name")

        assert updated.name == "New Name"
        assert updated.updated_at is not None

    @pytest.mark.asyncio
    async def test_delete_entity(self, store):
        """Test deleting an entity"""
        entity = await store.create_entity("To Delete", "concept")
        success = await store.delete_entity(entity.id)

        assert success is True
        assert await store.get_entity(entity.id) is None


class TestObservationOperations:
    """Test observation operations"""

    @pytest.mark.asyncio
    async def test_create_observation(self, store):
        """Test creating an observation"""
        entity = await store.create_entity("Test Entity", "person")
        obs = await store.create_observation(
            entity.id,
            "This is a test observation",
            source="test"
        )

        assert obs.id is not None
        assert obs.entity_id == entity.id
        assert obs.content == "This is a test observation"

    @pytest.mark.asyncio
    async def test_get_observations(self, store):
        """Test retrieving observations"""
        entity = await store.create_entity("Test Entity", "person")
        await store.create_observation(entity.id, "Observation 1")
        await store.create_observation(entity.id, "Observation 2")

        observations = await store.get_observations(entity.id)

        assert len(observations) == 2

    @pytest.mark.asyncio
    async def test_duplicate_observation_handling(self, store):
        """Test that duplicate observations are handled"""
        entity = await store.create_entity("Test Entity", "person")
        obs1 = await store.create_observation(entity.id, "Same content")
        obs2 = await store.create_observation(entity.id, "Same content")

        # Should return same observation (deduplication)
        assert obs1.id == obs2.id

    @pytest.mark.asyncio
    async def test_search_observations(self, store):
        """Test full-text search on observations"""
        entity = await store.create_entity("Developer", "person")
        await store.create_observation(entity.id, "Works on machine learning")
        await store.create_observation(entity.id, "Expert in Python")

        results = await store.search_observations("machine")

        assert len(results) >= 1
        assert any("machine" in obs.content.lower() for obs in results)


class TestRelationOperations:
    """Test relation operations"""

    @pytest.mark.asyncio
    async def test_create_relation(self, store):
        """Test creating a relation"""
        entity1 = await store.create_entity("Alice", "person")
        entity2 = await store.create_entity("Bob", "person")

        relation = await store.create_relation(
            entity1.id,
            entity2.id,
            "KNOWS"
        )

        assert relation.id is not None
        assert relation.from_entity == entity1.id
        assert relation.to_entity == entity2.id
        assert relation.relation_type == "KNOWS"

    @pytest.mark.asyncio
    async def test_get_relations(self, store):
        """Test retrieving relations"""
        alice = await store.create_entity("Alice", "person")
        bob = await store.create_entity("Bob", "person")
        project = await store.create_entity("Project X", "project")

        await store.create_relation(alice.id, bob.id, "KNOWS")
        await store.create_relation(alice.id, project.id, "WORKS_ON")

        relations = await store.get_relations(alice.id, direction="out")

        assert len(relations) == 2

    @pytest.mark.asyncio
    async def test_bidirectional_relation(self, store):
        """Test bidirectional relation creation"""
        alice = await store.create_entity("Alice", "person")
        bob = await store.create_entity("Bob", "person")

        await store.create_relation(alice.id, bob.id, "KNOWS", bidirectional=True)

        alice_relations = await store.get_relations(alice.id, direction="out")
        bob_relations = await store.get_relations(bob.id, direction="out")

        assert len(alice_relations) >= 1
        assert len(bob_relations) >= 1


class TestSearch:
    """Test search functionality"""

    @pytest.mark.asyncio
    async def test_search(self, store):
        """Test general search"""
        entity = await store.create_entity("Machine Learning Project", "project")
        await store.create_observation(entity.id, "Uses TensorFlow for deep learning")

        result = await store.search("machine learning")

        assert result.total_count > 0
        assert len(result.entities) > 0 or len(result.observations) > 0

    @pytest.mark.asyncio
    async def test_multi_hop_search(self, store):
        """Test multi-hop graph traversal"""
        alice = await store.create_entity("Alice", "person")
        bob = await store.create_entity("Bob", "person")
        charlie = await store.create_entity("Charlie", "person")

        await store.create_relation(alice.id, bob.id, "KNOWS")
        await store.create_relation(bob.id, charlie.id, "KNOWS")

        result = await store.multi_hop_search(alice.id, max_hops=2)

        # Should find Alice, Bob, and Charlie
        assert len(result.entities) == 3


class TestExport:
    """Test ISON export functionality"""

    @pytest.mark.asyncio
    async def test_export_to_ison(self, store):
        """Test ISON export"""
        await store.create_entity("Test Entity", "concept")
        ison_output = await store.export_to_ison()

        assert "table.entities" in ison_output
        assert "Test Entity" in ison_output

    @pytest.mark.asyncio
    async def test_export_to_isonl(self, store):
        """Test ISONL streaming export"""
        await store.create_entity("Test Entity", "concept")
        isonl_output = await store.export_to_isonl()

        assert "entities|" in isonl_output

    @pytest.mark.asyncio
    async def test_export_to_isongraph(self, store):
        """Test ISONGraph export"""
        entity = await store.create_entity("Test Entity", "concept")
        await store.create_observation(entity.id, "Test observation")
        isongraph_output = await store.export_to_isongraph()

        assert "nodes.concept" in isongraph_output
        assert "table.observations" in isongraph_output


class TestStats:
    """Test statistics functionality"""

    @pytest.mark.asyncio
    async def test_get_stats(self, store):
        """Test getting statistics"""
        await store.create_entity("Entity 1", "person")
        await store.create_entity("Entity 2", "project")

        stats = await store.get_stats()

        assert stats.entity_count == 2
        assert "person" in stats.entity_types
        assert "project" in stats.entity_types

    @pytest.mark.asyncio
    async def test_stats_to_ison(self, store):
        """Test ISON format for statistics"""
        await store.create_entity("Test", "concept")

        stats = await store.get_stats()
        ison_output = stats.to_ison()

        assert "object.stats" in ison_output
        assert "table.entity_types" in ison_output
