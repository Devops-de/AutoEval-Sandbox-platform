"""Unit and integration tests for API routes and evaluation lifecycles."""

from fastapi import BackgroundTasks

from autoeval.api.routes import (
    evaluate_sync,
    get_evaluation,
    health_check,
    rubric_spec,
    submit_evaluation,
)
from autoeval.api.schemas import EvaluationRequest


def test_health_check_endpoint():
    data = health_check()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "sandbox_engine" in data
    assert "limits" in data


def test_rubric_spec_endpoint():
    data = rubric_spec()
    assert "rubric_weights" in data
    assert "security_policy" in data
    assert "complexity_classes_supported" in data


def test_evaluate_sync_passing_quick_sort():
    req = EvaluationRequest(
        code="""
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
""",
        test_suite="""
def test_sort_basic():
    assert quick_sort([3, 1, 2]) == [1, 2, 3]

def test_sort_empty():
    assert quick_sort([]) == []

def test_sort_single():
    assert quick_sort([5]) == [5]
""",
        entrypoint="quick_sort",
        expected_complexity="O(N log N)",
        timeout_seconds=10.0,
        memory_limit_mb=256,
    )

    report = evaluate_sync(req)
    assert report.verdict.value in ("PASSED", "FAILED")
    assert report.test_results.passed == 3
    assert report.test_results.total_tests == 3
    assert report.security_analysis.is_safe is True
    assert report.score_breakdown.total_score > 70.0


def test_evaluate_sync_security_violation_blocked():
    req = EvaluationRequest(
        code="""
import os

def run():
    os.system("whoami")
    return 1
""",
        test_suite="def test_run(): assert run() == 1",
    )

    report = evaluate_sync(req)
    assert report.verdict.value == "SECURITY_VIOLATION"
    assert report.security_analysis.is_safe is False
    assert len(report.security_analysis.violations) > 0


def test_async_evaluation_submission_and_poll():
    req = EvaluationRequest(
        code="def double(x): return x * 2",
        test_suite="def test_double(): assert double(4) == 8",
        timeout_seconds=5.0,
    )

    bg = BackgroundTasks()
    submit_res = submit_evaluation(req, bg)
    task_id = submit_res.task_id
    assert submit_res.status.value == "QUEUED"
    assert submit_res.poll_url == f"/api/v1/evaluations/{task_id}"

    # Execute background tasks directly
    for task in bg.tasks:
        task.func(*task.args, **task.kwargs)

    # Poll status
    poll_data = get_evaluation(task_id)
    assert poll_data["task_id"] == task_id
    assert poll_data["status"] == "COMPLETED"
    assert poll_data["verdict"] == "PASSED"
    assert poll_data["score_breakdown"]["total_score"] >= 80.0
