"""this is the file shows the hotspots of the tomato village sort off.... awe"""


# ============================================================
# GEOSPATIAL HOTSPOTS — M6
# ============================================================
#
# Deterministic clustering of health reports by location,
# condition, and time window.
#
# What it does:
#   - finds groups of >= min_reports reports of the same
#     condition within radius_km of each other, within
#     days of each other
#   - returns each cluster with center, radius, farm list,
#     and risk summary
#
# What it does NOT do:
#   - persist anything
#   - use an LLM
#   - call any external API
#   - mutate any existing data
#
# Live-computed from HealthReport + AIPrediction +
# RiskAssessment + Farm. No new tables.
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

    Uses the haversine formula. Reliable for distances up to
    a few hundred km, which is well beyond our use case.
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
# CANDIDATE BUILDING
# ============================================================

def _load_candidates(
    db: Session,
    days: int,
    condition: str | None,
    district: str | None,
):
    """
    Load candidate reports that could belong to a hotspot.

    A candidate is:
        - has valid lat/lon
        - has an AIPrediction
        - reported within the last `days` days
        - matches `condition` if provided (normalized)
        - belongs to a farm in `district` if provided
    """

    cutoff = datetime.utcnow() - timedelta(days=days)

    query = (
        db.query(HealthReport)
        .filter(HealthReport.reported_at >= cutoff)
        .filter(HealthReport.latitude.isnot(None))
        .filter(HealthReport.longitude.isnot(None))
    )

    if district:
        query = query.join(
            Farm, Farm.id == HealthReport.farm_id
        ).filter(Farm.district == district)

    reports = query.all()

    candidates = []

    condition_target = (
        _normalize_condition(condition)
        if condition
        else None
    )

    for report in reports:

        prediction = (
            db.query(AIPrediction)
            .filter(AIPrediction.health_report_id == report.id)
            .order_by(desc(AIPrediction.created_at))
            .first()
        )

        if not prediction or not prediction.predicted_class:
            continue

        normalized = _normalize_condition(
            prediction.predicted_class
        )

        if condition_target and normalized != condition_target:
            continue

        risk = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.health_report_id == report.id)
            .order_by(desc(RiskAssessment.created_at))
            .first()
        )

        farm = (
            db.query(Farm)
            .filter(Farm.id == report.farm_id)
            .first()
        )

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
    """
    Group candidates by normalized condition.
    """

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
    Fixed-radius greedy clustering.

    Picks an unvisited candidate, gathers all candidates within
    radius_km of it, and if that group is large enough to be a
    cluster, emits it and marks all members visited.

    Deterministic: order of iteration is the input order.
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
            # Only mark visited if it becomes a group we might
            # keep. If the group is too small to be a hotspot,
            # we let the members be re-considered as anchors
            # for other potential groups.
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
    """
    Return the highest risk level present in the group.
    """

    levels = [
        member.get("risk_level")
        for member in members
        if member.get("risk_level")
    ]

    if not levels:
        return None

    return max(levels, key=_risk_rank)


def _build_hotspot(
    db,
    members: list[dict],
    radius_km: float,
    days: int,
) -> dict[str, Any]:
    """
    Convert a set of cluster members into a hotspot dict.
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
    # Enrich with farm + farmer + crop details
    # --------------------------------------------------------

    farms_detail = []

    for farm_id in farm_ids:

        farm = (
            db.query(Farm)
            .filter(Farm.id == farm_id)
            .first()
        )

        if not farm:
            continue

        farmer = None
        if farm.farmer_id:
            farmer = (
                db.query(Farmer)
                .filter(Farmer.id == farm.farmer_id)
                .first()
            )

        crop_name = None
        crop_season = (
            db.query(CropSeason)
            .join(HealthReport, HealthReport.crop_season_id == CropSeason.id)
            .filter(HealthReport.farm_id == farm_id)
            .first()
        )
        if crop_season:
            crop = (
                db.query(Crop)
                .filter(Crop.id == crop_season.crop_id)
                .first()
            )
            if crop:
                crop_name = crop.name

        farms_detail.append({
            "farm_id": farm.id,
            "farm_name": farm.farm_name,
            "district": farm.district,
            "state": farm.state,
            "farmer_name": farmer.name if farmer else None,
            "farmer_phone": farmer.phone if farmer else None,
            "crop_name": crop_name,
        })

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

    Returns a list of hotspot dicts.
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

        # Track which reports we've already claimed so a report
        # doesn't belong to two hotspots.
        claimed = set()

        for cluster in cluster_candidates:

            member_indices = cluster["member_indices"]

            # Skip if any member already belongs to a kept cluster
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

    # Sort by report count desc, then max risk desc, then recency
    all_hotspots.sort(
        key=lambda h: (
            -h["report_count"],
            -_risk_rank(h["max_risk_level"]),
            -(h["latest_report"].timestamp() if h["latest_report"] else 0),
        )
    )

    return all_hotspots[:MAX_RESULTS]