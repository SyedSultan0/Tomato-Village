# ============================================================
# MONITORING COMPARISON ENGINE
# ============================================================
#
# Deterministic comparison between an original HealthReport
# and its linked follow-up HealthReport.
#
# IMPORTANT:
# This engine does NOT:
# - call an LLM
# - recalculate risk
# - decide treatment
# - decide expert escalation
#
# It only reports structured, observable facts.
#
# The comparison is meant to support future layers:
# - Monitoring Decision Engine
# - Escalation Decision Engine
# - RAG
# - LLM explanation
# ============================================================

from datetime import datetime
from typing import Any


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value):
    try:
        if value is None:
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


def _safe_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    return None


def _hours_between(start, end):
    start_dt = _safe_datetime(start)
    end_dt = _safe_datetime(end)

    if start_dt is None or end_dt is None:
        return None

    return round(
        (end_dt - start_dt).total_seconds() / 3600.0,
        2
    )


def _normalize_label(label):
    if not isinstance(label, str):
        return None

    return label.strip().lower()


def _round_or_none(value, digits=4):
    value = _safe_float(value)

    if value is None:
        return None

    return round(value, digits)


# ============================================================
# SNAPSHOT SHAPE
# ============================================================
#
# Caller passes a plain dict for each report:
#
# {
#     "report_id": int,
#     "reported_at": datetime | None,
#     "predicted_class": str | None,
#     "confidence": float | None,
#     "risk_score": float | None,
#     "risk_level": str | None,
#     "risk_engine_version": str | None,
#     "advisory_id": int | None
# }
#
# Keeping inputs as plain dicts means:
# - monitoring_engine.py has zero DB dependency
# - it is trivially unit-testable
# - main.py is the only place that talks to SQLAlchemy
# ============================================================

def _build_snapshot(
    side: dict[str, Any] | None
) -> dict[str, Any]:

    if not side:
        return {
            "report_id": None,
            "reported_at": None,
            "predicted_class": None,
            "confidence": None,
            "risk_score": None,
            "risk_level": None,
            "risk_engine_version": None,
            "advisory_id": None,
        }

    return {
        "report_id":
            side.get("report_id"),

        "reported_at":
            side.get("reported_at"),

        "predicted_class":
            side.get("predicted_class"),

        "confidence":
            _round_or_none(
                side.get("confidence"),
                4
            ),

        "risk_score":
            _round_or_none(
                side.get("risk_score"),
                2
            ),

        "risk_level":
            side.get("risk_level"),

        "risk_engine_version":
            side.get("risk_engine_version"),

        "advisory_id":
            side.get("advisory_id"),
    }


# ============================================================
# OBSERVATION STRING
# ============================================================

def _build_observation(
    previous: dict[str, Any],
    current: dict[str, Any],
    flags: dict[str, Any],
) -> str:
    """
    Build a neutral, non-alarming observation sentence.

    Wording rules:
    - Never imply biological confirmation.
    - Never say "worsened" or "improved".
    - Report risk-level transitions explicitly.
    - Never describe missing data as unchanged.
    """

    if (
        previous["predicted_class"] is None
        or current["predicted_class"] is None
    ):
        return (
            "Comparison is limited because one of the reports "
            "is missing an AI prediction."
        )

    parts = []

    # --------------------------------------------------------
    # Condition
    # --------------------------------------------------------

    if flags["condition_changed"]:

        parts.append(
            f"The latest report shows a different predicted "
            f"condition "
            f"({previous['predicted_class']} → "
            f"{current['predicted_class']})."
        )

    else:

        parts.append(
            f"The predicted condition is unchanged "
            f"({current['predicted_class']})."
        )

    # --------------------------------------------------------
    # Risk category change
    # --------------------------------------------------------
    #
    # Only report this when both risk levels exist.
    # --------------------------------------------------------

    if flags["risk_level_changed"]:

        parts.append(
            f"The environmental risk category moved from "
            f"{previous['risk_level']} to "
            f"{current['risk_level']}."
        )

    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------
    #
    # Only describe increase/decrease/unchanged when both
    # risk scores are actually available.
    # --------------------------------------------------------

    if flags["risk_increased"]:

        parts.append(
            "The environmental risk score has increased."
        )

    elif flags["risk_decreased"]:

        parts.append(
            "The environmental risk score has decreased."
        )

    elif flags["risk_unchanged"]:

        parts.append(
            "The environmental risk score is essentially "
            "unchanged."
        )

    elif flags["risk_comparison_unavailable"]:

        parts.append(
            "Risk comparison is limited because one of the "
            "reports is missing a risk assessment."
        )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    if flags["confidence_increased"]:

        parts.append(
            "AI confidence for the latest report is higher."
        )

    elif flags["confidence_decreased"]:

        parts.append(
            "AI confidence for the latest report is lower, "
            "so the prediction should be treated as less "
            "certain."
        )

    return " ".join(parts)


# ============================================================
# MAIN COMPARISON
# ============================================================

def compare_reports(
    original_report: dict[str, Any],
    follow_up_report: dict[str, Any],
    risk_increase_threshold: float = 10.0,
    risk_decrease_threshold: float = 10.0,
    confidence_change_threshold: float = 0.10,
) -> dict[str, Any]:
    """
    Deterministically compare two reports.

    Inputs:
        original_report:
            Snapshot dict for the original report.

        follow_up_report:
            Snapshot dict for the follow-up report.

    Thresholds:
        risk_increase_threshold:
            Minimum absolute increase in risk_score required
            to mark risk_increased = True.

        risk_decrease_threshold:
            Minimum absolute decrease in risk_score required
            to mark risk_decreased = True.

        confidence_change_threshold:
            Minimum absolute change in confidence required
            to mark confidence_changed = True.

    Returns:
        Structured comparison dict.

    IMPORTANT:
        - Risk score is treated as environmental favorability,
          NOT disease probability.
        - "condition_changed" means the AI prediction label
          changed. It does NOT by itself prove that the crop
          biologically deteriorated or improved.
        - "risk_level_changed" is reported independently of
          the numeric risk delta.
    """

    previous = _build_snapshot(
        original_report
    )

    current = _build_snapshot(
        follow_up_report
    )

    # ========================================================
    # CONDITION CHANGE
    # ========================================================

    prev_label = _normalize_label(
        previous["predicted_class"]
    )

    curr_label = _normalize_label(
        current["predicted_class"]
    )

    if prev_label is None or curr_label is None:

        condition_changed = None

    else:

        condition_changed = (
            prev_label != curr_label
        )

    # ========================================================
    # RISK SCORE DELTA
    # ========================================================

    prev_risk = previous["risk_score"]
    curr_risk = current["risk_score"]

    risk_delta = None
    risk_increased = None
    risk_decreased = None
    risk_unchanged = None
    risk_comparison_unavailable = False

    if (
        prev_risk is not None
        and curr_risk is not None
    ):

        risk_delta = round(
            curr_risk - prev_risk,
            2
        )

        if risk_delta >= risk_increase_threshold:

            risk_increased = True
            risk_decreased = False
            risk_unchanged = False

        elif risk_delta <= -risk_decrease_threshold:

            risk_increased = False
            risk_decreased = True
            risk_unchanged = False

        else:

            risk_increased = False
            risk_decreased = False
            risk_unchanged = True

    else:

        risk_comparison_unavailable = True

    # ========================================================
    # RISK LEVEL CHANGE
    # ========================================================

    prev_level = previous["risk_level"]
    curr_level = current["risk_level"]

    if (
        prev_level is not None
        and curr_level is not None
    ):

        risk_level_changed = (
            prev_level != curr_level
        )

    else:

        risk_level_changed = None

    # ========================================================
    # CONFIDENCE CHANGE
    # ========================================================

    prev_conf = previous["confidence"]
    curr_conf = current["confidence"]

    confidence_delta = None
    confidence_changed = None
    confidence_increased = None
    confidence_decreased = None

    if (
        prev_conf is not None
        and curr_conf is not None
    ):

        confidence_delta = round(
            curr_conf - prev_conf,
            4
        )

        if (
            abs(confidence_delta)
            >= confidence_change_threshold
        ):

            confidence_changed = True

            confidence_increased = (
                confidence_delta > 0
            )

            confidence_decreased = (
                confidence_delta < 0
            )

        else:

            confidence_changed = False
            confidence_increased = False
            confidence_decreased = False

    # ========================================================
    # TIME BETWEEN OBSERVATIONS
    # ========================================================

    time_between_hours = _hours_between(
        previous["reported_at"],
        current["reported_at"],
    )

    # ========================================================
    # FLAGS FOR OBSERVATION BUILDER
    # ========================================================

    flags = {
        "condition_changed":
            bool(condition_changed),

        "risk_increased":
            bool(risk_increased),

        "risk_decreased":
            bool(risk_decreased),

        "risk_unchanged":
            bool(risk_unchanged),

        "risk_level_changed":
            bool(risk_level_changed),

        "risk_comparison_unavailable":
            risk_comparison_unavailable,

        "confidence_increased":
            bool(confidence_increased),

        "confidence_decreased":
            bool(confidence_decreased),
    }

    observation = _build_observation(
        previous,
        current,
        flags,
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "previous": {
            "report_id":
                previous["report_id"],

            "reported_at":
                previous["reported_at"],

            "predicted_class":
                previous["predicted_class"],

            "confidence":
                previous["confidence"],

            "risk_score":
                previous["risk_score"],

            "risk_level":
                previous["risk_level"],

            "risk_engine_version":
                previous["risk_engine_version"],

            "advisory_id":
                previous["advisory_id"],
        },

        "current": {
            "report_id":
                current["report_id"],

            "reported_at":
                current["reported_at"],

            "predicted_class":
                current["predicted_class"],

            "confidence":
                current["confidence"],

            "risk_score":
                current["risk_score"],

            "risk_level":
                current["risk_level"],

            "risk_engine_version":
                current["risk_engine_version"],

            "advisory_id":
                current["advisory_id"],
        },

        "time_between_hours":
            time_between_hours,

        "condition_changed":
            condition_changed,

        "risk_delta":
            risk_delta,

        "risk_increased":
            risk_increased,

        "risk_decreased":
            risk_decreased,

        "risk_unchanged":
            risk_unchanged,

        "risk_level_changed":
            risk_level_changed,

        "confidence_delta":
            confidence_delta,

        "confidence_changed":
            confidence_changed,

        "confidence_increased":
            confidence_increased,

        "confidence_decreased":
            confidence_decreased,

        "thresholds_used": {
            "risk_increase":
                risk_increase_threshold,

            "risk_decrease":
                risk_decrease_threshold,

            "confidence_change":
                confidence_change_threshold,
        },

        "comparison_engine": {
            "name":
                "deterministic-monitoring-comparison",

            "version":
                "1.0.2",
        },

        "observation":
            observation,
    }