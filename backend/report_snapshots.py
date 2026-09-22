# ============================================================
# SHARED REPORT HELPERS
# ============================================================
#
# Extracted from main.py so that other modules (expert_queue,
# future engines) can use them without a circular import.
#
# These functions are read-only over the DB. They never mutate
# state.
# ============================================================

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import (
    AIPrediction,
    Advisory,
    HealthReport,
    RiskAssessment,
    FollowUp,
)
from monitoring_engine import compare_reports
from escalation_engine import decide_escalation
from knowledge_retrieval import retrieve_evidence
from explanation_engine import generate_explanation


# ============================================================
# SNAPSHOT
# ============================================================

def _build_report_snapshot(db: Session, report_id: int):
    """
    Build a plain dict snapshot of a health report for the
    deterministic monitoring comparison engine.

    Returns None if the report does not exist.
    """

    report = (
        db.query(HealthReport)
        .filter(HealthReport.id == report_id)
        .first()
    )

    if not report:
        return None

    prediction_record = (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id == report.id)
        .order_by(desc(AIPrediction.created_at))
        .first()
    )

    risk_record = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.health_report_id == report.id)
        .order_by(desc(RiskAssessment.created_at))
        .first()
    )

    advisory_record = (
        db.query(Advisory)
        .filter(Advisory.health_report_id == report.id)
        .order_by(desc(Advisory.created_at))
        .first()
    )

    return {
        "report_id": report.id,
        "reported_at": report.reported_at,
        "predicted_class": (
            prediction_record.predicted_class
            if prediction_record
            else None
        ),
        "confidence": (
            prediction_record.confidence
            if prediction_record
            else None
        ),
        "risk_score": (
            risk_record.risk_score
            if risk_record
            else None
        ),
        "risk_level": (
            risk_record.risk_level
            if risk_record
            else None
        ),
        "risk_engine_version": (
            risk_record.calculation_method
            if risk_record
            else None
        ),
        "advisory_id": (
            advisory_record.id
            if advisory_record
            else None
        ),
    }


# ============================================================
# ESCALATION
# ============================================================

def _build_escalation(
    db: Session,
    current_report_id: int,
    comparison: dict | None = None,
):
    """
    Build a deterministic escalation decision for a health report.

    Escalation is computed from the current report snapshot and,
    when available, the monitoring comparison.

    No escalation state is persisted in the database.
    """

    current_snapshot = _build_report_snapshot(db, current_report_id)

    if not current_snapshot:
        return None

    return decide_escalation(
        current_report=current_snapshot,
        comparison=comparison,
    )


# ============================================================
# EVIDENCE
# ============================================================

def _build_evidence_for_report(db: Session, health_report_id: int):
    """
    Retrieve stored knowledge evidence for the condition and
    risk level associated with a health report.

    Deterministic and read-only.
    """

    prediction_record = (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id == health_report_id)
        .order_by(desc(AIPrediction.created_at))
        .first()
    )

    risk_record = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.health_report_id == health_report_id)
        .order_by(desc(RiskAssessment.created_at))
        .first()
    )

    if not prediction_record or not risk_record:
        return None

    try:
        return retrieve_evidence(
            db=db,
            condition_name=prediction_record.predicted_class,
            risk_level=risk_record.risk_level,
            crop_name="Tomato",
        )
    except Exception as e:
        print("Evidence retrieval failed:", str(e))
        return []


# ============================================================
# EXPLANATION
# ============================================================

def _build_explanation_for_report(db: Session, health_report_id: int):
    """
    Build a farmer-friendly explanation for a health report.

    Assembles already-determined facts and hands them to the
    explanation engine.
    """

    prediction_record = (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id == health_report_id)
        .order_by(desc(AIPrediction.created_at))
        .first()
    )

    risk_record = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.health_report_id == health_report_id)
        .order_by(desc(RiskAssessment.created_at))
        .first()
    )

    advisory_record = (
        db.query(Advisory)
        .filter(Advisory.health_report_id == health_report_id)
        .order_by(desc(Advisory.created_at))
        .first()
    )

    if not prediction_record or not risk_record:
        return None

    prediction = {
        "predicted_class": prediction_record.predicted_class,
        "confidence": prediction_record.confidence,
    }

    risk = {
        "risk_level": risk_record.risk_level,
        "risk_score": risk_record.risk_score,
    }

    advisory = {
        "summary": advisory_record.advisory_text
        if advisory_record
        else None,
        "immediate_actions": [],
        "prevention": [],
        "monitoring": [],
    }

    escalation = _build_escalation(db, health_report_id) or {}

    evidence = _build_evidence_for_report(db, health_report_id)

    return generate_explanation(
        prediction=prediction,
        risk=risk,
        advisory=advisory,
        escalation=escalation,
        evidence=evidence,
    )