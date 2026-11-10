"""Celery and Background evaluation task workers."""

import logging
from typing import Any

from autoeval.api.schemas import EvaluationRequest
from autoeval.evaluation.rubric import generate_evaluation_report
from autoeval.sandbox.docker_engine import DockerSandboxEngine
from autoeval.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def process_evaluation_job(task_id: str, request_data: dict[str, Any]) -> dict[str, Any]:
    """Core evaluation worker function.

    Takes raw request data, invokes the sandbox execution engine,
    and returns a serialized EvaluationReport.
    """
    request = EvaluationRequest(**request_data)
    engine = DockerSandboxEngine(
        memory_limit_mb=request.memory_limit_mb,
        default_timeout_seconds=request.timeout_seconds,
    )

    try:
        execution_data = engine.execute(request)
        report = generate_evaluation_report(
            task_id=task_id,
            request=request,
            execution_data=execution_data,
        )
    except Exception as exc:
        logger.error(f"Execution error on task {task_id}: {exc}")
        report = generate_evaluation_report(
            task_id=task_id,
            request=request,
            exception=exc,
        )

    return report.model_dump(mode="json")


# Register Celery task if Celery is enabled
if celery_app is not None:

    @celery_app.task(name="autoeval.evaluate_code", bind=True)
    def evaluate_code_celery_task(
        self, task_id: str, request_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Celery distributed task wrapper."""
        return process_evaluation_job(task_id, request_data)
