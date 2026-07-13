from __future__ import annotations


def bubble_sort(arr: list[int]) -> list[int]:
    """Return a sorted copy of `arr` using bubble sort."""
    arr = list(arr)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] < arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
