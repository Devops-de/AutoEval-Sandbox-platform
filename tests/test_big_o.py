"""Unit tests for Empirical Big-O Profiler and Curve Fitting."""

from autoeval.benchmarking.big_o_profiler import (
    compute_linear_regression,
    fit_complexity_models,
    generate_input_for_n,
    profile_function_complexity,
)
from autoeval.api.schemas import ComplexityDataPoint


def test_linear_regression_perfect_fit():
    # y = 2*x + 1
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [3.0, 5.0, 7.0, 9.0, 11.0]
    slope, intercept, r2 = compute_linear_regression(x, y)
    assert round(slope, 2) == 2.0
    assert round(intercept, 2) == 1.0
    assert round(r2, 4) == 1.0


def test_fit_linear_complexity_model():
    # Scaling linearly
    data = [
        ComplexityDataPoint(n=100, wall_time_ms=1.0),
        ComplexityDataPoint(n=200, wall_time_ms=2.0),
        ComplexityDataPoint(n=400, wall_time_ms=4.0),
        ComplexityDataPoint(n=800, wall_time_ms=8.0),
    ]
    inferred, r2, scores = fit_complexity_models(data)
    assert inferred in ("O(N)", "O(N log N)")
    assert r2 > 0.9


def test_fit_quadratic_complexity_model():
    # Scaling quadratically: N doubles, T quadruples
    data = [
        ComplexityDataPoint(n=100, wall_time_ms=1.0),
        ComplexityDataPoint(n=200, wall_time_ms=4.0),
        ComplexityDataPoint(n=400, wall_time_ms=16.0),
        ComplexityDataPoint(n=800, wall_time_ms=64.0),
    ]
    inferred, r2, scores = fit_complexity_models(data)
    assert inferred == "O(N^2)"
    assert r2 > 0.9


def test_profile_constant_function():
    def get_first(arr):
        return arr[0] if arr else None

    result = profile_function_complexity(
        func=get_first,
        sample_sizes=[50, 100, 200, 400],
        trials_per_size=2,
    )
    assert result.inferred_complexity in ("O(1)", "O(log N)")


def test_profile_linear_function():
    def linear_sum(arr):
        tot = 0
        for x in arr:
            tot += x
        return tot

    result = profile_function_complexity(
        func=linear_sum,
        sample_sizes=[200, 500, 1000, 2000, 4000],
        trials_per_size=2,
    )
    assert result.inferred_complexity in ("O(N)", "O(N log N)")


def test_input_generator_variations():
    random_ints = generate_input_for_n(50, "random_integers")
    assert len(random_ints) == 50
    assert isinstance(random_ints[0], int)

    sorted_ints = generate_input_for_n(30, "sorted_integers")
    assert sorted_ints == list(range(30))

    reversed_ints = generate_input_for_n(20, "reversed_integers")
    assert reversed_ints[0] == 20
    assert reversed_ints[-1] == 1
