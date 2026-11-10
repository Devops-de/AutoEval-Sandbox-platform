"""Deterministic Unit Test Runner for Code Evaluation.

Executes test suites against submitted code in an isolated execution namespace,
capturing pass/fail outcomes, assertions, execution time, and stdout/stderr.
"""

import io
import sys
import time
import traceback
from typing import Any
from autoeval.api.schemas import TestCaseResult, TestRunResult


def run_deterministic_tests(code: str, test_suite: str) -> TestRunResult:
    """Executes a test suite against untrusted code deterministically.

    Discovers functions starting with 'test_' in the test suite and executes
    them sequentially, capturing duration and assertions.
    """
    start_total_time = time.perf_counter_ns()
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    test_case_results: list[TestCaseResult] = []
    total = 0
    passed = 0
    failed = 0
    errors = 0

    execution_namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__doc__": None,
    }

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Step 1: Execute the user code in the shared namespace
        try:
            compiled_code = compile(code, "<submitted_code>", "exec")
            exec(compiled_code, execution_namespace)
        except Exception as e:
            total = 1
            errors = 1
            test_case_results.append(
                TestCaseResult(
                    name="code_compilation",
                    status="ERROR",
                    duration_ms=0.0,
                    error_message=f"Runtime error during code loading: {type(e).__name__}: {e}\n{traceback.format_exc()}",
                )
            )
            elapsed_ms = (time.perf_counter_ns() - start_total_time) / 1_000_000.0
            return TestRunResult(
                total_tests=total,
                passed=passed,
                failed=failed,
                errors=errors,
                pass_rate=0.0,
                duration_ms=round(elapsed_ms, 2),
                test_cases=test_case_results,
                raw_output=stdout_capture.getvalue() + stderr_capture.getvalue(),
            )

        # Step 2: Execute the test suite in the same namespace
        try:
            compiled_test = compile(test_suite, "<test_suite>", "exec")
            exec(compiled_test, execution_namespace)
        except Exception as e:
            total = 1
            errors = 1
            test_case_results.append(
                TestCaseResult(
                    name="test_suite_compilation",
                    status="ERROR",
                    duration_ms=0.0,
                    error_message=f"Error compiling test suite: {type(e).__name__}: {e}\n{traceback.format_exc()}",
                )
            )
            elapsed_ms = (time.perf_counter_ns() - start_total_time) / 1_000_000.0
            return TestRunResult(
                total_tests=total,
                passed=passed,
                failed=failed,
                errors=errors,
                pass_rate=0.0,
                duration_ms=round(elapsed_ms, 2),
                test_cases=test_case_results,
                raw_output=stdout_capture.getvalue() + stderr_capture.getvalue(),
            )

        # Step 3: Discover and run all test functions ('test_*')
        test_funcs = [
            (name, obj)
            for name, obj in execution_namespace.items()
            if callable(obj) and name.startswith("test_")
        ]

        # If no explicit test_* functions, check if top-level assertions were executed
        if not test_funcs:
            # Top-level code executed with no assertion errors => 1 implicit passing test
            total = 1
            passed = 1
            test_case_results.append(
                TestCaseResult(
                    name="top_level_assertions",
                    status="PASSED",
                    duration_ms=0.0,
                    error_message=None,
                )
            )
        else:
            total = len(test_funcs)
            for test_name, test_func in test_funcs:
                t_start = time.perf_counter_ns()
                try:
                    test_func()
                    t_end = time.perf_counter_ns()
                    dur_ms = (t_end - t_start) / 1_000_000.0
                    passed += 1
                    test_case_results.append(
                        TestCaseResult(
                            name=test_name,
                            status="PASSED",
                            duration_ms=round(dur_ms, 3),
                            error_message=None,
                        )
                    )
                except AssertionError as ae:
                    t_end = time.perf_counter_ns()
                    dur_ms = (t_end - t_start) / 1_000_000.0
                    failed += 1
                    tb = traceback.format_exc()
                    test_case_results.append(
                        TestCaseResult(
                            name=test_name,
                            status="FAILED",
                            duration_ms=round(dur_ms, 3),
                            error_message=f"AssertionError: {ae}\n{tb}",
                        )
                    )
                except Exception as e:
                    t_end = time.perf_counter_ns()
                    dur_ms = (t_end - t_start) / 1_000_000.0
                    errors += 1
                    tb = traceback.format_exc()
                    test_case_results.append(
                        TestCaseResult(
                            name=test_name,
                            status="ERROR",
                            duration_ms=round(dur_ms, 3),
                            error_message=f"{type(e).__name__}: {e}\n{tb}",
                        )
                    )

    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    elapsed_ms = (time.perf_counter_ns() - start_total_time) / 1_000_000.0
    pass_rate = round(passed / total, 4) if total > 0 else 0.0

    return TestRunResult(
        total_tests=total,
        passed=passed,
        failed=failed,
        errors=errors,
        pass_rate=pass_rate,
        duration_ms=round(elapsed_ms, 2),
        test_cases=test_case_results,
        raw_output=stdout_capture.getvalue() + stderr_capture.getvalue(),
    )
