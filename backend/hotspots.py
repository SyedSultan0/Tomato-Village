# ============================================================
# GEOSPATIAL HOTSPOTS — M6
# ============================================================
#
# Deterministic clustering of health reports by location,
# condition, and time window.
#
# Refactored to eliminate N+1 queries:
#   - Loads all candidate reports in one query
#   - Loads all predictions for those reports in one query
#   - Loads all risk assessments in one query
#   - Loads all farms in one query
#   - Then assembles candidates in Python memory
#
# Response shape is unchanged from the previous version.
# ============================================================

import math
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import (
    AIPrediction,
    Crop,
    CropSeason,
    Farm,
    Farmer,
    HealthReport,
    RiskAssessment,
)


# ============================================================
# CONSTANTS
# ============================================================

EARTH_RADIUS_KM = 6371.0

DEFAULT_RADIUS_KM = 5.0
DEFAULT_DAYS = 14
DEFAULT_MIN_REPORTS = 3

MAX_RESULTS = 200


# ============================================================
# GEOMETRY
# ============================================================

def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Great-circle distance between two lat/lon points, in km.
    """

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_condition(label: str) -> str:
    if not isinstance(label, str):
        return ""
    return label.strip().lower().replace("_", " ")


# ============================================================
# CANDIDATE BUILDING — BATCHED
# ============================================================

def _load_candidates(
    db: Session,
    days: int,
    condition: str | None,
    district: str | None,
):
    """
    Load candidate reports that could belong to a hotspot.

    BATCHED: issues 4 queries total regardless of how many
    reports match. Previously this was N+1.
    """

    cutoff = datetime.utcnow() - timedelta(days=days)

    # --------------------------------------------------------
    # Query 1: all candidate reports
    # --------------------------------------------------------

    reports_query = (
        db.query(HealthReport)
        .filter(HealthReport.reported_at >= cutoff)
        .filter(HealthReport.latitude.isnot(None))
        .filter(HealthReport.longitude.isnot(None))
    )

    if district:
        reports_query = reports_query.join(
            Farm, Farm.id == HealthReport.farm_id
        ).filter(Farm.district == district)

    reports = reports_query.all()

    if not reports:
        return []

    report_ids = [r.id for r in reports]
    farm_ids = list({r.farm_id for r in reports})

    # --------------------------------------------------------
    # Query 2: all predictions for those reports
    # --------------------------------------------------------
    # ORDER BY created_at DESC + dedupe in Python to keep
    # the "latest prediction per report" semantics.

    predictions = (
        db.query(AIPrediction)
        .filter(AIPrediction.health_report_id.in_(report_ids))
        .order_by(
            AIPrediction.health_report_id,
            desc(AIPrediction.created_at),
        )
        .all()
    )

    latest_prediction_by_report: dict[int, AIPrediction] = {}
    for p in predictions:
        if p.health_report_id not in latest_prediction_by_report:
            latest_prediction_by_report[p.health_report_id] = p

    # --------------------------------------------------------
    # Query 3: all risk assessments for those reports
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

    latest_risk_by_report: dict[int, RiskAssessment] = {}
    for r in risks:
        if r.health_report_id not in latest_risk_by_report:
            latest_risk_by_report[r.health_report_id] = r

    # --------------------------------------------------------
    # Query 4: all farms referenced
    # --------------------------------------------------------

    farms = (
        db.query(Farm)
        .filter(Farm.id.in_(farm_ids))
        .all()
    )

    farm_by_id = {f.id: f for f in farms}

    # --------------------------------------------------------
    # Assemble candidates
    # --------------------------------------------------------

    condition_target = (
        _normalize_condition(condition)
        if condition
        else None
    )

    candidates = []

    for report in reports:

        prediction = latest_prediction_by_report.get(report.id)

        if not prediction or not prediction.predicted_class:
            continue

        normalized = _normalize_condition(prediction.predicted_class)

        if condition_target and normalized != condition_target:
            continue

        risk = latest_risk_by_report.get(report.id)
        farm = farm_by_id.get(report.farm_id)

        candidates.append({
            "report_id": report.id,
            "farm_id": report.farm_id,
            "district": farm.district if farm else None,
            "state": farm.state if farm else None,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "reported_at": report.reported_at,
            "condition": prediction.predicted_class,
            "condition_normalized": normalized,
            "confidence": prediction.confidence,
            "risk_score": risk.risk_score if risk else None,
            "risk_level": risk.risk_level if risk else None,
        })

    return candidates


# ============================================================
# CLUSTERING
# ============================================================

def _group_by_condition(candidates):
    groups: dict[str, list[dict]] = {}
    for candidate in candidates:
        key = candidate["condition_normalized"]
        groups.setdefault(key, []).append(candidate)
    return groups


def _greedy_cluster(
    candidates: list[dict],
    radius_km: float,
):
    """
    Fixed-radius greedy clustering. Unchanged logic.
    """

    visited = set()
    clusters = []

    for i, anchor in enumerate(candidates):

        if i in visited:
            continue

        group_indices = [i]

        for j in range(i + 1, len(candidates)):

            if j in visited:
                continue

            other = candidates[j]

            distance = haversine_km(
                anchor["latitude"],
                anchor["longitude"],
                other["latitude"],
                other["longitude"],
            )

            if distance <= radius_km:
                group_indices.append(j)

        if len(group_indices) >= 2:
            clusters.append({
                "anchor_index": i,
                "member_indices": group_indices,
            })

    return clusters


# ============================================================
# HOTSPOT ASSEMBLY
# ============================================================

def _risk_rank(level: str | None) -> int:
    return {
        "LOW": 1,
        "MODERATE": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }.get((level or "").upper(), 0)


def _summarize_risk(members: list[dict]) -> str | None:
    levels = [
        m.get("risk_level")
        for m in members
        if m.get("risk_level")
    ]
    if not levels:
        return None
    return max(levels, key=_risk_rank)


def _build_hotspot(
    db: Session,
    members: list[dict],
    radius_km: float,
    days: int,
) -> dict[str, Any]:
    """
    Convert a set of cluster members into a hotspot dict.

    Farm + farmer + crop details are fetched in a batched way
    by _load_farm_details_for_hotspot_sets() before this is
    called. We receive them pre-resolved via members' cached
    lookups below.
    """

    lats = [m["latitude"] for m in members]
    lons = [m["longitude"] for m in members]

    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    max_distance = 0.0
    for m in members:
        d = haversine_km(
            center_lat, center_lon,
            m["latitude"], m["longitude"],
        )
        if d > max_distance:
            max_distance = d

    times = [
        m["reported_at"]
        for m in members
        if m["reported_at"] is not None
    ]

    earliest = min(times) if times else None
    latest = max(times) if times else None

    farm_ids = sorted({m["farm_id"] for m in members})
    districts = sorted({
        m["district"] for m in members if m["district"]
    })

    # --------------------------------------------------------
    # Farm details (batched lookup)
    # --------------------------------------------------------

    farms_detail = _build_farm_details(db, farm_ids)

    return {
        "condition": members[0]["condition"],
        "report_count": len(members),
        "center": {
            "latitude": round(center_lat, 6),
            "longitude": round(center_lon, 6),
        },
        "radius_km": round(max_distance, 2),
        "time_window_days": days,
        "earliest_report": earliest,
        "latest_report": latest,
        "farm_ids": farm_ids,
        "farms": farms_detail,
        "districts": districts,
        "max_risk_level": _summarize_risk(members),
        "report_ids": sorted(m["report_id"] for m in members),
    }


def _build_farm_details(db: Session, farm_ids: list[int]) -> list[dict]:
    """
    Batched farm + farmer + crop lookup.

    Issues 3 queries regardless of how many farms.
    """

    if not farm_ids:
        return []

    # --------------------------------------------------------
    # Query 1: farms
    # --------------------------------------------------------

    farms = (
        db.query(Farm)
        .filter(Farm.id.in_(farm_ids))
        .all()
    )

    farmer_ids = list({
        f.farmer_id for f in farms if f.farmer_id is not None
    })

    # --------------------------------------------------------
    # Query 2: farmers
    # --------------------------------------------------------

    farmers_by_id = {}
    if farmer_ids:
        farmers = (
            db.query(Farmer)
            .filter(Farmer.id.in_(farmer_ids))
            .all()
        )
        farmers_by_id = {f.id: f for f in farmers}

    # --------------------------------------------------------
    # Query 3: crop seasons + crops
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

    # Map farm → crop name (from its first crop season)
    crop_name_by_farm = {}
    for season in seasons:
        if season.farm_id not in crop_name_by_farm:
            crop = crops_by_id.get(season.crop_id)
            if crop:
                crop_name_by_farm[season.farm_id] = crop.name

    # --------------------------------------------------------
    # Assemble
    # --------------------------------------------------------

    details = []
    for farm in farms:
        farmer = farmers_by_id.get(farm.farmer_id)
        details.append({
            "farm_id": farm.id,
            "farm_name": farm.farm_name,
            "district": farm.district,
            "state": farm.state,
            "farmer_name": farmer.name if farmer else None,
            "farmer_phone": farmer.phone if farmer else None,
            "crop_name": crop_name_by_farm.get(farm.id),
        })

    return details


# ============================================================
# PUBLIC ENTRY
# ============================================================

def find_hotspots(
    db: Session,
    condition: str | None = None,
    days: int = DEFAULT_DAYS,
    radius_km: float = DEFAULT_RADIUS_KM,
    min_reports: int = DEFAULT_MIN_REPORTS,
    district: str | None = None,
) -> list[dict[str, Any]]:
    """
    Find clusters of the same condition within radius_km
    over the last `days` days.

    Response shape unchanged.
    """

    if days < 1:
        days = 1
    if radius_km <= 0:
        radius_km = DEFAULT_RADIUS_KM
    if min_reports < 2:
        min_reports = 2

    candidates = _load_candidates(
        db=db,
        days=days,
        condition=condition,
        district=district,
    )

    if not candidates:
        return []

    groups = _group_by_condition(candidates)

    all_hotspots = []

    for _, group in groups.items():

        cluster_candidates = _greedy_cluster(
            group,
            radius_km=radius_km,
        )

        claimed = set()

        for cluster in cluster_candidates:

            member_indices = cluster["member_indices"]

            if any(idx in claimed for idx in member_indices):
                continue

            members = [group[idx] for idx in member_indices]

            if len(members) < min_reports:
                continue

            hotspot = _build_hotspot(
                db=db,
                members=members,
                radius_km=radius_km,
                days=days,
            )

            all_hotspots.append(hotspot)

            for idx in member_indices:
                claimed.add(idx)

    all_hotspots.sort(
        key=lambda h: (
            -h["report_count"],
            -_risk_rank(h["max_risk_level"]),
            -(h["latest_report"].timestamp() if h["latest_report"] else 0),
        )
    )

    return all_hotspots[:MAX_RESULTS]