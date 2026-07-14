import inspect

import numpy as np

from memory_lab.bandwidth import streaming_triad


ELEMENTS = 16_000_000
PASSES = 256
SCALAR = 1.25


def make_arrays(elements: int):
    index = np.arange(elements, dtype=np.float64)
    a = (index % 97) * 0.5
    b = (index % 193) * 0.25
    c = (index % 389) * 0.125
    return a, b, c


def test_streaming_triad_small_correctness():
    a = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    b = np.array([4.0, 5.0, 6.0], dtype=np.float64)
    c = np.array([7.0, 8.0, 9.0], dtype=np.float64)

    result = streaming_triad(a, b, c, scalar=SCALAR, passes=2)

    assert np.allclose(result, a + SCALAR * b + c)


def test_streaming_triad_does_not_mutate_inputs():
    a, b, c = make_arrays(1024)
    original = (a.copy(), b.copy(), c.copy())

    streaming_triad(a, b, c, scalar=SCALAR, passes=4)

    assert np.array_equal(a, original[0])
    assert np.array_equal(b, original[1])
    assert np.array_equal(c, original[2])


def test_streaming_triad_uses_numpy_vectorized_streaming():
    source = inspect.getsource(streaming_triad)

    assert "np.multiply" in source
    assert "result +=" in source
    assert "for i in range" not in source
    assert "while " not in source


def test_streaming_triad_large_bandwidth_validation():
    a, b, c = make_arrays(ELEMENTS)

    result = streaming_triad(a, b, c, scalar=SCALAR, passes=PASSES)

    assert np.allclose(result, a + SCALAR * b + c)
