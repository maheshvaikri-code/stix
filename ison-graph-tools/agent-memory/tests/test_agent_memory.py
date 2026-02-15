import pytest
import tempfile
import os

from agent_memory import AgentMemory
from agent_memory.stores import (
    CodebaseStore, DecisionStore, ConventionStore, BugPatternStore,
    DependencyStore, TestPatternStore, PerformanceStore, TechDebtStore,
    TeamStore, SessionStore, TemplateStore, SkillStore,
)
from ison_graph import ISONGraph


class TestAgentMemory:
    @pytest.fixture
    def memory(self):
        return AgentMemory("test-project")

    def test_initialization(self, memory):
        assert memory.name == "test-project"


class TestCodebaseStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return CodebaseStore(g)

    def test_add_module(self, store):
        assert store.add_module("src/core", "Core") is not None


class TestDecisionStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return DecisionStore(g)

    def test_add_decision(self, store):
        assert store.add_decision("Use PG", "DB") is not None


class TestConventionStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return ConventionStore(g)

    def test_add_convention(self, store):
        assert store.add_convention("naming", "snake_case", "ruff") is not None


class TestBugPatternStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return BugPatternStore(g)

    def test_add_bug(self, store):
        assert store.add_bug("Memory leak", "high") is not None


class TestSessionStore:
    @pytest.fixture
    def store(self):
        return SessionStore(ISONGraph(name="test"))

    def test_start_session(self, store):
        assert store.start_session("Task").startswith("s_")


class TestDependencyStore:
    @pytest.fixture
    def store(self):
        return DependencyStore(ISONGraph(name="test"))

    def test_add_dependency(self, store):
        assert store.add_dependency("requests", "2.28", "http") is not None


class TestTeamStore:
    @pytest.fixture
    def store(self):
        return TeamStore(ISONGraph(name="test"))

    def test_add_member(self, store):
        assert store.add_member("Alice", "Dev") is not None


class TestPerformanceStore:
    @pytest.fixture
    def store(self):
        return PerformanceStore(ISONGraph(name="test"))

    def test_add_baseline(self, store):
        assert store.add_baseline("op", 10, 50, "100rps") is not None


class TestTechDebtStore:
    @pytest.fixture
    def store(self):
        return TechDebtStore(ISONGraph(name="test"))

    def test_add_debt(self, store):
        assert store.add_debt("src/old.py", "Old code", "high") is not None


class TestTemplateStore:
    @pytest.fixture
    def store(self):
        return TemplateStore(ISONGraph(name="test"))

    def test_add_template(self, store):
        assert store.add_template("Handler", "handler") is not None


class TestSkillStore:
    @pytest.fixture
    def store(self):
        return SkillStore(ISONGraph(name="test"))

    def test_add_skill(self, store):
        assert store.add_skill("Python", "lang", 0.8) is not None


class TestTestPatterns:
    @pytest.fixture
    def store(self):
        return TestPatternStore(ISONGraph(name="test"))

    def test_add_convention(self, store):
        assert store.add_convention("unit", "one behavior") is not None
