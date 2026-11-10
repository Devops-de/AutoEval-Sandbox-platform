"""FastAPI Main Application and Lifespan Entrypoint."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autoeval.api.routes import router
from autoeval.core.config import settings

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("autoeval")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version} [{settings.app_env}]")
    yield
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title="AutoEval Sandbox API",
    description=(
        "Ephemeral AI Code Evaluation & Algorithmic Benchmarking Platform. "
        "Safely executes untrusted LLM-generated code in hardened, resource-constrained "
        "sandboxes with deterministic unit tests, empirical Big-O profiling, and AST safety analysis."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("autoeval.api.main:app", host="0.0.0.0", port=8000, reload=True)
