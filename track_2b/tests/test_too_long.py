"""Too long / not too long: the classification at the ±10 % edge."""

from isochron import too_long


def test_classify() -> None:
    assert too_long.classify("1.1000", True) == (0, 1)  # exactly +10 % is not too long
    assert too_long.classify("1.1001", True) == (1, 0)
    assert too_long.classify("0.5", True) == (0, 1)  # short is tolerable
    assert too_long.classify("", False) == (0, 0) and too_long.classify("1.5", False) == (0, 0)
