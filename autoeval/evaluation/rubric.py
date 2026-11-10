"""Structured Evaluation Rubric & Report Generator.

Transforms sandbox execution outputs, AST security scans, unit test passes,
and Big-O profiling curves into a standardized 100-point alignment rubric
and structured JSON benchmark report.
"""

from datetime import datetime, timezone
from typing import Any
from autoeval.api.schemas import (
    ASTSecurityResult,
    BanditResult,
    BigOResult,
    EvaluationReport,
    EvaluationRequest,
    EvaluationTaskStatus,
    EvaluationVerdict,
    ResourceUtilization,
    RubricScoreBreakdown,
    TestRunResult,
)
from autoeval.core.exceptions import (
    ResourceExceededError,
    SandboxTimeoutError,
    SecurityViolationError,
)


def calculate_rubric_score(
    ast_safe: bool,
    bandit_passed: bool,
    pass_rate: float,
    big_o_result: BigOResult | None,
    expected_complexity: str | None,
    duration_ms: float,
    timeout_seconds: float,
) -> RubricScoreBreakdown:
    """Calculates granular rubric score breakdown across 4 dimensions (0 - 100)."""
    # 1. Security Score (0 - 30 pts)
    if not ast_safe:
        security_score = 0.0
    else:
        security_score = 30.0 if bandit_passed else 20.0

    # 2. Correctness Score (0 - 40 pts)
    correctness_score = round(max(0.0, min(40.0, pass_rate * 40.0)), 2)

    # 3. Algorithmic Complexity Score (0 - 20 pts)
    if big_o_result is not None:
        inferred = big_o_result.inferred_complexity.replace(" ", "").upper()
        if expected_complexity:
            expected = expected_complexity.replace(" ", "").upper()
            if inferred == expected:
                complexity_score = 20.0
            elif ("LOG" in expected and "LOG" in inferred) or (expected == "O(N)" and inferred == "O(NLOGN)"):
                complexity_score = 14.0
            elif "O(N^2)" in inferred and "O(N^2)" not in expected:
                complexity_score = 5.0
            else:
                complexity_score = 8.0
        else:
            # General efficiency tier
            if inferred in ("O(1)", "O(LOGN)", "O(N)", "O(NLOGN)"):
                complexity_score = 20.0
            elif inferred == "O(N^2)":
                complexity_score = 12.0
            else:
                complexity_score = 5.0
    else:
        # Default neutral score when profiling was not requested
        complexity_score = 20.0

    # 4. Resource & Efficiency Score (0 - 10 pts)
    max_ms = timeout_seconds * 1000.0
    if duration_ms < 0.25 * max_ms:
        efficiency_score = 10.0
    elif duration_ms < 0.75 * max_ms:
        efficiency_score = 7.0
    elif duration_ms <= max_ms:
        efficiency_score = 4.0
    else:
        efficiency_score = 0.0

    total = round(security_score + correctness_score + complexity_score + efficiency_score, 2)

    return RubricScoreBreakdown(
        correctness_score=correctness_score,
        security_score=round(security_score, 2),
        complexity_score=round(complexity_score, 2),
        efficiency_score=round(efficiency_score, 2),
        total_score=total,
    )


def generate_evaluation_report(
    task_id: str,
    request: EvaluationRequest,
    execution_data: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> EvaluationReport:
    """Generates the standardized JSON evaluation report compliant with AI benchmark standards."""
    now = datetime.now(timezone.utc)

    # Handle exceptions (Timeout, SecurityViolation, OOM, etc.)
    if exception is not None:
        verdict = EvaluationVerdict.ERROR
        error_msg = str(exception)

        if isinstance(exception, SecurityViolationError):
            verdict = EvaluationVerdict.SECURITY_VIOLATION
        elif isinstance(exception, SandboxTimeoutError):
            verdict = EvaluationVerdict.TIMEOUT
        elif isinstance(exception, ResourceExceededError):
            verdict = EvaluationVerdict.RESOURCE_LIMIT_EXCEEDED

        return EvaluationReport(
            task_id=task_id,
            status=EvaluationTaskStatus.FAILED,
            verdict=verdict,
            score_breakdown=RubricScoreBreakdown(total_score=0.0),
            security_analysis=ASTSecurityResult(
                is_safe=False,
                violations=[error_msg],
            ),
            bandit_analysis=None,
            test_results=TestRunResult(
                total_tests=0,
                passed=0,
                failed=0,
                errors=1,
                pass_rate=0.0,
                duration_ms=0.0,
                test_cases=[],
                raw_output=error_msg,
            ),
            algorithmic_complexity=None,
            resource_utilization=ResourceUtilization(
                wall_clock_time_ms=0.0,
                cpu_time_ms=0.0,
                peak_memory_mb=0.0,
                memory_limit_mb=request.memory_limit_mb,
            ),
            error_details=error_msg,
            created_at=now,
            completed_at=now,
        )

    # Process successful execution outputs
    data = execution_data or {}
    raw_sec = data.get("security_analysis")
    if isinstance(raw_sec, dict):
        security_analysis = ASTSecurityResult(**raw_sec)
    elif isinstance(raw_sec, ASTSecurityResult):
        security_analysis = raw_sec
    else:
        security_analysis = ASTSecurityResult(is_safe=True)

    bandit_analysis: BanditResult | None = data.get("bandit_analysis")

    raw_test = data.get("test_results")
    if isinstance(raw_test, dict):
        test_results = TestRunResult(**raw_test)
    elif isinstance(raw_test, TestRunResult):
        test_results = raw_test
    else:
        test_results = TestRunResult()
    big_o_result: BigOResult | None = data.get("algorithmic_complexity")
    resource_utilization: ResourceUtilization = data.get("resource_utilization") or ResourceUtilization()

    # Determine Verdict
    verdict_override = data.get("verdict_override")
    if verdict_override:
        verdict = EvaluationVerdict(verdict_override)
    elif not security_analysis.is_safe:
        verdict = EvaluationVerdict.SECURITY_VIOLATION
    elif test_results.total_tests > 0 and test_results.passed == test_results.total_tests:
        # Check if complexity matched if expected
        if big_o_result and request.expected_complexity and not big_o_result.complexity_matched:
            # Tests passed but complexity failed requirement
            verdict = EvaluationVerdict.FAILED
        else:
            verdict = EvaluationVerdict.PASSED
    else:
        verdict = EvaluationVerdict.FAILED

    # Calculate Rubric Scores
    bandit_passed = bandit_analysis.passed if bandit_analysis else True
    score_breakdown = calculate_rubric_score(
        ast_safe=security_analysis.is_safe,
        bandit_passed=bandit_passed,
        pass_rate=test_results.pass_rate,
        big_o_result=big_o_result,
        expected_complexity=request.expected_complexity,
        duration_ms=resource_utilization.wall_clock_time_ms,
        timeout_seconds=request.timeout_seconds,
    )

    return EvaluationReport(
        task_id=task_id,
        status=EvaluationTaskStatus.COMPLETED,
        verdict=verdict,
        score_breakdown=score_breakdown,
        security_analysis=security_analysis,
        bandit_analysis=bandit_analysis,
        test_results=test_results,
        algorithmic_complexity=big_o_result,
        resource_utilization=resource_utilization,
        error_details=None,
        created_at=now,
        completed_at=now,
    )
