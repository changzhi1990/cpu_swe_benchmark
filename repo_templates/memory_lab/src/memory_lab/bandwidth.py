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
    out = np.empty_like(a)
    for _ in range(passes):
        np.multiply(b, scalar, out=out)
        out += a
        # BUG: missing out += c
    return out
