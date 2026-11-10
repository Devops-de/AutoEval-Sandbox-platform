"""Unit tests for Structured Evaluation Rubric Generator."""

from autoeval.api.schemas import (
    BigOResult,
    EvaluationRequest,
    EvaluationVerdict,
)
from autoeval.core.exceptions import SandboxTimeoutError, SecurityViolationError
from autoeval.evaluation.rubric import (
    calculate_rubric_score,
    generate_evaluation_report,
)


def test_calculate_rubric_perfect_score():
    score = calculate_rubric_score(
        ast_safe=True,
        bandit_passed=True,
        pass_rate=1.0,
        big_o_result=BigOResult(
            inferred_complexity="O(N)",
            expected_complexity="O(N)",
            complexity_matched=True,
            r_squared=0.99,
            data_points=[],
            model_fit_scores={},
        ),
        expected_complexity="O(N)",
        duration_ms=50.0,
        timeout_seconds=10.0,
    )
    assert score.security_score == 30.0
    assert score.correctness_score == 40.0
    assert score.complexity_score == 20.0
    assert score.efficiency_score == 10.0
    assert score.total_score == 100.0


def test_calculate_rubric_ast_failure():
    score = calculate_rubric_score(
        ast_safe=False,
        bandit_passed=False,
        pass_rate=0.0,
        big_o_result=None,
        expected_complexity=None,
        duration_ms=10.0,
        timeout_seconds=10.0,
    )
    assert score.security_score == 0.0
    assert score.correctness_score == 0.0
    assert score.total_score == 30.0  # 20 default complexity + 10 efficiency


def test_generate_report_timeout_exception():
    request = EvaluationRequest(
        code="while True: pass",
        test_suite="def test_none(): pass",
        timeout_seconds=5.0,
    )
    report = generate_evaluation_report(
        task_id="task-123",
        request=request,
        exception=SandboxTimeoutError("Timeout exceeded", timeout_seconds=5.0),
    )
    assert report.verdict == EvaluationVerdict.TIMEOUT
    assert report.status.value == "FAILED"
    assert report.score_breakdown.total_score == 0.0


def test_generate_report_security_violation_exception():
    request = EvaluationRequest(
        code="import os",
        test_suite="def test_none(): pass",
    )
    report = generate_evaluation_report(
        task_id="task-456",
        request=request,
        exception=SecurityViolationError("OS imported", violations=["import os"]),
    )
    assert report.verdict == EvaluationVerdict.SECURITY_VIOLATION
    assert report.status.value == "FAILED"
