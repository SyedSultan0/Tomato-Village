# ============================================================
# TEST — M6 geospatial hotspots (geometry + clustering)
# ============================================================
#
# Pure-function tests. No database. No network.
#
# Run from backend/:
#     python -m pytest test_hotspots.py -v
# ============================================================

from hotspots import (
    haversine_km,
    _normalize_condition,
    _risk_rank,
    _summarize_risk,
    _greedy_cluster,
)


# ============================================================
# haversine_km
# ============================================================

def test_haversine_same_point_is_zero():
    d = haversine_km(19.076, 72.8777, 19.076, 72.8777)
    assert d == 0.0


def test_haversine_known_distance_mumbai_pune():
    # Mumbai ~ (19.0760, 72.8777), Pune ~ (18.5204, 73.8567)
    # Great-circle distance ~ 120 km
    d = haversine_km(19.0760, 72.8777, 18.5204, 73.8567)
    assert 100 < d < 140, f"Expected ~120 km, got {d}"


def test_haversine_known_distance_nashik_pune():
    # Nashik ~ (19.9975, 73.7898), Pune ~ (18.5204, 73.8567)
    d = haversine_km(19.9975, 73.7898, 18.5204, 73.8567)
    assert 150 < d < 180, f"Expected ~165 km, got {d}"


def test_haversine_symmetric():
    a = haversine_km(19.0760, 72.8777, 18.5204, 73.8567)
    b = haversine_km(18.5204, 73.8567, 19.0760, 72.8777)
    assert abs(a - b) < 1e-9


# ============================================================
# normalization
# ============================================================

def test_normalize_condition_lowercase():
    assert _normalize_condition("Late Blight") == "late blight"
    assert _normalize_condition("late_blight") == "late blight"
    assert _normalize_condition("  LATE BLIGHT  ") == "late blight"


def test_normalize_condition_handles_non_string():
    assert _normalize_condition(None) == ""
    assert _normalize_condition(123) == ""


# ============================================================
# risk ranking
# ============================================================

def test_risk_rank_ordering():
    assert _risk_rank("LOW") < _risk_rank("MODERATE")
    assert _risk_rank("MODERATE") < _risk_rank("HIGH")
    assert _risk_rank("HIGH") < _risk_rank("CRITICAL")
    assert _risk_rank(None) == 0


def test_summarize_risk_picks_highest():
    members = [
        {"risk_level": "LOW"},
        {"risk_level": "CRITICAL"},
        {"risk_level": "MODERATE"},
    ]
    assert _summarize_risk(members) == "CRITICAL"


def test_summarize_risk_empty_when_no_data():
    assert _summarize_risk([]) is None
    assert _summarize_risk([{"risk_level": None}]) is None


# ============================================================
# clustering
# ============================================================

def _candidate(lat, lon, report_id):
    return {
        "report_id": report_id,
        "farm_id": 1,
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": lat,
        "longitude": lon,
        "reported_at": None,
        "condition": "Late Blight",
        "condition_normalized": "late blight",
        "confidence": 0.95,
        "risk_score": 70.0,
        "risk_level": "HIGH",
    }


def test_greedy_cluster_finds_nearby_group():
    candidates = [
        _candidate(19.076, 72.8777, 1),
        _candidate(19.078, 72.879, 2),   # ~250m away
        _candidate(19.075, 72.876, 3),   # ~150m away
        _candidate(20.500, 75.000, 4),   # far away
    ]

    clusters = _greedy_cluster(candidates, radius_km=5.0)

    # The three nearby ones should form a cluster
    assert len(clusters) >= 1

    biggest = max(clusters, key=lambda c: len(c["member_indices"]))
    assert len(biggest["member_indices"]) == 3


def test_greedy_cluster_no_group_when_far():
    candidates = [
        _candidate(19.076, 72.8777, 1),
        _candidate(20.500, 75.000, 2),
        _candidate(21.000, 76.000, 3),
    ]

    clusters = _greedy_cluster(candidates, radius_km=5.0)

    # No group has more than 1 member within radius
    for cluster in clusters:
        assert len(cluster["member_indices"]) == 1


def test_greedy_cluster_boundary_uses_radius():
    # Two reports ~5.5 km apart
    candidates = [
        _candidate(19.000, 72.000, 1),
        _candidate(19.050, 72.000, 2),   # ~5.5 km away
    ]

    clusters = _greedy_cluster(candidates, radius_km=5.0)

    # Should NOT cluster (outside radius)
    for cluster in clusters:
        assert len(cluster["member_indices"]) == 1

    clusters_wide = _greedy_cluster(candidates, radius_km=6.0)

    # Should cluster (inside radius)
    assert any(len(c["member_indices"]) == 2 for c in clusters_wide)