import pytest
from database import SessionLocal
from expert_queue import (
    build_review_queue,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ACTIONABLE_DECISIONS,
    SEVERITY_RANK,
)


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def test_queue_returns_expected_shape(db):
    r = build_review_queue(db)
    assert "total" in r
    assert "total_candidates" in r
    assert "filters" in r
    assert "items" in r
    assert r["filters"]["limit"] == DEFAULT_LIMIT


def test_queue_limit_clamped_to_max(db):
    r = build_review_queue(db, limit=99999)
    assert r["filters"]["limit"] == MAX_LIMIT


def test_queue_limit_minimum_one(db):
    r = build_review_queue(db, limit=0)
    assert r["filters"]["limit"] == 1


def test_queue_invalid_limit_falls_back(db):
    r = build_review_queue(db, limit="not-a-number")
    assert r["filters"]["limit"] == DEFAULT_LIMIT


def test_all_items_have_actionable_decisions(db):
    r = build_review_queue(db, include_reviewed=True)
    for item in r["items"]:
        assert item["escalation"]["decision"] in ACTIONABLE_DECISIONS


def test_no_routine_reports_in_queue(db):
    r = build_review_queue(db, include_reviewed=True)
    for item in r["items"]:
        assert item["escalation"]["decision"] != "ROUTINE"


def test_items_sorted_by_severity_then_recency(db):
    r = build_review_queue(db, include_reviewed=True)
    items = r["items"]
    for i in range(len(items) - 1):
        cur = items[i]
        nxt = items[i + 1]
        cur_s = SEVERITY_RANK.get(cur["escalation"]["decision"], 0)
        nxt_s = SEVERITY_RANK.get(nxt["escalation"]["decision"], 0)
        assert cur_s >= nxt_s
        if cur_s == nxt_s and cur["reported_at"] and nxt["reported_at"]:
            assert cur["reported_at"] >= nxt["reported_at"]


def test_include_reviewed_does_not_reduce_total(db):
    pending = build_review_queue(db, include_reviewed=False)
    all_items = build_review_queue(db, include_reviewed=True)
    assert all_items["total_candidates"] >= pending["total_candidates"]


def test_queue_item_shape(db):
    r = build_review_queue(db, include_reviewed=True)
    if not r["items"]:
        pytest.skip("No actionable reports.")
    item = r["items"][0]
    for key in ["health_report_id", "reported_at", "farm", "farmer",
                "crop", "prediction", "risk", "escalation"]:
        assert key in item