"""
Python AST Parser - Extracts code elements from Python source files
"""

import ast
import os
from typing import List, Optional, Tuple

from ..graph_builder import (
    FileElement,
    ClassElement,
    FunctionElement,
    VariableElement,
    ModuleElement,
)


class PythonParser:
    """
    Parses Python source files and extracts code elements.

    Usage:
        parser = PythonParser()
        elements = parser.parse_file("path/to/file.py")
    """

    def __init__(self):
        self.current_file: Optional[str] = None
        self.current_class: Optional[str] = None

    def parse_file(self, file_path: str) -> Tuple[FileElement, List]:
        """Parse a Python file and return all code elements"""
        self.current_file = file_path
        self.current_class = None

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            # Return minimal file element for unparseable files
            file_elem = FileElement(
                name=os.path.basename(file_path),
                file_path=file_path,
                line_start=1,
                line_end=1,
                language="python",
                size_bytes=len(source.encode("utf-8")),
                imports=[],
            )
            return file_elem, []

        elements = []
        imports = []

        # First pass: collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Calculate line count
        lines = source.count("\n") + 1

        # Create file element
        file_elem = FileElement(
            name=os.path.basename(file_path),
            file_path=file_path,
            line_start=1,
            line_end=lines,
            language="python",
            size_bytes=len(source.encode("utf-8")),
            imports=imports,
        )

        # Parse top-level elements
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                elements.extend(self._parse_class(node, file_path))
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                elements.append(self._parse_function(node, file_path, None))
            elif isinstance(node, ast.Assign):
                elements.extend(self._parse_assignment(node, file_path, "module"))
            elif isinstance(node, ast.AnnAssign):
                elem = self._parse_annotated_assignment(node, file_path, "module")
                if elem:
                    elements.append(elem)

        return file_elem, elements

    def _parse_class(self, node: ast.ClassDef, file_path: str) -> List:
        """Parse a class definition"""
        elements = []

        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attribute_name(base))

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(self._get_attribute_name(dec))
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(self._get_attribute_name(dec.func))

        # Check if abstract
        is_abstract = "ABC" in bases or "ABCMeta" in bases or "abstractmethod" in decorators

        # Get docstring
        docstring = ast.get_docstring(node)

        class_elem = ClassElement(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            decorators=decorators,
            is_abstract=is_abstract,
            docstring=docstring,
        )
        elements.append(class_elem)

        # Parse class body
        self.current_class = node.name
        for child in node.body:
            if isinstance(child, ast.FunctionDef) or isinstance(child, ast.AsyncFunctionDef):
                elements.append(self._parse_function(child, file_path, node.name))
            elif isinstance(child, ast.Assign):
                elements.extend(self._parse_assignment(child, file_path, "class"))
            elif isinstance(child, ast.AnnAssign):
                elem = self._parse_annotated_assignment(child, file_path, "class")
                if elem:
                    elements.append(elem)
        self.current_class = None

        return elements

    def _parse_function(self, node, file_path: str, parent_class: Optional[str]) -> FunctionElement:
        """Parse a function/method definition"""
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Get parameters
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                param_name += f": {self._get_annotation_name(arg.annotation)}"
            parameters.append(param_name)

        # Get return type
        return_type = None
        if node.returns:
            return_type = self._get_annotation_name(node.returns)

        # Get decorators
        decorators = []
        is_static = False
        is_classmethod = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
                if dec.id == "staticmethod":
                    is_static = True
                elif dec.id == "classmethod":
                    is_classmethod = True
            elif isinstance(dec, ast.Attribute):
                decorators.append(self._get_attribute_name(dec))
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(self._get_attribute_name(dec.func))

        # Find function calls
        calls = self._find_calls(node)

        # Get docstring
        docstring = ast.get_docstring(node)

        return FunctionElement(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            is_async=is_async,
            is_method=parent_class is not None,
            is_static=is_static,
            is_classmethod=is_classmethod,
            parent_class=parent_class,
            calls=calls,
            docstring=docstring,
        )

    def _parse_assignment(self, node: ast.Assign, file_path: str, scope: str) -> List[VariableElement]:
        """Parse an assignment statement"""
        elements = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                is_constant = target.id.isupper()
                elements.append(VariableElement(
                    name=target.id,
                    file_path=file_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    var_type=None,
                    is_constant=is_constant,
                    scope=scope,
                ))
        return elements

    def _parse_annotated_assignment(self, node: ast.AnnAssign, file_path: str, scope: str) -> Optional[VariableElement]:
        """Parse an annotated assignment"""
        if isinstance(node.target, ast.Name):
            var_type = self._get_annotation_name(node.annotation)
            is_constant = node.target.id.isupper()
            return VariableElement(
                name=node.target.id,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                var_type=var_type,
                is_constant=is_constant,
                scope=scope,
            )
        return None

    def _find_calls(self, node) -> List[str]:
        """Find all function calls within a node"""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # For method calls like obj.method(), we record the method name
                    calls.append(child.func.attr)
        return list(set(calls))  # Remove duplicates

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name like 'module.submodule.name'"""
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _get_annotation_name(self, node) -> str:
        """Get string representation of a type annotation"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Subscript):
            base = self._get_annotation_name(node.value)
            if isinstance(node.slice, ast.Tuple):
                args = ", ".join(self._get_annotation_name(e) for e in node.slice.elts)
            else:
                args = self._get_annotation_name(node.slice)
            return f"{base}[{args}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union type like int | str
            left = self._get_annotation_name(node.left)
            right = self._get_annotation_name(node.right)
            return f"{left} | {right}"
        return "Any"

    def parse_directory(self, dir_path: str) -> Tuple[List[FileElement], List]:
        """Parse all Python files in a directory"""
        file_elements = []
        all_elements = []

        for root, dirs, files in os.walk(dir_path):
            # Skip hidden and virtual env directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "env", "__pycache__", "node_modules", ".git")]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        file_elem, elements = self.parse_file(file_path)
                        file_elements.append(file_elem)
                        all_elements.extend(elements)
                    except Exception:
                        continue  # Skip files that can't be parsed

        return file_elements, all_elements
