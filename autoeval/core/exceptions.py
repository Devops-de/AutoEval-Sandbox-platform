"""Custom domain exceptions for AutoEval Sandbox."""


class AutoEvalError(Exception):
    """Base exception for all AutoEval platform errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SecurityViolationError(AutoEvalError):
    """Raised when untrusted code violates AST security policies."""

    def __init__(self, message: str, violations: list[str] | None = None) -> None:
        super().__init__(message, details={"violations": violations or []})
        self.violations = violations or []


class SandboxTimeoutError(AutoEvalError):
    """Raised when container or evaluation exceeds execution timeout."""

    def __init__(self, message: str, timeout_seconds: float) -> None:
        super().__init__(message, details={"timeout_seconds": timeout_seconds})
        self.timeout_seconds = timeout_seconds


class ResourceExceededError(AutoEvalError):
    """Raised when memory, CPU or disk usage exceeds cgroup constraints."""

    def __init__(self, message: str, limit: str, observed: str) -> None:
        super().__init__(message, details={"limit": limit, "observed": observed})
        self.limit = limit
        self.observed = observed


class TestExecutionError(AutoEvalError):
    """Raised when test harness execution fails fatally."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message, details={"stderr": stderr})
        self.stderr = stderr


class EvaluationNotFoundError(AutoEvalError):
    """Raised when an evaluation task ID cannot be found."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Evaluation task '{task_id}' not found.", details={"task_id": task_id})
        self.task_id = task_id
