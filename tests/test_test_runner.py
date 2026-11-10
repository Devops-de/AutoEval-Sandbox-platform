"""Unit tests for Deterministic Test Runner."""

from autoeval.benchmarking.test_runner import run_deterministic_tests


def test_test_runner_all_passed():
    code = """
def multiply(a, b):
    return a * b
"""
    test_suite = """
def test_mult_positive():
    assert multiply(3, 4) == 12

def test_mult_zero():
    assert multiply(5, 0) == 0
"""
    result = run_deterministic_tests(code, test_suite)
    assert result.total_tests == 2
    assert result.passed == 2
    assert result.failed == 0
    assert result.errors == 0
    assert result.pass_rate == 1.0


def test_test_runner_assertion_failure():
    code = """
def buggy_add(a, b):
    return a - b  # Bug
"""
    test_suite = """
def test_add_correct():
    assert buggy_add(10, 5) == 15
"""
    result = run_deterministic_tests(code, test_suite)
    assert result.total_tests == 1
    assert result.passed == 0
    assert result.failed == 1
    assert result.pass_rate == 0.0
    assert "AssertionError" in result.test_cases[0].error_message


def test_test_runner_compilation_error():
    code = "def syntax_err(: pass"
    test_suite = "def test_nothing(): assert True"

    result = run_deterministic_tests(code, test_suite)
    assert result.errors == 1
    assert result.passed == 0
    assert "SyntaxError" in result.test_cases[0].error_message


def test_test_runner_runtime_exception():
    code = """
def div(a, b):
    return a / b
"""
    test_suite = """
def test_div_zero():
    div(1, 0)
"""
    result = run_deterministic_tests(code, test_suite)
    assert result.total_tests == 1
    assert result.errors == 1
    assert "ZeroDivisionError" in result.test_cases[0].error_message
