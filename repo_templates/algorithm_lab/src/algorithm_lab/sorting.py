from __future__ import annotations


def bubble_sort(values: list[int]) -> list[int]:
    """Return a sorted copy of `values` using bubble sort."""
    result = list(values)
    n = len(result)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if result[j] < result[j + 1]:
                result[j], result[j + 1] = result[j + 1], result[j]
                swapped = True
        if not swapped:
            break
    return result
