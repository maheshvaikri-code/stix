"""
Template Store - Code generation templates and snippets
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class TemplateStore(BaseStore):
    """
    Manages code template memory.

    Tracks:
    - Code generation templates
    - Reusable snippets
    - Template usage and evolution
    """

    def add_template(
        self,
        name: str,
        category: str,
        components: Optional[List[str]] = None
    ) -> str:
        """Add a code template"""
        tmpl_id = self._make_id("tmpl", name)

        self.graph.add_node(
            "template",
            tmpl_id,
            name=name,
            category=category,
            components=",".join(components or []),
            usage_count="0",
            last_used="",
        )

        return tmpl_id

    def add_template_component(
        self,
        template_name: str,
        component_name: str,
        required: bool = True,
        customizable: Optional[List[str]] = None
    ) -> str:
        """Add a component to a template"""
        tmpl_id = self._make_id("tmpl", template_name)
        comp_id = self._make_id("tc", f"{template_name}_{component_name}")

        self.graph.add_node(
            "template_component",
            comp_id,
            template_id=tmpl_id,
            component_name=component_name,
            required=str(required),
            customizable=",".join(customizable or []),
        )

        if self.graph.has_node("template", tmpl_id):
            self.graph.add_edge(
                "HAS_COMPONENT",
                ("template", tmpl_id),
                ("template_component", comp_id)
            )

        return comp_id

    def add_snippet(
        self,
        name: str,
        code: str,
        usage_context: str
    ) -> str:
        """Add a reusable code snippet"""
        snip_id = self._make_id("snip", name)

        self.graph.add_node(
            "snippet",
            snip_id,
            name=name,
            code=self._sanitize(code),
            usage_context=self._sanitize(usage_context),
        )

        return snip_id

    def link_snippet_to_template(
        self,
        template_name: str,
        snippet_name: str,
        in_component: str,
        adaptation_needed: str = ""
    ) -> None:
        """Link a snippet to a template"""
        tmpl_id = self._make_id("tmpl", template_name)
        snip_id = self._make_id("snip", snippet_name)

        if self.graph.has_node("template", tmpl_id) and self.graph.has_node("snippet", snip_id):
            self.graph.add_edge(
                "USES_SNIPPET",
                ("template", tmpl_id),
                ("snippet", snip_id),
                in_component=in_component,
                adaptation_needed=adaptation_needed
            )

    def record_template_use(self, template_name: str) -> None:
        """Record template usage"""
        tmpl_id = self._make_id("tmpl", template_name)

        if self.graph.has_node("template", tmpl_id):
            node = self.graph.get_node("template", tmpl_id)
            if node:
                count = int(node.properties.get("usage_count", 0)) + 1
                self.graph.update_node(
                    "template",
                    tmpl_id,
                    usage_count=str(count),
                    last_used=self._now()
                )

    def record_learning(
        self,
        template_name: str,
        confidence: float,
        successful_uses: int = 0,
        deviations_corrected: int = 0
    ) -> None:
        """Record agent learning a template"""
        tmpl_id = self._make_id("tmpl", template_name)

        if self.graph.has_node("template", tmpl_id):
            self.graph.add_edge(
                "AGENT_LEARNED",
                ("agent", "self"),
                ("template", tmpl_id),
                confidence=str(confidence),
                successful_uses=str(successful_uses),
                deviations_corrected=str(deviations_corrected)
            )

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template with its components and snippets"""
        tmpl_id = self._make_id("tmpl", name)

        if not self.graph.has_node("template", tmpl_id):
            return None

        node = self.graph.get_node("template", tmpl_id)
        if not node:
            return None

        result = {
            "template": node.properties,
            "components": [],
            "snippets": [],
        }

        # Get components
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_COMPONENT" and edge.source == ("template", tmpl_id):
                comp = self.graph.get_node(*edge.target)
                if comp:
                    result["components"].append(comp.properties)

        # Get snippets
        for edge in self.graph.edges():
            if edge.rel_type == "USES_SNIPPET" and edge.source == ("template", tmpl_id):
                snip = self.graph.get_node(*edge.target)
                if snip:
                    result["snippets"].append({
                        **snip.properties,
                        "in_component": edge.properties.get("in_component", ""),
                        "adaptation": edge.properties.get("adaptation_needed", ""),
                    })

        return result

    def get_template_for_task(self, task: str) -> Optional[Dict[str, Any]]:
        """Find the best template for a task"""
        task_lower = task.lower()

        # Category keywords
        category_keywords = {
            "model": ["model", "node", "entity", "class"],
            "handler": ["endpoint", "api", "handler", "route"],
            "algorithm": ["algorithm", "traverse", "search", "sort"],
            "migration": ["migration", "schema", "database"],
            "test": ["test", "spec"],
        }

        # Find matching category
        matched_category = None
        for category, keywords in category_keywords.items():
            if any(kw in task_lower for kw in keywords):
                matched_category = category
                break

        if not matched_category:
            return None

        # Find template of that category
        for node in self.graph.nodes():
            if node.type == "template":
                if node.properties.get("category") == matched_category:
                    return self.get_template(node.properties.get("name", ""))

        return None

    def get_snippets(self) -> List[Dict[str, Any]]:
        """Get all snippets"""
        return [
            {"id": node.id, **node.properties}
            for node in self.graph.nodes()
            if node.type == "snippet"
        ]

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant templates for context"""
        results = []

        task = context.get("task", "")
        if task:
            template = self.get_template_for_task(task)
            if template:
                results.append({
                    "type": "template",
                    **template
                })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get template store statistics"""
        templates = 0
        components = 0
        snippets = 0
        total_uses = 0

        for node in self.graph.nodes():
            if node.type == "template":
                templates += 1
                total_uses += int(node.properties.get("usage_count", 0))
            elif node.type == "template_component":
                components += 1
            elif node.type == "snippet":
                snippets += 1

        return {
            "templates": templates,
            "components": components,
            "snippets": snippets,
            "total_uses": total_uses,
        }
