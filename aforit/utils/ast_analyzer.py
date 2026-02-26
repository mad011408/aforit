"""AST analyzer - analyze Python code structure."""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionInfo:
    """Information about a function or method."""

    name: str
    lineno: int
    end_lineno: int | None
    args: list[str]
    decorators: list[str]
    is_async: bool
    docstring: str | None
    return_annotation: str | None
    complexity: int = 0


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    lineno: int
    end_lineno: int | None
    bases: list[str]
    methods: list[FunctionInfo]
    decorators: list[str]
    docstring: str | None


@dataclass
class ModuleInfo:
    """Information about a Python module."""

    imports: list[str]
    classes: list[ClassInfo]
    functions: list[FunctionInfo]
    global_variables: list[str]
    docstring: str | None
    total_lines: int
    complexity: int = 0


class ASTAnalyzer:
    """Analyze Python source code using the AST."""

    def analyze(self, source: str) -> ModuleInfo:
        """Analyze Python source code and return structured info."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")

        return ModuleInfo(
            imports=self._extract_imports(tree),
            classes=self._extract_classes(tree),
            functions=self._extract_functions(tree),
            global_variables=self._extract_globals(tree),
            docstring=ast.get_docstring(tree),
            total_lines=len(source.splitlines()),
            complexity=self._calculate_complexity(tree),
        )

    def _extract_imports(self, tree: ast.Module) -> list[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
        return imports

    def _extract_functions(self, tree: ast.Module) -> list[FunctionInfo]:
        """Extract top-level functions."""
        functions = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._parse_function(node))
        return functions

    def _extract_classes(self, tree: ast.Module) -> list[ClassInfo]:
        classes = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(self._parse_function(item))

                classes.append(ClassInfo(
                    name=node.name,
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                    bases=[ast.dump(b) for b in node.bases],
                    methods=methods,
                    decorators=[ast.dump(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node),
                ))
        return classes

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        return_ann = None
        if node.returns:
            try:
                return_ann = ast.unparse(node.returns)
            except Exception:
                return_ann = str(node.returns)

        return FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno,
            args=args,
            decorators=[ast.dump(d) for d in node.decorator_list],
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=ast.get_docstring(node),
            return_annotation=return_ann,
            complexity=self._calculate_complexity(node),
        )

    def _extract_globals(self, tree: ast.Module) -> list[str]:
        globals_ = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_.append(target.id)
        return globals_

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a node."""
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.Assert, ast.Raise)):
                complexity += 1
        return complexity

    def get_summary(self, source: str) -> str:
        """Get a human-readable summary of the code."""
        info = self.analyze(source)
        lines = []

        if info.docstring:
            lines.append(f"Module: {info.docstring.split(chr(10))[0]}")

        lines.append(f"Lines: {info.total_lines} | Complexity: {info.complexity}")
        lines.append(f"Imports: {len(info.imports)}")

        if info.classes:
            lines.append(f"Classes ({len(info.classes)}):")
            for cls in info.classes:
                lines.append(f"  - {cls.name} ({len(cls.methods)} methods)")
                for method in cls.methods:
                    async_tag = "async " if method.is_async else ""
                    lines.append(f"    - {async_tag}{method.name}({', '.join(method.args)})")

        if info.functions:
            lines.append(f"Functions ({len(info.functions)}):")
            for func in info.functions:
                async_tag = "async " if func.is_async else ""
                lines.append(f"  - {async_tag}{func.name}({', '.join(func.args)})")

        return "\n".join(lines)
