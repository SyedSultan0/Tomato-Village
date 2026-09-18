# ============================================================
# KNOWLEDGE RETRIEVAL — M4.2
# ============================================================
#
# Deterministic, metadata-driven evidence retrieval over the
# KnowledgeDocument / KnowledgeChunk tables.
#
# Scope (deliberately narrow):
#   - lookup by condition name (+ optional risk level)
#   - return evidence chunks with source metadata
#
# Out of scope:
#   - embeddings
#   - vector search
#   - free-text / semantic queries
#   - LLM
#
# This module has zero side effects. It never writes to the DB.
# It is safe to call from any endpoint, any engine, any test.
# ============================================================

from typing import Any

from sqlalchemy.orm import Session

from database import (
    Crop,
    Condition,
    KnowledgeDocument,
    KnowledgeChunk,
)


# ============================================================
# CONFIGURATION
# ============================================================

SEED_SOURCE_TYPE = "advisory_seed"

VALID_RISK_LEVELS = (
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
)


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_condition_name(name: str) -> str:
    """
    Normalize condition names the same way the advisory engine
    and ingestion do, so lookups are robust to small formatting
    differences.

    Examples:
        'Late Blight'    -> 'late blight'
        'late_blight'    -> 'late blight'
        '  LateBlight '  -> 'lateblight'
    """
    if not isinstance(name, str):
        raise ValueError("condition_name must be a string.")

    return (
        name.strip().lower()
        .replace("_", " ")
    )


def _normalize_risk_level(risk_level: str) -> str:
    if not isinstance(risk_level, str):
        raise ValueError("risk_level must be a string.")

    normalized = risk_level.strip().upper()

    if normalized not in VALID_RISK_LEVELS:
        raise ValueError(
            f"Unsupported risk level: {risk_level}. "
            f"Expected one of {list(VALID_RISK_LEVELS)}."
        )

    return normalized


# ============================================================
# LOOKUPS
# ============================================================

def _find_condition(
    db: Session,
    condition_name: str,
) -> Condition | None:
    """
    Find a Condition row by name.

    Uses a normalized comparison so 'Late Blight', 'late_blight',
    and 'Late  Blight' all resolve to the same row.
    """

    target = _normalize_condition_name(condition_name)

    candidates = db.query(Condition).all()

    for condition in candidates:
        if _normalize_condition_name(condition.name) == target:
            return condition

    return None


def _find_documents_for_condition(
    db: Session,
    condition: Condition,
    crop_name: str | None,
) -> list[KnowledgeDocument]:
    """
    Find all KnowledgeDocuments attached to a Condition.

    If crop_name is provided, restrict to documents for that crop.
    If not provided, return documents for any crop.
    """

    query = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.condition_id == condition.id,
        )
    )

    if crop_name:
        crop = (
            db.query(Crop)
            .filter(Crop.name == crop_name)
            .first()
        )

        if not crop:
            return []

        query = query.filter(
            KnowledgeDocument.crop_id == crop.id
        )

    return query.order_by(KnowledgeDocument.id).all()


# ============================================================
# EVIDENCE SHAPING
# ============================================================

def _build_evidence_item(
    chunk: KnowledgeChunk,
    document: KnowledgeDocument,
    condition: Condition,
) -> dict[str, Any]:
    """
    Convert ORM rows into a plain dict suitable for API responses
    and downstream engines.

    Never returns ORM objects — always plain dicts.
    """

    metadata = chunk.chunk_metadata or {}

    return {
        "chunk_id": chunk.id,
        "document_id": document.id,
        "document_title": document.title,

        "condition_id": condition.id,
        "condition_name": condition.name,
        "condition_type": condition.condition_type,

        "risk_level": metadata.get("risk_level"),

        "source": document.source,
        "display_source": metadata.get("display_source"),
        "source_reference": metadata.get("source_reference", []),

        "chunk_index": chunk.chunk_index,
        "chunk_text": chunk.chunk_text,
        "chunk_metadata": metadata,
    }


# ============================================================
# PUBLIC API
# ============================================================

def retrieve_evidence(
    db: Session,
    condition_name: str,
    risk_level: str | None = None,
    crop_name: str | None = "Tomato",
) -> list[dict[str, Any]]:
    """
    Retrieve evidence chunks for a condition.

    Parameters:
        db:
            SQLAlchemy session.

        condition_name:
            Name of the condition (e.g. 'Potassium Deficiency').
            Matched case-insensitively and tolerant of underscore /
            whitespace differences.

        risk_level:
            Optional. One of LOW / MODERATE / HIGH / CRITICAL.
            If None, evidence for all risk levels is returned.

        crop_name:
            Optional crop filter. Defaults to 'Tomato'.
            Pass None to retrieve regardless of crop.

    Returns:
        A list of evidence dicts ordered by:
            (document_id, chunk_index)

        Empty list when:
            - the condition does not exist
            - the crop does not exist
            - no documents are attached to the condition
            - no chunks match the requested risk level

    IMPORTANT:
        This function does NOT recalculate risk, decide diagnosis,
        decide treatment, or make escalation decisions. It only
        retrieves stored evidence.
    """

    if not isinstance(condition_name, str) or not condition_name.strip():
        raise ValueError("condition_name must be a non-empty string.")

    condition = _find_condition(db, condition_name)

    if condition is None:
        return []

    documents = _find_documents_for_condition(
        db=db,
        condition=condition,
        crop_name=crop_name,
    )

    if not documents:
        return []

    document_ids = [doc.id for doc in documents]

    chunk_query = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id.in_(document_ids))
    )

    if risk_level is not None:
        normalized_risk = _normalize_risk_level(risk_level)

        chunk_query = chunk_query.filter(
            KnowledgeChunk.chunk_metadata["risk_level"].as_string()
            == normalized_risk
        )

    chunks = (
        chunk_query
        .order_by(
            KnowledgeChunk.document_id,
            KnowledgeChunk.chunk_index,
        )
        .all()
    )

    if not chunks:
        return []

    documents_by_id = {doc.id: doc for doc in documents}

    return [
        _build_evidence_item(
            chunk=chunk,
            document=documents_by_id[chunk.document_id],
            condition=condition,
        )
        for chunk in chunks
    ]