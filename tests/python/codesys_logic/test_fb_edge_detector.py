"""
Unit Tests — Edge Detector (Python Reference Model)
"""

import pytest
from .fb_edge_detector import EdgeDetector


class TestRisingEdge:
    def test_fires_once_on_0_to_1(self):
        ed = EdgeDetector()
        ed.execute(False)  # First scan, sets prev
        ed.execute(True)   # 0→1 = rising
        assert ed.rising is True
        assert ed.falling is False

    def test_does_not_fire_on_steady_high(self):
        ed = EdgeDetector()
        ed.execute(False)
        ed.execute(True)   # Rising fires
        assert ed.rising is True
        ed.execute(True)   # Still high — no edge
        assert ed.rising is False

    def test_fires_again_after_toggle(self):
        ed = EdgeDetector()
        ed.execute(False)
        ed.execute(True)  # Rising
        ed.execute(False)  # Falling
        ed.execute(True)   # Rising again
        assert ed.rising is True


class TestFallingEdge:
    def test_fires_once_on_1_to_0(self):
        ed = EdgeDetector()
        ed.execute(True)   # First scan
        ed.execute(False)  # 1→0 = falling
        assert ed.falling is True
        assert ed.rising is False

    def test_does_not_fire_on_steady_low(self):
        ed = EdgeDetector()
        ed.execute(True)
        ed.execute(False)  # Falling fires
        assert ed.falling is True
        ed.execute(False)  # Still low — no edge
        assert ed.falling is False

    def test_fires_again_after_toggle(self):
        ed = EdgeDetector()
        ed.execute(True)
        ed.execute(False)  # Falling
        ed.execute(True)   # Rising
        ed.execute(False)  # Falling again
        assert ed.falling is True


class TestSteadyState:
    def test_no_edge_on_steady_false(self):
        ed = EdgeDetector()
        ed.execute(False)
        for _ in range(10):
            ed.execute(False)
        assert ed.rising is False
        assert ed.falling is False

    def test_no_edge_on_steady_true(self):
        ed = EdgeDetector()
        ed.execute(True)
        for _ in range(10):
            ed.execute(True)
        assert ed.rising is False
        assert ed.falling is False


class TestBothEdges:
    def test_toggle_fires_both(self):
        ed = EdgeDetector()
        ed.execute(False)   # First scan
        ed.execute(True)    # Rising
        assert ed.rising is True
        assert ed.falling is False
        ed.execute(False)   # Falling
        assert ed.rising is False
        assert ed.falling is True

    def test_rapid_toggle(self):
        ed = EdgeDetector()
        ed.execute(False)
        results_rising = []
        results_falling = []
        sequence = [True, False, True, False, True]
        for s in sequence:
            ed.execute(s)
            results_rising.append(ed.rising)
            results_falling.append(ed.falling)
        assert results_rising == [True, False, True, False, True]
        assert results_falling == [False, True, False, True, False]


class TestReset:
    def test_reset_clears_state(self):
        ed = EdgeDetector()
        ed.execute(True)
        ed.execute(False)
        assert ed.falling is True
        ed.reset()
        assert ed.rising is False
        assert ed.falling is False
