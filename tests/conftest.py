"""Shared test fixtures for AutoEval Sandbox test suite."""

import os
import sys
from pathlib import Path

# Enforce test environment flags before app imports
os.environ["APP_ENV"] = "test"
os.environ["SANDBOX_MODE"] = "mock"

import pytest

# Ensure root package is in python search path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


@pytest.fixture
def sample_valid_code():
    return """
def solve(n):
    return n * 2
"""


@pytest.fixture
def sample_valid_test():
    return """
def test_solve_positive():
    assert solve(5) == 10

def test_solve_zero():
    assert solve(0) == 0

def test_solve_negative():
    assert solve(-3) == -6
"""
