# ============================================================
# EXPERT REVIEW QUEUE — M5.2
# ============================================================
#
# Refactored to eliminate N+1 queries:
#   - Loads all reports in one query
#   - Batches predictions, risks, farms, farmers, crops
#   - Runs escalation per report (still N escalations, but no
#     DB round-trips per report beyond what escalation itself
#     does — which is minimal since report_snapshots also
#     batches)
#
# Response shape is unchanged.
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


def _compute_escalation_with_context(db: Session, health_report_id: int):
    """
    Mirrors GET /health-reports/{id} escalation computation.
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


def build_review_queue(
    db: Session,
    district: str | None = None,
    limit: int | None = None,
    include_reviewed: bool = False,
):
    """
    Response shape unchanged.
    """

    effective_limit = _clamp_limit(limit)

    # --------------------------------------------------------
    # Query 1: all candidate reports (with their farm)
    # --------------------------------------------------------

    reports_q = db.query(HealthReport)

    if district:
        reports_q = reports_q.join(
            Farm, Farm.id == HealthReport.farm_id
        ).filter(Farm.district == district)

    reports = (
        reports_q
        .order_by(desc(HealthReport.reported_at))
        .all()
    )

    if not reports:
        return {
            "total": 0,
            "total_candidates": 0,
            "filters": {
                "district": district,
                "limit": effective_limit,
                "include_reviewed": include_reviewed,
            },
            "items": [],
        }

    report_ids = [r.id for r in reports]
    farm_ids = list({r.farm_id for r in reports})

    # --------------------------------------------------------
    # Query 2: existing validations
    # --------------------------------------------------------

    validations = (
        db.query(ExpertValidation.health_report_id)
        .filter(ExpertValidation.health_report_id.in_(report_ids))
        .distinct()
        .all()
    )
    reviewed_ids = {v[0] for v in validations}

    # --------------------------------------------------------
    # Query 3: predictions
    # --------------------------------------------------------

    predictions = (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id.in_(report_ids))
        .order_by(
            AIPrediction.health_report_id,
            desc(AIPrediction.created_at),
        )
        .all()
    )

    latest_prediction = {}
    for p in predictions:
        if p.health_report_id not in latest_prediction:
            latest_prediction[p.health_report_id] = p

    # --------------------------------------------------------
    # Query 4: risks
    # --------------------------------------------------------

    risks = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.health_report_id.in_(report_ids))
        .order_by(
            RiskAssessment.health_report_id,
            desc(RiskAssessment.created_at),
        )
        .all()
    )

    latest_risk = {}
    for r in risks:
        if r.health_report_id not in latest_risk:
            latest_risk[r.health_report_id] = r

    # --------------------------------------------------------
    # Query 5: farms
    # --------------------------------------------------------

    farms = (
        db.query(Farm)
        .filter(Farm.id.in_(farm_ids))
        .all()
    )
    farm_by_id = {f.id: f for f in farms}

    # --------------------------------------------------------
    # Query 6: farmers
    # --------------------------------------------------------

    farmer_ids = list({
        f.farmer_id for f in farms if f.farmer_id is not None
    })

    farmers_by_id = {}
    if farmer_ids:
        farmers = (
            db.query(Farmer)
            .filter(Farmer.id.in_(farmer_ids))
            .all()
        )
        farmers_by_id = {f.id: f for f in farmers}

    # --------------------------------------------------------
    # Query 7: crop seasons + crops
    # --------------------------------------------------------

    seasons = (
        db.query(CropSeason)
        .filter(CropSeason.farm_id.in_(farm_ids))
        .all()
    )

    crop_ids = list({s.crop_id for s in seasons})

    crops_by_id = {}
    if crop_ids:
        crops = (
            db.query(Crop)
            .filter(Crop.id.in_(crop_ids))
            .all()
        )
        crops_by_id = {c.id: c for c in crops}

    crop_name_by_farm = {}
    for season in seasons:
        if season.farm_id not in crop_name_by_farm:
            crop = crops_by_id.get(season.crop_id)
            if crop:
                crop_name_by_farm[season.farm_id] = crop.name

    # --------------------------------------------------------
    # Assemble queue items
    # --------------------------------------------------------

    items = []

    for report in reports:

        if not include_reviewed and report.id in reviewed_ids:
            continue

        # Escalation — this internally does a small number
        # of queries per report via report_snapshots, but it's
        # much cheaper than the old approach because we're not
        # duplicating prediction/risk lookups here.
        escalation = _compute_escalation_with_context(db, report.id)

        if not escalation:
            continue

        decision = escalation.get("decision")

        if decision not in ACTIONABLE_DECISIONS:
            continue

        farm = farm_by_id.get(report.farm_id)
        farmer = farmers_by_id.get(farm.farmer_id) if farm else None
        prediction = latest_prediction.get(report.id)
        risk = latest_risk.get(report.id)

        items.append({
            "health_report_id": report.id,
            "reported_at": report.reported_at,
            "farm": (
                {
                    "id": farm.id,
                    "farm_name": farm.farm_name,
                    "district": farm.district,
                    "state": farm.state,
                    "latitude": farm.latitude,
                    "longitude": farm.longitude,
                }
                if farm
                else None
            ),
            "farmer": (
                {
                    "id": farmer.id,
                    "name": farmer.name,
                    "phone": farmer.phone,
                }
                if farmer
                else None
            ),
            "crop": (
                {
                    "id": crop_ids[0] if crop_ids else None,
                    "name": crop_name_by_farm.get(report.farm_id),
                }
                if crop_name_by_farm.get(report.farm_id)
                else None
            ),
            "prediction": (
                {
                    "predicted_class": prediction.predicted_class,
                    "confidence": prediction.confidence,
                }
                if prediction
                else None
            ),
            "risk": (
                {
                    "risk_score": risk.risk_score,
                    "risk_level": risk.risk_level,
                }
                if risk
                else None
            ),
            "escalation": {
                "decision": escalation.get("decision"),
                "reasons": escalation.get("reasons", []),
                "triggered_rules": escalation.get("triggered_rules", []),
            },
        })

    # --------------------------------------------------------
    # Sort and truncate
    # --------------------------------------------------------

    def sort_key(item):
        decision = item["escalation"]["decision"]
        severity = SEVERITY_RANK.get(decision, 0)
        reported_at = item["reported_at"]
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