"""Static AST Security Analyzer for untrusted Python code.

Inspects code structure before execution:
1. Blocks dangerous modules (os, sys, subprocess, socket, etc.)
2. Blocks dangerous builtins (eval, exec, compile, open, etc.)
3. Blocks dunder introspection attacks (__subclasses__, __globals__, etc.)
4. Extracts static complexity indicators (max loop depth, recursion).
"""

import ast
from typing import Any
from autoeval.api.schemas import ASTSecurityResult


# Whitelist of common safe standard library modules
SAFE_MODULES = {
    "math",
    "collections",
    "itertools",
    "functools",
    "heapq",
    "bisect",
    "random",
    "string",
    "copy",
    "json",
    "typing",
    "dataclasses",
    "enum",
    "re",
    "time",
    "datetime",
}

# Explicitly banned modules (potential RCE, file manipulation, network)
BANNED_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "shutil",
    "urllib",
    "requests",
    "http",
    "builtins",
    "importlib",
    "pickle",
    "marshal",
    "shelve",
    "ctypes",
    "pty",
    "posix",
    "webbrowser",
    "platform",
    "signal",
    "multiprocessing",
    "threading",
    "asyncio",  # keep sandboxed execution single-threaded / deterministic
}

# Dangerous built-in function names
BANNED_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "globals",
    "locals",
    "breakpoint",
    "input",
}

# Prohibited dunder attributes commonly used in python sandbox escape gadgets
BANNED_ATTRIBUTES = {
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__globals__",
    "__code__",
    "__builtins__",
    "__closure__",
    "__loader__",
    "__spec__",
    "__dict__",
}


class SecurityASTVisitor(ast.NodeVisitor):
    """AST visitor collecting security policy violations and structural complexity metrics."""

    def __init__(self, strict_mode: bool = True) -> None:
        self.strict_mode = strict_mode
        self.violations: list[str] = []
        self.banned_imports: list[str] = []
        self.banned_calls: list[str] = []
        self.banned_attributes: list[str] = []

        self.current_loop_depth = 0
        self.max_loop_depth = 0
        self.current_function: str | None = None
        self.function_calls: dict[str, set[str]] = {}
        self.has_recursion = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_module = alias.name.split(".")[0]
            if root_module in BANNED_MODULES or (self.strict_mode and root_module not in SAFE_MODULES):
                msg = f"Disallowed module import: '{alias.name}' at line {node.lineno}"
                self.violations.append(msg)
                self.banned_imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root_module = node.module.split(".")[0]
            if root_module in BANNED_MODULES or (self.strict_mode and root_module not in SAFE_MODULES):
                msg = f"Disallowed module import: 'from {node.module}' at line {node.lineno}"
                self.violations.append(msg)
                self.banned_imports.append(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct calls like eval(...), open(...)
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in BANNED_CALLS:
                msg = f"Disallowed function call: '{func_name}()' at line {node.lineno}"
                self.violations.append(msg)
                self.banned_calls.append(func_name)

            # Track recursion
            if self.current_function:
                self.function_calls.setdefault(self.current_function, set()).add(func_name)
                if func_name == self.current_function:
                    self.has_recursion = True

        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in BANNED_CALLS:
                msg = f"Disallowed method call: '.{attr_name}()' at line {node.lineno}"
                self.violations.append(msg)
                self.banned_calls.append(attr_name)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in BANNED_ATTRIBUTES:
            msg = f"Disallowed attribute access: '.{node.attr}' at line {node.lineno}"
            self.violations.append(msg)
            self.banned_attributes.append(node.attr)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        previous_func = self.current_function
        self.current_function = node.name
        self.function_calls.setdefault(node.name, set())
        self.generic_visit(node)
        self.current_function = previous_func

    def visit_For(self, node: ast.For) -> None:
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1


def analyze_code_ast(code: str, strict_mode: bool = True) -> ASTSecurityResult:
    """Parses and checks untrusted code for static security violations.

    Args:
        code: Untrusted Python source code string.
        strict_mode: When True, disallows any module outside SAFE_MODULES.

    Returns:
        ASTSecurityResult with safety verdict and violation details.
    """
    try:
        parsed_tree = ast.parse(code)
    except SyntaxError as e:
        return ASTSecurityResult(
            is_safe=False,
            violations=[f"SyntaxError during AST parsing: {e.msg} at line {e.lineno}"],
            banned_imports=[],
            banned_calls=[],
            banned_attributes=[],
            max_loop_depth=0,
            has_recursion=False,
        )

    visitor = SecurityASTVisitor(strict_mode=strict_mode)
    visitor.visit(parsed_tree)

    is_safe = len(visitor.violations) == 0

    return ASTSecurityResult(
        is_safe=is_safe,
        violations=visitor.violations,
        banned_imports=visitor.banned_imports,
        banned_calls=visitor.banned_calls,
        banned_attributes=visitor.banned_attributes,
        max_loop_depth=visitor.max_loop_depth,
        has_recursion=visitor.has_recursion,
    )
