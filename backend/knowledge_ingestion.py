# ============================================================
# KNOWLEDGE INGESTION — M4.1
# ============================================================
#
# Seeds KnowledgeDocument + KnowledgeChunk rows from
# advisory_data.json.
#
# Scope (deliberately narrow):
#   - creates Condition rows if missing
#   - creates KnowledgeDocument rows if missing
#   - creates KnowledgeChunk rows if missing
#
# Out of scope:
#   - embeddings
#   - vector database
#   - retrieval
#   - LLM
#   - CropCondition linking
#
# Idempotent: re-running does not create duplicates.
# ============================================================

import json
from pathlib import Path
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

BASE_DIR = Path(__file__).resolve().parent
ADVISORY_DATA_FILE = BASE_DIR / "advisory_data.json"

SEED_SOURCE_TYPE = "advisory_seed"
SEED_LANGUAGE = "English"
SEED_VERSION = "1.0"

# Map advisory_data category → Condition.condition_type
#
# The advisory JSON currently uses these categories:
#   disease, pest, nutrient_deficiency, healthy
#
# Additional aliases are tolerated so the ingestion does not
# break when the knowledge corpus expands.
CATEGORY_TO_CONDITION_TYPE = {
    # Disease
    "disease": "DISEASE",
    "fungal_disease": "DISEASE",
    "viral_disease": "DISEASE",
    "bacterial_disease": "DISEASE",

    # Pest
    "pest": "PEST",
    "insect": "PEST",
    "insect_pest": "PEST",

    # Nutrient deficiency
    "deficiency": "DEFICIENCY",
    "nutrient_deficiency": "DEFICIENCY",

    # Healthy / other
    "healthy": "OTHER",
    "other": "OTHER",
}


# ============================================================
# LOAD SOURCE DATA
# ============================================================

def _load_advisory_data() -> dict[str, Any]:
    if not ADVISORY_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Advisory data file not found: {ADVISORY_DATA_FILE}"
        )

    with open(ADVISORY_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_category(value: str) -> str:
    """
    Normalize category strings so small formatting differences
    do not break the lookup.
    """
    return (
        value.strip().lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


# ============================================================
# HELPERS
# ============================================================

def _get_or_create_condition(
    db: Session,
    name: str,
    condition_type: str,
) -> tuple[Condition, bool]:
    """
    Return (Condition, created).

    created=True only when this call inserted a new row.
    """

    existing = (
        db.query(Condition)
        .filter(Condition.name == name)
        .first()
    )

    if existing:
        return existing, False

    condition = Condition(
        name=name,
        condition_type=condition_type,
    )

    db.add(condition)
    db.flush()  # assigns id without committing

    return condition, True


def _get_tomato_crop(db: Session) -> Crop:
    crop = (
        db.query(Crop)
        .filter(Crop.name == "Tomato")
        .first()
    )

    if not crop:
        raise RuntimeError(
            "Crop 'Tomato' not found in crops table. "
            "Create it before running ingestion."
        )

    return crop


def _document_exists(
    db: Session,
    title: str,
) -> bool:
    return (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.title == title,
            KnowledgeDocument.source_type == SEED_SOURCE_TYPE,
        )
        .first()
        is not None
    )


def _build_document_title(model_label: str) -> str:
    return f"{model_label} — Advisory Knowledge"


def _build_chunk_text(risk_entry: dict[str, Any]) -> str:
    """
    Concatenate the four advisory sections into readable text.

    This is what will be embedded / retrieved in M4.2+.
    """

    parts = []

    summary = risk_entry.get("summary")
    if summary:
        parts.append(f"Summary: {summary}")

    for field, label in [
        ("immediate_actions", "Immediate actions"),
        ("prevention", "Prevention"),
        ("monitoring", "Monitoring"),
    ]:
        values = risk_entry.get(field)

        if not values:
            continue

        if isinstance(values, str):
            parts.append(f"{label}: {values}")
            continue

        bullets = "\n".join(
            f"- {item}" for item in values
            if isinstance(item, str)
        )

        if bullets:
            parts.append(f"{label}:\n{bullets}")

    return "\n\n".join(parts)


def _build_chunk_metadata(
    condition: Condition,
    condition_entry: dict[str, Any],
    risk_level: str,
) -> dict[str, Any]:
    """
    Metadata stored on each KnowledgeChunk.

    Kept JSON-serializable.
    """

    return {
        "condition_id": condition.id,
        "condition_name": condition.name,
        "condition_type": condition.condition_type,
        "advisory_condition_key": condition_entry.get("condition_id"),
        "model_label": condition_entry.get("model_label"),
        "category": condition_entry.get("category"),
        "cause": condition_entry.get("cause"),
        "risk_level": risk_level,
        "source": condition_entry.get("source"),
        "source_reference": condition_entry.get("source_reference", []),
        "display_source": condition_entry.get("display_source"),
        "seed_source_type": SEED_SOURCE_TYPE,
        "seed_version": SEED_VERSION,
    }


# ============================================================
# MAIN ENTRY
# ============================================================

def ingest_advisory_seed(db: Session) -> dict[str, int]:
    """
    Populate Condition + KnowledgeDocument + KnowledgeChunk
    rows from advisory_data.json.

    Idempotent: existing rows are reused.
    Caller is responsible for committing or rolling back.
    """

    data = _load_advisory_data()

    if "advisories" not in data:
        raise ValueError(
            "advisory_data.json is missing the 'advisories' key."
        )

    advisories = data["advisories"]

    # --------------------------------------------------------
    # Pre-flight: confirm every category is mappable
    # --------------------------------------------------------
    #
    # Fail once, with all unknown categories listed, rather
    # than failing partway through ingestion.
    # --------------------------------------------------------

    unknown_categories = set()

    for entry in advisories:
        raw = entry.get("category")

        if not raw:
            raise ValueError(
                f"Advisory entry missing 'category': "
                f"{entry.get('model_label', '?')}"
            )

        normalized = _normalize_category(raw)

        if normalized not in CATEGORY_TO_CONDITION_TYPE:
            unknown_categories.add(normalized)

    if unknown_categories:
        raise ValueError(
            "Unknown advisory categories: "
            f"{sorted(unknown_categories)}. "
            "Add them to CATEGORY_TO_CONDITION_TYPE."
        )

    tomato_crop = _get_tomato_crop(db)

    summary = {
        "conditions_created": 0,
        "conditions_reused": 0,
        "documents_created": 0,
        "documents_skipped": 0,
        "chunks_created": 0,
    }

    for condition_entry in advisories:

        model_label = condition_entry.get("model_label")
        category = condition_entry.get("category")

        if not model_label or not category:
            raise ValueError(
                f"Advisory entry missing model_label or category: "
                f"{condition_entry}"
            )

        condition_type = CATEGORY_TO_CONDITION_TYPE[
            _normalize_category(category)
        ]

        # ----------------------------------------------------
        # Condition
        # ----------------------------------------------------

        condition, created = _get_or_create_condition(
            db=db,
            name=model_label,
            condition_type=condition_type,
        )

        if created:
            summary["conditions_created"] += 1
        else:
            summary["conditions_reused"] += 1

        # ----------------------------------------------------
        # Document
        # ----------------------------------------------------

        title = _build_document_title(model_label)

        if _document_exists(db, title):
            summary["documents_skipped"] += 1
            continue

        document = KnowledgeDocument(
            title=title,
            source=condition_entry.get("display_source")
                or condition_entry.get("source"),
            source_type=SEED_SOURCE_TYPE,
            crop_id=tomato_crop.id,
            condition_id=condition.id,
            language=SEED_LANGUAGE,
            version=SEED_VERSION,
        )

        db.add(document)
        db.flush()  # assigns document.id

        summary["documents_created"] += 1

        # ----------------------------------------------------
        # Chunks — one per risk level
        # ----------------------------------------------------

        risk_levels = condition_entry.get("risk_levels", {})

        for index, risk_level in enumerate(
            ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        ):
            risk_entry = risk_levels.get(risk_level)

            if not risk_entry:
                continue

            chunk = KnowledgeChunk(
                document_id=document.id,
                chunk_text=_build_chunk_text(risk_entry),
                chunk_index=index,
                chunk_metadata=_build_chunk_metadata(
                    condition=condition,
                    condition_entry=condition_entry,
                    risk_level=risk_level,
                ),
                embedding_reference=None,
            )

            db.add(chunk)
            summary["chunks_created"] += 1

    return summary