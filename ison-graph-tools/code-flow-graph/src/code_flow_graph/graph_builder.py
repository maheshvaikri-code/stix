"""
Graph Builder - Constructs ISONGraph from parsed code elements

Node Types:
    - file: Source files
    - module: Packages/modules
    - class: Classes/structs/interfaces
    - function: Functions/methods
    - variable: Global variables/constants

Edge Types:
    - IMPORTS: File/module imports another
    - CALLS: Function calls another function
    - DEFINES: File/class defines a function/class
    - CONTAINS: Module contains file/submodule
    - INHERITS: Class extends/implements another
    - USES: Function uses a variable/type
    - RETURNS: Function returns a type
    - DECORATES: Decorator applied to function/class
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from ison_graph import ISONGraph


@dataclass
class CodeElement:
    """Base class for code elements"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileElement(CodeElement):
    """Represents a source file"""
    language: str = "unknown"
    size_bytes: int = 0
    imports: List[str] = field(default_factory=list)


@dataclass
class ModuleElement(CodeElement):
    """Represents a module/package"""
    is_package: bool = False
    submodules: List[str] = field(default_factory=list)


@dataclass
class ClassElement(CodeElement):
    """Represents a class/struct/interface"""
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    is_abstract: bool = False
    docstring: Optional[str] = None


@dataclass
class FunctionElement(CodeElement):
    """Represents a function/method"""
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    parent_class: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class VariableElement(CodeElement):
    """Represents a variable/constant"""
    var_type: Optional[str] = None
    is_constant: bool = False
    scope: str = "module"  # module, class, function


class CodeFlowGraphBuilder:
    """
    Builds an ISONGraph from code elements.

    Usage:
        builder = CodeFlowGraphBuilder("my-project")
        builder.add_file(file_element)
        builder.add_function(func_element)
        builder.add_call("func_a", "func_b")
        graph = builder.build()
    """

    def __init__(self, name: str = "code-flow"):
        self.name = name
        self.graph = ISONGraph(name=name)

        # Track added elements to avoid duplicates
        self._files: Set[str] = set()
        self._modules: Set[str] = set()
        self._classes: Set[str] = set()
        self._functions: Set[str] = set()
        self._variables: Set[str] = set()

        # Deferred edges (resolved after all nodes added)
        self._deferred_edges: List[tuple] = []

    def _make_id(self, name: str) -> str:
        """Create a valid ID from a name"""
        return name.replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")

    def _sanitize_string(self, s: str) -> str:
        """Sanitize a string for safe storage (remove problematic characters)"""
        # Replace newlines with spaces, remove quotes that could break parsing
        return s.replace("\n", " ").replace("\r", " ").replace('"', "'").replace("\\", "/")

    def add_file(self, element: FileElement) -> None:
        """Add a file node"""
        file_id = self._make_id(element.file_path)
        if file_id in self._files:
            return

        self._files.add(file_id)
        self.graph.add_node(
            "file",
            file_id,
            name=element.name,
            path=element.file_path,
            language=element.language,
            size_bytes=str(element.size_bytes),
            line_start=str(element.line_start),
            line_end=str(element.line_end),
        )

        # Add import edges (deferred)
        for imp in element.imports:
            self._deferred_edges.append(("IMPORTS", ("file", file_id), ("file", self._make_id(imp))))

    def add_module(self, element: ModuleElement) -> None:
        """Add a module node"""
        mod_id = self._make_id(element.name)
        if mod_id in self._modules:
            return

        self._modules.add(mod_id)
        self.graph.add_node(
            "module",
            mod_id,
            name=element.name,
            path=element.file_path,
            is_package=str(element.is_package),
            line_start=str(element.line_start),
            line_end=str(element.line_end),
        )

        # Add contains edges for submodules
        for submod in element.submodules:
            self._deferred_edges.append(("CONTAINS", ("module", mod_id), ("module", self._make_id(submod))))

    def add_class(self, element: ClassElement, parent_file: Optional[str] = None) -> None:
        """Add a class node"""
        class_id = self._make_id(element.name)
        if class_id in self._classes:
            return

        self._classes.add(class_id)
        props = {
            "name": element.name,
            "path": element.file_path,
            "line_start": str(element.line_start),
            "line_end": str(element.line_end),
            "is_abstract": str(element.is_abstract),
        }
        if element.docstring:
            props["docstring"] = self._sanitize_string(element.docstring[:500])
        if element.decorators:
            props["decorators"] = ",".join(element.decorators)

        self.graph.add_node("class", class_id, **props)

        # Add inheritance edges
        for base in element.bases:
            self._deferred_edges.append(("INHERITS", ("class", class_id), ("class", self._make_id(base))))

        # Add defines edge from file
        if parent_file:
            self._deferred_edges.append(("DEFINES", ("file", self._make_id(parent_file)), ("class", class_id)))

        # Add decorator edges
        for dec in element.decorators:
            self._deferred_edges.append(("DECORATES", ("function", self._make_id(dec)), ("class", class_id)))

    def add_function(self, element: FunctionElement, parent_file: Optional[str] = None) -> None:
        """Add a function node"""
        # Create unique ID for methods
        if element.parent_class:
            func_id = self._make_id(f"{element.parent_class}.{element.name}")
        else:
            func_id = self._make_id(element.name)

        if func_id in self._functions:
            return

        self._functions.add(func_id)
        props = {
            "name": element.name,
            "path": element.file_path,
            "line_start": str(element.line_start),
            "line_end": str(element.line_end),
            "is_async": str(element.is_async),
            "is_method": str(element.is_method),
            "is_static": str(element.is_static),
            "is_classmethod": str(element.is_classmethod),
        }
        if element.parameters:
            props["parameters"] = ",".join(element.parameters)
        if element.return_type:
            props["return_type"] = element.return_type
        if element.docstring:
            props["docstring"] = self._sanitize_string(element.docstring[:500])
        if element.decorators:
            props["decorators"] = ",".join(element.decorators)
        if element.parent_class:
            props["parent_class"] = element.parent_class

        self.graph.add_node("function", func_id, **props)

        # Add call edges
        for call in element.calls:
            self._deferred_edges.append(("CALLS", ("function", func_id), ("function", self._make_id(call))))

        # Add defines edge
        if element.parent_class:
            self._deferred_edges.append(("DEFINES", ("class", self._make_id(element.parent_class)), ("function", func_id)))
        elif parent_file:
            self._deferred_edges.append(("DEFINES", ("file", self._make_id(parent_file)), ("function", func_id)))

        # Add decorator edges
        for dec in element.decorators:
            self._deferred_edges.append(("DECORATES", ("function", self._make_id(dec)), ("function", func_id)))

        # Add returns edge
        if element.return_type:
            self._deferred_edges.append(("RETURNS", ("function", func_id), ("class", self._make_id(element.return_type))))

    def add_variable(self, element: VariableElement, parent: Optional[str] = None) -> None:
        """Add a variable node"""
        var_id = self._make_id(element.name)
        if var_id in self._variables:
            return

        self._variables.add(var_id)
        props = {
            "name": element.name,
            "path": element.file_path,
            "line_start": str(element.line_start),
            "line_end": str(element.line_end),
            "is_constant": str(element.is_constant),
            "scope": element.scope,
        }
        if element.var_type:
            props["var_type"] = element.var_type

        self.graph.add_node("variable", var_id, **props)

        # Add defines edge
        if parent:
            parent_type = "class" if parent in self._classes else "file"
            self._deferred_edges.append(("DEFINES", (parent_type, self._make_id(parent)), ("variable", var_id)))

    def add_call(self, caller: str, callee: str) -> None:
        """Add a call relationship"""
        self._deferred_edges.append(("CALLS", ("function", self._make_id(caller)), ("function", self._make_id(callee))))

    def add_import(self, importer: str, imported: str) -> None:
        """Add an import relationship"""
        self._deferred_edges.append(("IMPORTS", ("file", self._make_id(importer)), ("file", self._make_id(imported))))

    def add_inheritance(self, child: str, parent: str) -> None:
        """Add an inheritance relationship"""
        self._deferred_edges.append(("INHERITS", ("class", self._make_id(child)), ("class", self._make_id(parent))))

    def _resolve_edges(self) -> None:
        """Resolve deferred edges, only adding those where both nodes exist"""
        for rel_type, source, target in self._deferred_edges:
            source_type, source_id = source
            target_type, target_id = target

            # Check if both nodes exist
            if not self.graph.has_node(source_type, source_id):
                continue
            if not self.graph.has_node(target_type, target_id):
                continue

            # Check if edge already exists
            if self.graph.has_edge(rel_type, source, target):
                continue

            try:
                self.graph.add_edge(rel_type, source, target)
            except Exception:
                pass  # Skip invalid edges

    def build(self) -> ISONGraph:
        """Build and return the final graph"""
        self._resolve_edges()
        return self.graph

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the graph"""
        return {
            "files": len(self._files),
            "modules": len(self._modules),
            "classes": len(self._classes),
            "functions": len(self._functions),
            "variables": len(self._variables),
            "total_nodes": self.graph.node_count(),
            "total_edges": self.graph.edge_count(),
        }
