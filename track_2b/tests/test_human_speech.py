"""The human-speech check's statistics."""

from __future__ import annotations

import numpy as np
import pytest

from isochron import human_speech as hs


def test_kappa_spearman_and_bootstrap() -> None:
    a = np.array([1, 1, 0, 0, 1, 0], bool)
    assert hs.kappa(a, a) == 1.0 and hs.kappa(a, ~a) == pytest.approx(-1.0)
    assert np.isnan(hs.kappa(np.ones(4, bool), np.ones(4, bool)))
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert hs.spearman(x, x ** 3) == pytest.approx(1.0) and hs.pearson(x, 2 * x) == pytest.approx(1.0)
    value, lo, hi = hs.boot(lambda v: float(np.mean(v)), np.arange(100, dtype=float), n=2000)
    assert value == 49.5 and lo < 49.5 < hi and hi - lo < 15
    assert hs.boot(lambda v: float(np.mean(v)), np.arange(10.0), n=50) == hs.boot(lambda v: float(np.mean(v)), np.arange(10.0), n=50)
    assert hs.fmt((-0.05, -0.12, 0.02), signed=True) == "−0.05 [−0.12, +0.02]" and hs.fmt((0.5, 0.4, 0.6), pct=True) == "50.0 [40.0, 60.0]"
