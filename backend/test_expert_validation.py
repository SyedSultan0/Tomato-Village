import pytest
from database import SessionLocal
from expert_validation import (
    validate_submission,
    normalize_status,
    find_condition_by_name,
)


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def test_normalize_status_valid():
    assert normalize_status("confirmed") == "CONFIRMED"
    assert normalize_status("  CORRECTED ") == "CORRECTED"
    assert normalize_status("rejected") == "REJECTED"


def test_normalize_status_invalid():
    with pytest.raises(ValueError):
        normalize_status("approved")


def test_find_condition_by_name_normalization(db):
    c = find_condition_by_name(db, "potassium_deficiency")
    assert c is not None
    assert c.name == "Potassium Deficiency"


def test_find_condition_by_name_unknown(db):
    assert find_condition_by_name(db, "Nonexistent Condition") is None


def test_confirmed_matches_ai_prediction(db):
    r = validate_submission(db, 9, "CONFIRMED", "Potassium Deficiency")
    assert r["ok"] is True
    assert r["confirmed_condition"].name == "Potassium Deficiency"


def test_corrected_to_different_condition(db):
    r = validate_submission(db, 9, "CORRECTED", "Nitrogen Deficiency")
    assert r["ok"] is True
    assert r["confirmed_condition"].name == "Nitrogen Deficiency"


def test_rejected_without_condition(db):
    r = validate_submission(db, 9, "REJECTED", None)
    assert r["ok"] is True


def test_inconclusive_without_condition(db):
    r = validate_submission(db, 9, "INCONCLUSIVE", None)
    assert r["ok"] is True


def test_health_report_not_found(db):
    r = validate_submission(db, 99999, "CONFIRMED", "Late Blight")
    assert r["ok"] is False


def test_confirmed_with_wrong_condition(db):
    r = validate_submission(db, 9, "CONFIRMED", "Late Blight")
    assert r["ok"] is False


def test_corrected_to_same_condition(db):
    r = validate_submission(db, 9, "CORRECTED", "Potassium Deficiency")
    assert r["ok"] is False


def test_confirmed_without_condition(db):
    r = validate_submission(db, 9, "CONFIRMED", None)
    assert r["ok"] is False


def test_rejected_with_condition(db):
    r = validate_submission(db, 9, "REJECTED", "Late Blight")
    assert r["ok"] is False


def test_unknown_condition_name(db):
    r = validate_submission(db, 9, "CORRECTED", "Purple Spot Blight")
    assert r["ok"] is False


def test_invalid_status(db):
    r = validate_submission(db, 9, "APPROVED", None)
    assert r["ok"] is False