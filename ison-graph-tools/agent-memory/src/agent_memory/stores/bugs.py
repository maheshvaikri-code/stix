"""
Bug Pattern Store - Historical bugs and fix patterns
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class BugPatternStore(BaseStore):
    """
    Manages bug pattern memory.

    Tracks:
    - Historical bugs and their fixes
    - Recurring bug patterns
    - Agent's awareness and prevention
    """

    def add_bug(
        self,
        title: str,
        severity: str = "medium",
        module: Optional[str] = None,
        fix_commit: Optional[str] = None,
        root_cause: Optional[str] = None,
    ) -> str:
        """Record a historical bug"""
        bug_id = self._make_id("bug", title[:30])

        self.graph.add_node(
            "bug",
            bug_id,
            title=title,
            severity=severity,
            module=module or "",
            introduced=self._now(),
            fixed=self._now(),
            fix_commit=fix_commit or "",
            root_cause=self._sanitize(root_cause or ""),
        )

        return bug_id

    def add_pattern(
        self,
        name: str,
        signature: str,
        modules_affected: Optional[List[str]] = None
    ) -> str:
        """Add a recurring bug pattern"""
        pattern_id = self._make_id("bp", name)

        self.graph.add_node(
            "bug_pattern",
            pattern_id,
            name=name,
            signature=self._sanitize(signature),
            modules_affected=",".join(modules_affected or []),
        )

        return pattern_id

    def add_fix_pattern(
        self,
        bug_pattern_name: str,
        fix_template: str,
        caveats: Optional[str] = None
    ) -> str:
        """Add a fix pattern for a bug type"""
        pattern_id = self._make_id("bp", bug_pattern_name)
        fix_id = self._make_id("fix", bug_pattern_name)

        self.graph.add_node(
            "fix_pattern",
            fix_id,
            bug_pattern_id=pattern_id,
            fix_template=self._sanitize(fix_template),
            caveats=self._sanitize(caveats or ""),
        )

        if self.graph.has_node("bug_pattern", pattern_id):
            self.graph.add_edge(
                "FIX_FOR",
                ("fix_pattern", fix_id),
                ("bug_pattern", pattern_id)
            )

        return fix_id

    def link_bug_to_pattern(self, bug_title: str, pattern_name: str) -> None:
        """Link a specific bug to a pattern"""
        bug_id = self._make_id("bug", bug_title[:30])
        pattern_id = self._make_id("bp", pattern_name)

        if self.graph.has_node("bug", bug_id) and self.graph.has_node("bug_pattern", pattern_id):
            self.graph.add_edge(
                "INSTANCE_OF",
                ("bug", bug_id),
                ("bug_pattern", pattern_id)
            )

    def mark_similar_code(
        self,
        pattern_name: str,
        location: str,
        risk: str = "medium"
    ) -> None:
        """Mark that similar risky code exists"""
        pattern_id = self._make_id("bp", pattern_name)

        if self.graph.has_node("bug_pattern", pattern_id):
            self.graph.add_edge(
                "SIMILAR_CODE_EXISTS",
                ("bug_pattern", pattern_id),
                ("location", location),
                location=location,
                risk=risk,
                identified=self._now()
            )

    def record_prevention(
        self,
        pattern_name: str,
        code_location: str
    ) -> None:
        """Record when agent prevented a bug"""
        pattern_id = self._make_id("bp", pattern_name)

        if self.graph.has_node("bug_pattern", pattern_id):
            self.graph.add_edge(
                "PREVENTED_BY_AGENT",
                ("agent", "self"),
                ("bug_pattern", pattern_id),
                when=self._now(),
                code_location=code_location
            )

    def record_miss(
        self,
        pattern_name: str,
        consequence: str,
        post_mortem: str
    ) -> None:
        """Record when agent missed a bug"""
        pattern_id = self._make_id("bp", pattern_name)

        if self.graph.has_node("bug_pattern", pattern_id):
            self.graph.add_edge(
                "MISSED_BY_AGENT",
                ("agent", "self"),
                ("bug_pattern", pattern_id),
                when=self._now(),
                consequence=self._sanitize(consequence),
                post_mortem=self._sanitize(post_mortem)
            )

    def get_risks_for_module(self, module_path: str) -> List[Dict[str, Any]]:
        """Get bug patterns that might affect a module"""
        risks = []

        for node in self.graph.nodes():
            if node.type == "bug_pattern":
                modules = node.properties.get("modules_affected", "").split(",")
                if any(module_path in m or m in module_path for m in modules if m):
                    # Get fix pattern
                    fix = None
                    for edge in self.graph.edges():
                        if edge.rel_type == "FIX_FOR" and edge.target == ("bug_pattern", node.id):
                            fix_node = self.graph.get_node(*edge.source)
                            if fix_node:
                                fix = fix_node.properties
                            break

                    risks.append({
                        "pattern": node.properties,
                        "fix": fix,
                    })

        return risks

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant bug patterns for context"""
        results = []

        files = context.get("files", [])
        for file_path in files:
            # Find matching patterns
            for node in self.graph.nodes():
                if node.type == "bug_pattern":
                    modules = node.properties.get("modules_affected", "").split(",")
                    if any(file_path in m or m in file_path for m in modules if m):
                        results.append({
                            "type": "bug_risk",
                            "file": file_path,
                            "pattern": node.properties
                        })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get bug pattern store statistics"""
        bugs = 0
        patterns = 0
        fixes = 0
        prevented = 0
        missed = 0

        for node in self.graph.nodes():
            if node.type == "bug":
                bugs += 1
            elif node.type == "bug_pattern":
                patterns += 1
            elif node.type == "fix_pattern":
                fixes += 1

        for edge in self.graph.edges():
            if edge.rel_type == "PREVENTED_BY_AGENT":
                prevented += 1
            elif edge.rel_type == "MISSED_BY_AGENT":
                missed += 1

        return {
            "bugs": bugs,
            "patterns": patterns,
            "fixes": fixes,
            "prevented": prevented,
            "missed": missed,
        }
