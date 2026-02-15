"""
Memory Integration
==================

Integrates Agent Learning with agent-memory and ISONCache patterns.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import math

from ison_graph import ISONGraph

from .stores.base import BaseLearningStore
from .schema import (
    LearningEventType,
    ExperienceOutcome,
    MistakeCategory,
    SkillLevel,
    FORGETTING_CURVE,
    SPACED_REPETITION_INTERVALS,
)


# =============================================================================
# Learning Memory Store - Follows agent-memory patterns
# =============================================================================

class LearningMemoryStore(BaseLearningStore):
    """
    Memory store for learning that follows agent-memory patterns.

    Features:
    - Working memory for current session
    - Episodic memory for experiences
    - Semantic memory for consolidated learnings
    - Procedural memory for skills
    """

    def __init__(self, graph: ISONGraph):
        super().__init__(graph, "learning_memory")

        # In-memory working context (non-persistent)
        self._working_memory: Dict[str, Any] = {}
        self._session_context: Dict[str, Any] = {}

    # =========================================================================
    # Working Memory (Current Session)
    # =========================================================================

    def set_working_context(
        self,
        agent_id: str,
        key: str,
        value: Any,
        importance: float = 0.5,
    ) -> None:
        """Set a value in working memory."""
        if agent_id not in self._working_memory:
            self._working_memory[agent_id] = {}

        self._working_memory[agent_id][key] = {
            "value": value,
            "importance": importance,
            "set_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_working_context(
        self,
        agent_id: str,
        key: str,
    ) -> Optional[Any]:
        """Get a value from working memory."""
        if agent_id not in self._working_memory:
            return None
        entry = self._working_memory[agent_id].get(key)
        return entry.get("value") if entry else None

    def get_working_memory(self, agent_id: str) -> Dict[str, Any]:
        """Get all working memory for an agent."""
        return self._working_memory.get(agent_id, {})

    def clear_working_memory(self, agent_id: str) -> None:
        """Clear working memory for an agent."""
        if agent_id in self._working_memory:
            del self._working_memory[agent_id]

    # =========================================================================
    # Episodic Memory (Experiences)
    # =========================================================================

    def store_episode(
        self,
        agent_id: str,
        episode_type: str,
        content: Dict[str, Any],
        outcome: str,
        emotional_valence: float,  # -1 (negative) to 1 (positive)
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Store an episode in episodic memory."""
        episode_id = self._generate_id("episode")

        self._add_node("episode", episode_id, {
            "agent_id": agent_id,
            "episode_type": episode_type,
            "content": content,
            "outcome": outcome,
            "emotional_valence": emotional_valence,
            "importance": importance,
            "tags": tags or [],
            "recall_count": 0,
            "last_recalled": None,
            "retention_strength": 1.0,
        })

        return episode_id

    def recall_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Recall an episode and update recall stats."""
        episode = self._get_node("episode", episode_id)
        if not episode:
            return None

        recall_count = episode.get("recall_count", 0) + 1
        retention = min(1.0, episode.get("retention_strength", 1.0) + 0.1)

        self._update_node("episode", episode_id, {
            "recall_count": recall_count,
            "last_recalled": self._now(),
            "retention_strength": retention,
        })

        return episode

    def search_episodes(
        self,
        agent_id: str,
        episode_type: Optional[str] = None,
        outcome: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search episodic memory."""
        episodes = self._find_nodes("episode", agent_id=agent_id)

        if episode_type:
            episodes = [e for e in episodes if e.get("episode_type") == episode_type]

        if outcome:
            episodes = [e for e in episodes if e.get("outcome") == outcome]

        if tags:
            tag_set = set(tags)
            episodes = [e for e in episodes if tag_set & set(e.get("tags", []))]

        episodes = [e for e in episodes if e.get("importance", 0) >= min_importance]

        # Sort by combined score of importance and recency
        for ep in episodes:
            ep["_relevance_score"] = self._calculate_episode_relevance(ep)

        episodes.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)

        return episodes[:limit]

    def _calculate_episode_relevance(self, episode: Dict[str, Any]) -> float:
        """Calculate relevance score for episode retrieval."""
        importance = episode.get("importance", 0.5)
        retention = episode.get("retention_strength", 1.0)
        valence_magnitude = abs(episode.get("emotional_valence", 0))

        # Recency factor
        created_at = episode.get("_created_at", "")
        recency = 1.0
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - created).days
                recency = math.exp(-0.05 * days_ago)
            except Exception:
                pass

        return (importance * 0.3 + retention * 0.3 + recency * 0.2 + valence_magnitude * 0.2)

    # =========================================================================
    # Semantic Memory (Consolidated Knowledge)
    # =========================================================================

    def store_semantic(
        self,
        agent_id: str,
        concept: str,
        category: str,
        content: str,
        confidence: float = 0.7,
        source_episodes: Optional[List[str]] = None,
        related_concepts: Optional[List[str]] = None,
    ) -> str:
        """Store semantic knowledge."""
        semantic_id = self._generate_id("semantic")

        self._add_node("semantic_memory", semantic_id, {
            "agent_id": agent_id,
            "concept": concept,
            "category": category,
            "content": content,
            "confidence": confidence,
            "source_episodes": source_episodes or [],
            "related_concepts": related_concepts or [],
            "reinforcement_count": 0,
            "last_reinforced": None,
        })

        # Link to source episodes
        for ep_id in (source_episodes or []):
            self._add_edge(
                "semantic_memory", semantic_id,
                "DERIVED_FROM",
                "episode", ep_id,
                {}
            )

        return semantic_id

    def reinforce_semantic(
        self,
        semantic_id: str,
        new_evidence: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reinforce semantic memory."""
        semantic = self._get_node("semantic_memory", semantic_id)
        if not semantic:
            return {"error": "Semantic memory not found"}

        reinforcement_count = semantic.get("reinforcement_count", 0) + 1
        confidence = min(1.0, semantic.get("confidence", 0.7) + 0.05)

        self._update_node("semantic_memory", semantic_id, {
            "reinforcement_count": reinforcement_count,
            "confidence": confidence,
            "last_reinforced": self._now(),
        })

        return {
            "reinforced": True,
            "new_confidence": confidence,
            "reinforcement_count": reinforcement_count,
        }

    def search_semantic(
        self,
        agent_id: str,
        category: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search semantic memory."""
        if category:
            memories = self._find_nodes("semantic_memory", agent_id=agent_id, category=category)
        else:
            memories = self._find_nodes("semantic_memory", agent_id=agent_id)

        memories = [m for m in memories if m.get("confidence", 0) >= min_confidence]
        memories.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return memories[:limit]

    # =========================================================================
    # Procedural Memory (Skills/Procedures)
    # =========================================================================

    def store_procedure(
        self,
        agent_id: str,
        name: str,
        category: str,
        steps: List[Dict[str, Any]],
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        proficiency: float = 0.0,
    ) -> str:
        """Store a procedure in procedural memory."""
        procedure_id = self._generate_id("procedure")

        self._add_node("procedural_memory", procedure_id, {
            "agent_id": agent_id,
            "name": name,
            "category": category,
            "steps": steps,
            "preconditions": preconditions or [],
            "postconditions": postconditions or [],
            "proficiency": proficiency,
            "execution_count": 0,
            "success_count": 0,
            "last_executed": None,
            "automaticity": 0.0,  # How automatic the procedure is (0-1)
        })

        return procedure_id

    def record_procedure_execution(
        self,
        procedure_id: str,
        success: bool,
        execution_time_ms: int,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record execution of a procedure."""
        procedure = self._get_node("procedural_memory", procedure_id)
        if not procedure:
            return {"error": "Procedure not found"}

        execution_count = procedure.get("execution_count", 0) + 1
        success_count = procedure.get("success_count", 0) + (1 if success else 0)

        # Update proficiency
        current_proficiency = procedure.get("proficiency", 0)
        alpha = 0.2
        new_proficiency = current_proficiency + alpha * ((1.0 if success else 0.0) * 100 - current_proficiency)

        # Update automaticity (increases with consistent execution)
        current_automaticity = procedure.get("automaticity", 0)
        if success:
            new_automaticity = min(1.0, current_automaticity + 0.05)
        else:
            new_automaticity = max(0, current_automaticity - 0.1)

        self._update_node("procedural_memory", procedure_id, {
            "execution_count": execution_count,
            "success_count": success_count,
            "proficiency": new_proficiency,
            "automaticity": new_automaticity,
            "last_executed": self._now(),
        })

        return {
            "executed": True,
            "success": success,
            "new_proficiency": new_proficiency,
            "automaticity": new_automaticity,
        }

    def get_procedure(
        self,
        agent_id: str,
        name: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a procedure by name."""
        procedures = self._find_nodes("procedural_memory", agent_id=agent_id, name=name)
        return procedures[0] if procedures else None

    # =========================================================================
    # Memory Consolidation
    # =========================================================================

    def consolidate_episodes_to_semantic(
        self,
        agent_id: str,
        episode_type: str,
        min_episodes: int = 3,
    ) -> Dict[str, Any]:
        """Consolidate similar episodes into semantic memory."""
        episodes = self.search_episodes(
            agent_id=agent_id,
            episode_type=episode_type,
            limit=50,
        )

        if len(episodes) < min_episodes:
            return {"consolidated": False, "reason": "Not enough episodes"}

        # Group by outcome
        by_outcome = {}
        for ep in episodes:
            outcome = ep.get("outcome", "unknown")
            if outcome not in by_outcome:
                by_outcome[outcome] = []
            by_outcome[outcome].append(ep)

        consolidated = []
        for outcome, eps in by_outcome.items():
            if len(eps) >= min_episodes:
                # Extract common patterns
                common_tags = self._find_common_tags(eps)

                semantic_id = self.store_semantic(
                    agent_id=agent_id,
                    concept=f"{episode_type}_{outcome}_pattern",
                    category=episode_type,
                    content=f"Pattern from {len(eps)} episodes with outcome {outcome}",
                    confidence=min(0.9, 0.5 + len(eps) * 0.05),
                    source_episodes=[ep.get("id") for ep in eps],
                    related_concepts=common_tags,
                )

                consolidated.append({
                    "semantic_id": semantic_id,
                    "episode_type": episode_type,
                    "outcome": outcome,
                    "source_count": len(eps),
                })

        return {
            "consolidated": True,
            "patterns_created": len(consolidated),
            "patterns": consolidated,
        }

    def _find_common_tags(self, episodes: List[Dict[str, Any]]) -> List[str]:
        """Find common tags across episodes."""
        if not episodes:
            return []

        tag_counts = {}
        for ep in episodes:
            for tag in ep.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        threshold = len(episodes) * 0.5
        return [tag for tag, count in tag_counts.items() if count >= threshold]

    def apply_memory_decay(self, agent_id: str) -> Dict[str, Any]:
        """Apply forgetting curve to memories."""
        episodes = self._find_nodes("episode", agent_id=agent_id)
        semantics = self._find_nodes("semantic_memory", agent_id=agent_id)
        procedures = self._find_nodes("procedural_memory", agent_id=agent_id)

        decayed_episodes = 0
        decayed_semantics = 0
        decayed_procedures = 0

        for ep in episodes:
            if self._apply_decay_to_memory(ep, "episode"):
                decayed_episodes += 1

        for sem in semantics:
            if self._apply_decay_to_memory(sem, "semantic_memory"):
                decayed_semantics += 1

        for proc in procedures:
            if self._apply_decay_to_memory(proc, "procedural_memory"):
                decayed_procedures += 1

        return {
            "agent_id": agent_id,
            "decayed_episodes": decayed_episodes,
            "decayed_semantics": decayed_semantics,
            "decayed_procedures": decayed_procedures,
        }

    def _apply_decay_to_memory(
        self,
        memory: Dict[str, Any],
        memory_type: str,
    ) -> bool:
        """Apply decay to a single memory entry."""
        # Get last access time
        last_access_field = {
            "episode": "last_recalled",
            "semantic_memory": "last_reinforced",
            "procedural_memory": "last_executed",
        }.get(memory_type, "last_recalled")

        last_access = memory.get(last_access_field) or memory.get("_created_at")

        if not last_access:
            return False

        try:
            last = datetime.fromisoformat(last_access.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - last).days
        except Exception:
            return False

        if days_since <= 0:
            return False

        # Apply decay
        decay_rate = FORGETTING_CURVE["decay_rate"]
        min_retention = FORGETTING_CURVE["min_retention"]

        decay_factor = max(min_retention, math.exp(-days_since / decay_rate))

        # Update retention/confidence/proficiency
        if memory_type == "episode":
            current = memory.get("retention_strength", 1.0)
            new_value = current * decay_factor
            self._update_node(memory_type, memory["id"], {
                "retention_strength": new_value,
            })
        elif memory_type == "semantic_memory":
            current = memory.get("confidence", 1.0)
            new_value = max(0.3, current * decay_factor)
            self._update_node(memory_type, memory["id"], {
                "confidence": new_value,
            })
        elif memory_type == "procedural_memory":
            current_prof = memory.get("proficiency", 0)
            current_auto = memory.get("automaticity", 0)
            self._update_node(memory_type, memory["id"], {
                "proficiency": current_prof * decay_factor,
                "automaticity": max(0, current_auto - 0.05 * days_since),
            })

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        episodes = self._find_nodes("episode")
        semantics = self._find_nodes("semantic_memory")
        procedures = self._find_nodes("procedural_memory")

        return {
            "total_episodes": len(episodes),
            "total_semantics": len(semantics),
            "total_procedures": len(procedures),
            "working_memory_agents": len(self._working_memory),
        }


# =============================================================================
# Cached Learning Context - Follows ISONCache patterns
# =============================================================================

class CachedLearningContext:
    """
    Token-budgeted context retrieval for learning.

    Follows ISONCache patterns for efficient context retrieval.
    """

    # Priority categories for learning context
    CATEGORY_PRIORITIES = {
        "active_mistakes": 100,      # Currently making this mistake
        "prevention_rules": 95,      # Rules to prevent mistakes
        "critical_learnings": 90,    # High-confidence learnings
        "relevant_episodes": 80,     # Relevant past experiences
        "skill_procedures": 75,      # Relevant procedures
        "semantic_knowledge": 70,    # Related knowledge
        "attention_reminders": 65,   # What to pay attention to
        "supervision_feedback": 60,  # Recent feedback
        "practice_due": 50,          # Skills needing practice
    }

    # Estimated tokens per item type
    TOKENS_PER_ITEM = {
        "active_mistakes": 150,
        "prevention_rules": 100,
        "critical_learnings": 80,
        "relevant_episodes": 200,
        "skill_procedures": 150,
        "semantic_knowledge": 100,
        "attention_reminders": 50,
        "supervision_feedback": 120,
        "practice_due": 60,
    }

    def __init__(
        self,
        memory_store: LearningMemoryStore,
        mistake_store,
        attention_store,
        supervision_store,
        skill_store,
    ):
        self.memory = memory_store
        self.mistake = mistake_store
        self.attention = attention_store
        self.supervision = supervision_store
        self.skill = skill_store

    def get_context(
        self,
        agent_id: str,
        task_type: str,
        token_budget: int = 2000,
        context_hints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get learning context within token budget.

        Prioritizes most relevant learning context for the current task.
        """
        context_hints = context_hints or {}
        context = {
            "agent_id": agent_id,
            "task_type": task_type,
            "token_budget": token_budget,
            "items": [],
        }

        remaining_budget = token_budget
        items_by_category = {}

        # Gather items by category
        items_by_category["active_mistakes"] = self._get_active_mistake_context(
            agent_id, task_type
        )
        items_by_category["prevention_rules"] = self._get_prevention_rules(
            agent_id, task_type
        )
        items_by_category["critical_learnings"] = self._get_critical_learnings(
            agent_id, task_type
        )
        items_by_category["relevant_episodes"] = self._get_relevant_episodes(
            agent_id, task_type, context_hints
        )
        items_by_category["skill_procedures"] = self._get_skill_procedures(
            agent_id, task_type
        )
        items_by_category["semantic_knowledge"] = self._get_semantic_knowledge(
            agent_id, task_type
        )
        items_by_category["attention_reminders"] = self._get_attention_reminders(
            agent_id, task_type
        )
        items_by_category["supervision_feedback"] = self._get_recent_feedback(
            agent_id
        )
        items_by_category["practice_due"] = self._get_practice_reminders(
            agent_id
        )

        # Sort categories by priority
        sorted_categories = sorted(
            self.CATEGORY_PRIORITIES.keys(),
            key=lambda x: self.CATEGORY_PRIORITIES[x],
            reverse=True,
        )

        # Fill context within budget
        for category in sorted_categories:
            items = items_by_category.get(category, [])
            tokens_per = self.TOKENS_PER_ITEM.get(category, 100)

            for item in items:
                if remaining_budget < tokens_per:
                    break

                context["items"].append({
                    "category": category,
                    "priority": self.CATEGORY_PRIORITIES[category],
                    "content": item,
                    "estimated_tokens": tokens_per,
                })
                remaining_budget -= tokens_per

            if remaining_budget < 50:
                break

        context["tokens_used"] = token_budget - remaining_budget
        context["items_included"] = len(context["items"])

        return context

    def _get_active_mistake_context(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get context about mistakes to avoid."""
        patterns = self.mistake.get_mistake_patterns(agent_id, min_frequency=2)

        relevant = []
        for pattern in patterns[:3]:
            relevant.append({
                "type": "mistake_pattern",
                "root_cause": pattern.get("root_cause"),
                "category": pattern.get("category"),
                "frequency": pattern.get("frequency"),
                "warning": f"Watch out for: {pattern.get('root_cause')}",
            })

        return relevant

    def _get_prevention_rules(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get prevention rules from mistake patterns."""
        recommendations = self.mistake.get_prevention_recommendations(agent_id, limit=3)

        rules = []
        for rec in recommendations:
            for strategy in rec.get("existing_strategies", [])[:1]:
                rules.append({
                    "type": "prevention_rule",
                    "pattern": rec.get("pattern_name"),
                    "rule": strategy.get("strategy"),
                })

        return rules

    def _get_critical_learnings(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get high-confidence learnings."""
        learnings = self.memory.search_semantic(
            agent_id=agent_id,
            min_confidence=0.8,
            limit=5,
        )

        return [
            {
                "type": "learning",
                "concept": l.get("concept"),
                "content": l.get("content"),
                "confidence": l.get("confidence"),
            }
            for l in learnings
        ]

    def _get_relevant_episodes(
        self,
        agent_id: str,
        task_type: str,
        context_hints: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get relevant past episodes."""
        tags = context_hints.get("tags", [])

        episodes = self.memory.search_episodes(
            agent_id=agent_id,
            episode_type=task_type,
            tags=tags if tags else None,
            min_importance=0.6,
            limit=3,
        )

        return [
            {
                "type": "episode",
                "outcome": ep.get("outcome"),
                "importance": ep.get("importance"),
                "tags": ep.get("tags", []),
            }
            for ep in episodes
        ]

    def _get_skill_procedures(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get relevant procedures."""
        procedure = self.memory.get_procedure(agent_id, task_type)

        if procedure:
            return [{
                "type": "procedure",
                "name": procedure.get("name"),
                "steps": procedure.get("steps", [])[:3],
                "proficiency": procedure.get("proficiency"),
            }]

        return []

    def _get_semantic_knowledge(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get relevant semantic knowledge."""
        knowledge = self.memory.search_semantic(
            agent_id=agent_id,
            category=task_type,
            min_confidence=0.6,
            limit=3,
        )

        return [
            {
                "type": "knowledge",
                "concept": k.get("concept"),
                "content": k.get("content"),
            }
            for k in knowledge
        ]

    def _get_attention_reminders(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get attention reminders."""
        frequently_missed = self.attention.get_frequently_missed(agent_id, min_count=2)

        return [
            {
                "type": "attention_reminder",
                "element": m.get("element"),
                "attention_type": m.get("attention_type"),
                "reminder": f"Remember to check: {m.get('element')}",
            }
            for m in frequently_missed[:3]
        ]

    def _get_recent_feedback(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get recent supervision feedback."""
        learnings = self.supervision.get_learnings_from_supervision(
            agent_id=agent_id,
            min_confidence=0.7,
        )

        return [
            {
                "type": "feedback",
                "content": l.get("learning_content"),
                "confidence": l.get("confidence"),
            }
            for l in learnings[:3]
        ]

    def _get_practice_reminders(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get skills due for practice."""
        due_skills = self.skill.get_skills_due_for_practice(agent_id, limit=3)

        return [
            {
                "type": "practice_due",
                "skill": s.get("name"),
                "level": s.get("level"),
                "reminder": f"Skill '{s.get('name')}' needs practice",
            }
            for s in due_skills
        ]


# =============================================================================
# Learning Session Manager
# =============================================================================

class LearningSessionManager:
    """
    Manages learning sessions with context continuity.
    """

    def __init__(self, memory_store: LearningMemoryStore):
        self.memory = memory_store
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def start_session(
        self,
        agent_id: str,
        task: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a learning session."""
        session_id = self.memory._generate_id("session")

        session = {
            "session_id": session_id,
            "agent_id": agent_id,
            "task": task,
            "task_type": task_type,
            "context": context or {},
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
            "learnings": [],
            "mistakes": [],
            "attention_points": [],
        }

        self._active_sessions[session_id] = session
        return session_id

    def add_event(
        self,
        session_id: str,
        event_type: str,
        details: Dict[str, Any],
    ) -> None:
        """Add an event to the session."""
        if session_id not in self._active_sessions:
            return

        self._active_sessions[session_id]["events"].append({
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_learning(
        self,
        session_id: str,
        learning: str,
        confidence: float = 0.7,
    ) -> None:
        """Record a learning during the session."""
        if session_id not in self._active_sessions:
            return

        self._active_sessions[session_id]["learnings"].append({
            "content": learning,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_mistake(
        self,
        session_id: str,
        mistake: str,
        severity: str = "medium",
    ) -> None:
        """Record a mistake during the session."""
        if session_id not in self._active_sessions:
            return

        self._active_sessions[session_id]["mistakes"].append({
            "description": mistake,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def end_session(
        self,
        session_id: str,
        outcome: str,
        summary: str,
        reward_signal: float = 0.0,
    ) -> Dict[str, Any]:
        """End a learning session and persist to memory."""
        if session_id not in self._active_sessions:
            return {"error": "Session not found"}

        session = self._active_sessions[session_id]
        session["ended_at"] = datetime.now(timezone.utc).isoformat()
        session["outcome"] = outcome
        session["summary"] = summary
        session["reward_signal"] = reward_signal

        # Calculate emotional valence from outcome
        valence_map = {
            "success": 0.8,
            "partial_success": 0.3,
            "failure": -0.7,
            "blocked": -0.3,
            "corrected": 0.2,
        }
        emotional_valence = valence_map.get(outcome, 0.0)

        # Store as episode
        episode_id = self.memory.store_episode(
            agent_id=session["agent_id"],
            episode_type=session["task_type"],
            content={
                "task": session["task"],
                "events": session["events"],
                "learnings": session["learnings"],
                "mistakes": session["mistakes"],
            },
            outcome=outcome,
            emotional_valence=emotional_valence,
            importance=abs(emotional_valence) + len(session["learnings"]) * 0.1,
            tags=[session["task_type"], outcome],
        )

        # Clean up
        del self._active_sessions[session_id]

        return {
            "session_id": session_id,
            "episode_id": episode_id,
            "outcome": outcome,
            "learnings_recorded": len(session["learnings"]),
            "mistakes_recorded": len(session["mistakes"]),
        }

    def get_session_handoff(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """Get session data for handoff to another agent."""
        if session_id not in self._active_sessions:
            return {"error": "Session not found"}

        session = self._active_sessions[session_id]

        return {
            "session_id": session_id,
            "task": session["task"],
            "task_type": session["task_type"],
            "started_at": session["started_at"],
            "events_count": len(session["events"]),
            "learnings": session["learnings"],
            "mistakes": session["mistakes"],
            "context": session["context"],
        }

    def get_active_sessions(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get active sessions for an agent."""
        return [
            {
                "session_id": sid,
                "task": s["task"],
                "task_type": s["task_type"],
                "started_at": s["started_at"],
            }
            for sid, s in self._active_sessions.items()
            if s["agent_id"] == agent_id
        ]
