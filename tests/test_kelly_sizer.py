import pytest
from core.kelly_sizer import compute_bet_size

def test_zero_edge_returns_zero():
    assert compute_bet_size(0.5, 0.5, 300.0) == 0.0

def test_negative_edge_returns_zero():
    assert compute_bet_size(0.4, 0.5, 300.0) == 0.0

def test_positive_edge_computes_bet():
    result = compute_bet_size(0.6, 0.5, 300.0)
    assert result == pytest.approx(15.0, rel=1e-3)

def test_clamps_to_min_bet():
    result = compute_bet_size(0.501, 0.500, 300.0, min_bet=2.0)
    assert result == 2.0

def test_clamps_to_max_bet_pct():
    result = compute_bet_size(0.95, 0.10, 300.0, max_bet_pct=0.10)
    assert result == pytest.approx(30.0, rel=1e-3)

def test_kelly_fraction_scales_bet():
    small = compute_bet_size(0.6, 0.5, 300.0, kelly_fraction=0.10)
    large = compute_bet_size(0.6, 0.5, 300.0, kelly_fraction=0.50)
    assert large > small

def test_returns_zero_when_full_kelly_non_positive():
    result = compute_bet_size(0.51, 0.99, 300.0)
    assert result == 0.0
