"""Unit tests for AST Static Security Analyzer."""

from autoeval.security.ast_analyzer import analyze_code_ast


def test_benign_code_passes():
    code = """
import math

def calculate(arr):
    total = sum(arr)
    return math.sqrt(total)
"""
    result = analyze_code_ast(code)
    assert result.is_safe is True
    assert len(result.violations) == 0
    assert result.banned_imports == []
    assert result.banned_calls == []


def test_banned_os_import_blocked():
    code = """
import os

def run():
    os.system("echo hacked")
"""
    result = analyze_code_ast(code)
    assert result.is_safe is False
    assert any("os" in v for v in result.violations)
    assert "os" in result.banned_imports


def test_banned_subprocess_from_import_blocked():
    code = """
from subprocess import Popen

def run():
    Popen(["ls", "-l"])
"""
    result = analyze_code_ast(code)
    assert result.is_safe is False
    assert any("subprocess" in v for v in result.violations)
    assert "subprocess" in result.banned_imports


def test_banned_eval_call_blocked():
    code = """
def execute(cmd):
    return eval(cmd)
"""
    result = analyze_code_ast(code)
    assert result.is_safe is False
    assert any("eval" in v for v in result.violations)
    assert "eval" in result.banned_calls


def test_banned_open_call_blocked():
    code = """
def read_file(path):
    with open(path) as f:
        return f.read()
"""
    result = analyze_code_ast(code)
    assert result.is_safe is False
    assert any("open" in v for v in result.violations)
    assert "open" in result.banned_calls


def test_dunder_subclasses_exploit_blocked():
    code = """
def escape():
    return ().__class__.__bases__[0].__subclasses__()
"""
    result = analyze_code_ast(code)
    assert result.is_safe is False
    assert any("__subclasses__" in v for v in result.violations)
    assert "__subclasses__" in result.banned_attributes


def test_nested_loop_depth_detection():
    code = """
def matrix_mult(A, B):
    n = len(A)
    C = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
    return C
"""
    result = analyze_code_ast(code)
    assert result.is_safe is True
    assert result.max_loop_depth == 3


def test_recursion_detection():
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    result = analyze_code_ast(code)
    assert result.is_safe is True
    assert result.has_recursion is True


def test_syntax_error_handled_gracefully():
    code = "def invalid_syntax(:"
    result = analyze_code_ast(code)
    assert result.is_safe is False
    assert any("SyntaxError" in v for v in result.violations)
