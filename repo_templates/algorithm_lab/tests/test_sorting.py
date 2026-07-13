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
