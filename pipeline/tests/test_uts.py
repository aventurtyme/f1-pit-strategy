"""
pipeline/tests/test_uts.py

Unit tests for the UTS computation engine.
No FastF1, no database, no I/O — pure function testing.

Run with:
  pytest pipeline/tests/test_uts.py -v
"""

import pytest
import pandas as pd
import numpy as np

from pipeline.core.uts import (
    compute_ptl,
    compute_uts_raw,
    apply_minmax_stretch,
    classify_strategy,
    compute_uts_for_session,
)
from pipeline.core.config import UTSWeights, UTS_WEIGHTS


# ---------------------------------------------------------------------------
# PTL tests
# ---------------------------------------------------------------------------

class TestComputePTL:

    def test_reactive_stop(self):
        """Small gap, fresh softs behind — PTL should be positive."""
        ptl = compute_ptl(
            gap_behind=5.0,
            tire_age_behind=3,
            compound_behind="SOFT",
            pit_loss=22.0,
        )
        # PTL = 22 - 5 - (3 * 0.065) = 16.805
        assert ptl == pytest.approx(16.805, abs=0.01)
        assert ptl > 0

    def test_proactive_stop(self):
        """Large gap, old hards behind — no threat, PTL negative."""
        ptl = compute_ptl(
            gap_behind=25.0,
            tire_age_behind=10,
            compound_behind="HARD",
            pit_loss=22.0,
        )
        # PTL = 22 - 25 - (10 * 0.034) = -3.34
        assert ptl == pytest.approx(-3.34, abs=0.01)
        assert ptl < 0

    def test_none_compound_falls_back_to_medium(self):
        ptl_none   = compute_ptl(5.0, 10, None,     22.0)
        ptl_medium = compute_ptl(5.0, 10, "MEDIUM",  22.0)
        assert ptl_none == ptl_medium

    def test_unknown_compound_falls_back_to_medium(self):
        ptl = compute_ptl(5.0, 10, "HYPERSOFT", 22.0)
        assert isinstance(ptl, float)

    def test_lead_car_gap_fallback(self):
        """P1 with 40s gap (§3.4 notebook value) → strongly negative PTL."""
        ptl = compute_ptl(gap_behind=40.0, tire_age_behind=0,
                          compound_behind="SOFT", pit_loss=22.0)
        assert ptl < 0

    def test_custom_decay_rates(self):
        custom = {"SOFT": 0.10, "MEDIUM": 0.05, "HARD": 0.01}
        ptl = compute_ptl(5.0, 10, "SOFT", 22.0, decay_rates=custom)
        # PTL = 22 - 5 - (10 * 0.10) = 16.0
        assert ptl == pytest.approx(16.0, abs=0.01)

    def test_higher_pit_loss_increases_ptl(self):
        ptl_high = compute_ptl(5.0, 10, "SOFT", pit_loss=29.0)  # Singapore
        ptl_low  = compute_ptl(5.0, 10, "SOFT", pit_loss=20.0)  # Bahrain
        assert ptl_high > ptl_low


# ---------------------------------------------------------------------------
# Raw UTS score tests
# ---------------------------------------------------------------------------

class TestComputeUTSRaw:

    def test_output_is_float(self):
        score = compute_uts_raw(ptl=10.0, ppd=-2, timing_delta=0.0)
        assert isinstance(score, float)

    def test_high_ptl_high_position_gain_gives_high_raw(self):
        """Reactive stop with position gain → high raw score."""
        score = compute_uts_raw(ptl=15.0, ppd=-3, timing_delta=0.0)
        assert score > 0.6

    def test_negative_ptl_position_loss_gives_low_raw(self):
        """Proactive stop with position loss → low raw score."""
        score = compute_uts_raw(ptl=-10.0, ppd=5, timing_delta=8.0)
        assert score < 0.4

    def test_zero_inputs_gives_mid_range(self):
        """All neutral inputs → score near middle of range."""
        score = compute_uts_raw(ptl=0.0, ppd=0, timing_delta=0.0)
        assert 0.3 < score < 0.7

    def test_timing_clean_inverted(self):
        """Lower timing_delta = better window = higher timing_clean contribution."""
        score_early = compute_uts_raw(ptl=5.0, ppd=0, timing_delta=1.0)
        score_late  = compute_uts_raw(ptl=5.0, ppd=0, timing_delta=7.0)
        assert score_early > score_late

    def test_weights_sum_to_one(self):
        total = round(UTS_WEIGHTS.ptl + UTS_WEIGHTS.ppd + UTS_WEIGHTS.timing, 10)
        assert total == 1.0

    def test_invalid_weights_raise(self):
        with pytest.raises(ValueError, match="must sum to 1.0"):
            UTSWeights(ptl=0.5, ppd=0.4, timing=0.5)

    def test_validated_weights(self):
        """Confirm notebook-validated weights are set correctly."""
        assert UTS_WEIGHTS.ptl    == pytest.approx(0.20,   abs=0.001)
        assert UTS_WEIGHTS.ppd    == pytest.approx(0.5905, abs=0.001)
        assert UTS_WEIGHTS.timing == pytest.approx(0.2095, abs=0.001)


# ---------------------------------------------------------------------------
# Min-max stretch tests
# ---------------------------------------------------------------------------

class TestApplyMinmaxStretch:

    def test_min_maps_to_zero(self):
        scores = pd.Series([1.0, 2.0, 3.0])
        result = apply_minmax_stretch(scores)
        assert result.min() == 0.0

    def test_max_maps_to_100(self):
        scores = pd.Series([1.0, 2.0, 3.0])
        result = apply_minmax_stretch(scores)
        assert result.max() == 100.0

    def test_degenerate_all_same_returns_50(self):
        scores = pd.Series([0.5, 0.5, 0.5])
        result = apply_minmax_stretch(scores)
        assert all(result == 50.0)

    def test_preserves_order(self):
        scores = pd.Series([0.1, 0.5, 0.9])
        result = apply_minmax_stretch(scores)
        assert result.iloc[0] < result.iloc[1] < result.iloc[2]

    def test_output_range_bounded(self):
        scores = pd.Series(np.random.rand(100))
        result = apply_minmax_stretch(scores)
        assert result.min() >= 0.0
        assert result.max() <= 100.0


# ---------------------------------------------------------------------------
# Strategy classification tests
# ---------------------------------------------------------------------------

class TestClassifyStrategy:

    def test_positive_ptl_is_reactive(self):
        assert classify_strategy(5.0) == "reactive"

    def test_zero_ptl_is_neutral(self):
        assert classify_strategy(0.0) == "neutral"

    def test_small_negative_ptl_is_neutral(self):
        assert classify_strategy(-1.5) == "neutral"

    def test_large_negative_ptl_is_proactive(self):
        assert classify_strategy(-5.0) == "proactive"

    def test_boundary_exactly_minus_three(self):
        assert classify_strategy(-3.0) == "proactive"
        assert classify_strategy(-2.99) == "neutral"


# ---------------------------------------------------------------------------
# Batch computation tests
# ---------------------------------------------------------------------------

class TestComputeUTSForSession:

    def _make_pit_stops(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "driver_code":    "VER", "team": "Red Bull Racing",
                "lap": 20, "compound_self": "SOFT", "tire_age_self": 15,
                "gap_behind": 4.5, "compound_behind": "SOFT", "tire_age_behind": 8,
                "position_before": 1, "position_after": 1, "ppd": 0,
                "race_flag": "green", "is_tactical": False, "timing_delta": 2.0,
            },
            {
                "driver_code":    "LEC", "team": "Ferrari",
                "lap": 22, "compound_self": "MEDIUM", "tire_age_self": 17,
                "gap_behind": 12.0, "compound_behind": "MEDIUM", "tire_age_behind": 5,
                "position_before": 3, "position_after": 4, "ppd": 1,
                "race_flag": "sc", "is_tactical": False, "timing_delta": 0.0,
            },
            {
                "driver_code":    "HAM", "team": "Mercedes",
                "lap": 58, "compound_self": "HARD", "tire_age_self": 20,
                "gap_behind": 40.0, "compound_behind": None, "tire_age_behind": 0,
                "position_before": 5, "position_after": 5, "ppd": 0,
                "race_flag": "green", "is_tactical": True, "timing_delta": 0.0,
            },
            {
                "driver_code":    "NOR", "team": "McLaren",
                "lap": 30, "compound_self": "SOFT", "tire_age_self": 20,
                "gap_behind": 3.0, "compound_behind": "SOFT", "tire_age_behind": 5,
                "position_before": 2, "position_after": 2, "ppd": 0,
                "race_flag": "green", "is_tactical": False, "timing_delta": 3.0,
            },
        ])

    def test_sc_stop_gets_no_uts(self):
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        lec = result[result["driver_code"] == "LEC"].iloc[0]
        assert lec["uts"] is None or pd.isna(lec["uts"])

    def test_tactical_stop_gets_no_uts(self):
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        ham = result[result["driver_code"] == "HAM"].iloc[0]
        assert ham["uts"] is None or pd.isna(ham["uts"])

    def test_green_stops_get_uts(self):
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        green_scored = result[
            (result["race_flag"] == "green") &
            (result["is_tactical"] == False)
        ]
        assert green_scored["uts"].notna().all()

    def test_uts_range_0_to_100(self):
        """Min-max stretch must produce scores in 0–100."""
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        scored = result[result["uts"].notna()]["uts"]
        assert scored.min() >= 0.0
        assert scored.max() <= 100.0

    def test_min_max_anchors(self):
        """With ≥2 scoreable stops, min=0 and max=100 must appear."""
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        scored = result[result["uts"].notna()]["uts"]
        assert scored.min() == pytest.approx(0.0,   abs=0.1)
        assert scored.max() == pytest.approx(100.0, abs=0.1)

    def test_ptl_column_present(self):
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        assert "ptl" in result.columns

    def test_strategy_type_values(self):
        result = compute_uts_for_session(self._make_pit_stops(), "bahrain_grand_prix")
        assert set(result["strategy_type"]).issubset({"proactive", "reactive", "neutral"})

    def test_sc_stop_opportunistic_when_position_gained(self):
        stops = self._make_pit_stops()
        stops.loc[stops["driver_code"] == "LEC", "ppd"] = -1
        result = compute_uts_for_session(stops, "bahrain_grand_prix")
        assert result[result["driver_code"] == "LEC"].iloc[0]["is_opportunistic"] == True

    def test_empty_dataframe_returns_empty(self):
        assert compute_uts_for_session(pd.DataFrame(), "bahrain_grand_prix").empty

    def test_unknown_circuit_uses_fallback(self):
        stops = self._make_pit_stops()
        stops = stops[stops["race_flag"] == "green"].copy()
        result = compute_uts_for_session(stops, "unknown_circuit_grand_prix")
        assert not result.empty