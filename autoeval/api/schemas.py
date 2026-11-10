"""Pydantic schemas for AutoEval Sandbox requests and rubric responses."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EvaluationVerdict(str, Enum):
    """Final assessment verdict for evaluated code."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    ERROR = "ERROR"


class EvaluationTaskStatus(str, Enum):
    """Status of an asynchronous evaluation job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvaluationRequest(BaseModel):
    """Payload to submit code for sandbox evaluation and benchmarking."""

    code: str = Field(..., description="Untrusted Python code to be evaluated.", min_length=1)
    test_suite: str = Field(..., description="Pytest-compatible test suite code.", min_length=1)
    entrypoint: str | None = Field(
        default=None,
        description="Target function name for empirical Big-O profiling (e.g. 'quick_sort').",
    )
    expected_complexity: str | None = Field(
        default=None,
        description="Expected Big-O complexity class (e.g. 'O(N)', 'O(N log N)', 'O(N^2)').",
    )
    input_generator_type: str = Field(
        default="random_integers",
        description="Type of test input scaling: 'random_integers', 'sorted_integers', 'reversed_integers', 'string_tokens'.",
    )
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0, description="Max execution timeout in seconds.")
    memory_limit_mb: int = Field(default=256, ge=32, le=1024, description="Container cgroup memory quota in MB.")
    cpu_quota_vcpu: float = Field(default=0.5, ge=0.1, le=2.0, description="Container CPU quota in vCPU.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)\n",
                "test_suite": "def test_sort():\n    assert quick_sort([3, 1, 2]) == [1, 2, 3]\n    assert quick_sort([]) == []\n    assert quick_sort([5]) == [5]\n",
                "entrypoint": "quick_sort",
                "expected_complexity": "O(N log N)",
                "timeout_seconds": 10.0,
                "memory_limit_mb": 256,
            }
        }
    }


class ASTSecurityResult(BaseModel):
    """Static AST security analysis report."""

    is_safe: bool = Field(..., description="True if code passes all AST security checks.")
    violations: list[str] = Field(default_factory=list, description="List of detected policy violations.")
    banned_imports: list[str] = Field(default_factory=list, description="Disallowed modules imported.")
    banned_calls: list[str] = Field(default_factory=list, description="Disallowed functions or builtins invoked.")
    banned_attributes: list[str] = Field(default_factory=list, description="Disallowed dunder/sensitive attributes.")
    max_loop_depth: int = Field(default=0, description="Maximum nested loop depth detected in AST.")
    has_recursion: bool = Field(default=False, description="Whether recursive function definitions are present.")


class BanditResult(BaseModel):
    """Static application security testing (SAST) via Bandit."""

    passed: bool = Field(..., description="True if no high/medium severity vulnerabilities found.")
    issues_found: int = Field(default=0, description="Count of security findings.")
    details: list[dict[str, Any]] = Field(default_factory=list, description="Bandit issue records.")


class TestCaseResult(BaseModel):
    """Individual test execution outcome."""

    __test__ = False  # Prevent pytest from collecting this schema as a test class
    name: str = Field(..., description="Name of the test function or case.")
    status: str = Field(..., description="'PASSED', 'FAILED', or 'ERROR'.")
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds.")
    error_message: str | None = Field(default=None, description="Assertion failure message or traceback.")


class TestRunResult(BaseModel):
    """Pytest suite execution summary."""

    __test__ = False  # Prevent pytest from collecting this schema as a test class
    total_tests: int = Field(default=0, description="Total number of tests executed.")
    passed: int = Field(default=0, description="Number of passed tests.")
    failed: int = Field(default=0, description="Number of failed tests.")
    errors: int = Field(default=0, description="Number of test harness setup/runtime errors.")
    pass_rate: float = Field(default=0.0, description="Fraction of passing tests (0.0 to 1.0).")
    duration_ms: float = Field(default=0.0, description="Total test duration in ms.")
    test_cases: list[TestCaseResult] = Field(default_factory=list, description="Individual test details.")
    raw_output: str = Field(default="", description="Captured stdout/stderr from test runner.")


class ComplexityDataPoint(BaseModel):
    """Empirical benchmark sample for a given input size N."""

    n: int = Field(..., description="Input size dimension.")
    wall_time_ms: float = Field(..., description="Execution duration in milliseconds.")
    memory_peak_kb: float = Field(default=0.0, description="Peak memory allocated in KB.")


class BigOResult(BaseModel):
    """Empirical algorithmic complexity analysis."""

    inferred_complexity: str = Field(..., description="Best-fit Big-O class (e.g. O(N log N)).")
    expected_complexity: str | None = Field(default=None, description="Expected Big-O from request.")
    complexity_matched: bool | None = Field(default=None, description="True if inferred matches expected.")
    r_squared: float = Field(..., description="Coefficient of determination for best-fit model (0 to 1).")
    data_points: list[ComplexityDataPoint] = Field(default_factory=list, description="Empirical benchmark points.")
    model_fit_scores: dict[str, float] = Field(
        default_factory=dict, description="R^2 correlation scores for each candidate Big-O model."
    )


class ResourceUtilization(BaseModel):
    """Resource consumption recorded during execution."""

    wall_clock_time_ms: float = Field(default=0.0, description="Total execution wall time.")
    cpu_time_ms: float = Field(default=0.0, description="CPU time consumed.")
    peak_memory_mb: float = Field(default=0.0, description="Peak memory utilized.")
    memory_limit_mb: int = Field(default=256, description="Allocated cgroup memory limit.")


class RubricScoreBreakdown(BaseModel):
    """Detailed score breakdown matching alignment rubrics."""

    correctness_score: float = Field(default=0.0, description="Score for unit test pass rate (0 to 40).")
    security_score: float = Field(default=0.0, description="Score for AST & SAST safety compliance (0 to 30).")
    complexity_score: float = Field(default=0.0, description="Score for Big-O complexity alignment (0 to 20).")
    efficiency_score: float = Field(default=0.0, description="Score for resource bounds & efficiency (0 to 10).")
    total_score: float = Field(default=0.0, description="Cumulative score (0 to 100).")


class EvaluationReport(BaseModel):
    """Comprehensive evaluation rubric and benchmark JSON report."""

    task_id: str = Field(..., description="Unique task evaluation identifier.")
    status: EvaluationTaskStatus = Field(..., description="Evaluation status.")
    verdict: EvaluationVerdict = Field(..., description="Overall verdict.")
    score_breakdown: RubricScoreBreakdown = Field(..., description="Rubric score breakdown.")
    security_analysis: ASTSecurityResult = Field(..., description="Static AST security results.")
    bandit_analysis: BanditResult | None = Field(default=None, description="Bandit SAST scanner results.")
    test_results: TestRunResult = Field(..., description="Deterministic unit test results.")
    algorithmic_complexity: BigOResult | None = Field(default=None, description="Big-O profiling report.")
    resource_utilization: ResourceUtilization = Field(..., description="Execution resource metrics.")
    error_details: str | None = Field(default=None, description="Top-level error explanation if failed.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = Field(default=None)


class EvaluationSubmitResponse(BaseModel):
    """Response returned upon submitting an asynchronous evaluation task."""

    task_id: str = Field(..., description="Task identifier for polling evaluation results.")
    status: EvaluationTaskStatus = Field(default=EvaluationTaskStatus.QUEUED)
    poll_url: str = Field(..., description="URL endpoint to poll for status and final report.")
    message: str = Field(default="Evaluation job queued successfully.")
