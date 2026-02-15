"""
Team Store - Team knowledge and expertise
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class TeamStore(BaseStore):
    """
    Manages team knowledge memory.

    Tracks:
    - Team members and roles
    - Expertise areas
    - Knowledge artifacts
    - Who to contact for what
    """

    def add_member(
        self,
        name: str,
        role: str,
        active: bool = True,
        timezone: Optional[str] = None
    ) -> str:
        """Add a team member"""
        member_id = self._make_id("tm", name)

        self.graph.add_node(
            "team_member",
            member_id,
            name=name,
            role=role,
            active=str(active),
            timezone=timezone or "",
        )

        return member_id

    def add_expertise(
        self,
        domain: str,
        depth: str,
        modules: Optional[List[str]] = None
    ) -> str:
        """Add an expertise area"""
        exp_id = self._make_id("ea", domain)

        self.graph.add_node(
            "expertise_area",
            exp_id,
            domain=domain,
            depth=depth,
            modules=",".join(modules or []),
        )

        return exp_id

    def link_expertise(
        self,
        member_name: str,
        domain: str,
        confidence: float = 0.8
    ) -> None:
        """Link a member to an expertise area"""
        member_id = self._make_id("tm", member_name)
        exp_id = self._make_id("ea", domain)

        if self.graph.has_node("team_member", member_id) and self.graph.has_node("expertise_area", exp_id):
            self.graph.add_edge(
                "HAS_EXPERTISE",
                ("team_member", member_id),
                ("expertise_area", exp_id),
                confidence=str(confidence),
                last_demonstrated=self._now()
            )

    def add_knowledge_artifact(
        self,
        artifact_type: str,
        location: str,
        author: str,
        freshness: str = "current"
    ) -> str:
        """Add a knowledge artifact (doc, PR, comment)"""
        art_id = self._make_id("ka", location[:30])
        author_id = self._make_id("tm", author)

        self.graph.add_node(
            "knowledge_artifact",
            art_id,
            artifact_type=artifact_type,
            location=location,
            author=author,
            freshness=freshness,
        )

        if self.graph.has_node("team_member", author_id):
            self.graph.add_edge(
                "AUTHORED",
                ("team_member", author_id),
                ("knowledge_artifact", art_id)
            )

        return art_id

    def link_authored_decision(
        self,
        member_name: str,
        decision_title: str,
        context: str
    ) -> None:
        """Link member to a decision they authored"""
        member_id = self._make_id("tm", member_name)
        dec_id = self._make_id("dec", decision_title)

        if self.graph.has_node("team_member", member_id) and self.graph.has_node("decision", dec_id):
            self.graph.add_edge(
                "AUTHORED_DECISION",
                ("team_member", member_id),
                ("decision", dec_id),
                context=self._sanitize(context)
            )

    def set_contact_for(
        self,
        domain: str,
        member_name: str,
        response_time: str = "days",
        best_channel: str = "email"
    ) -> None:
        """Set who to contact for an expertise area"""
        exp_id = self._make_id("ea", domain)
        member_id = self._make_id("tm", member_name)

        if self.graph.has_node("expertise_area", exp_id) and self.graph.has_node("team_member", member_id):
            self.graph.add_edge(
                "CONTACT_FOR",
                ("expertise_area", exp_id),
                ("team_member", member_id),
                response_time=response_time,
                best_channel=best_channel
            )

    def find_expert(self, topic: str) -> Optional[Dict[str, Any]]:
        """Find the best expert for a topic"""
        topic_lower = topic.lower()
        best_match = None
        best_depth = 0
        depth_order = {"shallow": 1, "medium": 2, "deep": 3, "expert": 4}

        for node in self.graph.nodes():
            if node.type == "expertise_area":
                domain = node.properties.get("domain", "").lower()
                if topic_lower in domain or domain in topic_lower:
                    depth = depth_order.get(node.properties.get("depth", "shallow"), 0)
                    if depth > best_depth:
                        best_depth = depth
                        # Find member with this expertise
                        for edge in self.graph.edges():
                            if edge.rel_type == "HAS_EXPERTISE" and edge.target == ("expertise_area", node.id):
                                member = self.graph.get_node(*edge.source)
                                if member and member.properties.get("active") == "True":
                                    best_match = {
                                        "member": member.properties,
                                        "expertise": node.properties,
                                    }
                                    # Get contact info
                                    for e2 in self.graph.edges():
                                        if e2.rel_type == "CONTACT_FOR" and e2.source == ("expertise_area", node.id):
                                            best_match["contact"] = e2.properties
                                            break
                                break

        return best_match

    def get_knowledge_for_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Get knowledge artifacts for a topic"""
        results = []
        topic_lower = topic.lower()

        for node in self.graph.nodes():
            if node.type == "knowledge_artifact":
                location = node.properties.get("location", "").lower()
                if topic_lower in location:
                    results.append(node.properties)

        return results

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant team knowledge for context"""
        results = []

        task = context.get("task", "")
        if task:
            # Find expert for task topic
            expert = self.find_expert(task)
            if expert:
                results.append({
                    "type": "expert",
                    "topic": task,
                    **expert
                })

            # Find knowledge artifacts
            artifacts = self.get_knowledge_for_topic(task)
            for a in artifacts:
                results.append({
                    "type": "knowledge_artifact",
                    **a
                })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get team store statistics"""
        members = 0
        active = 0
        expertise_areas = 0
        artifacts = 0

        for node in self.graph.nodes():
            if node.type == "team_member":
                members += 1
                if node.properties.get("active") == "True":
                    active += 1
            elif node.type == "expertise_area":
                expertise_areas += 1
            elif node.type == "knowledge_artifact":
                artifacts += 1

        return {
            "members": members,
            "active": active,
            "expertise_areas": expertise_areas,
            "knowledge_artifacts": artifacts,
        }
