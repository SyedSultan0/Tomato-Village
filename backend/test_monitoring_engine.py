# ============================================================
# UNIT TESTS — MONITORING COMPARISON ENGINE
# ============================================================
#
# Pure deterministic tests.
# No database. No network. No FastAPI.
#
# Run from backend/:
#     pytest test_monitoring_engine.py -v
# ============================================================

from datetime import datetime, timedelta

from monitoring_engine import compare_reports


# ============================================================
# HELPERS
# ============================================================

def _report(
    report_id,
    predicted_class,
    confidence,
    risk_score,
    risk_level,
    reported_at=None,
):
    """
    Small helper to build a report snapshot.

    Keeps tests readable so each case only shows the
    differences that matter.
    """

    if reported_at is None:
        reported_at = datetime(2026, 9, 15, 14, 0, 0)

    return {
        "report_id": report_id,
        "reported_at": reported_at,
        "predicted_class": predicted_class,
        "confidence": confidence,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_engine_version": "rule-engine-v1",
        "advisory_id": report_id,
    }


# ============================================================
# CASE 1 — MISSING DATA ON ONE SIDE
# ============================================================

def test_missing_risk_on_original():
    original = _report(
        report_id=1,
        predicted_class="Healthy",
        confidence=0.60,          # <-- changed: was 0.92
        risk_score=None,
        risk_level=None,
    )

    follow_up = _report(
        report_id=9,
        predicted_class="Potassium Deficiency",
        confidence=0.997,
        risk_score=71.5,
        risk_level="HIGH",
    )

    result = compare_reports(original, follow_up)

    # Condition comparison still works
    assert result["condition_changed"] is True

    # Risk comparison is unavailable
    assert result["risk_delta"] is None
    assert result["risk_increased"] is None
    assert result["risk_decreased"] is None
    assert result["risk_level_changed"] is None

    # Confidence comparison still works
    # 0.60 -> 0.997 = +0.397, well above the 0.10 threshold
    assert result["confidence_changed"] is True
    assert result["confidence_increased"] is True
    assert result["confidence_decreased"] is False

    # Observation should not crash, should mention limited data
    assert isinstance(result["observation"], str)
    assert len(result["observation"]) > 0
# ============================================================
# CASE 2 — RISK INCREASE ABOVE THRESHOLD
# ============================================================

def test_risk_increase_above_threshold():
    original = _report(
        report_id=1,
        predicted_class="Late Blight",
        confidence=0.90,
        risk_score=20.0,
        risk_level="LOW",
    )

    follow_up = _report(
        report_id=9,
        predicted_class="Late Blight",
        confidence=0.90,
        risk_score=72.0,
        risk_level="HIGH",
    )

    result = compare_reports(original, follow_up)

    assert result["risk_delta"] == 52.0
    assert result["risk_increased"] is True
    assert result["risk_decreased"] is False
    assert result["risk_unchanged"] is False
    assert result["risk_level_changed"] is True

    assert "increased" in result["observation"].lower()
    assert "moved from LOW to HIGH" in result["observation"]


# ============================================================
# CASE 3 — RISK DECREASE BELOW THRESHOLD
# ============================================================

def test_risk_decrease_below_threshold():
    original = _report(
        report_id=1,
        predicted_class="Late Blight",
        confidence=0.90,
        risk_score=72.0,
        risk_level="HIGH",
    )

    follow_up = _report(
        report_id=9,
        predicted_class="Late Blight",
        confidence=0.90,
        risk_score=20.0,
        risk_level="LOW",
    )

    result = compare_reports(original, follow_up)

    assert result["risk_delta"] == -52.0
    assert result["risk_decreased"] is True
    assert result["risk_increased"] is False
    assert result["risk_unchanged"] is False
    assert result["risk_level_changed"] is True

    assert "decreased" in result["observation"].lower()
    assert "moved from HIGH to LOW" in result["observation"]


# ============================================================
# CASE 4 — CONDITION CHANGE, RISK ESSENTIALLY UNCHANGED
# ============================================================

def test_condition_changed_risk_unchanged():
    original = _report(
        report_id=1,
        predicted_class="Healthy",
        confidence=0.91,
        risk_score=0.0,
        risk_level="LOW",
    )

    follow_up = _report(
        report_id=9,
        predicted_class="Potassium Deficiency",
        confidence=0.90,
        risk_score=5.0,
        risk_level="LOW",
    )

    result = compare_reports(original, follow_up)

    assert result["condition_changed"] is True
    assert result["risk_delta"] == 5.0
    assert result["risk_increased"] is False
    assert result["risk_unchanged"] is True
    assert result["risk_level_changed"] is False

    observation = result["observation"].lower()
    assert "different predicted condition" in observation
    assert "essentially unchanged" in observation


# ============================================================
# CASE 5 — BOUNDARY CROSSING (49 -> 51)
# ============================================================
#
# This is the case that motivated the v1.1 fix.
#
# Raw delta is only +2, below the 10-point threshold,
# so numeric risk_increased is False.
#
# But the level moved from MODERATE to HIGH.
# The observation must surface that explicitly.
# ============================================================

def test_boundary_crossing_small_delta_level_change():
    original = _report(
        report_id=1,
        predicted_class="Late Blight",
        confidence=0.90,
        risk_score=49.0,
        risk_level="MODERATE",
    )

    follow_up = _report(
        report_id=9,
        predicted_class="Late Blight",
        confidence=0.90,
        risk_score=51.0,
        risk_level="HIGH",
    )

    result = compare_reports(original, follow_up)

    assert result["risk_delta"] == 2.0
    assert result["risk_increased"] is False
    assert result["risk_decreased"] is False
    assert result["risk_unchanged"] is True
    assert result["risk_level_changed"] is True

    observation = result["observation"]

    # The important part: level transition must be visible.
    assert "moved from MODERATE to HIGH" in observation

    # Neutral wording — no interpretation.
    assert "worsened" not in observation.lower()
    assert "improved" not in observation.lower()

    # And we must NOT also print "essentially unchanged",
    # because that would contradict the level-change sentence.
    assert "essentially unchanged" not in observation.lower()