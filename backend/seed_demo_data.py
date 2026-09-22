# ============================================================
# SEED DEMO DATA — populated Maharashtra tomato farms
# ============================================================
#
# Idempotent: skips if any demo farm already exists.
#
# Usage:
#     python seed_demo_data.py
#
# Creates:
#     - 1 demo farmer
#     - 8 farms across Maharashtra tomato districts
#     - 8 crop seasons (Tomato)
#     - ~3 health reports per farm (24 total)
#       with varied conditions and locations
#
# No weather/risk/advisory pipeline runs here — this script
# only inserts the base rows so hotspot clustering has data
# to work with. Run /health-reports normally for full reports.
# ============================================================

from datetime import datetime, timedelta
import random

from database import (
    SessionLocal,
    Farmer,
    Farm,
    Crop,
    CropSeason,
    HealthReport,
    AIPrediction,
    RiskAssessment,
    Advisory,
)


DEMO_EMAIL = "demo@demo.tomato-village"

DISTRICTS = [
    # (district, latitude, longitude, condition, risk_level, risk_score)
    ("Nashik",      19.9975, 73.7898, "Late Blight",           "HIGH",     72.0),
    ("Pune",        18.5204, 73.8567, "Early Blight",          "HIGH",     68.0),
    ("Satara",      17.6805, 74.0183, "Spotted Wilt Virus",    "MODERATE", 45.0),
    ("Solapur",     17.6599, 75.9064, "Leaf Miner",            "MODERATE", 38.0),
    ("Ahmednagar",  19.0948, 74.7480, "Potassium Deficiency",  "HIGH",     65.0),
    ("Kolhapur",    16.7050, 74.2433, "Late Blight",           "CRITICAL", 82.0),
    ("Sangli",      16.8524, 74.5815, "Nitrogen Deficiency",   "MODERATE", 40.0),
    ("Latur",       18.4088, 76.5604, "Healthy",               "LOW",      5.0),
]


def _demo_farm_exists(db) -> bool:
    existing = (
        db.query(Farmer)
        .filter(Farmer.email == DEMO_EMAIL)
        .first()
    )
    return existing is not None


def seed(db) -> dict:
    summary = {
        "skipped": False,
        "farms_created": 0,
        "seasons_created": 0,
        "reports_created": 0,
        "predictions_created": 0,
        "risk_created": 0,
    }

    if _demo_farm_exists(db):
        summary["skipped"] = True
        return summary

    # --------------------------------------------------------
    # Farmer
    # --------------------------------------------------------

    farmer = Farmer(
        name="Demo Farmer",
        phone="0000000001",
        email=DEMO_EMAIL,
        preferred_language="English",
    )
    db.add(farmer)
    db.flush()

    # --------------------------------------------------------
    # Crop: Tomato (must exist)
    # --------------------------------------------------------

    tomato = (
        db.query(Crop)
        .filter(Crop.name == "Tomato")
        .first()
    )
    if not tomato:
        raise RuntimeError(
            "Crop 'Tomato' not found. Create it before seeding."
        )

    # --------------------------------------------------------
    # Farms + Seasons + Reports
    # --------------------------------------------------------

    now = datetime.utcnow()

    for district, lat, lon, condition, risk_level, risk_score in DISTRICTS:

        farm = Farm(
            farmer_id=farmer.id,
            farm_name=f"{district} Demo Farm",
            latitude=lat,
            longitude=lon,
            district=district,
            state="Maharashtra",
        )
        db.add(farm)
        db.flush()
        summary["farms_created"] += 1

        season = CropSeason(
            farm_id=farm.id,
            crop_id=tomato.id,
            variety="Local Tomato",
            planting_date=(now - timedelta(days=45)).date(),
            expected_harvest_date=(now + timedelta(days=75)).date(),
            status="ACTIVE",
        )
        db.add(season)
        db.flush()
        summary["seasons_created"] += 1

        # 3 reports per farm — small jitter around district center
        for i in range(3):

            jitter_lat = lat + random.uniform(-0.01, 0.01)
            jitter_lon = lon + random.uniform(-0.01, 0.01)

            days_ago = random.randint(1, 10)
            reported_at = now - timedelta(days=days_ago)

            report = HealthReport(
                farm_id=farm.id,
                crop_season_id=season.id,
                latitude=jitter_lat,
                longitude=jitter_lon,
                source="FARMER",
                status="COMPLETED",
                reported_at=reported_at,
            )
            db.add(report)
            db.flush()
            summary["reports_created"] += 1

            prediction = AIPrediction(
                health_report_id=report.id,
                model_name="tomato-disease-v1",
                model_version="1.0",
                prediction_type="CLASSIFICATION",
                predicted_class=condition,
                confidence=round(random.uniform(0.90, 0.99), 4),
                prediction_data={"disease": condition},
            )
            db.add(prediction)
            summary["predictions_created"] += 1

            risk = RiskAssessment(
                health_report_id=report.id,
                risk_score=round(
                    risk_score + random.uniform(-5, 5), 1
                ),
                risk_level=risk_level,
                calculation_method="rule-engine-v1",
                factors=[],
            )
            db.add(risk)
            summary["risk_created"] += 1

            # ----------------------------------------------------
            # Advisory (so officer view + farmer view look complete)
            # ----------------------------------------------------

            try:
                from advisory_engine import generate_advisory

                advisory_result = generate_advisory(
                    disease=condition,
                    risk_level=risk_level,
                    confidence=0.95,
                    weather_snapshot={},
                )

                advisory = Advisory(
                    health_report_id=report.id,
                    language="English",
                    risk_level=risk_level,
                    advisory_text=advisory_result["summary"],
                    model_name=advisory_result["engine"]["name"],
                    model_version=advisory_result["engine"]["version"],
                    sources=advisory_result["sources"],
                )
                db.add(advisory)
                summary["advisories_created"] = summary.get("advisories_created", 0) + 1

            except Exception as e:
                print(f"Advisory skipped for report {report.id}: {e}")

    return summary


def main():
    db = SessionLocal()
    try:
        result = seed(db)
        db.commit()

        print("Seed complete.")
        print()
        for k, v in result.items():
            print(f"  {k:<22} {v}")

        if result.get("skipped"):
            print()
            print("Demo data already exists — skipped.")

    except Exception as e:
        db.rollback()
        print(f"Seed failed — rolled back. Reason: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()