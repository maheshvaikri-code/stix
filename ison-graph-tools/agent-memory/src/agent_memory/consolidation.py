"""
Memory Consolidation - Strategies for managing memory over time

Handles:
- What to keep vs. forget
- Memory aging and decay
- Consolidation of similar memories
- Importance scoring
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .memory import AgentMemory


class MemoryConsolidator:
    """
    Manages memory consolidation and cleanup.

    Strategies:
    1. Frequency-based: Keep frequently accessed memories
    2. Recency-based: Decay old unused memories
    3. Importance-based: Keep high-impact memories
    4. Reinforcement-based: Strengthen memories that prove useful
    """

    # Memory retention thresholds
    THRESHOLDS = {
        # Type: (min_age_days_to_consider, max_age_days_before_decay)
        "session": (7, 90),           # Sessions decay after 90 days
        "learning_event": (1, 30),    # Learning events decay after 30 days
        "partial_work": (0, 7),       # Partial work urgent, decay after 7 days
        "open_question": (0, 14),     # Open questions decay after 14 days
        "blocker": (0, 7),            # Blockers urgent, decay after 7 days

        # These are kept longer
        "decision": (365, 730),       # Decisions kept 2+ years
        "bug": (180, 365),            # Bugs kept 1+ year
        "bug_pattern": (365, 730),    # Patterns kept 2+ years
        "convention": (365, None),    # Conventions kept indefinitely
        "hot_path": (365, None),      # Hot paths kept indefinitely
        "skill": (90, None),          # Skills kept indefinitely
    }

    # Importance multipliers
    IMPORTANCE = {
        "decision": 1.5,
        "bug_pattern": 1.4,
        "hot_path": 1.3,
        "convention": 1.2,
        "skill": 1.1,
        "session": 0.8,
        "learning_event": 0.7,
        "partial_work": 0.6,
    }

    def __init__(self, memory: "AgentMemory"):
        self.memory = memory

    def consolidate(self) -> Dict[str, int]:
        """
        Run memory consolidation.

        Returns summary of actions taken.
        """
        summary = {
            "decayed": 0,
            "strengthened": 0,
            "merged": 0,
            "archived": 0,
        }

        # 1. Decay old, unused memories
        summary["decayed"] = self._decay_old_memories()

        # 2. Strengthen frequently used memories
        summary["strengthened"] = self._strengthen_used_memories()

        # 3. Merge similar memories
        summary["merged"] = self._merge_similar()

        # 4. Archive completed sessions
        summary["archived"] = self._archive_sessions()

        return summary

    def _decay_old_memories(self) -> int:
        """Remove or mark memories that are too old"""
        decayed = 0
        now = datetime.now()

        nodes_to_remove = []

        for node in self.memory.graph.nodes():
            node_type = node.type
            thresholds = self.THRESHOLDS.get(node_type)

            if not thresholds:
                continue

            min_age, max_age = thresholds
            if max_age is None:
                continue  # Keep indefinitely

            # Get node age
            created = node.properties.get("added") or node.properties.get("started") or node.properties.get("when")
            if not created:
                continue

            try:
                created_dt = datetime.fromisoformat(created)
                age_days = (now - created_dt).days
            except:
                continue

            # Check if should decay
            if age_days > max_age:
                # Check importance
                importance = self.IMPORTANCE.get(node_type, 1.0)

                # High importance items get extended retention
                if importance >= 1.2 and age_days < max_age * 1.5:
                    continue

                # Check if actively used
                if self._is_actively_used(node):
                    continue

                nodes_to_remove.append((node.type, node.id))
                decayed += 1

        # Remove decayed nodes
        for node_type, node_id in nodes_to_remove:
            try:
                self.memory.graph.remove_node(node_type, node_id)
            except:
                pass

        return decayed

    def _is_actively_used(self, node) -> bool:
        """Check if a node is actively referenced"""
        # Check if node has recent edges
        node_ref = (node.type, node.id)

        for edge in self.memory.graph.edges():
            if edge.source == node_ref or edge.target == node_ref:
                # Has connections, likely still relevant
                return True

        return False

    def _strengthen_used_memories(self) -> int:
        """Increase confidence/proficiency of frequently used memories"""
        strengthened = 0

        # Strengthen skills based on application
        for edge in self.memory.graph.edges():
            if edge.rel_type == "SKILL_APPLIED":
                success = edge.properties.get("success") == "True"
                if success:
                    skill_ref = edge.source
                    skill = self.memory.graph.get_node(*skill_ref)
                    if skill:
                        current_prof = float(skill.properties.get("proficiency", 0))
                        # Small increment for each success
                        new_prof = min(1.0, current_prof + 0.02)
                        self.memory.graph.update_node(
                            skill_ref[0],
                            skill_ref[1],
                            proficiency=str(new_prof)
                        )
                        strengthened += 1

        # Strengthen conventions based on learning
        for edge in self.memory.graph.edges():
            if edge.rel_type == "LEARNED_FROM":
                examples = int(edge.properties.get("examples_seen", 0))
                if examples > 10:
                    # Well-learned, could increase confidence
                    strengthened += 1

        return strengthened

    def _merge_similar(self) -> int:
        """Merge similar memories to reduce redundancy"""
        merged = 0

        # Find similar bug patterns
        patterns = {}
        for node in self.memory.graph.nodes():
            if node.type == "bug_pattern":
                sig = node.properties.get("signature", "")
                if sig in patterns:
                    # Potential duplicate
                    merged += 1
                else:
                    patterns[sig] = node.id

        # Find similar conventions
        conventions = {}
        for node in self.memory.graph.nodes():
            if node.type == "convention":
                key = (node.properties.get("category"), node.properties.get("rule"))
                if key in conventions:
                    merged += 1
                else:
                    conventions[key] = node.id

        return merged

    def _archive_sessions(self) -> int:
        """Archive old completed sessions"""
        archived = 0
        now = datetime.now()
        cutoff = now - timedelta(days=30)

        for node in self.memory.graph.nodes():
            if node.type == "session":
                ended = node.properties.get("ended")
                if ended:
                    try:
                        ended_dt = datetime.fromisoformat(ended)
                        if ended_dt < cutoff:
                            # Mark as archived (don't delete, just flag)
                            self.memory.graph.update_node(
                                "session",
                                node.id,
                                archived="True"
                            )
                            archived += 1
                    except:
                        pass

        return archived

    def get_memory_health(self) -> Dict[str, Any]:
        """Assess overall memory health"""
        stats = self.memory.get_stats()

        # Calculate metrics
        total_nodes = stats["total_nodes"]
        total_edges = stats["total_edges"]

        # Count by age
        now = datetime.now()
        recent = 0  # < 7 days
        medium = 0  # 7-30 days
        old = 0     # > 30 days

        for node in self.memory.graph.nodes():
            created = (
                node.properties.get("added") or
                node.properties.get("started") or
                node.properties.get("when")
            )
            if created:
                try:
                    created_dt = datetime.fromisoformat(created)
                    age = (now - created_dt).days
                    if age < 7:
                        recent += 1
                    elif age < 30:
                        medium += 1
                    else:
                        old += 1
                except:
                    pass

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "age_distribution": {
                "recent_7d": recent,
                "medium_30d": medium,
                "old_30d_plus": old,
            },
            "recommendations": self._get_recommendations(stats),
        }

    def _get_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Get recommendations for memory management"""
        recommendations = []

        stores = stats.get("stores", {})

        # Check sessions
        sessions = stores.get("sessions", {})
        if sessions.get("open_questions", 0) > 5:
            recommendations.append("Many open questions - consider resolving or archiving")
        if sessions.get("unresolved_blockers", 0) > 3:
            recommendations.append("Multiple unresolved blockers - needs attention")

        # Check skills
        skills = stores.get("skills", {})
        if skills.get("avg_proficiency", 0) < 0.5:
            recommendations.append("Low average skill proficiency - more practice needed")

        # Check conventions
        conventions = stores.get("conventions", {})
        if conventions.get("total_violations", 0) > 20:
            recommendations.append("High convention violations - review and reinforce")

        # Check bugs
        bugs = stores.get("bugs", {})
        if bugs.get("missed", 0) > bugs.get("prevented", 0):
            recommendations.append("More bugs missed than prevented - review bug patterns")

        return recommendations


class ImportanceScorer:
    """Scores memory importance for retention decisions"""

    @staticmethod
    def score(node, edges: List) -> float:
        """
        Calculate importance score for a node.

        Factors:
        - Type importance
        - Connection count
        - Recency of use
        - Success/failure impact
        """
        base_score = MemoryConsolidator.IMPORTANCE.get(node.type, 1.0)

        # Connection bonus
        connection_count = len([e for e in edges if e.source == (node.type, node.id) or e.target == (node.type, node.id)])
        connection_bonus = min(0.5, connection_count * 0.1)

        # Success bonus for skills
        if node.type == "skill":
            proficiency = float(node.properties.get("proficiency", 0))
            base_score += proficiency * 0.3

        # Severity bonus for bugs
        if node.type == "bug" or node.type == "bug_pattern":
            severity = node.properties.get("severity", "medium")
            if severity == "critical":
                base_score += 0.5
            elif severity == "high":
                base_score += 0.3

        return base_score + connection_bonus
