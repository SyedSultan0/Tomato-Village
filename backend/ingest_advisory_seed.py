# ============================================================
# ONE-OFF SCRIPT — run M4.1 ingestion
# ============================================================
#
# Usage:
#     python ingest_advisory_seed.py
#
# Idempotent: safe to re-run.
# ============================================================

from database import SessionLocal
from knowledge_ingestion import ingest_advisory_seed


def main() -> None:
    db = SessionLocal()

    try:
        summary = ingest_advisory_seed(db)

        db.commit()

        print("M4.1 ingestion complete.")
        print()

        for key, value in summary.items():
            print(f"  {key:<22} {value}")

        print()
        print("Committed.")

    except Exception as exc:
        db.rollback()
        print(f"Ingestion failed — rolled back. Reason: {exc}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()