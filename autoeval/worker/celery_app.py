"""Celery application instance and Redis broker configuration."""

import logging
from autoeval.core.config import settings

logger = logging.getLogger(__name__)

celery_app = None

try:
    from celery import Celery

    celery_app = Celery(
        "autoeval_sandbox",
        broker=settings.redis_url,
        backend=settings.celery_result_backend,
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=60,
        worker_prefetch_multiplier=1,
    )
except ImportError:
    logger.info("Celery library not present. In-process queue will handle background execution.")
