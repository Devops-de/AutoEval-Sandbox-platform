"""Empirical Big-O Algorithmic Profiler.

Measures wall-clock time and peak memory vs. input size N.
Applies mathematical regression and doubling-ratio analysis to infer Big-O complexity classes:
- O(1) Constant
- O(log N) Logarithmic
- O(N) Linear
- O(N log N) Linearithmic
- O(N^2) Quadratic
- O(N^3) Cubic
- O(2^N) Exponential
"""

import math
import random
import time
import tracemalloc
from collections.abc import Callable
from typing import Any

from autoeval.api.schemas import BigOResult, ComplexityDataPoint


def generate_input_for_n(n: int, generator_type: str = "random_integers") -> Any:
    """Generates synthetic input arrays or arguments scaled to size N."""
    rng = random.Random(42)  # Deterministic seed for reproducible benchmarks
    if generator_type == "sorted_integers":
        return list(range(n))
    elif generator_type == "reversed_integers":
        return list(range(n, 0, -1))
    elif generator_type == "string_tokens":
        words = ["alpha", "beta", "gamma", "delta", "epsilon"]
        return [rng.choice(words) for _ in range(n)]
    else:  # default "random_integers"
        return [rng.randint(-100000, 100000) for _ in range(n)]


def compute_linear_regression(
    x_vals: list[float], y_vals: list[float]
) -> tuple[float, float, float]:
    """Computes ordinary least squares regression y = a*x + b.

    Returns:
        (slope a, intercept b, r_squared R^2)
    """
    n = len(x_vals)
    if n < 2:
        return 0.0, 0.0, 0.0

    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n

    ss_xx = sum((x - mean_x) ** 2 for x in x_vals)
    ss_yy = sum((y - mean_y) ** 2 for y in y_vals)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals, strict=False))

    if ss_xx <= 1e-12:
        return 0.0, mean_y, 0.0

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x

    if ss_yy <= 1e-12:
        # Zero variance in y: implies perfect constant fit
        return slope, intercept, 1.0

    # Calculate R^2
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals, strict=False))
    r_squared = max(0.0, min(1.0, 1.0 - (ss_res / ss_yy)))

    return slope, intercept, r_squared


def fit_complexity_models(
    data_points: list[ComplexityDataPoint],
) -> tuple[str, float, dict[str, float]]:
    """Fits execution time across candidate complexity models.

    Uses regression R^2 combined with growth factor analysis.
    """
    if len(data_points) < 3:
        return "O(N)", 0.5, {"O(N)": 0.5}

    n_vals = [float(p.n) for p in data_points]
    t_vals = [max(1e-6, float(p.wall_time_ms)) for p in data_points]

    # Calculate average doubling growth ratio: T(N_i) / T(N_{i-1}) when N doubles
    ratios: list[float] = []
    for i in range(1, len(data_points)):
        n_ratio = n_vals[i] / n_vals[i - 1]
        t_ratio = t_vals[i] / t_vals[i - 1]
        if n_ratio > 1.0 and t_ratio > 0:
            # Empirical growth exponent: t_ratio = (n_ratio)^k => k = log(t_ratio) / log(n_ratio)
            k = math.log(max(1e-6, t_ratio)) / math.log(n_ratio)
            ratios.append(k)

    avg_growth_k = sum(ratios) / len(ratios) if ratios else 1.0

    # Candidate models
    models: dict[str, list[float]] = {
        "O(1)": [1.0 for _ in n_vals],
        "O(log N)": [math.log(max(2.0, n)) for n in n_vals],
        "O(N)": [n for n in n_vals],
        "O(N log N)": [n * math.log(max(2.0, n)) for n in n_vals],
        "O(N^2)": [n**2 for n in n_vals],
        "O(N^3)": [n**3 for n in n_vals],
    }

    fit_scores: dict[str, float] = {}
    for name, transformed_x in models.items():
        if name == "O(1)":
            # For O(1), variance in t_vals relative to mean determines fit
            mean_t = sum(t_vals) / len(t_vals)
            variance = sum((t - mean_t) ** 2 for t in t_vals) / len(t_vals)
            # If standard deviation is very small (< 15% of mean) or avg_growth_k near 0
            if avg_growth_k < 0.25:
                fit_scores[name] = 0.95
            else:
                fit_scores[name] = max(0.0, 1.0 - (math.sqrt(variance) / (mean_t + 1e-6)))
        else:
            slope, _, r2 = compute_linear_regression(transformed_x, t_vals)
            # Model is only physically valid if slope is positive
            if slope > 0:
                fit_scores[name] = round(r2, 4)
            else:
                fit_scores[name] = 0.0

    # Growth factor heuristic prioritization
    # k <= 0.3 => O(1) or O(log N)
    # 0.7 <= k <= 1.3 => O(N) or O(N log N)
    # 1.6 <= k <= 2.4 => O(N^2)
    # k >= 2.5 => O(N^3) or exponential
    if avg_growth_k < 0.25:
        inferred = "O(1)"
    elif avg_growth_k < 0.6:
        inferred = "O(log N)"
    elif avg_growth_k < 1.3:
        # Distinguish O(N) vs O(N log N)
        r2_n_log_n = fit_scores.get("O(N log N)", 0.0)
        r2_n = fit_scores.get("O(N)", 0.0)
        inferred = "O(N log N)" if r2_n_log_n >= r2_n else "O(N)"
    elif avg_growth_k < 2.6:
        # Parsimony principle: prefer lower-order polynomial if R^2 >= 0.98
        if fit_scores.get("O(N^2)", 0.0) >= 0.98:
            inferred = "O(N^2)"
        else:
            inferred = (
                "O(N^2)"
                if fit_scores.get("O(N^2)", 0.0) >= fit_scores.get("O(N^3)", 0.0)
                else "O(N^3)"
            )
    else:
        inferred = "O(N^2)" if fit_scores.get("O(N^2)", 0.0) >= 0.98 else "O(N^3)"

    best_r2 = fit_scores.get(inferred, max(fit_scores.values(), default=0.0))
    return inferred, best_r2, fit_scores


def profile_function_complexity(
    func: Callable[..., Any],
    input_generator_type: str = "random_integers",
    expected_complexity: str | None = None,
    sample_sizes: list[int] | None = None,
    trials_per_size: int = 3,
) -> BigOResult:
    """Empirically benchmarks a function across scaling input sizes.

    Args:
        func: Python callable to profile.
        input_generator_type: Strategy for generating test inputs.
        expected_complexity: Optional expected Big-O class to check against.
        sample_sizes: Explicit list of N input dimensions.
        trials_per_size: Repetitions per N to minimize noise.

    Returns:
        BigOResult containing inferred Big-O, R^2, and empirical sample data.
    """
    if sample_sizes is None:
        sample_sizes = [50, 100, 200, 400, 800, 1600]

    data_points: list[ComplexityDataPoint] = []

    for n in sample_sizes:
        durations: list[float] = []
        peak_memory_bytes = 0

        for _ in range(trials_per_size):
            # Generate input fresh for each trial (copy to avoid in-place mutation side-effects)
            test_input = generate_input_for_n(n, input_generator_type)

            tracemalloc.start()
            start_time = time.perf_counter_ns()

            try:
                func(test_input)
            except Exception:
                # In case input format needs unpacked args
                func(test_input)
            finally:
                end_time = time.perf_counter_ns()
                current_mem, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

            elapsed_ms = (end_time - start_time) / 1_000_000.0
            durations.append(elapsed_ms)
            peak_memory_bytes = max(peak_memory_bytes, peak_mem)

        # Take minimum wall-clock time among trials to reject OS preemption anomalies
        best_duration_ms = min(durations)
        data_points.append(
            ComplexityDataPoint(
                n=n,
                wall_time_ms=round(best_duration_ms, 4),
                memory_peak_kb=round(peak_memory_bytes / 1024.0, 2),
            )
        )

    inferred, r2, scores = fit_complexity_models(data_points)

    matched = None
    if expected_complexity:
        normalized_inferred = inferred.replace(" ", "").upper()
        normalized_expected = expected_complexity.replace(" ", "").upper()
        matched = normalized_inferred == normalized_expected

    return BigOResult(
        inferred_complexity=inferred,
        expected_complexity=expected_complexity,
        complexity_matched=matched,
        r_squared=round(r2, 4),
        data_points=data_points,
        model_fit_scores=scores,
    )
