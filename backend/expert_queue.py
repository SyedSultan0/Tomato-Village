# ============================================================
# EXPERT REVIEW QUEUE — M5.2
# ============================================================
#
# Computes the officer-facing review queue live from existing
# data. No queue table. No persisted state. No schema change.
# ============================================================

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import (
    AIPrediction,
    Crop,
    CropSeason,
    ExpertValidation,
    Farm,
    Farmer,
    HealthReport,
    RiskAssessment,
    FollowUp,
)
from report_snapshots import (
    _build_escalation,
    _build_report_snapshot,
)
from monitoring_engine import compare_reports


ACTIONABLE_DECISIONS = (
    "EXPERT_REVIEW",
    "ATTENTION",
    "MONITOR",
)

SEVERITY_RANK = {
    "EXPERT_REVIEW": 3,
    "ATTENTION": 2,
    "MONITOR": 1,
    "ROUTINE": 0,
}

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _clamp_limit(limit):
    if limit is None:
        return DEFAULT_LIMIT
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    if value < 1:
        return 1
    if value > MAX_LIMIT:
        return MAX_LIMIT
    return value


def _has_any_validation(db: Session, health_report_id: int) -> bool:
    return (
        db.query(ExpertValidation)
        .filter(ExpertValidation.health_report_id == health_report_id)
        .first() is not None
    )


def _compute_escalation_with_context(db: Session, health_report_id: int):
    """
    Mirrors GET /health-reports/{id} escalation computation:
    if the report is a follow-up, include the comparison.
    """

    follow_up_as_completed = (
        db.query(FollowUp)
        .filter(FollowUp.follow_up_report_id == health_report_id)
        .order_by(desc(FollowUp.id))
        .first()
    )

    comparison = None

    if follow_up_as_completed:
        original_snapshot = _build_report_snapshot(
            db, follow_up_as_completed.original_report_id
        )
        current_snapshot = _build_report_snapshot(
            db, health_report_id
        )
        if original_snapshot and current_snapshot:
            comparison = compare_reports(
                original_report=original_snapshot,
                follow_up_report=current_snapshot,
            )

    return _build_escalation(
        db, health_report_id, comparison=comparison
    )


def _build_queue_item(db: Session, report: HealthReport, escalation: dict):
    farm = db.query(Farm).filter(Farm.id == report.farm_id).first()

    farmer = None
    if farm:
        farmer = db.query(Farmer).filter(Farmer.id == farm.farmer_id).first()

    crop_season = (
        db.query(CropSeason)
        .filter(CropSeason.id == report.crop_season_id)
        .first()
    )

    crop = None
    if crop_season:
        crop = db.query(Crop).filter(Crop.id == crop_season.crop_id).first()

    prediction = (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id == report.id)
        .order_by(desc(AIPrediction.created_at))
        .first()
    )

    risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.health_report_id == report.id)
        .order_by(desc(RiskAssessment.created_at))
        .first()
    )

    return {
        "health_report_id": report.id,
        "reported_at": report.reported_at,
        "farm": (
            {
                "id": farm.id, "farm_name": farm.farm_name,
                "district": farm.district, "state": farm.state,
                "latitude": farm.latitude, "longitude": farm.longitude,
            } if farm else None
        ),
        "farmer": (
            {"id": farmer.id, "name": farmer.name, "phone": farmer.phone}
            if farmer else None
        ),
        "crop": (
            {"id": crop.id, "name": crop.name} if crop else None
        ),
        "prediction": (
            {
                "predicted_class": prediction.predicted_class,
                "confidence": prediction.confidence,
            } if prediction else None
        ),
        "risk": (
            {
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
            } if risk else None
        ),
        "escalation": {
            "decision": escalation.get("decision"),
            "reasons": escalation.get("reasons", []),
            "triggered_rules": escalation.get("triggered_rules", []),
        },
    }


def build_review_queue(
    db: Session,
    district: str | None = None,
    limit: int | None = None,
    include_reviewed: bool = False,
):
    effective_limit = _clamp_limit(limit)

    candidate_ids = (
        db.query(AIPrediction.health_report_id)
        .distinct()
        .subquery()
    )

    reports_query = (
        db.query(HealthReport)
        .filter(
            HealthReport.id.in_(
                db.query(candidate_ids.c.health_report_id)
            )
        )
    )

    if district:
        reports_query = reports_query.join(
            Farm, Farm.id == HealthReport.farm_id
        ).filter(Farm.district == district)

    reports = (
        reports_query
        .order_by(desc(HealthReport.reported_at))
        .all()
    )

    items = []

    for report in reports:

        if not include_reviewed and _has_any_validation(db, report.id):
            continue

        escalation = _compute_escalation_with_context(db, report.id)

        if not escalation:
            continue

        decision = escalation.get("decision")

        if decision not in ACTIONABLE_DECISIONS:
            continue

        items.append(_build_queue_item(db, report, escalation))

    def sort_key(item):
        decision = item["escalation"]["decision"]
        severity = SEVERITY_RANK.get(decision, 0)
        reported_at = item["reported_at"]
        # Convert None to a very old datetime so it sorts last.
        if reported_at is None:
            from datetime import datetime
            reported_at = datetime(1970, 1, 1)
        return (severity, reported_at)

    items.sort(key=sort_key, reverse=True)

    truncated = items[:effective_limit]

    return {
        "total": len(truncated),
        "total_candidates": len(items),
        "filters": {
            "district": district,
            "limit": effective_limit,
            "include_reviewed": include_reviewed,
        },
        "items": truncated,
    }