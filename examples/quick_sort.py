"""Example: Quick Sort Implementation - Expected Complexity: O(N log N)"""

CODE = """
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
"""

TEST_SUITE = """
def test_sorted():
    assert quick_sort([5, 2, 9, 1, 5, 6]) == [1, 2, 5, 5, 6, 9]

def test_empty():
    assert quick_sort([]) == []

def test_single_element():
    assert quick_sort([42]) == [42]

def test_already_sorted():
    assert quick_sort([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]

def test_reversed():
    assert quick_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]
"""

PAYLOAD = {
    "code": CODE.strip(),
    "test_suite": TEST_SUITE.strip(),
    "entrypoint": "quick_sort",
    "expected_complexity": "O(N log N)",
    "input_generator_type": "random_integers",
    "timeout_seconds": 10.0,
    "memory_limit_mb": 256,
}
