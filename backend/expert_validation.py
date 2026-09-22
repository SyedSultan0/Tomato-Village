# ============================================================
# EXPERT VALIDATION — M5.1
# ============================================================
#
# Append-only expert validation layer over HealthReport.
# ============================================================

from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import (
    AIPrediction,
    Condition,
    ExpertValidation,
    HealthReport,
)


VALID_STATUSES = (
    "CONFIRMED",
    "CORRECTED",
    "REJECTED",
    "INCONCLUSIVE",
)

STATUSES_REQUIRING_CONDITION = ("CONFIRMED", "CORRECTED")
STATUSES_FORBIDDING_CONDITION = ("REJECTED", "INCONCLUSIVE")


def _normalize_condition_name(name: str) -> str:
    return name.strip().lower().replace("_", " ")


def normalize_status(status: str) -> str:
    if not isinstance(status, str):
        raise ValueError("status must be a string.")
    normalized = status.strip().upper()
    if normalized not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. "
            f"Expected one of {list(VALID_STATUSES)}."
        )
    return normalized


def find_condition_by_name(db: Session, condition_name: str):
    if not isinstance(condition_name, str) or not condition_name.strip():
        return None
    target = _normalize_condition_name(condition_name)
    for condition in db.query(Condition).all():
        if _normalize_condition_name(condition.name) == target:
            return condition
    return None


def get_latest_ai_prediction(db: Session, health_report_id: int):
    return (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id == health_report_id)
        .order_by(desc(AIPrediction.created_at))
        .first()
    )


def validate_submission(
    db: Session,
    health_report_id: int,
    status: str,
    confirmed_condition_name: str | None,
) -> dict[str, Any]:

    report = (
        db.query(HealthReport)
        .filter(HealthReport.id == health_report_id)
        .first()
    )

    if not report:
        return {
            "ok": False, "error": "Health report not found.",
            "status": None, "confirmed_condition": None,
            "ai_prediction": None,
        }

    try:
        normalized_status = normalize_status(status)
    except ValueError as e:
        return {
            "ok": False, "error": str(e), "status": None,
            "confirmed_condition": None, "ai_prediction": None,
        }

    ai_prediction = get_latest_ai_prediction(db, health_report_id)

    if normalized_status in STATUSES_REQUIRING_CONDITION:

        if not confirmed_condition_name:
            return {
                "ok": False,
                "error": f"status='{normalized_status}' requires 'confirmed_condition'.",
                "status": normalized_status, "confirmed_condition": None,
                "ai_prediction": ai_prediction,
            }

        condition = find_condition_by_name(db, confirmed_condition_name)

        if not condition:
            return {
                "ok": False,
                "error": f"Unknown condition '{confirmed_condition_name}'.",
                "status": normalized_status, "confirmed_condition": None,
                "ai_prediction": ai_prediction,
            }

        if normalized_status == "CONFIRMED":

            if not ai_prediction:
                return {
                    "ok": False,
                    "error": "Cannot CONFIRM a report that has no AI prediction.",
                    "status": normalized_status,
                    "confirmed_condition": None, "ai_prediction": None,
                }

            ai_condition = find_condition_by_name(
                db, ai_prediction.predicted_class
            )

            if not ai_condition:
                return {
                    "ok": False,
                    "error": (
                        f"AI predicted condition "
                        f"'{ai_prediction.predicted_class}' does not "
                        f"resolve to a known Condition."
                    ),
                    "status": normalized_status,
                    "confirmed_condition": None,
                    "ai_prediction": ai_prediction,
                }

            if ai_condition.id != condition.id:
                return {
                    "ok": False,
                    "error": (
                        f"status='CONFIRMED' requires the condition "
                        f"to match the AI prediction "
                        f"('{ai_condition.name}'). Use "
                        f"status='CORRECTED' if the expert disagrees."
                    ),
                    "status": normalized_status,
                    "confirmed_condition": None,
                    "ai_prediction": ai_prediction,
                }

        if normalized_status == "CORRECTED":

            if not ai_prediction:
                return {
                    "ok": False,
                    "error": "Cannot CORRECT a report that has no AI prediction.",
                    "status": normalized_status,
                    "confirmed_condition": None, "ai_prediction": None,
                }

            ai_condition = find_condition_by_name(
                db, ai_prediction.predicted_class
            )

            if ai_condition and ai_condition.id == condition.id:
                return {
                    "ok": False,
                    "error": (
                        f"status='CORRECTED' requires a condition "
                        f"different from the AI prediction "
                        f"('{ai_condition.name}'). Use "
                        f"status='CONFIRMED' if the expert agrees."
                    ),
                    "status": normalized_status,
                    "confirmed_condition": None,
                    "ai_prediction": ai_prediction,
                }

        return {
            "ok": True, "error": None,
            "status": normalized_status,
            "confirmed_condition": condition,
            "ai_prediction": ai_prediction,
        }

    if normalized_status in STATUSES_FORBIDDING_CONDITION:

        if confirmed_condition_name:
            return {
                "ok": False,
                "error": f"status='{normalized_status}' does not accept 'confirmed_condition'.",
                "status": normalized_status,
                "confirmed_condition": None,
                "ai_prediction": ai_prediction,
            }

        return {
            "ok": True, "error": None,
            "status": normalized_status,
            "confirmed_condition": None,
            "ai_prediction": ai_prediction,
        }

    return {
        "ok": False, "error": "Unhandled status.",
        "status": normalized_status,
        "confirmed_condition": None, "ai_prediction": ai_prediction,
    }


def serialize_validation(db: Session, validation: ExpertValidation):
    confirmed_condition = None
    if validation.confirmed_condition_id:
        confirmed_condition = (
            db.query(Condition)
            .filter(Condition.id == validation.confirmed_condition_id)
            .first()
        )

    return {
        "id": validation.id,
        "health_report_id": validation.health_report_id,
        "expert_id": validation.expert_id,
        "status": validation.status,
        "confirmed_condition_id": validation.confirmed_condition_id,
        "confirmed_condition_name": (
            confirmed_condition.name if confirmed_condition else None
        ),
        "comments": validation.comments,
        "validated_at": validation.validated_at,
    }