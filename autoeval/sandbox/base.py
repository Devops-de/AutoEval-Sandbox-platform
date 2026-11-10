"""Abstract interface and Protocol definitions for Sandbox Execution Engines."""

from typing import Any, Protocol, runtime_checkable

from autoeval.api.schemas import EvaluationRequest


@runtime_checkable
class SandboxEngine(Protocol):
    """Protocol defining the contract for sandboxed execution backends.

    Implementations include:
    - DockerSandboxEngine: Hardened ephemeral Docker containers with cgroups v2.
    - MockSandboxEngine: In-process isolated watchdog executor for local testing.
    """

    def execute(self, request: EvaluationRequest) -> dict[str, Any]:
        """Executes the evaluation request under security constraints.

        Args:
            request: The validated code evaluation payload.

        Returns:
            Dictionary containing security_analysis, test_results,
            algorithmic_complexity, and resource_utilization metrics.
        """
        ...
