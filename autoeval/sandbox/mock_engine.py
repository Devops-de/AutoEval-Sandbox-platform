"""Mock / In-Process Sandboxed Execution Engine.

Provides isolated execution with timeout watchdogs, memory tracking, and
AST pre-execution checks when Docker daemon is not active.
"""

import concurrent.futures
import time
import tracemalloc
from typing import Any
from autoeval.api.schemas import (
    EvaluationRequest,
    ResourceUtilization,
    TestRunResult,
)
from autoeval.core.exceptions import SandboxTimeoutError
from autoeval.security.ast_analyzer import analyze_code_ast
from autoeval.security.bandit_scanner import run_bandit_scan
from autoeval.benchmarking.test_runner import run_deterministic_tests
from autoeval.benchmarking.big_o_profiler import profile_function_complexity


class MockSandboxEngine:
    """In-process execution engine simulating Docker container constraints."""

    def __init__(self, default_timeout_seconds: float = 10.0) -> None:
        self.default_timeout_seconds = default_timeout_seconds

    def execute(self, request: EvaluationRequest) -> dict[str, Any]:
        """Runs the complete evaluation pipeline inside an isolated worker thread with watchdog."""
        timeout = request.timeout_seconds or self.default_timeout_seconds

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_internal, request)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise SandboxTimeoutError(
                    f"Execution exceeded timeout quota of {timeout}s",
                    timeout_seconds=timeout,
                )

    def _run_internal(self, request: EvaluationRequest) -> dict[str, Any]:
        wall_start = time.perf_counter_ns()
        tracemalloc.start()

        # Step 1: AST Security check
        ast_result = analyze_code_ast(request.code)
        bandit_result = run_bandit_scan(request.code)

        if not ast_result.is_safe:
            wall_end = time.perf_counter_ns()
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            elapsed_ms = (wall_end - wall_start) / 1_000_000.0
            return {
                "verdict_override": "SECURITY_VIOLATION",
                "security_analysis": ast_result,
                "bandit_analysis": bandit_result,
                "test_results": TestRunResult(
                    total_tests=0,
                    passed=0,
                    failed=0,
                    errors=0,
                    pass_rate=0.0,
                    duration_ms=0.0,
                    test_cases=[],
                    raw_output="Security violations detected during AST static analysis.",
                ),
                "algorithmic_complexity": None,
                "resource_utilization": ResourceUtilization(
                    wall_clock_time_ms=round(elapsed_ms, 2),
                    cpu_time_ms=round(elapsed_ms, 2),
                    peak_memory_mb=round(peak_mem / (1024 * 1024), 2),
                    memory_limit_mb=request.memory_limit_mb,
                ),
            }

        # Step 2: Run Deterministic Unit Tests
        test_result = run_deterministic_tests(request.code, request.test_suite)

        # Step 3: Big-O Profiling (if entrypoint specified)
        big_o_result = None
        if request.entrypoint:
            try:
                ns: dict[str, Any] = {}
                exec(compile(request.code, "<submitted_code>", "exec"), ns)
                if request.entrypoint in ns and callable(ns[request.entrypoint]):
                    target_func = ns[request.entrypoint]
                    big_o_result = profile_function_complexity(
                        func=target_func,
                        input_generator_type=request.input_generator_type,
                        expected_complexity=request.expected_complexity,
                    )
            except Exception:
                # If function fails or causes error during profiling
                big_o_result = None

        wall_end = time.perf_counter_ns()
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed_ms = (wall_end - wall_start) / 1_000_000.0

        return {
            "verdict_override": None,
            "security_analysis": ast_result,
            "bandit_analysis": bandit_result,
            "test_results": test_result,
            "algorithmic_complexity": big_o_result,
            "resource_utilization": ResourceUtilization(
                wall_clock_time_ms=round(elapsed_ms, 2),
                cpu_time_ms=round(elapsed_ms, 2),
                peak_memory_mb=round(peak_mem / (1024 * 1024), 2),
                memory_limit_mb=request.memory_limit_mb,
            ),
        }
