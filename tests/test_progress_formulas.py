"""
Unit tests for the progress score formula function.
Import it directly — no HTTP needed.
"""
import pytest
from datetime import date


# Import your actual formula function
# Adjust the import path to match your project
from routers.goals_router import compute_progress_score


def test_min_uom_full_achievement():
    """Actual equals target → 100%."""
    score = compute_progress_score("min", target=1000, actual=1000)
    assert score == pytest.approx(1.0)


def test_min_uom_over_achievement():
    """Actual exceeds target → score > 1."""
    score = compute_progress_score("min", target=1000, actual=1200)
    assert score > 1.0


def test_min_uom_partial():
    """Actual is 80% of target → score ≈ 0.8."""
    score = compute_progress_score("min", target=1000, actual=800)
    assert score == pytest.approx(0.8)


def test_min_uom_zero_target():
    """Zero target must not crash (division by zero guard)."""
    score = compute_progress_score("min", target=0, actual=100)
    assert score == 0 or score is not None


def test_max_uom_on_target():
    """Lower is better — actual equals target → 100%."""
    score = compute_progress_score("max", target=48, actual=48)
    assert score == pytest.approx(1.0)


def test_max_uom_better_than_target():
    """Actual below target (better) → score > 1."""
    score = compute_progress_score("max", target=48, actual=24)
    assert score > 1.0


def test_max_uom_worse_than_target():
    """Actual above target (worse) → score < 1."""
    score = compute_progress_score("max", target=48, actual=72)
    assert score < 1.0


def test_max_uom_zero_actual():
    """Zero actual must not crash."""
    score = compute_progress_score("max", target=48, actual=0)
    assert score == 0 or score is not None


def test_timeline_uom_on_time():
    """Completed on or before deadline → 1.0."""
    score = compute_progress_score(
        "timeline", target=0, actual=0,
        target_date=date(2025, 9, 30),
        actual_date=date(2025, 9, 15)
    )
    assert score == pytest.approx(1.0)


def test_timeline_uom_exactly_on_deadline():
    score = compute_progress_score(
        "timeline", target=0, actual=0,
        target_date=date(2025, 9, 30),
        actual_date=date(2025, 9, 30)
    )
    assert score == pytest.approx(1.0)


def test_timeline_uom_late():
    """Completed after deadline → score < 1.0."""
    score = compute_progress_score(
        "timeline", target=0, actual=0,
        target_date=date(2025, 9, 30),
        actual_date=date(2025, 10, 15)
    )
    assert score < 1.0


def test_timeline_uom_no_actual_date():
    """Not yet completed → 0.0."""
    score = compute_progress_score(
        "timeline", target=0, actual=0,
        target_date=date(2025, 9, 30),
        actual_date=None
    )
    assert score == 0.0


def test_zero_uom_achieved():
    """Zero incidents → score 1.0."""
    score = compute_progress_score("zero", target=0, actual=0)
    assert score == pytest.approx(1.0)


def test_zero_uom_not_achieved():
    """Non-zero actual → score 0.0."""
    score = compute_progress_score("zero", target=0, actual=3)
    assert score == pytest.approx(0.0)
