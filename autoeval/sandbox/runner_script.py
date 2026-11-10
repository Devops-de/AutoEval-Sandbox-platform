"""In-container runner script for AutoEval Sandbox.

Executes inside ephemeral Docker container under cgroup and resource quota constraints.
Sets Linux RLIMIT_AS (memory limit), executes test suite and Big-O profiler,
and emits structured JSON to stdout.
"""

import json
import os
import sys
from autoeval.security.ast_analyzer import analyze_code_ast
from autoeval.benchmarking.test_runner import run_deterministic_tests
from autoeval.benchmarking.big_o_profiler import profile_function_complexity


def apply_linux_resource_limits(memory_limit_mb: int) -> None:
    """Sets OS-level virtual memory limit using Linux resource module."""
    try:
        import resource

        # Convert MB to bytes
        limit_bytes = memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    except (ImportError, AttributeError, ValueError, OSError):
        # Ignored on platforms without resource / RLIMIT_AS (like Windows)
        pass


def execute_payload(payload: dict) -> dict:
    """Executes the evaluation payload and returns the structured evaluation dict."""
    code = payload.get("code", "")
    test_suite = payload.get("test_suite", "")
    entrypoint = payload.get("entrypoint")
    expected_complexity = payload.get("expected_complexity")
    input_generator_type = payload.get("input_generator_type", "random_integers")
    memory_limit_mb = payload.get("memory_limit_mb", 256)

    # Apply internal memory limits
    apply_linux_resource_limits(memory_limit_mb)

    # 1. AST Security Analysis
    ast_result = analyze_code_ast(code)
    if not ast_result.is_safe:
        return {
            "status": "SECURITY_VIOLATION",
            "security_analysis": ast_result.model_dump(),
            "test_results": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "pass_rate": 0.0,
                "duration_ms": 0.0,
                "test_cases": [],
                "raw_output": "",
            },
            "algorithmic_complexity": None,
        }

    # 2. Deterministic Unit Tests
    test_result = run_deterministic_tests(code, test_suite)

    # 3. Big-O Profiling (if entrypoint provided and tests did not fail catastrophically)
    big_o_data = None
    if entrypoint:
        try:
            ns: dict = {}
            exec(compile(code, "<code_bench>", "exec"), ns)
            if entrypoint in ns and callable(ns[entrypoint]):
                func = ns[entrypoint]
                big_o_res = profile_function_complexity(
                    func=func,
                    input_generator_type=input_generator_type,
                    expected_complexity=expected_complexity,
                )
                big_o_data = big_o_res.model_dump()
        except Exception as e:
            big_o_data = {"error": str(e)}

    return {
        "status": "SUCCESS",
        "security_analysis": ast_result.model_dump(),
        "test_results": test_result.model_dump(),
        "algorithmic_complexity": big_o_data,
    }


def main() -> None:
    """CLI entrypoint for in-container runner."""
    input_str = ""
    payload_file = os.getenv("PAYLOAD_PATH", "/tmp/payload.json")

    if os.path.exists(payload_file):
        with open(payload_file, "r", encoding="utf-8") as f:
            input_str = f.read()
    else:
        input_str = sys.stdin.read()

    if not input_str:
        print(json.dumps({"error": "Empty payload provided to runner."}))
        sys.exit(1)

    try:
        payload = json.loads(input_str)
        result = execute_payload(payload)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
