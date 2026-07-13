from __future__ import annotations

import numpy as np


def streaming_triad(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    *,
    scalar: float,
    passes: int,
) -> np.ndarray:
    """Return a + scalar * b + c after repeated streaming passes."""
    result = np.empty_like(a)
    for _ in range(passes):
        np.multiply(b, scalar, out=result)
        result += a
        # BUG: missing result += c
    return result
