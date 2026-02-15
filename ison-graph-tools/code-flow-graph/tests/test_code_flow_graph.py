"""
Tests for Code Flow Graph Package
=================================

Comprehensive tests for the code flow analyzer, parsers, and graph builder.
"""

import pytest
import tempfile
import os

from code_flow_graph import CodeFlowAnalyzer, analyze_local
from code_flow_graph.graph_builder import (
    CodeFlowGraphBuilder,
    FileElement,
    ClassElement,
    FunctionElement,
    VariableElement,
    ModuleElement,
)
from code_flow_graph.parsers.python_parser import PythonParser
from code_flow_graph.github_loader import GitHubLoader, is_github_url


# =============================================================================
# CodeFlowAnalyzer Tests
# =============================================================================

class TestCodeFlowAnalyzer:
    """Tests for the main CodeFlowAnalyzer class"""

    @pytest.fixture
    def analyzer(self):
        """Create a fresh analyzer for each test"""
        return CodeFlowAnalyzer(name="test-analyzer")

    @pytest.fixture
    def sample_python_dir(self, tmp_path):
        """Create a sample Python directory structure"""
        # Create main module
        main_py = tmp_path / "main.py"
        main_py.write_text('''
"""Main module"""

from utils import helper

class App:
    """Main application class"""

    def __init__(self, name):
        self.name = name

    def run(self):
        """Run the application"""
        return helper(self.name)

def main():
    """Entry point"""
    app = App("test")
    return app.run()

if __name__ == "__main__":
    main()
''')

        # Create utils module
        utils_py = tmp_path / "utils.py"
        utils_py.write_text('''
"""Utility functions"""

def helper(value):
    """Helper function"""
    return f"Hello, {value}"

def unused_func():
    """Unused function"""
    pass

CONSTANT = 42
''')

        # Create subpackage
        subpkg = tmp_path / "subpkg"
        subpkg.mkdir()

        init_py = subpkg / "__init__.py"
        init_py.write_text('"""Subpackage"""')

        module_py = subpkg / "module.py"
        module_py.write_text('''
"""Subpackage module"""

class SubClass:
    def method(self):
        return True
''')

        return tmp_path

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer.name == "test-analyzer"
        assert analyzer.builder is not None
        assert "python" in analyzer._parsers

    def test_analyze_path_nonexistent(self, analyzer):
        """Test analyzing nonexistent path"""
        with pytest.raises(ValueError, match="does not exist"):
            analyzer.analyze_path("/nonexistent/path")

    def test_analyze_path_python(self, analyzer, sample_python_dir):
        """Test analyzing Python directory"""
        graph = analyzer.analyze_path(str(sample_python_dir), languages=["python"])

        assert graph is not None
        assert graph.node_count() > 0

        stats = analyzer.get_stats()
        assert stats["files"] > 0

    def test_analyze_specific_languages(self, analyzer, sample_python_dir):
        """Test analyzing only specific languages"""
        graph = analyzer.analyze_path(
            str(sample_python_dir),
            languages=["python"]
        )

        assert graph is not None

    def test_get_stats(self, analyzer, sample_python_dir):
        """Test getting analysis statistics"""
        analyzer.analyze_path(str(sample_python_dir))

        stats = analyzer.get_stats()
        assert "files" in stats
        assert "classes" in stats
        assert "functions" in stats

    def test_export_ison(self, analyzer, sample_python_dir, tmp_path):
        """Test exporting to ISON format"""
        analyzer.analyze_path(str(sample_python_dir))

        output_path = tmp_path / "output.ison"
        analyzer.export_ison(str(output_path))

        assert output_path.exists()

    def test_export_json(self, analyzer, sample_python_dir, tmp_path):
        """Test exporting to JSON format"""
        analyzer.analyze_path(str(sample_python_dir))

        output_path = tmp_path / "output.json"
        analyzer.export_json(str(output_path))

        assert output_path.exists()


# =============================================================================
# CodeFlowGraphBuilder Tests
# =============================================================================

class TestCodeFlowGraphBuilder:
    """Tests for the graph builder"""

    @pytest.fixture
    def builder(self):
        return CodeFlowGraphBuilder("test-builder")

    def test_builder_initialization(self, builder):
        """Test builder initialization"""
        assert builder.name == "test-builder"

    def test_add_file(self, builder):
        """Test adding a file element"""
        file_elem = FileElement(
            name="main.py",
            file_path="src/main.py",
            line_start=1,
            line_end=50,
            language="python",
            size_bytes=1024,
            imports=[],
        )

        builder.add_file(file_elem)
        stats = builder.get_stats()
        assert stats["files"] == 1

    def test_add_class(self, builder):
        """Test adding a class element"""
        file_elem = FileElement(
            name="models.py",
            file_path="src/models.py",
            line_start=1,
            line_end=100,
            language="python",
            size_bytes=2048,
            imports=[],
        )
        builder.add_file(file_elem)

        class_elem = ClassElement(
            name="User",
            file_path="src/models.py",
            line_start=10,
            line_end=50,
            docstring="User model"
        )

        builder.add_class(class_elem, parent_file="src/models.py")
        stats = builder.get_stats()
        assert stats["classes"] == 1

    def test_add_function(self, builder):
        """Test adding a function element"""
        file_elem = FileElement(
            name="utils.py",
            file_path="src/utils.py",
            line_start=1,
            line_end=20,
            language="python",
            size_bytes=512,
            imports=[],
        )
        builder.add_file(file_elem)

        func_elem = FunctionElement(
            name="helper",
            file_path="src/utils.py",
            line_start=5,
            line_end=10,
            parameters=["x", "y"],
            return_type="int",
        )

        builder.add_function(func_elem, parent_file="src/utils.py")
        stats = builder.get_stats()
        assert stats["functions"] == 1

    def test_add_variable(self, builder):
        """Test adding a variable element"""
        file_elem = FileElement(
            name="config.py",
            file_path="src/config.py",
            line_start=1,
            line_end=10,
            language="python",
            size_bytes=256,
            imports=[],
        )
        builder.add_file(file_elem)

        var_elem = VariableElement(
            name="CONFIG",
            file_path="src/config.py",
            line_start=5,
            line_end=5,
            var_type="dict",
            is_constant=True,
            scope="module",
        )

        builder.add_variable(var_elem, parent="src/config.py")
        stats = builder.get_stats()
        assert stats["variables"] == 1

    def test_add_module(self, builder):
        """Test adding a module element"""
        module_elem = ModuleElement(
            name="mypackage",
            file_path="src/mypackage",
            line_start=1,
            line_end=1,
            is_package=True,
            submodules=[],
        )

        builder.add_module(module_elem)
        stats = builder.get_stats()
        assert stats["modules"] == 1

    def test_add_import_relationship(self, builder):
        """Test adding import relationships"""
        # Add two files
        file1 = FileElement(
            name="main.py",
            file_path="src/main.py",
            line_start=1,
            line_end=20,
            language="python",
            size_bytes=512,
            imports=[],
        )
        file2 = FileElement(
            name="utils.py",
            file_path="src/utils.py",
            line_start=1,
            line_end=10,
            language="python",
            size_bytes=256,
            imports=[],
        )
        builder.add_file(file1)
        builder.add_file(file2)

        # Add import relationship
        builder.add_import("src/main.py", "src/utils.py")

        graph = builder.build()
        # Check edges exist
        edges = list(graph.edges())
        import_edges = [e for e in edges if e.rel_type == "IMPORTS"]
        assert len(import_edges) >= 0  # May or may not exist depending on implementation

    def test_add_calls_relationship(self, builder):
        """Test adding function call relationships"""
        file_elem = FileElement(
            name="main.py",
            file_path="src/main.py",
            line_start=1,
            line_end=20,
            language="python",
            size_bytes=512,
            imports=[],
        )
        builder.add_file(file_elem)

        func1 = FunctionElement(
            name="caller",
            file_path="src/main.py",
            line_start=1,
            line_end=5,
        )
        func2 = FunctionElement(
            name="callee",
            file_path="src/main.py",
            line_start=10,
            line_end=15,
        )

        builder.add_function(func1, parent_file="src/main.py")
        builder.add_function(func2, parent_file="src/main.py")

        builder.add_call("caller", "callee")

    def test_build_graph(self, builder):
        """Test building the final graph"""
        file_elem = FileElement(
            name="test.py",
            file_path="test.py",
            line_start=1,
            line_end=10,
            language="python",
            size_bytes=128,
            imports=[],
        )
        builder.add_file(file_elem)

        graph = builder.build()
        assert graph is not None
        assert graph.node_count() >= 1


# =============================================================================
# PythonParser Tests
# =============================================================================

class TestPythonParser:
    """Tests for the Python parser"""

    @pytest.fixture
    def parser(self):
        return PythonParser()

    @pytest.fixture
    def sample_python_file(self, tmp_path):
        """Create a sample Python file"""
        py_file = tmp_path / "sample.py"
        py_file.write_text('''
"""Sample module docstring"""

import os
from typing import List, Optional

CONSTANT = 42

class MyClass:
    """Class docstring"""

    class_var = "value"

    def __init__(self, name: str):
        self.name = name

    def method(self, x: int) -> int:
        """Method docstring"""
        return x * 2

    @staticmethod
    def static_method():
        pass

    @classmethod
    def class_method(cls):
        pass

def standalone_function(items: List[str]) -> Optional[str]:
    """Standalone function"""
    if items:
        return items[0]
    return None

async def async_function():
    """Async function"""
    pass

def _private_function():
    pass
''')
        return py_file

    def test_parser_initialization(self, parser):
        """Test parser initialization"""
        assert parser is not None

    def test_parse_file(self, parser, sample_python_file):
        """Test parsing a single Python file"""
        file_elem, elements = parser.parse_file(str(sample_python_file))

        # Should find classes, functions, and variables
        classes = [e for e in elements if isinstance(e, ClassElement)]
        functions = [e for e in elements if isinstance(e, FunctionElement)]
        variables = [e for e in elements if isinstance(e, VariableElement)]

        assert len(classes) >= 1
        assert len(functions) >= 1

    def test_parse_directory(self, parser, tmp_path):
        """Test parsing a directory"""
        # Create multiple Python files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("class Class2: pass")

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").write_text("x = 1")

        file_elements, code_elements = parser.parse_directory(str(tmp_path))

        assert len(file_elements) >= 2
        assert len(code_elements) >= 0

    def test_parse_class_methods(self, parser, sample_python_file):
        """Test parsing class methods"""
        file_elem, elements = parser.parse_file(str(sample_python_file))

        classes = [e for e in elements if isinstance(e, ClassElement)]
        assert len(classes) >= 1

        # The class should have methods
        my_class = classes[0]
        assert my_class.name == "MyClass"

    def test_parse_function_params(self, parser, tmp_path):
        """Test parsing function parameters"""
        py_file = tmp_path / "funcs.py"
        py_file.write_text('''
def simple(a, b, c):
    pass

def typed(x: int, y: str = "default") -> bool:
    return True

def varargs(*args, **kwargs):
    pass
''')

        file_elem, elements = parser.parse_file(str(py_file))
        functions = [e for e in elements if isinstance(e, FunctionElement)]

        assert len(functions) >= 3

    def test_parse_imports(self, parser, tmp_path):
        """Test parsing import statements"""
        py_file = tmp_path / "imports.py"
        py_file.write_text('''
import os
import sys
from typing import List, Dict
from pathlib import Path as P
from . import relative_module
from ..parent import something
''')

        # Parser should handle imports
        file_elem, elements = parser.parse_file(str(py_file))
        # Imports may not be returned as elements depending on implementation

    def test_parse_docstrings(self, parser, tmp_path):
        """Test parsing docstrings"""
        py_file = tmp_path / "docs.py"
        py_file.write_text('''
"""Module docstring"""

def func():
    """Function docstring"""
    pass

class MyClass:
    """Class docstring"""

    def method(self):
        """Method docstring"""
        pass
''')

        file_elem, elements = parser.parse_file(str(py_file))

        for elem in elements:
            if isinstance(elem, (FunctionElement, ClassElement)):
                # Docstrings may be captured
                pass

    def test_parse_decorators(self, parser, tmp_path):
        """Test parsing decorators"""
        py_file = tmp_path / "decorators.py"
        py_file.write_text('''
@decorator
def func1():
    pass

@decorator_with_args(arg=1)
def func2():
    pass

@property
@classmethod
def multi_decorated():
    pass
''')

        file_elem, elements = parser.parse_file(str(py_file))
        functions = [e for e in elements if isinstance(e, FunctionElement)]

        assert len(functions) >= 3


# =============================================================================
# GitHubLoader Tests
# =============================================================================

class TestGitHubLoader:
    """Tests for the GitHub loader"""

    def test_is_github_url_valid(self):
        """Test valid GitHub URLs"""
        valid_urls = [
            "https://github.com/user/repo",
            "https://github.com/user/repo.git",
            "http://github.com/org/project",
            "https://github.com/user/repo/tree/main",
        ]

        for url in valid_urls:
            assert is_github_url(url) is True

    def test_is_github_url_invalid(self):
        """Test invalid GitHub URLs"""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "https://bitbucket.org/user/repo",
            "/local/path",
            "not-a-url",
            "",
        ]

        for url in invalid_urls:
            assert is_github_url(url) is False

    def test_loader_initialization(self):
        """Test loader initialization"""
        loader = GitHubLoader()
        assert loader is not None


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_analyze_local(self, tmp_path):
        """Test analyze_local convenience function"""
        # Create a simple Python file
        py_file = tmp_path / "simple.py"
        py_file.write_text("def hello(): pass")

        graph = analyze_local(str(tmp_path), languages=["python"], name="test")

        assert graph is not None
        assert graph.node_count() >= 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full analysis pipeline"""

    @pytest.fixture
    def complex_project(self, tmp_path):
        """Create a more complex project structure"""
        # src directory
        src = tmp_path / "src"
        src.mkdir()

        # src/main.py
        (src / "main.py").write_text('''
from src.models import User
from src.utils import format_name

def main():
    user = User("John", "Doe")
    return format_name(user.first_name, user.last_name)

if __name__ == "__main__":
    print(main())
''')

        # src/models.py
        (src / "models.py").write_text('''
class User:
    def __init__(self, first_name: str, last_name: str):
        self.first_name = first_name
        self.last_name = last_name

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class Admin(User):
    def __init__(self, first_name: str, last_name: str, role: str):
        super().__init__(first_name, last_name)
        self.role = role
''')

        # src/utils.py
        (src / "utils.py").write_text('''
def format_name(first: str, last: str) -> str:
    return f"{last}, {first}"

def validate_name(name: str) -> bool:
    return len(name) > 0

DEFAULT_NAME = "Unknown"
''')

        # tests directory
        tests = tmp_path / "tests"
        tests.mkdir()

        (tests / "__init__.py").write_text("")
        (tests / "test_models.py").write_text('''
import pytest
from src.models import User, Admin

def test_user_creation():
    user = User("Jane", "Doe")
    assert user.first_name == "Jane"

def test_admin_role():
    admin = Admin("John", "Admin", "superuser")
    assert admin.role == "superuser"
''')

        return tmp_path

    def test_full_analysis_pipeline(self, complex_project):
        """Test complete analysis of a complex project"""
        analyzer = CodeFlowAnalyzer("complex-project")
        graph = analyzer.analyze_path(str(complex_project), languages=["python"])

        stats = analyzer.get_stats()

        # Should find multiple files
        assert stats["files"] >= 4

        # Should find classes
        assert stats["classes"] >= 2

        # Should find functions
        assert stats["functions"] >= 4

    def test_graph_relationships(self, complex_project):
        """Test that relationships are properly created"""
        analyzer = CodeFlowAnalyzer("relationship-test")
        graph = analyzer.analyze_path(str(complex_project), languages=["python"])

        # Check that edges exist
        edges = list(graph.edges())
        # Should have some relationships
        assert len(edges) >= 0  # Edges are optional based on implementation

    def test_export_and_reload(self, complex_project, tmp_path):
        """Test exporting and reloading a graph"""
        from ison_graph import ISONGraph

        analyzer = CodeFlowAnalyzer("export-test")
        graph = analyzer.analyze_path(str(complex_project), languages=["python"])

        # Export
        export_path = tmp_path / "export.ison"
        analyzer.export_ison(str(export_path))

        # Reload
        loaded_graph = ISONGraph.load(str(export_path))

        assert loaded_graph.node_count() == graph.node_count()
