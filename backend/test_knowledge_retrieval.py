# ============================================================
# TEST — M4.2 knowledge retrieval
# ============================================================
#
# Run from backend/:
#     pytest test_knowledge_retrieval.py -v
#
# Pure read-only test. Does not write to the database.
#
# Assumes M4.1 ingestion has already been run and the
# knowledge_documents / knowledge_chunks tables contain the
# advisory seed data.
# ============================================================

import pytest

from database import SessionLocal
from knowledge_retrieval import retrieve_evidence


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ============================================================
# CASE 1 — specific risk level returns exactly one chunk
# ============================================================

def test_retrieve_specific_risk_level(db):
    evidence = retrieve_evidence(
        db,
        condition_name="Potassium Deficiency",
        risk_level="HIGH",
    )

    assert len(evidence) == 1, (
        f"Expected 1 chunk for Potassium Deficiency/HIGH, "
        f"got {len(evidence)}"
    )

    item = evidence[0]

    assert item["condition_name"] == "Potassium Deficiency"
    assert item["risk_level"] == "HIGH"
    assert item["chunk_text"]
    assert item["document_title"].startswith("Potassium Deficiency")
    assert item["chunk_metadata"]["seed_source_type"] == "advisory_seed"
    assert isinstance(item["source_reference"], list)


# ============================================================
# CASE 2 — no risk level returns all four levels
# ============================================================

def test_retrieve_all_risk_levels(db):
    evidence = retrieve_evidence(
        db,
        condition_name="Late Blight",
        risk_level=None,
    )

    assert len(evidence) == 4, (
        f"Expected 4 chunks for Late Blight (all levels), "
        f"got {len(evidence)}"
    )

    levels = [item["risk_level"] for item in evidence]

    assert levels == ["LOW", "MODERATE", "HIGH", "CRITICAL"]


# ============================================================
# CASE 3 — unknown condition returns empty list
# ============================================================

def test_retrieve_unknown_condition(db):
    evidence = retrieve_evidence(
        db,
        condition_name="Powdery Mildew On Mars",
        risk_level="HIGH",
    )

    assert evidence == []


# ============================================================
# CASE 4 — condition type does not matter
# ============================================================
#
# 'Healthy' is stored as condition_type='OTHER'.
# Retrieval must work for it regardless.
# ============================================================

def test_retrieve_healthy_condition(db):
    evidence = retrieve_evidence(
        db,
        condition_name="Healthy",
        risk_level="LOW",
    )

    assert len(evidence) == 1
    assert evidence[0]["condition_name"] == "Healthy"
    assert evidence[0]["condition_type"] == "OTHER"
    assert evidence[0]["risk_level"] == "LOW"


# ============================================================
# CASE 5 — normalization tolerance
# ============================================================
#
# Same input, three formatting variants. All must resolve.
# ============================================================

def test_retrieve_normalization_tolerant(db):
    variants = [
        "Late Blight",
        "late blight",
        "late_blight",
        "  LATE BLIGHT  ",
    ]

    for variant in variants:
        evidence = retrieve_evidence(
            db,
            condition_name=variant,
            risk_level="HIGH",
        )

        assert len(evidence) == 1, (
            f"Variant {variant!r} should resolve to Late Blight/HIGH"
        )

        assert evidence[0]["condition_name"] == "Late Blight"