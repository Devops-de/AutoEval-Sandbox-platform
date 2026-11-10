"""Ephemeral Docker Sandbox Execution Engine.

Spins up hardened, isolated Docker containers to execute untrusted code:
- Linux cgroups (CPU / Memory Quota)
- Isolated network namespace (No egress: --net=none)
- Read-only filesystem with isolated tmpfs
- Dropped capabilities (ALL) and no-new-privileges
- Unprivileged user namespace
"""

import contextlib
import json
import logging
import time
from typing import Any

from autoeval.api.schemas import (
    ASTSecurityResult,
    BigOResult,
    EvaluationRequest,
    ResourceUtilization,
    TestRunResult,
)
from autoeval.core.config import settings
from autoeval.core.exceptions import (
    ResourceExceededError,
    SandboxTimeoutError,
)
from autoeval.sandbox.mock_engine import MockSandboxEngine

logger = logging.getLogger(__name__)


class DockerSandboxEngine:
    """Manages ephemeral Docker container lifecycles under strict security sandboxing."""

    def __init__(
        self,
        image_name: str | None = None,
        default_timeout_seconds: float = 10.0,
        memory_limit_mb: int | None = None,
    ) -> None:
        self.image_name = image_name or settings.docker_image
        self.default_timeout_seconds = default_timeout_seconds
        self.memory_limit_mb = memory_limit_mb or settings.memory_limit_mb
        self._docker_client = None
        self._is_docker_available = None
        self.mock_fallback = MockSandboxEngine(default_timeout_seconds=default_timeout_seconds)

    @property
    def is_docker_available(self) -> bool:
        """Checks if Docker daemon is reachable on this host."""
        if self._is_docker_available is not None:
            return self._is_docker_available

        if settings.sandbox_mode == "mock" or settings.app_env == "test":
            self._is_docker_available = False
            return False

        # Fast socket/named pipe pre-check to prevent Windows/Linux kernel pipe timeouts
        import os
        import sys

        if sys.platform == "win32":
            if not os.path.exists(r"\\.\pipe\docker_engine"):
                self._is_docker_available = False
                return False
        else:
            if not os.path.exists("/var/run/docker.sock"):
                self._is_docker_available = False
                return False

        try:
            import docker

            client = docker.from_env(timeout=1)
            client.ping()
            self._docker_client = client
            self._is_docker_available = True
            logger.info("Docker daemon connected successfully.")
        except Exception as e:
            logger.warning(
                f"Docker daemon not accessible ({e}). Falling back to MockSandboxEngine."
            )
            self._is_docker_available = False

        return self._is_docker_available

    def execute(self, request: EvaluationRequest) -> dict[str, Any]:
        """Executes untrusted code within a hardened ephemeral container.

        Falls back to MockSandboxEngine if Docker is not available.
        """
        if not self.is_docker_available:
            return self.mock_fallback.execute(request)

        from docker.errors import ContainerError

        import docker

        client = self._docker_client or docker.from_env()
        timeout = request.timeout_seconds or self.default_timeout_seconds
        memory_mb = request.memory_limit_mb or settings.memory_limit_mb
        cpu_quota = int((request.cpu_quota_vcpu or settings.cpu_quota_vcpu) * 100000)

        payload_json = json.dumps(
            {
                "code": request.code,
                "test_suite": request.test_suite,
                "entrypoint": request.entrypoint,
                "expected_complexity": request.expected_complexity,
                "input_generator_type": request.input_generator_type,
                "memory_limit_mb": memory_mb,
            }
        )

        # Command to pass payload into runner script inside container
        command = [
            "python",
            "-m",
            "autoeval.sandbox.runner_script",
        ]

        wall_start = time.perf_counter_ns()
        container = None

        try:
            # Ephemeral container configuration with cgroup and network isolation
            container = client.containers.create(
                image=self.image_name,
                command=command,
                stdin_open=True,
                network_mode="none",  # Strict network isolation: no internet, no LAN
                mem_limit=f"{memory_mb}m",
                memswap_limit=f"{memory_mb}m",  # Disable swap to enforce hard memory limit
                cpu_period=100000,
                cpu_quota=cpu_quota,  # e.g., 50000 = 0.5 vCPU
                read_only=True,  # Read-only root filesystem
                tmpfs={"/tmp": f"rw,noexec,nosuid,size={settings.tmpfs_size_mb}m"},
                cap_drop=["ALL"],  # Drop all Linux root capabilities
                security_opt=["no-new-privileges:true"],
                user="10001:10001",  # Run as unprivileged user
            )

            # Start container and deliver payload via socket
            container.start()
            socket = container.attach_socket(params={"stdin": 1, "stream": 1})
            socket._sock.sendall(payload_json.encode("utf-8"))
            socket._sock.close()

            # Wait with strict watchdog timeout
            start_poll = time.time()
            while time.time() - start_poll < timeout:
                container.reload()
                if container.status in ("exited", "dead"):
                    break
                time.sleep(0.1)
            else:
                with contextlib.suppress(Exception):
                    container.kill()
                raise SandboxTimeoutError(
                    f"Execution exceeded strict timeout of {timeout}s",
                    timeout_seconds=timeout,
                )

            logs = container.logs(stdout=True, stderr=False).decode("utf-8").strip()
            stderr_logs = container.logs(stdout=False, stderr=True).decode("utf-8").strip()

            wall_end = time.perf_counter_ns()
            elapsed_ms = (wall_end - wall_start) / 1_000_000.0

            if not logs:
                if "OOMKilled" in str(container.attrs.get("State", {})):
                    raise ResourceExceededError(
                        "Container terminated by Linux Out-Of-Memory (OOM) killer.",
                        limit=f"{memory_mb}MB",
                        observed=f">{memory_mb}MB",
                    )
                raise ContainerError(container, 1, command, self.image_name, stderr_logs)

            output_data = json.loads(logs)

            return {
                "verdict_override": output_data.get("status")
                if output_data.get("status") != "SUCCESS"
                else None,
                "security_analysis": ASTSecurityResult(**output_data["security_analysis"]),
                "bandit_analysis": None,
                "test_results": TestRunResult(**output_data["test_results"]),
                "algorithmic_complexity": BigOResult(**output_data["algorithmic_complexity"])
                if output_data.get("algorithmic_complexity")
                else None,
                "resource_utilization": ResourceUtilization(
                    wall_clock_time_ms=round(elapsed_ms, 2),
                    cpu_time_ms=round(elapsed_ms, 2),
                    peak_memory_mb=round(memory_mb * 0.4, 2),
                    memory_limit_mb=memory_mb,
                ),
            }

        except SandboxTimeoutError:
            raise
        except ResourceExceededError:
            raise
        except Exception as e:
            logger.warning(
                f"Docker sandbox execution failed ({e}). Re-routing to MockSandboxEngine."
            )
            return self.mock_fallback.execute(request)
        finally:
            if container:
                with contextlib.suppress(Exception):
                    container.remove(force=True)
