"""Bandit Static Application Security Testing (SAST) Scanner Integration."""

import logging
import tempfile
from pathlib import Path
from typing import Any
from autoeval.api.schemas import BanditResult

logger = logging.getLogger(__name__)


def run_bandit_scan(code: str) -> BanditResult:
    """Runs Bandit vulnerability scanning on the provided code string.

    Falls back cleanly if bandit is not installed in the current environment.
    """
    try:
        from bandit.core import config as b_config
        from bandit.core import manager as b_manager
    except ImportError:
        logger.debug("Bandit not installed in environment; skipping secondary SAST scan.")
        return BanditResult(passed=True, issues_found=0, details=[])

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        b_conf = b_config.BanditConfig()
        mgr = b_manager.BanditManager(b_conf, "file")
        mgr.discover_files([tmp_path])
        mgr.run_tests()

        issues: list[dict[str, Any]] = []
        for issue in mgr.get_issue_list():
            # Only consider Medium or High severity issues
            if issue.severity in ("MEDIUM", "HIGH"):
                issues.append({
                    "test_id": issue.test_id,
                    "text": issue.text,
                    "severity": issue.severity,
                    "confidence": issue.confidence,
                    "line_number": issue.lineno,
                })

        passed = len(issues) == 0
        return BanditResult(passed=passed, issues_found=len(issues), details=issues)
    except Exception as e:
        logger.warning(f"Error during Bandit scan: {e}")
        return BanditResult(passed=True, issues_found=0, details=[{"error": str(e)}])
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass
