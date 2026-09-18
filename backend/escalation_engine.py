# ============================================================
# ESCALATION DECISION ENGINE
# ============================================================
#
# Deterministic decision layer built on top of:
# - current AI prediction
# - current environmental risk
# - monitoring comparison
#
# IMPORTANT:
#
# This engine does NOT:
# - call an LLM
# - diagnose disease
# - recalculate risk
# - prescribe treatment
# - determine pesticide dosage
#
# It only determines whether the case requires:
# - ROUTINE
# - MONITOR
# - ATTENTION
# - EXPERT_REVIEW
#
# The decision is based on explicit, auditable rules.
# ============================================================

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


def _normalize_level(level):
    if not isinstance(level, str):
        return None

    return level.strip().upper()


def _normalize_confidence(value):
    value = _safe_float(value)

    if value is None:
        return None

    return round(value, 4)


# ============================================================
# ESCALATION DECISION
# ============================================================

def decide_escalation(
    current_report: dict[str, Any],
    comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Determine the appropriate escalation level for the
    current crop health report.

    Inputs
    ------

    current_report:
        Plain dictionary containing the current observation.

        Expected fields:

        {
            "report_id": int | None,
            "predicted_class": str | None,
            "confidence": float | None,
            "risk_score": float | None,
            "risk_level": str | None
        }

    comparison:
        Optional result returned by monitoring_engine.compare_reports().

    Returns
    -------

    {
        "decision": str,
        "reasons": list[str],
        "triggered_rules": list[str],
        "engine": {
            "name": str,
            "version": str
        }
    }

    IMPORTANT:

    This engine does not determine biological deterioration.

    "ATTENTION" or "EXPERT_REVIEW" means the configured
    decision rules have identified a signal that deserves
    additional attention.

    It does not mean the AI prediction is biologically
    confirmed.
    """

    # ========================================================
    # CURRENT OBSERVATION
    # ========================================================

    report_id = current_report.get(
        "report_id"
    )

    predicted_class = current_report.get(
        "predicted_class"
    )

    confidence = _normalize_confidence(
        current_report.get("confidence")
    )

    risk_score = _safe_float(
        current_report.get("risk_score")
    )

    risk_level = _normalize_level(
        current_report.get("risk_level")
    )

    # ========================================================
    # RESULT CONTAINERS
    # ========================================================

    reasons = []
    triggered_rules = []

    # ========================================================
    # RULE FLAGS
    # ========================================================

    critical_risk = (
        risk_level == "CRITICAL"
    )

    high_risk = (
        risk_level == "HIGH"
    )

    low_confidence = (
        confidence is not None
        and confidence < 0.50
    )

    medium_confidence = (
        confidence is not None
        and 0.50 <= confidence < 0.70
    )

    condition_changed = False
    risk_increased = False

    if comparison:

        condition_changed = (
            comparison.get(
                "condition_changed"
            )
            is True
        )

        risk_increased = (
            comparison.get(
                "risk_increased"
            )
            is True
        )

    # ========================================================
    # EXPERT REVIEW RULES
    # ========================================================
    #
    # These rules have the highest priority.
    # ========================================================

    if critical_risk:

        triggered_rules.append(
            "CRITICAL_RISK"
        )

        reasons.append(
            "The current environmental risk category "
            "is CRITICAL."
        )

    if low_confidence:

        triggered_rules.append(
            "LOW_AI_CONFIDENCE"
        )

        reasons.append(
            "AI confidence for the current prediction "
            "is below 50%."
        )

    # ========================================================
    # ATTENTION RULES
    # ========================================================

    if high_risk:

        triggered_rules.append(
            "HIGH_RISK"
        )

        reasons.append(
            "The current environmental risk category "
            "is HIGH."
        )

    if condition_changed:

        triggered_rules.append(
            "CONDITION_CHANGED"
        )

        reasons.append(
            "The predicted condition changed between "
            "the previous and current observation."
        )

    if risk_increased:

        triggered_rules.append(
            "RISK_INCREASED"
        )

        reasons.append(
            "The environmental risk score increased "
            "by the configured monitoring threshold."
        )

    # ========================================================
    # MEDIUM-CONFIDENCE + CONCERNING SIGNAL
    # ========================================================

    if (
        medium_confidence
        and (
            high_risk
            or critical_risk
            or condition_changed
            or risk_increased
        )
    ):

        triggered_rules.append(
            "MEDIUM_CONFIDENCE_CONCERNING_SIGNAL"
        )

        reasons.append(
            "AI confidence is between 50% and 70% "
            "while another configured concern signal "
            "is present."
        )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    if (
        critical_risk
        or low_confidence
    ):

        decision = "EXPERT_REVIEW"

    elif (
        high_risk
        or condition_changed
        or risk_increased
    ):

        decision = "ATTENTION"

    elif (
        medium_confidence
    ):

        decision = "MONITOR"

        triggered_rules.append(
            "MEDIUM_AI_CONFIDENCE"
        )

        reasons.append(
            "AI confidence is between 50% and 70%; "
            "continued monitoring is recommended."
        )

    else:

        decision = "ROUTINE"

        triggered_rules.append(
            "NO_ESCALATION_SIGNAL"
        )

        reasons.append(
            "No configured escalation signal was detected."
        )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "decision": decision,

        "report_id": report_id,

        "predicted_class": predicted_class,

        "confidence": confidence,

        "risk_score": (
            round(risk_score, 2)
            if risk_score is not None
            else None
        ),

        "risk_level": risk_level,

        "reasons": reasons,

        "triggered_rules": triggered_rules,

        "engine": {
            "name":
                "deterministic-escalation-engine",

            "version":
                "1.0.0",
        },
    }