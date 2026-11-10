"""Example: Bubble Sort Implementation - Expected Complexity: O(N^2)"""

CODE = """
def bubble_sort(arr):
    arr_copy = list(arr)
    n = len(arr_copy)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr_copy[j] > arr_copy[j + 1]:
                arr_copy[j], arr_copy[j + 1] = arr_copy[j + 1], arr_copy[j]
    return arr_copy
"""

TEST_SUITE = """
def test_bubble_sort_basic():
    assert bubble_sort([64, 34, 25, 12, 22, 11, 90]) == [11, 12, 22, 25, 34, 64, 90]

def test_bubble_sort_empty():
    assert bubble_sort([]) == []

def test_bubble_sort_duplicates():
    assert bubble_sort([3, 1, 2, 3]) == [1, 2, 3, 3]
"""

PAYLOAD = {
    "code": CODE.strip(),
    "test_suite": TEST_SUITE.strip(),
    "entrypoint": "bubble_sort",
    "expected_complexity": "O(N^2)",
    "input_generator_type": "random_integers",
    "timeout_seconds": 10.0,
    "memory_limit_mb": 256,
}
