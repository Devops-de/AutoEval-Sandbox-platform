"""FastAPI Gateway route definitions for AutoEval Sandbox."""

import uuid
from typing import Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from autoeval.api.schemas import (
    EvaluationReport,
    EvaluationRequest,
    EvaluationSubmitResponse,
    EvaluationTaskStatus,
)
from autoeval.core.config import settings
from autoeval.sandbox.docker_engine import DockerSandboxEngine
from autoeval.worker.celery_app import celery_app
from autoeval.worker.tasks import process_evaluation_job

router = APIRouter(prefix="/api/v1", tags=["Evaluations"])

# In-memory evaluation store for local or async task status tracking
# When Celery/Redis is active, this also synchronizes with Redis
_TASK_STORE: dict[str, dict[str, Any]] = {}


def _run_in_background(task_id: str, request_data: dict[str, Any]) -> None:
    """Background task runner for environments operating without Celery/Redis daemon."""
    try:
        _TASK_STORE[task_id]["status"] = EvaluationTaskStatus.RUNNING.value
        result = process_evaluation_job(task_id, request_data)
        _TASK_STORE[task_id] = result
    except Exception as e:
        _TASK_STORE[task_id]["status"] = EvaluationTaskStatus.FAILED.value
        _TASK_STORE[task_id]["error_details"] = str(e)


@router.post(
    "/evaluations",
    response_model=EvaluationSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit code for asynchronous sandboxed evaluation",
)
def submit_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
) -> EvaluationSubmitResponse:
    """Enqueues an untrusted code evaluation task.

    The task is either dispatched to Celery/Redis or executed via the background
    worker pool depending on system configuration.
    """
    task_id = str(uuid.uuid4())
    req_dict = request.model_dump()

    # Initial state
    _TASK_STORE[task_id] = {
        "task_id": task_id,
        "status": EvaluationTaskStatus.QUEUED.value,
        "message": "Evaluation queued.",
    }

    # Dispatch to Celery if configured and available
    dispatched_celery = False
    if celery_app is not None and settings.app_env != "test":
        try:
            from autoeval.worker.tasks import evaluate_code_celery_task
            evaluate_code_celery_task.apply_async(args=[task_id, req_dict], task_id=task_id)
            dispatched_celery = True
        except Exception:
            dispatched_celery = False

    if not dispatched_celery:
        # Use background task worker
        background_tasks.add_task(_run_in_background, task_id, req_dict)

    return EvaluationSubmitResponse(
        task_id=task_id,
        status=EvaluationTaskStatus.QUEUED,
        poll_url=f"/api/v1/evaluations/{task_id}",
        message="Evaluation job queued for execution in isolated sandbox.",
    )


@router.get(
    "/evaluations/{task_id}",
    response_model=EvaluationReport | dict[str, Any],
    summary="Get evaluation status and complete rubric report",
)
def get_evaluation(task_id: str) -> dict[str, Any]:
    """Retrieves current execution state or final evaluation rubric report for a task."""
    # Check Celery result store if enabled
    if celery_app is not None:
        try:
            async_res = celery_app.AsyncResult(task_id)
            if async_res.ready():
                return async_res.result
            elif async_res.status in ("PENDING", "STARTED"):
                return {
                    "task_id": task_id,
                    "status": EvaluationTaskStatus.RUNNING.value
                    if async_res.status == "STARTED"
                    else EvaluationTaskStatus.QUEUED.value,
                }
        except Exception:
            pass

    # Check local task store
    if task_id not in _TASK_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation task '{task_id}' not found.",
        )

    return _TASK_STORE[task_id]


@router.post(
    "/evaluations/sync",
    response_model=EvaluationReport,
    summary="Synchronously evaluate code and return complete rubric report",
)
def evaluate_sync(request: EvaluationRequest) -> EvaluationReport:
    """Directly evaluates untrusted code and returns the complete JSON rubric report synchronously."""
    task_id = str(uuid.uuid4())
    req_dict = request.model_dump()
    result = process_evaluation_job(task_id, req_dict)
    return EvaluationReport(**result)


@router.get("/health", summary="Platform and sandbox health check")
def health_check() -> dict[str, Any]:
    """Returns runtime health status of API gateway, Docker daemon, and queue connectivity."""
    engine = DockerSandboxEngine()
    docker_status = "connected" if engine.is_docker_available else "mock_engine_active"

    redis_status = "offline"
    if settings.app_env == "production":
        try:
            import redis
            r = redis.Redis.from_url(
                settings.redis_url,
                socket_timeout=0.2,
                socket_connect_timeout=0.2,
                retry_on_timeout=False,
                single_connection_client=True,
            )
            r.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "offline"

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "sandbox_engine": docker_status,
        "redis_broker": redis_status,
        "limits": {
            "default_memory_limit_mb": settings.memory_limit_mb,
            "default_cpu_quota_vcpu": settings.cpu_quota_vcpu,
            "default_timeout_seconds": settings.default_timeout_seconds,
        },
    }


@router.get("/rubric/spec", summary="Evaluation rubric specifications")
def rubric_spec() -> dict[str, Any]:
    """Returns the platform evaluation scoring criteria and weights."""
    return {
        "rubric_weights": {
            "correctness": "40 points (Deterministic unit test pass rate)",
            "security": "30 points (AST safety & Bandit SAST compliance)",
            "algorithmic_complexity": "20 points (Big-O empirical profiling alignment)",
            "resource_efficiency": "10 points (Execution time & memory utilization limits)",
        },
        "security_policy": {
            "disallowed_modules": [
                "os", "sys", "subprocess", "socket", "shutil", "urllib", "requests", "importlib", "pickle"
            ],
            "disallowed_builtins": ["eval", "exec", "compile", "open", "__import__", "globals", "locals"],
            "disallowed_dunders": ["__subclasses__", "__bases__", "__mro__", "__globals__", "__code__"],
        },
        "complexity_classes_supported": [
            "O(1)", "O(log N)", "O(N)", "O(N log N)", "O(N^2)", "O(N^3)", "O(2^N)"
        ],
    }
