import inspect
import random

from algorithm_lab.sorting import bubble_sort


def test_bubble_sort_sorts_unsorted_values():
    assert bubble_sort([5, 1, 4, 2, 8]) == [1, 2, 4, 5, 8]


def test_bubble_sort_handles_duplicates_and_negatives():
    assert bubble_sort([3, -1, 3, 0, -1]) == [-1, -1, 0, 3, 3]


def test_bubble_sort_does_not_mutate_input():
    values = [4, 2, 1]

    result = bubble_sort(values)

    assert result == [1, 2, 4]
    assert values == [4, 2, 1]


def test_bubble_sort_does_not_delegate_to_builtin_sorting():
    source = inspect.getsource(bubble_sort)

    assert "sorted(" not in source
    assert ".sort(" not in source


def test_bubble_sort_sorts_reference_benchmark_sizes():
    for size in (10_000, 20_000):
        rng = random.Random(20260713 + size)
        values = [rng.randint(-1_000_000, 1_000_000) for _ in range(size)]

        result = bubble_sort(values)

        assert result == sorted(values)
        assert values != result
