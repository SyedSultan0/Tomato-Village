# ============================================================
# TEST — M4.1 ingestion
# ============================================================
#
# Run from backend/:
#     pytest test_knowledge_ingestion.py -v
#
# This test creates real rows in the database.
# It rolls back at the end, so the DB state is unchanged.
# ============================================================

from database import (
    SessionLocal,
    Condition,
    KnowledgeDocument,
    KnowledgeChunk,
)
from knowledge_ingestion import (
    ingest_advisory_seed,
    SEED_SOURCE_TYPE,
)


EXPECTED_CONDITIONS = {
    "Late Blight",
    "Early Blight",
    "Leaf Miner",
    "Spotted Wilt Virus",
    "Magnesium Deficiency",
    "Nitrogen Deficiency",
    "Potassium Deficiency",
    "Healthy",
}


def test_ingest_creates_conditions_documents_chunks():
    db = SessionLocal()

    try:
        summary = ingest_advisory_seed(db)

        # ----------------------------------------------------
        # Conditions
        # ----------------------------------------------------

        conditions = (
            db.query(Condition)
            .filter(Condition.name.in_(EXPECTED_CONDITIONS))
            .all()
        )

        assert len(conditions) == 8, (
            f"Expected 8 conditions, found {len(conditions)}"
        )

        # ----------------------------------------------------
        # Documents
        # ----------------------------------------------------

        documents = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.source_type == SEED_SOURCE_TYPE,
            )
            .all()
        )

        assert len(documents) == 8, (
            f"Expected 8 knowledge documents, "
            f"found {len(documents)}"
        )

        # Every document must be linked to a condition and Tomato
        for doc in documents:
            assert doc.condition_id is not None
            assert doc.crop_id is not None

        # ----------------------------------------------------
        # Chunks
        # ----------------------------------------------------

        for doc in documents:
            chunks = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id == doc.id)
                .order_by(KnowledgeChunk.chunk_index)
                .all()
            )

            assert len(chunks) == 4, (
                f"Document '{doc.title}' should have 4 chunks, "
                f"found {len(chunks)}"
            )

            risk_levels = [
                chunk.chunk_metadata.get("risk_level")
                for chunk in chunks
            ]

            assert risk_levels == [
                "LOW",
                "MODERATE",
                "HIGH",
                "CRITICAL",
            ]

            for chunk in chunks:
                assert chunk.chunk_text
                assert chunk.embedding_reference is None
                assert chunk.chunk_metadata["condition_id"] == doc.condition_id
                assert chunk.chunk_metadata["seed_source_type"] == SEED_SOURCE_TYPE

        # ----------------------------------------------------
        # Idempotency — run again, no duplicates
        # ----------------------------------------------------

        second_summary = ingest_advisory_seed(db)

        assert second_summary["documents_created"] == 0
        assert second_summary["documents_skipped"] == 8
        assert second_summary["chunks_created"] == 0

        # ----------------------------------------------------
        # Summary sanity
        # ----------------------------------------------------

        assert summary["documents_created"] == 8
        assert summary["chunks_created"] == 32

    finally:
        db.rollback()
        db.close()