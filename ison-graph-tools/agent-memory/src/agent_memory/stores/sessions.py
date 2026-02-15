"""
Session Store - Session continuity and handoff
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class SessionStore(BaseStore):
    """
    Manages session continuity memory.

    Tracks:
    - Session history
    - Partial work
    - Decisions made during sessions
    - Open questions
    - Blockers
    """

    _session_counter = 0

    def start_session(self, task: str) -> str:
        """Start a new session"""
        SessionStore._session_counter += 1
        timestamp = self._now().replace(':', '').replace('-', '').replace('.', '').replace('T', '')[:14]
        session_id = f"s_{timestamp}_{SessionStore._session_counter}"

        self.graph.add_node(
            "session",
            session_id,
            started=self._now(),
            ended="",
            task=self._sanitize(task),
            completion="0.0",
        )

        # Ensure agent node exists
        if not self.graph.has_node("agent", "self"):
            self.graph.add_node("agent", "self", name="agent")

        return session_id

    def end_session(self, session_id: str, completion: float) -> None:
        """End a session"""
        if self.graph.has_node("session", session_id):
            self.graph.update_node(
                "session",
                session_id,
                ended=self._now(),
                completion=str(completion)
            )

    def continue_session(self, new_session_id: str, previous_session_id: str) -> None:
        """Mark that a session continues a previous one"""
        if (self.graph.has_node("session", new_session_id) and
            self.graph.has_node("session", previous_session_id)):
            self.graph.add_edge(
                "CONTINUES",
                ("session", new_session_id),
                ("session", previous_session_id),
                context_preserved="0.8"
            )

    def add_partial_work(
        self,
        session_id: str,
        work_type: str,
        location: str,
        state: str
    ) -> str:
        """Record partial/incomplete work"""
        pw_id = self._make_id("pw", location[:30])

        self.graph.add_node(
            "partial_work",
            pw_id,
            session_id=session_id,
            work_type=work_type,
            location=location,
            state=self._sanitize(state),
        )

        if self.graph.has_node("session", session_id):
            self.graph.add_edge(
                "HAS_PARTIAL_WORK",
                ("session", session_id),
                ("partial_work", pw_id)
            )

        return pw_id

    def add_decision(
        self,
        session_id: str,
        decision: str,
        rationale: str,
        sticky: bool = True
    ) -> str:
        """Record a decision made during session"""
        dec_id = self._make_id("sd", decision[:30])

        self.graph.add_node(
            "session_decision",
            dec_id,
            session_id=session_id,
            decision=self._sanitize(decision),
            rationale=self._sanitize(rationale),
            sticky=str(sticky),
        )

        if self.graph.has_node("session", session_id):
            self.graph.add_edge(
                "DECIDED_IN",
                ("session_decision", dec_id),
                ("session", session_id)
            )

        return dec_id

    def add_open_question(
        self,
        session_id: str,
        question: str
    ) -> str:
        """Record an open question"""
        q_id = self._make_id("oq", question[:30])

        self.graph.add_node(
            "open_question",
            q_id,
            session_id=session_id,
            question=self._sanitize(question),
            answered_in="",
            answer="",
        )

        if self.graph.has_node("session", session_id):
            self.graph.add_edge(
                "QUESTION_FROM",
                ("open_question", q_id),
                ("session", session_id)
            )

        return q_id

    def answer_question(
        self,
        question_text: str,
        answer: str,
        answered_in_session: str
    ) -> None:
        """Mark a question as answered"""
        q_id = self._make_id("oq", question_text[:30])

        if self.graph.has_node("open_question", q_id):
            self.graph.update_node(
                "open_question",
                q_id,
                answered_in=answered_in_session,
                answer=self._sanitize(answer)
            )

    def add_blocker(
        self,
        session_id: str,
        description: str
    ) -> str:
        """Record a blocker"""
        bl_id = self._make_id("bl", description[:30])

        self.graph.add_node(
            "blocker",
            bl_id,
            session_id=session_id,
            description=self._sanitize(description),
            resolved_in="",
            resolution="",
        )

        return bl_id

    def resolve_blocker(
        self,
        description: str,
        resolved_in_session: str,
        resolution: str
    ) -> None:
        """Mark a blocker as resolved"""
        bl_id = self._make_id("bl", description[:30])

        if self.graph.has_node("blocker", bl_id):
            self.graph.update_node(
                "blocker",
                bl_id,
                resolved_in=resolved_in_session,
                resolution=self._sanitize(resolution)
            )

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get full context for a session"""
        context = {
            "session": None,
            "previous_sessions": [],
            "decisions": [],
            "partial_work": [],
            "open_questions": [],
            "blockers": [],
        }

        if not self.graph.has_node("session", session_id):
            return context

        # Get session
        session = self.graph.get_node("session", session_id)
        if session:
            context["session"] = session.properties

        # Get previous sessions (follow CONTINUES chain)
        visited = set()
        current_id = session_id
        while True:
            found_prev = False
            for edge in self.graph.edges():
                if edge.rel_type == "CONTINUES" and edge.source == ("session", current_id):
                    prev_id = edge.target[1]
                    if prev_id not in visited:
                        visited.add(prev_id)
                        prev = self.graph.get_node("session", prev_id)
                        if prev:
                            context["previous_sessions"].append(prev.properties)
                        current_id = prev_id
                        found_prev = True
                        break
            if not found_prev or len(visited) > 10:
                break

        # Get decisions (sticky ones carry forward)
        for node in self.graph.nodes():
            if node.type == "session_decision":
                if node.properties.get("sticky") == "True":
                    context["decisions"].append(node.properties)

        # Get partial work
        for node in self.graph.nodes():
            if node.type == "partial_work":
                context["partial_work"].append(node.properties)

        # Get open questions (unanswered)
        for node in self.graph.nodes():
            if node.type == "open_question":
                if not node.properties.get("answered_in"):
                    context["open_questions"].append(node.properties)

        # Get unresolved blockers
        for node in self.graph.nodes():
            if node.type == "blocker":
                if not node.properties.get("resolved_in"):
                    context["blockers"].append(node.properties)

        return context

    def get_last_session(self) -> Optional[str]:
        """Get the most recent session ID"""
        sessions = []
        for node in self.graph.nodes():
            if node.type == "session":
                sessions.append((node.id, node.properties.get("started", "")))

        if sessions:
            sessions.sort(key=lambda x: x[1], reverse=True)
            return sessions[0][0]

        return None

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant session info for context"""
        results = []

        # Get last session context
        last_session = self.get_last_session()
        if last_session:
            session_ctx = self.get_session_context(last_session)

            # Add open questions
            for q in session_ctx.get("open_questions", []):
                results.append({
                    "type": "open_question",
                    **q
                })

            # Add unresolved blockers
            for b in session_ctx.get("blockers", []):
                results.append({
                    "type": "blocker",
                    **b
                })

            # Add partial work
            for pw in session_ctx.get("partial_work", []):
                results.append({
                    "type": "partial_work",
                    **pw
                })

            # Add sticky decisions
            for d in session_ctx.get("decisions", []):
                results.append({
                    "type": "session_decision",
                    **d
                })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get session store statistics"""
        sessions = 0
        partial_work = 0
        decisions = 0
        open_questions = 0
        blockers = 0

        for node in self.graph.nodes():
            if node.type == "session":
                sessions += 1
            elif node.type == "partial_work":
                partial_work += 1
            elif node.type == "session_decision":
                decisions += 1
            elif node.type == "open_question":
                if not node.properties.get("answered_in"):
                    open_questions += 1
            elif node.type == "blocker":
                if not node.properties.get("resolved_in"):
                    blockers += 1

        return {
            "sessions": sessions,
            "partial_work": partial_work,
            "decisions": decisions,
            "open_questions": open_questions,
            "unresolved_blockers": blockers,
        }
