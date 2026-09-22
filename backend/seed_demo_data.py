# ============================================================
# SEED DEMO DATA — extended Maharashtra coverage
# ============================================================
#
# Idempotent: skips if any demo farm already exists.
#
# Usage:
#     python seed_demo_data.py
#
# To re-seed from scratch:
#     1. Delete the demo farmer via SQL
#     2. Re-run this script
#
# See the DELETE statements at the bottom of this file
# for the exact cleanup SQL.
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

# ------------------------------------------------------------
#  25 Maharashtra districts with tomato-relevant conditions
#  (district, lat, lon, condition, risk_level, risk_score)
# ------------------------------------------------------------
DISTRICTS = [
    # --- Original 8 ---
    ("Nashik",       19.9975, 73.7898, "Late Blight",           "HIGH",     72.0),
    ("Pune",         18.5204, 73.8567, "Early Blight",          "HIGH",     68.0),
    ("Satara",       17.6805, 74.0183, "Spotted Wilt Virus",    "MODERATE", 45.0),
    ("Solapur",      17.6599, 75.9064, "Leaf Miner",            "MODERATE", 38.0),
    ("Ahmednagar",   19.0948, 74.7480, "Potassium Deficiency",  "HIGH",     65.0),
    ("Kolhapur",     16.7050, 74.2433, "Late Blight",           "CRITICAL", 82.0),
    ("Sangli",       16.8524, 74.5815, "Nitrogen Deficiency",   "MODERATE", 40.0),
    ("Latur",        18.4088, 76.5604, "Healthy",               "LOW",      5.0),

    # --- 17 more tomato-growing districts ---
    ("Nagpur",       21.1458, 79.0882, "Early Blight",          "HIGH",     70.0),
    ("Aurangabad",   19.8762, 75.3433, "Late Blight",           "HIGH",     74.0),
    ("Amravati",     20.9320, 77.7523, "Leaf Miner",            "MODERATE", 42.0),
    ("Nanded",       19.1383, 77.3210, "Magnesium Deficiency",  "MODERATE", 48.0),
    ("Jalgaon",      21.0077, 75.5626, "Early Blight",          "MODERATE", 52.0),
    ("Akola",        20.7002, 77.0082, "Spotted Wilt Virus",    "HIGH",     66.0),
    ("Buldhana",     20.5292, 76.1842, "Late Blight",           "CRITICAL", 79.0),
    ("Washim",       20.1110, 77.1332, "Potassium Deficiency",  "HIGH",     63.0),
    ("Yavatmal",     20.3880, 78.1204, "Early Blight",          "MODERATE", 55.0),
    ("Beed",         18.9890, 75.7600, "Late Blight",           "HIGH",     71.0),
    ("Osmanabad",    18.1860, 76.0417, "Magnesium Deficiency",  "MODERATE", 47.0),
    ("Parbhani",     19.2704, 76.7741, "Nitrogen Deficiency",   "MODERATE", 43.0),
    ("Hingoli",      19.7170, 77.1490, "Leaf Miner",            "LOW",      28.0),
    ("Jalna",        19.8410, 75.8800, "Late Blight",           "HIGH",     69.0),
    ("Raigad",       18.5158, 73.1822, "Potassium Deficiency",  "MODERATE", 51.0),
    ("Ratnagiri",    16.9902, 73.3120, "Healthy",               "LOW",      8.0),
    ("Sindhudurg",   16.0000, 73.5000, "Early Blight",          "MODERATE", 44.0),
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
        "advisories_created": 0,
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
    # Crop
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

    now = datetime.utcnow()

    # Lazy import to avoid circular dependency
    from advisory_engine import generate_advisory

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

        # 3 reports per farm
        for i in range(3):

            # ~1km jitter around district center
            jitter_lat = lat + random.uniform(-0.008, 0.008)
            jitter_lon = lon + random.uniform(-0.008, 0.008)

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

            confidence = round(random.uniform(0.90, 0.99), 4)

            prediction = AIPrediction(
                health_report_id=report.id,
                model_name="tomato-disease-v1",
                model_version="1.0",
                prediction_type="CLASSIFICATION",
                predicted_class=condition,
                confidence=confidence,
                prediction_data={"disease": condition},
            )
            db.add(prediction)
            summary["predictions_created"] += 1

            jitter_risk = round(
                risk_score + random.uniform(-5, 5), 1
            )
            # clamp to 0-100
            jitter_risk = max(0.0, min(100.0, jitter_risk))

            risk = RiskAssessment(
                health_report_id=report.id,
                risk_score=jitter_risk,
                risk_level=risk_level,
                calculation_method="rule-engine-v1",
                factors=[],
            )
            db.add(risk)
            summary["risk_created"] += 1

            # Advisory (so officer view isn't empty)
            try:
                advisory_result = generate_advisory(
                    disease=condition,
                    risk_level=risk_level,
                    confidence=confidence,
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
                summary["advisories_created"] += 1
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
            print()
            print("To re-seed, run these SQL statements first:")
            print("  SELECT id FROM farmers WHERE email = '" + DEMO_EMAIL + "';")
            print("  -- then use that id in the DELETEs shown in the")
            print("  -- comment block at the top of this file.")

    except Exception as e:
        db.rollback()
        print(f"Seed failed — rolled back. Reason: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()